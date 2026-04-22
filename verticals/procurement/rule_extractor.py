"""
verticals/procurement/rule_extractor.py — Procurement 판단 엔진

land_dispute와 동일한 구조 (hold_check → evidence → score → output).
domain isolation 적용됨.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

from .schema import ProcurementCase

_RULES_PATH = Path(__file__).parent / "rules.yaml"


def _load_rules() -> dict:
    with open(_RULES_PATH) as f:
        return yaml.safe_load(f)


@dataclass
class DecisionOutput:
    status:        str            # "ALLOW" | "HOLD"
    score:         float
    confidence:    str            # "high" | "medium" | "low"
    conclusion:    str
    win_prob_pct:  Optional[int]
    evidence_layer: list = field(default_factory=list)
    reasoning:     list  = field(default_factory=list)
    risks:         list  = field(default_factory=list)
    actions:       list  = field(default_factory=list)
    hold_reasons:  list  = field(default_factory=list)
    applied_rules: list  = field(default_factory=list)
    conflict_resolution: dict = field(default_factory=dict)
    # {"selected": [...], "suppressed": [...], "fallback_used": bool, "reason": "..."}


@dataclass
class EvidenceItem:
    rule_id:       str
    effect:        float
    reason:        str
    source_pattern: str
    reasoning:     str


def _check_holds(case: ProcurementCase, hold_conditions: list) -> list[dict]:
    triggered = []
    for hc in hold_conditions:
        cond = hc["condition"]
        hit  = False
        if cond == "supplier_id == null":
            hit = case.supplier_id is None
        elif cond == "contract_value == null AND dispute_type == \"payment\"":
            hit = case.contract_value is None and case.dispute_type == "payment"
        if hit:
            triggered.append(hc)
    return triggered


def _eval_condition(case: ProcurementCase, condition: dict) -> bool:
    for field_name, expected in condition.items():
        actual = getattr(case, field_name, None)
        if isinstance(expected, str) and expected.startswith(">="):
            threshold = float(expected.split(">=")[1].strip())
            if actual is None or actual < threshold:
                return False
        elif isinstance(expected, str) and expected.startswith("<"):
            threshold = float(expected.split("<")[1].strip())
            if actual is None or actual >= threshold:
                return False
        else:
            if actual != expected:
                return False
    return True


def _build_evidence(case: ProcurementCase, rules: list) -> tuple[float, list[EvidenceItem]]:
    score    = 0.0
    evidence = []
    for rule in rules:
        # INTERACTION layer rules는 _extract_interactions에서만 처리
        if rule.get("layer") == "INTERACTION" or rule.get("id", "").startswith("INT-"):
            continue
        cond = rule.get("condition", {})
        if not _eval_condition(case, cond):
            continue
        score += rule["effect"]
        triggered = [f"{k}={cond[k]}" for k in cond if getattr(case, k, None) == cond[k]]
        reasoning = f"케이스 필드 매칭: {', '.join(triggered)}" if triggered else rule["reason"]
        evidence.append(EvidenceItem(
            rule_id        = rule["id"],
            effect         = rule["effect"],
            reason         = rule["reason"],
            source_pattern = rule.get("source_pattern", ""),
            reasoning      = reasoning,
        ))
    return round(score, 3), evidence


def _select_actions(score: float, actions_map: dict) -> list[str]:
    if score >= 0.5:
        return actions_map.get("high_plaintiff_advantage", [])
    if score >= 0.2:
        return actions_map.get("moderate_plaintiff_advantage", [])
    if score > -0.2:
        return actions_map.get("neutral", [])
    return actions_map.get("defendant_advantage", [])


def _extract_interactions(case: ProcurementCase, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    """
    단일 rule hit → 복합 interaction feature 추출.

    조건: 이미 매칭된 evidence rule들의 조합으로만 생성.
    (데이터 없는 interaction은 만들지 않음)
    """
    hit_rules = {ev.rule_id for ev in evidence}
    interactions = []

    # rule hit 외에 case 필드로도 감지 (dispute_type이 단일이어도 복합 신호 가능)
    del_hits  = (any(r.startswith("PROC-DEL") for r in hit_rules)
                 or case.dispute_type == "delivery_delay")
    qual_hits = (any(r.startswith("PROC-QUAL") for r in hit_rules)
                 or case.dispute_type == "quality"
                 or case.inspection_passed is False
                 or (getattr(case, "defect_rate_pct", None) is not None))
    pay_hits  = (any(r.startswith("PROC-PAY") for r in hit_rules)
                 or case.dispute_type == "payment"
                 or case.payment_overdue is True)

    # DEL + QUAL → shared_fault 신호
    if del_hits and qual_hits:
        interactions.append(EvidenceItem(
            rule_id        = "INT-DEL-QUAL",
            effect         = -0.05,   # shared로 당기는 방향 (양쪽 책임)
            reason         = "납기지연 + 품질 복합 — 공동 책임 신호",
            source_pattern = "PROC-DEL-* AND PROC-QUAL-*",
            reasoning      = "납기 지연과 품질 이슈 동시 발생은 buyer/supplier 공동 책임 구조 가능성 높음",
        ))

    # DEL + PAY → 납기지연으로 인한 대금 보류
    if del_hits and pay_hits:
        interactions.append(EvidenceItem(
            rule_id        = "INT-DEL-PAY",
            effect         = +0.05,   # supplier 책임 강화 (납기 → 대금보류 인과)
            reason         = "납기지연 → 대금 보류 연쇄 — supplier 책임 강화",
            source_pattern = "PROC-DEL-* AND PROC-PAY-*",
            reasoning      = "납기 위반이 대금 지급 거절의 원인인 경우 supplier 귀책 가중",
        ))

    # QUAL + PAY → 품질 분쟁으로 인한 결제 보류
    if qual_hits and pay_hits:
        interactions.append(EvidenceItem(
            rule_id        = "INT-QUAL-PAY",
            effect         = -0.03,   # shared로 당기는 방향
            reason         = "품질 분쟁 + 대금 보류 — 협상 국면",
            source_pattern = "PROC-QUAL-* AND PROC-PAY-*",
            reasoning      = "품질 이슈로 인한 대금 보류는 양측 협상 필요 구조 — shared 가능성",
        ))

    return interactions


def evaluate(case: ProcurementCase) -> DecisionOutput:
    rules_data  = _load_rules()
    hold_conds  = rules_data.get("hold_conditions", [])
    rules       = rules_data.get("rules", [])
    actions_map = rules_data.get("actions", {})

    holds = _check_holds(case, hold_conds)
    if holds:
        return DecisionOutput(
            status       = "HOLD",
            score        = 0.0,
            confidence   = "low",
            conclusion   = "판단 보류 — 필수 정보 부족",
            win_prob_pct = None,
            hold_reasons = [{"id": h["id"], "reason": h["reason"], "resume": h["resume"]}
                            for h in holds],
        )

    score, evidence = _build_evidence(case, rules)

    # Interaction layer (단일 rule hit 조합으로 생성)
    interactions = _extract_interactions(case, evidence)
    if interactions:
        for ia in interactions:
            score += ia.effect
            evidence.append(ia)

    if not evidence:
        return DecisionOutput(
            status       = "HOLD",
            score        = 0.0,
            confidence   = "low",
            conclusion   = "판단 보류 — 매칭 룰 없음 (케이스 상세 정보 추가 필요)",
            win_prob_pct = None,
            hold_reasons = [{"id": "PROC-NO-RULE", "reason": "매칭 룰 없음",
                             "resume": "dispute_type + 핵심 필드 보완 후 재판단"}],
        )

    # ── Conflict Resolution ──────────────────────────────────────────────
    cr_result = None
    suppressed_rule_ids: list = []
    try:
        from verticals.procurement.conflict_resolver import resolve_conflicts
        all_rule_ids = [ev.rule_id for ev in evidence]
        cr_result = resolve_conflicts(all_rule_ids, case, rules_meta=rules)

        if cr_result.suppressed:
            suppressed_rule_ids = cr_result.suppressed
            # suppressed rule들의 effect를 score에서 제거하고 evidence에서 삭제
            suppressed_evidence = [ev for ev in evidence if ev.rule_id in suppressed_rule_ids]
            for ev in suppressed_evidence:
                score -= ev.effect
            evidence = [ev for ev in evidence if ev.rule_id not in suppressed_rule_ids]
            score = round(score, 3)
    except Exception:
        pass  # conflict resolution 실패해도 기존 판단 계속

    win_prob   = int(50 + score * 45)
    win_prob   = max(5, min(95, win_prob))
    confidence = "high" if len(evidence) >= 2 else "medium" if evidence else "low"

    if win_prob >= 65:
        conclusion = f"원고(구매자/공급자) 유리 — 승소 가능성 {win_prob}% 추정"
    elif win_prob >= 45:
        conclusion = f"중립 — 추가 증거에 따라 결과 달라짐 ({win_prob}%)"
    else:
        conclusion = f"상대방 측 유리 — 청구 리스크 있음 ({win_prob}%)"

    # conflict_resolution trace dict 구성
    cr_dict: dict = {}
    if cr_result is not None:
        cr_dict = {
            "selected":     cr_result.selected,
            "suppressed":   cr_result.suppressed,
            "fallback_used": cr_result.fallback_used,
            "reason":       cr_result.reason,
        }

    return DecisionOutput(
        status              = "ALLOW",
        score               = score,
        confidence          = confidence,
        conclusion          = conclusion,
        win_prob_pct        = win_prob,
        evidence_layer      = evidence,
        reasoning           = [ev.reasoning for ev in evidence],
        actions             = _select_actions(score, actions_map),
        hold_reasons        = [],
        applied_rules       = [f"{ev.rule_id} (effect={ev.effect:+.2f}): {ev.reason}"
                               for ev in evidence],
        conflict_resolution = cr_dict,
    )
