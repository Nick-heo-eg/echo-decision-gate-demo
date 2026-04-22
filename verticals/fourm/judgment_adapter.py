"""
verticals/fourm/judgment_adapter.py — 4M Change Gate
4M 유형별 RACI + Assumption 강제 검증 + 비용 귀속 판단
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from .regulatory_gate import extract_regulatory_slots, regulatory_gate


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ── HIGH_RISK 판정 (YAML SSOT) ────────────────────────────────────────────────
def is_high_risk(slots: dict, meta: dict) -> tuple[bool, list[str]]:
    """
    high_risk_rules.yaml 기준으로 HIGH RISK 여부 판정.
    Returns (is_high_risk: bool, triggered_rules: list[str])
    """
    triggered = []
    ft   = meta.get("selected") or slots.get("change_type", "")
    pin  = meta.get("pin_map_changed", slots.get("pin_map_same", "UNKNOWN"))
    func = meta.get("functional_change", slots.get("functional_equivalence", "UNKNOWN"))
    comp = slots.get("comp_type", "unknown")

    if pin == "YES":
        triggered.append("HR-001: pin_map_changed=YES")
    if func == "YES":
        triggered.append("HR-002: functional_change=YES")
    if comp in ("trigger", "sensing", "protection"):
        triggered.append(f"HR-003: component_type={comp}")
    if ft == "M5_design":
        triggered.append("HR-004: fourm_type=M5_design")
    if ft in ("M1_material", "M6_supplier") and func == "UNKNOWN":
        triggered.append("HR-005: M1/M6 + functional_change=UNKNOWN")

    phase        = meta.get("phase", slots.get("phase", "UNKNOWN"))
    product_type = meta.get("product_type", slots.get("product_type", "UNKNOWN"))

    if phase == "PRE_MP":
        triggered.append("HR-006: phase=PRE_MP — 양산 전, 개발 검증 우선")
    if phase == "MP" and product_type == "EXISTING" and ft == "M5_design":
        triggered.append("HR-007: MP+EXISTING+M5 — 최고위험, 자동 ALLOW 금지")
    if phase == "MP" and product_type == "NEW":
        triggered.append("HR-008: MP+NEW — 신규 제품 양산 초기, 개발 책임 유지")

    # HR-009: M1 대체품 핀맵 미확인 → 개발 서명 강제 (INC-001, 2026-04-22)
    if ft == "M1_material" and pin not in ("YES",):
        triggered.append("HR-009: M1 대체품 핀맵 미확인 — 개발 서명 필수 (INC-001)")

    return bool(triggered), triggered


# ── 4M 유형 정의 ──────────────────────────────────────────────────────────────
_4M_TYPES = {
    "M1_material": ["부품 변경", "ic 교체", "대체품", "component change", "material change",
                    "passive 변경", "저항 변경", "콘덴서 변경", "부품 교체"],
    "M2_method":   ["공정 변경", "process change", "recipe 변경", "조건 변경", "순서 변경",
                    "method change"],
    "M3_machine":  ["설비 변경", "장비 변경", "machine change", "tool 변경", "라인 변경"],
    "M4_man":      ["작업자 변경", "운영 변경", "man change", "인원 변경", "교육 변경"],
    "M5_design":   ["설계 변경", "회로 변경", "design change", "spec 변경", "구조 변경"],
    "M6_supplier": ["공급사 변경", "supplier change", "dual source", "dual sourcing",
                    "업체 변경", "벤더 변경"],
}

# ── RACI 템플릿 (유형별) ──────────────────────────────────────────────────────
_RACI = {
    "M1_material": {
        "A": "Development",
        "R_primary": "Development",
        "R_support": ["SQE", "SDE", "Purchasing", "Reliability", "Environmental"],
        "C": ["OQA", "Manufacturing", "Strategy Purchasing"],
        "I": ["Marketing"],
        "rule": "부품 변경 최종 기능 보증 = Development 고정",
    },
    "M2_method": {
        "A": "Manufacturing",
        "R_primary": "Manufacturing",
        "R_support": ["Quality", "Reliability"],
        "C": ["Development", "SQE"],
        "I": ["Purchasing"],
        "rule": "공정 안정성 보증 = Manufacturing 고정",
    },
    "M3_machine": {
        "A": "Manufacturing",
        "R_primary": "Manufacturing",
        "R_support": ["Quality"],
        "C": ["Development", "Reliability", "SQE"],
        "I": ["Purchasing"],
        "rule": "생산 안정성 보증 = Manufacturing 고정",
    },
    "M4_man": {
        "A": "Manufacturing",
        "R_primary": "Manufacturing",
        "R_support": ["Quality"],
        "C": [],
        "I": ["Development", "Purchasing"],
        "rule": "운영 품질 유지 = Manufacturing 고정",
    },
    "M5_design": {
        "A": "Development",
        "R_primary": "Development",
        "R_support": ["Reliability"],
        "C": ["Quality", "Manufacturing", "SQE"],
        "I": ["Purchasing"],
        "rule": "제품 기능/성능 보증 = Development 절대 불변",
    },
    "M6_supplier": {
        "A": "Purchasing",
        "R_primary": "Purchasing",
        "R_support": ["SQE"],
        "C": ["Development", "Reliability", "Manufacturing", "Quality"],
        "I": [],
        "rule": "공급 안정성 = Purchasing (기능 영향 없을 때만)",
    },
}

# ── 고위험 부품 ───────────────────────────────────────────────────────────────
_HIGH_RISK_TYPES = {"trigger", "sensing", "protection"}
_COMP_TYPE_KW = {
    "trigger":    ["trigger", "트리거"],
    "sensing":    ["sensing", "sensor", "센서", "센싱"],
    "protection": ["protection", "보호", "tvs", "esd"],
    "logic":      ["logic", "로직", "mcu", "cpu", "gate ic"],
    "passive":    ["저항", "콘덴서", "capacitor", "resistor", "inductor", "인덕터"],
}

_PIN_YES   = ["pin-to-pin", "pin to pin", "핀 동일", "핀투핀", "동일 핀"]
_PIN_NO    = ["pin 다름", "핀 다름", "pin mismatch", "핀 변경", "pin map 변경", "핀맵 변경"]
_FUNC_SAME = ["기능 동일", "functional same", "동등 기능", "spec 동일", "기능동일"]
_FUNC_DIFF = ["기능 다름", "functional diff", "spec 다름", "동작 차이", "기능 차이"]
_VERIFIED  = ["검증 완료", "verified", "개발 확인", "개발 승인", "검증됨",
              "개발팀 확인", "개발팀 승인",
              "oq 완료", "pq 완료", "iq 완료", "sign-off 완료", "signoff 완료",
              "sqe 검증 완료", "품질팀 확인", "품질팀 승인", "품질 sign-off",
              "sqe 완료", "oqa 완료",
              "품질 검증 완료", "quality_validation_done", "내부 검증 완료",
              "manufacturing 검증 완료", "공정 검증 완료"]
_VERIFIED_BY_DEV = ["개발 확인", "개발 승인", "개발팀 확인", "개발팀 승인",
                    "개발팀 회로 재설계", "회로 재설계 완료", "개발 재설계"]
_PENDING   = ["검증 필요", "pending", "미검증", "검증 전", "개발 미확인"]

# ── 추가 슬롯 키워드 ──────────────────────────────────────────────────────────
_SUPPLIER_NEW      = ["신규 공급사", "new supplier", "품질 이력 없음", "신규업체", "이력 없음"]
_SUPPLIER_EXISTING = ["기존 공급사", "이력 있음", "approved supplier", "등록 공급사"]
_SQE_VERIFIED      = ["sqe 검증 완료", "sqe 완료", "sqe 승인", "sqe approved",
                      "공급사 심사 완료", "sqe sign-off", "sqe signoff"]
_SQE_SKIPPED       = ["sqe 생략", "sqe 스킵", "sqe skip", "sqe 검증 생략", "sqe 미수행",
                      "sqe 없이", "검증 생략"]
_CUST_APPROVED = ["고객 승인 완료", "고객사 승인", "customer approved", "고객 승인"]
_CUST_PENDING  = ["고객 승인 미완료", "고객 검토 중", "승인 대기", "customer pending", "고객사 검토 중"]
_WAIVER        = ["waiver", "웨이버", "조건부 합의", "조건부 진행 합의", "임시 승인"]
_FIRST_LOT     = ["초도품", "초도 lot", "first lot", "첫 lot", "initial lot"]
_SITE_CHANGE   = ["공장 변경", "사이트 변경", "site change", "생산지 변경", "거점 변경",
                  "다른 사이트", "공장 이전", "생산 거점 변경"]
_CUST_NOTIFIED = ["고객 통지 완료", "고객사 통지", "customer notified", "신고 완료", "통지 완료"]
# change_type 기반 고객 신고 선행 필수 유형
_PROCESS_SEQ_CHANGE = ["공정 순서", "작업 순서", "process sequence", "순서 조정", "작업 지시서 변경",
                       "wi 변경", "work instruction 변경", "공정 순서 변경"]
_PROCESS_ADD        = ["공정 추가", "process addition", "단계 추가", "스텝 추가",
                       "세척 공정 추가", "검사 공정 추가", "추가 공정"]

_PROCESS_FUNDAMENTAL = ["자동화 도입", "수작업 → 자동", "수작업에서 자동", "로봇 자동화",
                         "자동화 라인", "수작업 제거", "작업자 개입 제거",
                         "automation", "manual to auto", "공정 방식 변경"]
_CUSTOMER_IMPACT_UNKNOWN = ["고객 영향 여부 불명확", "영향 불명확", "영향 여부 미확인",
                             "신고 여부 불명확", "신고 필요 여부 미확인",
                             "담당자 구두", "구두 판단", "구두로"]

# ── M4 Internal Control 슬롯 키워드 ──────────────────────────────────────────
_M4_TRAINING   = ["ojt 완료", "교육 완료", "training completed", "훈련 완료", "교육 수료"]
_M4_CERTIFIED  = ["자격증", "certification", "자격 보유", "licensed", "자격 취득"]
_M4_NO_CERT    = ["자격증 없음", "무자격", "uncertified", "자격 미취득"]
_M4_SUPERVISED = ["감독 하에", "감독자", "supervision", "숙련자 감독", "이중 확인"]

# ── phase / product_type 키워드 ───────────────────────────────────────────────
_PHASE_PRE_MP  = ["pre-mp", "pre mp", "양산 전", "양산전", "개발 단계", "proto", "pilot", "선행"]
_PHASE_MP      = ["mp", "양산", "mass production", "양산 중", "양산중", "량산"]
_PRODUCT_NEW   = ["신규 제품", "new product", "신제품", "신규 모델", "new model"]
_PRODUCT_EXIST = ["기존 제품", "existing product", "기존 모델", "양산 중인 제품", "현행 제품"]


def _extract(raw: str) -> dict:
    r = raw.lower()

    def _kw(pos, neg=None):
        if any(k in r for k in pos): return "YES"
        if neg and any(k in r for k in neg): return "NO"
        return "UNKNOWN"

    # 4M 유형 감지
    change_type = "M1_material"  # default
    for ct, kws in _4M_TYPES.items():
        if any(k in r for k in kws):
            change_type = ct
            break

    # 부품 유형
    comp_type = "unknown"
    for ct, kws in _COMP_TYPE_KW.items():
        if any(k in r for k in kws):
            comp_type = ct
            break

    pin_map_same           = _kw(_PIN_YES, _PIN_NO)
    functional_equivalence = _kw(_FUNC_SAME, _FUNC_DIFF)
    supplier_claim         = any(k in r for k in ["supplier 보장", "공급사 보장", "데이터시트 확인"])

    # verification_status: 개발팀 서명 여부 구분
    verified_by_dev = any(k in r for k in _VERIFIED_BY_DEV)
    if any(k in r for k in _PENDING):
        verification_status = "PENDING"
    elif any(k in r for k in _VERIFIED):
        verification_status = "VERIFIED_DEV" if verified_by_dev else "VERIFIED_OTHER"
    else:
        verification_status = "PENDING"

    # 추가 슬롯
    supplier_new = (
        True  if any(k in r for k in _SUPPLIER_NEW) else
        False if any(k in r for k in _SUPPLIER_EXISTING) else
        None
    )
    sqe_verified  = any(k in r for k in _SQE_VERIFIED)
    sqe_skipped   = any(k in r for k in _SQE_SKIPPED)
    customer_approval = (
        "PENDING"  if any(k in r for k in _CUST_PENDING) else
        "APPROVED" if any(k in r for k in _CUST_APPROVED) else
        None
    )
    waiver_obtained = any(k in r for k in _WAIVER)
    first_lot       = any(k in r for k in _FIRST_LOT)

    # Site change / notification 슬롯
    site_change          = any(k in r for k in _SITE_CHANGE)
    customer_notified    = any(k in r for k in _CUST_NOTIFIED)
    process_seq_change        = any(k in r for k in _PROCESS_SEQ_CHANGE)
    process_add               = any(k in r for k in _PROCESS_ADD)
    process_fundamental_change  = any(k in r for k in _PROCESS_FUNDAMENTAL)
    customer_impact_unknown     = any(k in r for k in _CUSTOMER_IMPACT_UNKNOWN)

    # M4 Internal Control 슬롯
    m4_training_done  = any(k in r for k in _M4_TRAINING)
    m4_certified      = any(k in r for k in _M4_CERTIFIED) and not any(k in r for k in _M4_NO_CERT)
    m4_supervised     = any(k in r for k in _M4_SUPERVISED)

    # phase / product_type (키워드 없으면 UNKNOWN — fail-closed)
    if any(k in r for k in _PHASE_PRE_MP):
        phase = "PRE_MP"
    elif any(k in r for k in _PHASE_MP):
        phase = "MP"
    else:
        phase = "UNKNOWN"

    if any(k in r for k in _PRODUCT_NEW):
        product_type = "NEW"
    elif any(k in r for k in _PRODUCT_EXIST):
        product_type = "EXISTING"
    else:
        product_type = "UNKNOWN"

    return {
        "change_type":           change_type,
        "comp_type":             comp_type,
        "pin_map_same":          pin_map_same,
        "functional_equivalence": functional_equivalence,
        "verification_status":   verification_status,
        "verified_by_dev":       verified_by_dev,
        "supplier_claim":        supplier_claim,
        "supplier_new":          supplier_new,
        "sqe_verified":          sqe_verified,
        "sqe_skipped":           sqe_skipped,
        "customer_approval":     customer_approval,
        "waiver_obtained":       waiver_obtained,
        "first_lot":             first_lot,
        "m4_training_done":      m4_training_done,
        "m4_certified":          m4_certified,
        "m4_supervised":         m4_supervised,
        "site_change":           site_change,
        "customer_notified":     customer_notified,
        "process_seq_change":          process_seq_change,
        "process_add":                 process_add,
        "process_fundamental_change":   process_fundamental_change,
        "customer_impact_unknown":      customer_impact_unknown,
        "phase":                        phase,
        "product_type":                 product_type,
    }


def _resolve_owner(slots: dict) -> tuple[str, dict]:
    """
    4M 유형 기반 RACI 확정.
    M1/M6에서 기능 영향 있으면 Development로 override.
    """
    ct    = slots["change_type"]
    raci  = _RACI.get(ct, _RACI["M1_material"]).copy()
    owner = raci["A"]

    # Override: 부품/공급사 변경인데 pin/기능 영향 있으면 → Development
    if ct in ("M1_material", "M6_supplier"):
        if slots["pin_map_same"] == "NO" or slots["functional_equivalence"] in ("NO", "UNKNOWN"):
            owner = "Development"
            raci = {**_RACI["M1_material"],
                    "rule": f"[OVERRIDE] {ct} → 기능 영향 감지 → Development 책임으로 전환"}

    return owner, raci


def _check_customer_approval_chain(slots: dict) -> tuple[str, str, str] | None:
    """
    Permission layer: 고객 승인 체인 강제.
    state(검증) ≠ permission(승인) — 검증 완료만으로 ALLOW 불가.
    M5_design 은 고객사 신고/승인 의무. 기타 유형은 고객 승인 명시 시에만 체크.
    Returns (decision, reason, next_action) or None (체인 통과)
    """
    ctype = slots["change_type"]
    ca    = slots.get("customer_approval")
    waiver = slots.get("waiver_obtained", False)

    # 공정 추가 → 고객 승인 필수 (신고만으로 불충분)
    if slots.get("process_add") and ca != "APPROVED":
        if waiver:
            return ("CONDITIONAL_ALLOW",
                    "공정 추가 — 고객 승인 미완료 (Waiver 조건부)",
                    "고객 승인 후 정식 적용")
        return ("HOLD",
                "공정 추가 — 고객 승인 필요",
                "고객사 승인 완료 후 진행")

    # 고객 영향 불명확 + 미신고 → fail-closed (구두 판단 무효)
    if slots.get("customer_impact_unknown") and not slots.get("customer_notified"):
        return ("HOLD",
                "고객 영향 불명확 — 구두 판단 무효, 공식 신고 선행 필수",
                "고객사 공식 신고 및 영향 범위 확인 후 진행")

    # 공정 방식 근본 변경 (자동화 도입 등) → 고객 신고 선행 필수
    if slots.get("process_fundamental_change") and not slots.get("customer_notified"):
        return ("HOLD",
                "공정 방식 근본 변경 (자동화 등) — 고객 신고 선행 필수",
                "고객사 신고 완료 후 진행")

    # 공정 순서 변경 → change_type 기반 고객 신고 선행 필수 (impact 판단 이전)
    if slots.get("process_seq_change") and not slots.get("customer_notified"):
        return ("HOLD",
                "공정 순서 변경 — 고객 신고 선행 필수 (CTQ 흐름 변경 대상)",
                "고객사 신고 완료 후 진행")

    # site change → 고객 선행 통지 필수 (ALLOW = 실행 가능 상태 기준)
    if slots.get("site_change") and not slots.get("customer_notified"):
        if ca == "APPROVED":
            return None  # 승인까지 됐으면 통지 포함
        return ("HOLD",
                "생산 사이트 변경 — 고객 선행 통지 필요",
                "고객사 통지 완료 후 진행")

    # 고객 승인이 명시적으로 필요한 유형: M5는 무조건, 나머지는 ca가 명시된 경우만
    approval_required = (ctype == "M5_design") or (ca is not None)
    if not approval_required:
        return None

    if ca == "APPROVED":
        return None  # 승인 완료 → 통과

    if ca == "PENDING" or (ctype == "M5_design" and ca is None):
        if waiver:
            # waiver = 조건부 진행 — CONDITIONAL_ALLOW
            return ("CONDITIONAL_ALLOW",
                    "고객 승인 미완료 — Waiver 조건부 진행",
                    "Waiver 조건 이행 + 고객 공식 승인 병행 추진")
        return ("HOLD",
                "고객 승인 미완료 — 고객 승인 전 양산 불가",
                "고객 승인 또는 Waiver 확보 후 진행")

    return None


def _gate(slots: dict, owner: str) -> tuple[str, str, str]:
    """Returns (decision, reason, next_action)"""
    pin   = slots["pin_map_same"]
    func  = slots["functional_equivalence"]
    vst   = slots["verification_status"]
    ct    = slots["comp_type"]
    ctype = slots["change_type"]
    phase        = slots.get("phase", "UNKNOWN")
    product_type = slots.get("product_type", "UNKNOWN")

    # [PHASE GATE] PRE_MP — 모든 변경 개발 검증 우선
    if phase == "PRE_MP":
        return "REDIRECT_DEV", (
            f"PRE_MP 단계 — 양산 전 변경은 개발 검증 우선 ({ctype})"
        ), "개발팀 검증 완료 후 재제출"

    # [PHASE GATE] MP + EXISTING + M5 — 최고위험, 전수 검증
    if phase == "MP" and product_type == "EXISTING" and ctype == "M5_design":
        return "REDIRECT_DEV", (
            "MP 기존 제품 설계 변경 (HR-007) — ECN 발행 + 전수 검증 + 고객 승인 필수"
        ), "ECN 발행 → 개발/신뢰성/SQE 전수 검증 → 고객 승인"

    # [PHASE GATE] MP + NEW — 개발 책임 유지
    if phase == "MP" and product_type == "NEW" and ctype in ("M1_material", "M5_design", "M6_supplier"):
        if func in ("YES", "UNKNOWN") or pin in ("NO", "UNKNOWN"):
            return "REDIRECT_DEV", (
                "MP 신규 제품 양산 초기 + 기능 영향 불명확 — 개발 책임 유지"
            ), "개발팀 기능 영향 확인 후 재제출"

    # [HR-009] M1 대체품 — 핀맵 NO로 명시 안 되면 개발 서명 강제 (INC-001)
    if ctype == "M1_material" and pin not in ("YES",):
        if pin == "NO":
            return "REDIRECT_DEV", (
                "M1 핀맵 불일치 확인 — 개발팀 회로 검토 필수 (HR-009, INC-001)"
            ), "개발팀 핀맵 데이터시트 대조 → 서명 확보 후 재제출"
        # UNKNOWN
        return "REDIRECT_DEV", (
            "M1 대체품 핀맵 미확인 — 개발팀 직접 확인 필수 (HR-009, INC-001)"
        ), "개발팀 핀맵 데이터시트 대조 확인 → Pin-to-Pin 여부 명시 후 재제출"

    # [LAYER 0] 고위험 부품 — 고객 승인 완료 or waiver 시 면제
    if ct in _HIGH_RISK_TYPES:
        ca = slots.get("customer_approval")
        if ca == "APPROVED":
            pass  # 고객 승인 완료 → 신뢰성 검증 내포 → 통과
        elif ca == "PENDING" and slots.get("waiver_obtained"):
            pass  # waiver = 공급사 품질보증레터 조건부 → CONDITIONAL_ALLOW로 처리
        else:
            return "REDIRECT_DEV", f"{ct} 고위험 부품 → 신뢰성 검증 + 개발 검증 후 고객 승인 필요", "신뢰성 검증 → 고객 승인 후 진행"

    # [LAYER 1-M4] Internal Control Path — M4는 검증이 아니라 통제
    # Rule (2026-04-21 확정, Cases 010/035/045/051~055 기반):
    #   training=false → HOLD (라인 OJT 없으면 경력/자격 무관)
    #   training=true + certified=true → ALLOW
    #   training=true + certified=false → CONDITIONAL_ALLOW (감독 여부 무관)
    if ctype == "M4_man":
        if not slots.get("m4_training_done"):
            return "HOLD", "M4 라인 OJT 미완료 — 경력/자격 무관하게 투입 불가", "라인 OJT 완료 후 진행"
        if slots.get("m4_certified"):
            return "ALLOW", "M4 OJT 완료 + 자격증 보유 — 독립 작업 가능", "4M 승인 진행"
        return "CONDITIONAL_ALLOW", "M4 OJT 완료 + 자격증 없음 — 감독 하 조건부 투입", "감독자 배치 확인 후 제한 투입"

    # [LAYER 0-SQE] SQE 명시적 생략 → 고객 승인 무관하게 HOLD (절차 우회 차단)
    if slots.get("sqe_skipped"):
        return "HOLD", "SQE 검증 생략 명시 — 절차 우회 불가 (납기 사유 무효)", "SQE 검증 수행 후 진행"

    # [LAYER 1] State check — 검증 완료 여부 (state, not permission)
    if ctype in ("M2_method", "M3_machine"):
        if vst == "PENDING":
            return "HOLD", f"{ctype} 변경 — 품질 영향 검증 필요", "Manufacturing/Quality 검증 후 진행"
        # state 통과 → permission layer로 진입
    else:
        if vst == "PENDING":
            return "HOLD", "Assumption 미검증 — 검증 책임자 지정 후 진행", "검증 요청 / 진행 금지"
        if vst == "VERIFIED_OTHER" and ctype in ("M1_material", "M5_design", "M6_supplier"):
            # site_change는 고객 통지가 우선 이슈 — REDIRECT_DEV 면제, LAYER 2로 넘김
            if not slots.get("site_change"):
                return "REDIRECT_DEV", "검증 서명자 개발팀 아님 → 개발 확인 필수", "개발팀 서명 확보"

    # [LAYER 2] Permission check — 고객 승인 체인 (state와 독립)
    ca_result = _check_customer_approval_chain(slots)
    if ca_result is not None:
        return ca_result

    # [LAYER 3] M2/M3 — permission 통과 시 ALLOW (pin/func 체크 불필요)
    if ctype in ("M2_method", "M3_machine"):
        if vst == "PENDING":
            return "REDIRECT_MFG", (
                f"{ctype} 변경 — Manufacturing/Quality 검증 미완료"
            ), "Manufacturing 검증 완료 후 Gate 재진입"
        return "ALLOW", f"{ctype} 변경 검증 완료", "4M 승인 진행"

    # [LAYER 4] M6: SQE 검증 없으면 REDIRECT_SQE (fail-closed)
    if ctype == "M6_supplier":
        if not slots.get("sqe_verified"):
            if slots.get("supplier_new") is True:
                return "REDIRECT_SQE", "신규 공급사 — SQE 공급사 심사 선행 필수", "SQE 공급사 현장 심사 → 품질시스템 확인 → 승인"
            return "REDIRECT_SQE", "공급사 변경 — SQE 검증 미확인 (승인 범위 불명확)", "SQE 검증 완료 후 재제출"

    # [LAYER 5] pin/func 구조 체크 — 고객 승인 완료 시 면제 (승인 = 재설계 포함 증거)
    ca = slots.get("customer_approval")
    if ca != "APPROVED":
        if pin == "NO":
            return "REDIRECT_DEV", "Pin map 불일치 → 개발 검증 필수", "개발 검증 수행"
        if pin == "UNKNOWN" and ctype == "M1_material":
            return "HOLD", "Pin map UNKNOWN — 공급사/개발 확인 필요", "Pin map 확인 후 재제출"
        if func == "UNKNOWN":
            return "REDIRECT_DEV", "Functional equivalence 미확인 → 개발 검증 필수", "개발 검증 수행"

    first_lot_note = " (초도품 신뢰성 시험 필요)" if slots.get("first_lot") else ""
    return "ALLOW", "검증 완료 + 기능 동등 확인 + 고객 승인 완료", f"4M 승인 진행{first_lot_note}"


def _cost_owner(decision: str, slots: dict) -> dict:
    if decision == "ALLOW":
        return {"owner": "N/A", "type": "none"}
    vst = slots["verification_status"]
    if vst != "VERIFIED":
        return {"owner": "system(4M process)", "type": "process_failure_cost",
                "note": "Assumption 미관리 — 프로세스 실패"}
    if slots["pin_map_same"] == "NO" and not slots["supplier_claim"]:
        return {"owner": "purchasing + development", "type": "shared_cost",
                "note": "잘못된 정보 확정 전달"}
    if slots["supplier_claim"]:
        return {"owner": "supplier", "type": "claim",
                "note": "supplier 정보 오류 → 클레임 대상"}
    return {"owner": "development", "type": "engineering_quality_cost",
            "note": "개발 검증 미수행"}


def run_judgment(case: dict) -> dict:
    input_str  = json.dumps({"id": case["id"], "raw": case.get("raw", ""),
                              "domain": "fourm"}, ensure_ascii=False, sort_keys=True)
    input_hash = _sha256(input_str)
    raw        = case.get("raw", "")

    try:
        slots = _extract(raw)

        # UI에서 사용자가 명시 선택한 4M 유형 우선 적용 (책임 시스템)
        meta = case.get("fourm_meta", {})
        if meta.get("selected"):
            slots["change_type"] = meta["selected"]
        # UI 명시 pin/functional 선택 반영
        if meta.get("pin_map_changed") in ("YES", "NO"):
            slots["pin_map_same"] = "NO" if meta["pin_map_changed"] == "YES" else "YES"
        if meta.get("functional_change") in ("YES", "NO"):
            slots["functional_equivalence"] = "NO" if meta["functional_change"] == "YES" else "YES"
        # UI 명시 phase/product_type 반영 (텍스트 추출보다 우선)
        if meta.get("phase") in ("PRE_MP", "MP"):
            slots["phase"] = meta["phase"]
        if meta.get("product_type") in ("NEW", "EXISTING"):
            slots["product_type"] = meta["product_type"]

        owner, raci    = _resolve_owner(slots)
        decision, reason, next_action = _gate(slots, owner)

        # [REGULATORY GATE] Domain ALLOW 이후 출하 가능성 판단
        if decision == "ALLOW":
            reg_slots = extract_regulatory_slots(raw, slots["change_type"],
                                                 customer_approval=slots.get("customer_approval"))
            reg_result = regulatory_gate(reg_slots)
            if reg_result is not None:
                decision, reason, next_action = reg_result
                slots["_regulatory_hold"] = True

        cost           = _cost_owner(decision, slots)

        hr_flag, hr_rules = is_high_risk(slots, meta)
        risk = {"ALLOW": "low", "CONDITIONAL_ALLOW": "medium",
                "HOLD": "medium", "REDIRECT_DEV": "medium"}.get(decision, "medium")
        if hr_flag and decision in ("REDIRECT_DEV", "HOLD", "CONDITIONAL_ALLOW"):
            risk = "high"

        gate_action = {
            "ALLOW":              "EXECUTE",
            "CONDITIONAL_ALLOW":  "EXECUTE_WITH_CONDITIONS",
            "HOLD":               "ESCALATE",
            "REDIRECT_DEV":       "ESCALATE",
            "REDIRECT_MFG":       "REDIRECT",
            "REDIRECT_SQE":       "REDIRECT",
        }.get(decision, "ESCALATE")
        conf = {
            "ALLOW": 0.88, "CONDITIONAL_ALLOW": 0.72,
            "HOLD": 0.75, "REDIRECT_DEV": 0.82,
            "REDIRECT_MFG": 0.85, "REDIRECT_SQE": 0.85,
        }.get(decision, 0.5)

        missing = []
        if slots["pin_map_same"] == "UNKNOWN" and slots["change_type"] == "M1_material":
            missing.append("pin_map_same")
        if slots["functional_equivalence"] == "UNKNOWN":
            missing.append("functional_equivalence")
        if slots["verification_status"] == "PENDING":
            missing.append("verification_status")

        issues = [{"level": "HIGH" if risk == "high" else "MEDIUM",
                   "text": f"[4M:{slots['change_type']}] {reason}"}]
        if cost["type"] != "none":
            issues.append({"level": "MEDIUM",
                           "text": f"[Cost→{cost['owner']}] {cost['type']}"})

        return {
            "decision":       decision,
            "risk":           risk,
            "confidence":     conf,
            "reason":         reason,
            "unblock_action": next_action,
            "missing_fields": missing,
            "input_hash":     input_hash,
            "decision_key":   decision,
            "risk_level":     risk,
            "hold_reason":    reason if decision != "ALLOW" else "",
            "domain":         "fourm",
            "gate_action":    gate_action,
            "gate_reason":    (f"type={slots['change_type']} pin={slots['pin_map_same']} "
                               f"func={slots['functional_equivalence']} "
                               f"vst={slots['verification_status']} comp={slots['comp_type']}"),
            "issues":         issues,
            "evidence":       [],
            "next_step":      next_action,
            "proof_id":       None,
            # 4M 전용
            "fourm_type":     slots["change_type"],
            "fourm_slots":    slots,
            "fourm_classification": {
                "selected":      meta.get("selected", slots["change_type"]),
                "suggested":     meta.get("suggested", ""),
                "overridden":    meta.get("overridden", False),
                "override_reason": meta.get("reason", ""),
            },
            "high_risk": {
                "flag":    hr_flag,
                "rules":   hr_rules,
            },
            "raci": {
                "A":         raci["A"],
                "owner":     owner,
                "R_primary": raci["R_primary"],
                "R_support": raci["R_support"],
                "C":         raci["C"],
                "I":         raci["I"],
                "rule":      raci["rule"],
            },
            "cost_attribution": cost,
        }

    except Exception as e:
        return {
            "decision": "HOLD", "risk": "high", "confidence": 0.0,
            "reason": f"4M adapter 오류: {str(e)[:120]}",
            "unblock_action": "4M 담당자 확인", "missing_fields": [],
            "input_hash": input_hash, "decision_key": "HOLD", "risk_level": "high",
            "hold_reason": "adapter error", "domain": "fourm",
            "gate_action": "ESCALATE", "gate_reason": "adapter error",
            "issues": [{"level": "HIGH", "text": str(e)[:120]}],
            "evidence": [], "next_step": "Request Missing Info", "proof_id": None,
        }
