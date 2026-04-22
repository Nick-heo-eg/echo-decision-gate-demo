"""
verticals/contract/gate.py

Contract Rule Gate — YAML-driven
새 계약 유형 추가 = contract_rules.yaml만 수정, 코드 수정 없음.

흐름:
  case dict → _match_contract_type() → _evaluate_clauses() → GateResult
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


_RULES_PATH = Path(__file__).parent / "contract_rules.yaml"


def _load() -> dict:
    with open(_RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class ClauseHit:
    clause_id:    str
    rule_id:      str
    gate_action:  str          # ALLOW | HOLD | REDIRECT
    owner:        str
    reason:       str
    fix_required: str | None   = None
    route_to:     str | None   = None
    financial_impact: str | None = None


@dataclass
class GateResult:
    decision:         str                    # ALLOW | HOLD | REDIRECT
    contract_type:    str
    owner:            str
    reason:           str
    execution_locked: bool
    hits:             list[ClauseHit] = field(default_factory=list)
    financial_impact: str | None      = None
    fix_owner:        str | None      = None   # HOLD → submitter
    route_owner:      str | None      = None   # REDIRECT → team


def _resolve(template: str, params: dict) -> str:
    """템플릿 문자열의 {key}를 params로 치환."""
    try:
        return template.format(**params)
    except KeyError:
        return template


def _eval_condition(cond: dict, case: dict) -> bool:
    field_name = cond.get("field", "")
    operator   = cond.get("operator", "eq")
    raw_value  = cond.get("value")
    actual     = case.get(field_name)

    # 템플릿 값 처리 ({threshold_days} 등은 case에서 가져옴)
    if isinstance(raw_value, str) and raw_value.startswith("{") and raw_value.endswith("}"):
        param_key = raw_value[1:-1]
        expected  = case.get(param_key)
    else:
        expected = raw_value

    if operator == "eq":
        return actual == expected
    if operator == "gt":
        return actual is not None and expected is not None and float(actual) > float(expected)
    if operator == "lt":
        return actual is not None and expected is not None and float(actual) < float(expected)
    if operator == "exists":
        return actual is not None
    if operator == "not_exists":
        return actual is None
    if operator == "contains":
        return expected in str(actual or "")
    return False


def _calc_financial_impact(formula: str, case: dict) -> str | None:
    """간단한 수식 계산 — 복잡한 수식은 None 반환."""
    try:
        result = eval(formula, {"__builtins__": {}}, case)  # noqa: S307
        return f"${result:,.0f}"
    except Exception:
        return None


def evaluate(case: dict) -> GateResult:
    """
    case dict → GateResult

    case 필수 필드:
      dispute_type: str  (contract_type trigger 매핑용)
      + contract_type별 필드 (contract_rules.yaml 참조)
    """
    rules_doc = _load()
    contract_types = rules_doc.get("contract_types", {})
    owners_map     = rules_doc.get("owners", {})
    gate_map       = rules_doc.get("gate_decisions", {})

    dispute_type = case.get("dispute_type", "")

    # 1. contract_type 매칭
    matched_type = None
    matched_def  = None
    for ctype, cdef in contract_types.items():
        triggers = cdef.get("triggers", [])
        for t in triggers:
            if t.get("dispute_type") == dispute_type:
                matched_type = ctype
                matched_def  = cdef
                break
        if matched_type:
            break

    if not matched_type:
        return GateResult(
            decision="HOLD",
            contract_type="unknown",
            owner="submitter",
            reason=f"계약 유형 미분류 (dispute_type={dispute_type!r}) — 수동 검토 필요",
            execution_locked=True,
        )

    # 2. clause 평가
    hits: list[ClauseHit] = []
    for clause in matched_def.get("clauses", []):
        clause_id = clause.get("id", "")
        for rule in clause.get("rules", []):
            rule_id = rule.get("id", "")

            # primary condition
            cond = rule.get("condition", {})
            if not _eval_condition(cond, case):
                continue

            # and_condition (선택)
            and_cond = rule.get("and_condition")
            if and_cond and not _eval_condition(and_cond, case):
                continue

            # financial impact
            fin_formula = rule.get("financial_impact_formula")
            fin_impact  = _calc_financial_impact(fin_formula, case) if fin_formula else None

            hits.append(ClauseHit(
                clause_id       = clause_id,
                rule_id         = rule_id,
                gate_action     = rule.get("gate_action", "HOLD"),
                owner           = rule.get("owner", "submitter"),
                reason          = rule.get("reason", ""),
                fix_required    = rule.get("fix_required"),
                route_to        = rule.get("route_to"),
                financial_impact= fin_impact,
            ))

    if not hits:
        return GateResult(
            decision="ALLOW",
            contract_type=matched_type,
            owner="submitter",
            reason="모든 조항 검토 통과 — 진행 가능",
            execution_locked=False,
            hits=[],
        )

    # 3. 최종 결정 (우선순위: REDIRECT > HOLD > ALLOW)
    priority = {"REDIRECT": 3, "HOLD": 2, "ALLOW": 1}
    hits.sort(key=lambda h: priority.get(h.gate_action, 0), reverse=True)
    top = hits[0]

    decision  = top.gate_action
    gate_cfg  = gate_map.get(decision, {})
    owner_cfg = owners_map.get(top.owner, {})

    # 재무 영향: 첫 번째 hit에서 가져옴
    fin_impact = next((h.financial_impact for h in hits if h.financial_impact), None)

    return GateResult(
        decision         = decision,
        contract_type    = matched_type,
        owner            = top.owner,
        reason           = top.reason,
        execution_locked = gate_cfg.get("execution_locked", True),
        hits             = hits,
        financial_impact = fin_impact,
        fix_owner        = "submitter" if decision == "HOLD" else None,
        route_owner      = top.route_to if decision == "REDIRECT" else None,
    )
