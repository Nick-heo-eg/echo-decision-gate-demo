"""
verticals/procurement/schema.py — 구매/조달 분쟁 케이스 스키마

External Signal 필드 (v2 추가):
  외부 데이터는 raw 저장이 아니라 "신호(signal)"로 변환해서 저장.
  Signal Extractor → 이 필드 채움 → rule_extractor에서 score 반영.

  supplier_trade_signal   : Panjiva/ImportGenius 류 (선적 이력)
  commodity_pressure      : World Bank Pink Sheet (원자재 가격 변동)
  country_supply_risk     : UN Comtrade (국가별 공급 위험)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

DISPUTE_TYPES = {
    "delivery_delay": "납기 지연",
    "payment":        "지급 분쟁",
    "quality":        "품질 불량",
    "contract":       "계약 위반",
    "unknown":        "미분류",
}

_DELIVERY_KW = ["납기", "납품", "지연", "delay", "delivery"]
_PAYMENT_KW  = ["지급", "대금", "payment", "미지급", "invoice"]
_QUALITY_KW  = ["불량", "품질", "quality", "defect", "하자"]


def _classify_dispute(text: str) -> str:
    t = text.lower()
    if any(k in t for k in _DELIVERY_KW):
        return "delivery_delay"
    if any(k in t for k in _PAYMENT_KW):
        return "payment"
    if any(k in t for k in _QUALITY_KW):
        return "quality"
    return "unknown"


@dataclass
class ProcurementCase:
    case_id:          str  = ""
    raw_description:  str  = ""

    dispute_type:     str  = "unknown"   # DISPUTE_TYPES 키

    # 공급업체
    supplier_id:      Optional[str]  = None
    supplier_name:    Optional[str]  = None

    # 납기
    delivery_delay_days: Optional[int]  = None
    penalty_clause:   Optional[bool] = None   # 패널티 조항 여부

    # 지급
    contract_value:   Optional[float] = None  # 계약 금액
    payment_overdue:  Optional[bool]  = None  # 지급 지연 여부
    contract_active:  Optional[bool]  = None  # 계약 유효 여부

    # 품질
    inspection_passed: Optional[bool] = None  # 검수 합격 여부
    defect_rate_pct:   Optional[float] = None # 불량률

    # 기타
    claim_goal:       str = ""

    # ── Power Structure Fields (v3) ───────────────────────────────────────
    # 힘의 구조 — 협상 레이어에서 leverage_score + negotiation_type 계산에 사용.
    # None이면 해당 신호 무시 (레거시 케이스 호환).

    single_source:       Optional[bool] = None   # 단일 공급원 여부 (대체 불가)
    alt_supplier_ready:  Optional[bool] = None   # 대체 공급사 즉시 가용 여부
    urgency:             Optional[str]  = None   # "high" | "medium" | "low"
    # negotiation_type: 협상 상대방 유형 (아래 5가지)
    #   "dominant_supplier" — 공급사 갑 (단독 공급, 교체 어려움)
    #   "dominant_buyer"    — 구매자 갑 (대체 공급사 多, 물량 레버리지)
    #   "no_contract"       — 계약 없음 (구두/관행 거래)
    #   "toxic_terms"       — 독소조항 있음 (불리한 계약 조건)
    #   "bluffing_supplier" — 배째라 타입 (강경 반응 예상)
    negotiation_type:    Optional[str]  = None
    supply_risk:         Optional[str]  = None   # "critical" | "high" | "medium" | "low"
    supplier_tier:       Optional[str]  = None   # "strategic" | "preferred" | "standard"

    # ── External Signal Fields (v2) ───────────────────────────────────────
    # Signal Extractor가 채우는 필드. None이면 rule에서 무시.

    # A. Supplier Trade Signal (Panjiva / ImportGenius 류)
    shipment_count_12m:      Optional[int]   = None  # 최근 12개월 선적 횟수
    shipment_recency_days:   Optional[int]   = None  # 마지막 선적 후 경과일
    active_buyer_count:      Optional[int]   = None  # 활성 바이어 수 (다양성)
    trade_continuity_score:  Optional[float] = None  # 0.0~1.0 (높을수록 안정)

    # B. Commodity Pressure Signal (World Bank Pink Sheet)
    commodity_3m_change_pct: Optional[float] = None  # 원자재 3개월 변동률 (%)
    energy_3m_change_pct:    Optional[float] = None  # 에너지 3개월 변동률 (%)
    raw_material_volatility: Optional[str]   = None  # "low" | "medium" | "high"

    # C. Country Supply Risk (UN Comtrade)
    country_of_origin:       Optional[str]   = None  # "CN" | "VN" | "KR" ...
    import_growth_yoy:       Optional[float] = None  # 수입 YoY 증감률 (%)
    export_drop_from_origin: Optional[bool]  = None  # 주요 원산지 수출 급감 여부
    alternate_origin_count:  Optional[int]   = None  # 대체 공급 가능 국가 수

    def __post_init__(self):
        if self.dispute_type == "unknown" and self.raw_description:
            self.dispute_type = _classify_dispute(self.raw_description)


def parse_case(case_dict: dict) -> "ProcurementCase":
    """case_dict → ProcurementCase. raw_description 있으면 자동 분류."""
    c = ProcurementCase()
    for f in ProcurementCase.__dataclass_fields__:
        if f in case_dict and case_dict[f] is not None:
            setattr(c, f, case_dict[f])
    if c.raw_description and c.dispute_type == "unknown":
        c.dispute_type = _classify_dispute(c.raw_description)
    return c
