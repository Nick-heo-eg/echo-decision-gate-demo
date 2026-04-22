"""
verticals/procurement/judgment_adapter.py

procurement domain → Echo Legal OS judgment schema adapter.

입력:  case dict (app_legal.py _make_empty_case 형태)
출력:  {decision, risk, confidence, reason, unblock_action, missing_fields, input_hash}
       + 추가 필드 (gate_action, issues, evidence, next_step, negotiation 등)

절대 규칙:
  - 이 파일은 기존 runner/rule_extractor 수정 없이 mapping만 한다
  - 출력 스키마는 _validate_judgment_schema() 통과 보장
  - 실패 시 HOLD 반환 (fail-closed)
"""
from __future__ import annotations

import json
import hashlib
from typing import Any


# ── schema 필수 필드 (app_legal.py와 동기화) ──────────────────────────────────
_REQUIRED = {"decision", "risk", "confidence", "reason",
             "unblock_action", "missing_fields", "input_hash"}


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _confidence_to_float(conf: str | float | None) -> float:
    if isinstance(conf, float):
        return round(conf, 4)
    return {"high": 0.85, "medium": 0.55, "low": 0.25}.get(str(conf).lower(), 0.3)


def _risk_from_procurement(r: dict) -> str:
    """supply_risk + win_prob → unified risk level."""
    supply_risk = (r.get("decision_packet") or {}).get(
        "supply_risk",
        (r.get("negotiation") or {}).get("supply_risk", "")
    )
    win_prob = r.get("win_prob_pct", 50) or 50
    if supply_risk == "critical" or win_prob < 35:
        return "high"
    if supply_risk == "high" or win_prob < 55:
        return "medium"
    return "low"


def _extract_supplier(raw: str, scope: dict) -> str | None:
    """scope.suppliers 우선, 없으면 raw에서 '공급사: XXX' 패턴 추출."""
    suppliers = scope.get("suppliers") or []
    if suppliers:
        return suppliers[0]
    import re
    m = re.search(r"공급사[:：\s]+([A-Za-z0-9가-힣\-_]+)", raw)
    if m:
        return m.group(1).strip()
    return None


def _build_payload(case: dict) -> dict:
    """case dict → run_procurement payload."""
    scope     = case.get("scope", {})
    raw       = case.get("raw", "")
    case_type = scope.get("case_type", "") or ""

    # dispute_type 추론 (case_type 또는 raw 키워드)
    dispute_map = {
        "delivery": "delivery_delay",
        "납기":     "delivery_delay",
        "payment":  "payment",
        "지급":     "payment",
        "quality":  "quality",
        "품질":     "quality",
        "contract": "contract",
        "계약":     "contract",
    }
    dispute_type = "unknown"
    for kw, dt in dispute_map.items():
        if kw in case_type.lower() or kw in raw[:100]:
            dispute_type = dt
            break

    return {
        "vertical": "procurement",
        "case": {
            "case_id":         case["id"],
            "raw_description": raw,
            "dispute_type":    dispute_type,
            "supplier_id":     _extract_supplier(raw, scope),
            "supply_risk":     scope.get("supply_risk") or None,
            "urgency":         case.get("urgency", "NORMAL").lower()
                               if case.get("urgency", "NORMAL") != "NORMAL" else "medium",
        },
    }


def _missing_fields_from(payload: dict, r: dict) -> list[str]:
    c = payload.get("case", {})
    missing = []
    if not c.get("supplier_id"):
        missing.append("supplier_id")
    if c.get("dispute_type") == "unknown":
        missing.append("dispute_type")
    # hold rule id만 추가 (resume 문자열은 unblock_action에서 별도 처리)
    if r.get("status") == "HOLD":
        for h in r.get("hold_reasons", []):
            rule_id = h.get("id", "")
            if rule_id and rule_id not in missing:
                missing.append(rule_id)
    return missing


def _issues_from(r: dict) -> list[dict]:
    issues = []
    for risk_text in (r.get("risks") or [])[:3]:
        issues.append({"level": "HIGH", "text": str(risk_text)[:120]})
    for reasoning in (r.get("reasoning") or [])[:2]:
        if not issues:
            issues.append({"level": "MEDIUM", "text": str(reasoning)[:120]})
    return issues


def _evidence_from(r: dict) -> list[dict]:
    out = []
    for ev in (r.get("evidence") or [])[:5]:
        out.append({
            "citation":        ev.get("rule_id", ""),
            "authority_level": ev.get("layer", "rule"),
            "support_type":    ev.get("outcome_label", ""),
            "score":           round(float(ev.get("effect", 0)), 4),
            "text":            ev.get("reason", "")[:200],
        })
    return out


def _next_step(decision_key: str, r: dict) -> str:
    if decision_key == "ALLOW":
        neg = r.get("negotiation") or {}
        stance = neg.get("stance", "")
        if stance:
            return f"Proceed — stance: {stance}"
        return "Proceed to Action"
    hold_reasons = r.get("hold_reasons") or []
    if hold_reasons:
        return hold_reasons[0].get("resume", "Request Missing Info")
    return "Request Missing Info"


def _gate_action_from(r: dict) -> str:
    """procurement 결과 → EXECUTE / ESCALATE / BLOCK."""
    if r.get("status") != "ALLOW":
        return "ESCALATE"
    pkt = r.get("decision_packet") or {}
    if pkt.get("approval_status") == "APPROVAL_REQUIRED":
        return "ESCALATE"
    win_prob = r.get("win_prob_pct", 0) or 0
    if win_prob >= 60:
        return "EXECUTE"
    return "ESCALATE"


def _run_delivery_recovery(case: dict, procurement_result: dict) -> dict | None:
    """
    dispute_type == delivery_delay이고 ALLOW/ESCALATE일 때 delivery_recovery 체이닝.
    raw 텍스트에서 state 슬롯을 최대한 추출해 run_vertical 호출.
    실패 시 None 반환 (체이닝 실패가 판단 전체를 막지 않음).
    """
    try:
        import re
        from pathlib import Path
        import importlib.util as _ilu

        _rc_path = Path(__file__).resolve().parents[2] / ".." / "echo-gate" / "verticals" / "run_case.py"
        if not _rc_path.exists():
            return None
        _spec = _ilu.spec_from_file_location("run_case", _rc_path)
        _mod  = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)

        raw = case.get("raw", "").lower()

        # raw 텍스트 → delivery_recovery 슬롯 최대 추출
        def _bool(keywords: list[str]) -> bool | None:
            return True if any(k in raw for k in keywords) else None

        lt_match = re.search(r"lt\s*(\d+)\s*[w주]", raw)
        lt_weeks  = int(lt_match.group(1)) if lt_match else None
        # LT 증가 일수 추정: (새LT - 기존LT) * 7
        lt_inc_match = re.search(r"(\d+)\s*[w주]\s*(?:->|→|-)\s*(\d+)\s*[w주]", raw)
        shortage_days = None
        if lt_inc_match:
            shortage_days = (int(lt_inc_match.group(2)) - int(lt_inc_match.group(1))) * 7

        state = {
            "shortage_days":              shortage_days,
            "customer_due_days":          None,
            "bridge_stock_days":          None,
            "production_possible":        _bool(["생산 가능", "production ok"]),
            "fg_stock_available":         _bool(["재고 있", "fg stock", "재고 보유"]),
            "distributor_stock":          "unknown",
            "emergency_production_possible": None,
            "substitute_available":       _bool(["대체", "substitute", "alternative"]),
            "substitute_approval_needed": None,
            "air_freight_possible":       _bool(["항공", "air freight", "air"]),
            "partial_shipment_ok":        _bool(["분할 출하", "partial", "부분 출하"]),
            "penalty_exposure":           "mid",
            "customer_line_stop_risk":    _bool(["라인 정지", "line stop", "생산 중단"]),
            "customer_communication_done": False,
            "original_site_status":       "active",
            "new_site_status":            None,
        }
        # None 슬롯 제거 (run_vertical이 None을 missing으로 처리)
        state = {k: v for k, v in state.items() if v is not None}

        result = _mod.run_vertical(state, _mod.LIB_REC)
        return result
    except Exception:
        return None


def run_judgment(case: dict) -> dict:
    """
    procurement adapter 진입점.
    app_legal._run_judgment_for_domain()에서 domain=='procurement' 시 호출.
    """
    from verticals.procurement.runner import run_procurement

    input_str  = json.dumps({"id": case["id"], "raw": case.get("raw", ""),
                              "domain": "procurement"}, ensure_ascii=False, sort_keys=True)
    input_hash = _sha256(input_str)
    payload    = _build_payload(case)

    try:
        r = run_procurement(payload)

        status     = r.get("status", "HOLD")          # "ALLOW" | "HOLD"
        decision   = status                            # 그대로 사용
        decision_key = "ALLOW" if status == "ALLOW" else "HOLD"
        risk       = _risk_from_procurement(r)
        confidence = _confidence_to_float(r.get("confidence"))
        gate_action = _gate_action_from(r)

        # reason: conclusion + reasoning 첫 항목
        reason_parts = [r.get("conclusion", "")]
        if r.get("reasoning"):
            reason_parts.append(r["reasoning"][0])
        reason = " | ".join(p for p in reason_parts if p)[:300]

        # unblock_action
        hold_reasons = r.get("hold_reasons") or []
        if hold_reasons:
            unblock_action = hold_reasons[0].get("resume", "공급업체 정보 입력 후 재판단")
        elif decision_key == "ALLOW":
            neg = r.get("negotiation") or {}
            unblock_action = neg.get("opening_position", "Proceed to negotiation")
        else:
            unblock_action = "필수 정보 보완 후 재제출"

        missing_fields = _missing_fields_from(payload, r)
        issues         = _issues_from(r)
        evidence       = _evidence_from(r)

        j = {
            # schema 필수
            "decision":       decision,
            "risk":           risk,
            "confidence":     confidence,
            "reason":         reason,
            "unblock_action": unblock_action,
            "missing_fields": missing_fields,
            "input_hash":     input_hash,
            # 추가 필드
            "decision_key":   decision_key,
            "risk_level":     risk,
            "hold_reason":    hold_reasons[0].get("reason", "") if hold_reasons else "",
            "domain":         "procurement",
            "gate_action":    gate_action,
            "gate_reason":    f"win_prob={r.get('win_prob_pct')}% conf={r.get('confidence')}",
            "issues":         issues,
            "evidence":       evidence,
            "next_step":      _next_step(decision_key, r),
            "proof_id":       None,
            # procurement 전용 (UI에서 활용 가능)
            "win_prob_pct":   r.get("win_prob_pct"),
            "negotiation":    r.get("negotiation"),
            "approval_status": (r.get("decision_packet") or {}).get("approval_status"),
            "recovery":       None,
        }

        # delivery_delay + ALLOW/ESCALATE → delivery_recovery 체이닝
        dispute_type = payload.get("case", {}).get("dispute_type", "")
        if dispute_type == "delivery_delay" and decision_key in ("ALLOW", "HOLD"):
            rec = _run_delivery_recovery(case, r)
            if rec:
                j["recovery"] = {
                    "recovery_path":  (rec.get("matched_rule") or {}).get("recovery_path"),
                    "confidence":     (rec.get("matched_rule") or {}).get("confidence"),
                    "reason":         (rec.get("matched_rule") or {}).get("reason"),
                    "action_plan":    rec.get("action_plan", []),
                    "missing_t1":     rec.get("missing_t1", []),
                    "missing_t2":     rec.get("missing_t2", []),
                }
                # recovery action_plan을 issues에 반영
                for ap in rec.get("action_plan", [])[:2]:
                    lvl = "HIGH" if ap.get("priority") == "critical" else "MEDIUM"
                    j["issues"].append({"level": lvl, "text": f"[Recovery] {ap.get('action', '')}"})

        return j

    except Exception as e:
        return {
            "decision":       "HOLD",
            "risk":           "high",
            "confidence":     0.0,
            "reason":         f"procurement adapter 오류: {str(e)[:120]}",
            "unblock_action": "공급업체 정보 및 분쟁 유형 확인 후 재제출",
            "missing_fields": ["supplier_id", "dispute_type"],
            "input_hash":     input_hash,
            "decision_key":   "HOLD",
            "risk_level":     "high",
            "hold_reason":    "adapter error",
            "domain":         "procurement",
            "gate_action":    "ESCALATE",
            "gate_reason":    "adapter error",
            "issues":         [{"level": "HIGH", "text": str(e)[:120]}],
            "evidence":       [],
            "next_step":      "Request Missing Info",
            "proof_id":       None,
            "win_prob_pct":   None,
            "negotiation":    None,
            "approval_status": None,
        }
