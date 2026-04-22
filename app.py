"""
Echo Decision Gate — Public Demo
"LLMs shouldn't execute. They should pass a gate."

Run: streamlit run app.py
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Echo Decision Gate",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .gate-allow    { background:#1b5e20; color:#fff; padding:14px 22px; border-radius:8px; font-size:1.4rem; font-weight:700; letter-spacing:.5px; }
  .gate-hold     { background:#b71c1c; color:#fff; padding:14px 22px; border-radius:8px; font-size:1.4rem; font-weight:700; letter-spacing:.5px; }
  .gate-redirect { background:#4a148c; color:#fff; padding:14px 22px; border-radius:8px; font-size:1.4rem; font-weight:700; letter-spacing:.5px; }
  .ev-row        { border-left:3px solid #9e9e9e; background:#f5f5f5; padding:7px 12px; margin:3px 0; font-size:0.88rem; border-radius:0 4px 4px 0; }
  .ev-pos        { border-color:#2e7d32; background:#f1f8f1; }
  .ev-neg        { border-color:#c62828; background:#fdf1f1; }
  .ev-neutral    { border-color:#e65100; background:#fff8f0; }
  .clause-box    { background:#1a237e; color:#e8eaf6; padding:10px 16px; border-radius:6px; font-family:monospace; font-size:0.85rem; margin:8px 0; }
  .hook          { background:#e65100; color:#fff; padding:10px 16px; border-radius:6px; font-size:0.92rem; margin-bottom:12px; }
  .impact-box    { background:#212121; color:#fff; padding:10px 16px; border-radius:6px; font-size:0.9rem; margin:8px 0; }
  .step          { font-size:0.72rem; color:#888; text-transform:uppercase; letter-spacing:1.2px; margin-bottom:2px; }
  .locked-btn    { background:#616161 !important; color:#bdbdbd !important; cursor:not-allowed !important;
                   padding:10px 20px; border-radius:6px; font-weight:700; font-size:0.95rem; border:none; width:100%; }
  .execute-btn   { background:#2e7d32; color:#fff; padding:10px 20px; border-radius:6px;
                   font-weight:700; font-size:0.95rem; border:none; width:100%; cursor:pointer; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DEMO CASES
# Each case carries: display fields + contract_clauses (shown to user) + gate_override (static result)
# gate_override = None means run real engine; dict = use static (for contract-clause demos)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_CASES = {
    "— pick a case —": None,

    "⛔ Case 1 — Partial delivery: penalty clause blocks acceptance": {
        "title": "Partial Delivery Acceptance",
        "subtitle": "Supplier 12 days late. Offering partial shipment. Penalty clause active.",
        "action_label": "✅  Accept Partial Delivery",
        "domain": "procurement",
        "dispute_type": "delivery_delay",
        "delivery_delay_days": 12,
        "penalty_clause": True,
        "penalty_rate_per_day": 2000,
        "waiver_obtained": False,
        "single_source": True,
        "alt_supplier_ready": False,
        "urgency": "high",
        "supply_risk": "high",
        "supplier_id": "ACME-PARTS",
        "contract_clauses": [
            ("4.2", "Penalty", "Delay beyond 7 days incurs $2,000/day. No cap."),
            ("6.1", "Waiver",  "Penalty waiver requires written approval from both parties prior to acceptance."),
            ("8.3", "Partial", "Partial delivery does not constitute acceptance. Full SLA applies."),
        ],
        "gate_override": {
            "decision": "HOLD",
            "owner": {"role": "구매 담당자", "action": "Fix — 조건부 수락 서한 작성 또는 waiver 요청", "why": "계약 조항 해소 권한은 제출자에게 있음 — 수정 후 재제출 가능"},
            "user_verdict": "지금 수락하면 안 됩니다",
            "user_verdict_sub": "계약서에 따르면 $10,000 청구권이 사라집니다",
            "user_reason": (
                "계약 4.2조에 따라 7일 초과 지연은 하루 $2,000 패널티가 발생합니다. "
                "현재 12일 지연 = $10,000입니다. "
                "그런데 지금 부분 납품을 수락하면, 서면 면제(waiver) 없이 수락한 것으로 간주되어 "
                "이 $10,000 청구권을 포기하게 됩니다(6.1조). "
                "8.3조에 따라 부분 납품 수락은 납품 완료로 인정되지 않으므로, "
                "SLA 위반 시계는 계속 돌아갑니다."
            ),
            "user_action": "수락하기 전에 공급사로부터 서면 면제를 받거나, 부분 납품을 거절하고 $10,000 패널티 크레딧을 요청하세요.",
            "reason":   "Clause 4.2 — 12-day delay × $2,000/day = $10,000 exposure. Clause 6.1 — no waiver on record. Accepting partial shipment triggers Clause 8.3: full SLA clock restarts.",
            "unblock":  "Option A: obtain written waiver before accepting. Option B: reject partial, demand full delivery + penalty credit.",
            "financial_impact": "$10,000 unclaimed if accepted without waiver",
            "execution_locked": True,
            "evidence": [
                ("neg",     "Clause 4.2 — penalty active: 12 days × $2k = $10,000",   "BLOCK trigger"),
                ("neg",     "Clause 6.1 — no written waiver on record",                "BLOCK trigger"),
                ("neg",     "Clause 8.3 — partial delivery ≠ acceptance",              "HOLD trigger"),
                ("neutral", "Single source: leverage low — renegotiate, don't reject", "advisory"),
            ],
            "confidence": 0.91,
            "risk": "high",
            "fix": {
                "label":  "🔧 Fix it — 수정된 초안 생성",
                "output_title": "수정된 수락 서한 (권리 보전)",
                "output": (
                    "Subject: Conditional Acceptance of Partial Delivery — Without Prejudice\n\n"
                    "Dear [Supplier Contact],\n\n"
                    "We are prepared to accept the partial shipment on the following basis:\n\n"
                    "  1. Acceptance is WITHOUT PREJUDICE to our rights under Clause 4.2.\n"
                    "  2. Accrued penalty of $10,000 (12 days × $2,000) remains due — to be\n"
                    "     credited against the next invoice or invoiced separately.\n"
                    "  3. Full delivery of remaining units required by [DATE].\n"
                    "  4. SLA obligations continue per Clause 8.3.\n\n"
                    "Please confirm receipt and remaining delivery schedule.\n\n"
                    "Regards,\n[Your Name]"
                ),
                "diff": [
                    ("del", "Subject: Re: Partial Delivery Offer"),
                    ("add", "Subject: Conditional Acceptance of Partial Delivery — Without Prejudice"),
                    ("ctx", ""),
                    ("ctx", "Dear [Supplier Contact],"),
                    ("ctx", ""),
                    ("del", "We are happy to accept the partial shipment."),
                    ("add", "We are prepared to accept the partial shipment on the following basis:"),
                    ("ctx", ""),
                    ("add", "  1. Acceptance is WITHOUT PREJUDICE to our rights under Clause 4.2."),
                    ("add", "  2. Accrued penalty of $10,000 (12 days × $2,000) remains due."),
                    ("add", "  3. Full delivery of remaining units required by [DATE]."),
                    ("add", "  4. SLA obligations continue per Clause 8.3."),
                    ("ctx", ""),
                    ("del", "Consider this matter resolved on our end."),
                    ("add", "Please confirm receipt and remaining delivery schedule."),
                ],
            },
            "route": {
                "label":  "📤 Route — 담당자에게 넘기기",
                "output_title": "법무팀 전달 메모",
                "output": (
                    "To: Legal Team\n"
                    "From: Procurement\n"
                    "Subject: [검토 요청] 부분 납품 수락 전 계약 검토\n\n"
                    "Issue:\n"
                    "  공급사가 12일 지연 후 부분 납품을 제안했습니다.\n"
                    "  수락 전 계약 조항 검토가 필요합니다.\n\n"
                    "위반 위험 조항:\n"
                    "  - Clause 4.2: 패널티 $10,000 발생 (12일 × $2,000)\n"
                    "  - Clause 6.1: 서면 면제 없이 수락 시 청구권 소멸\n"
                    "  - Clause 8.3: 부분 수락 ≠ 납품 완료\n\n"
                    "재무 영향: $10,000 청구권 소멸 위험\n\n"
                    "요청사항:\n"
                    "  □ 서면 면제 수령 가능 여부 확인\n"
                    "  □ 조건부 수락 문구 검토\n"
                    "  □ 승인 후 회신\n\n"
                    "판단 근거: Contract Gate (Clause 4.2, 6.1, 8.3) — 자동 차단됨"
                ),
            },
        },
    },

    "✅ Case 2 — Unpaid invoice: contract active, claim clear": {
        "title": "Unpaid Invoice — Demand Letter",
        "subtitle": "Buyer 60 days overdue on $45,000 invoice. Contract in force. No dispute raised.",
        "action_label": "📨  Issue Demand Letter",
        "domain": "procurement",
        "dispute_type": "payment",
        "contract_value": 45000.0,
        "payment_overdue": True,
        "contract_active": True,
        "supplier_id": "BUYER-XYZ",
        "urgency": "high",
        "supply_risk": "medium",
        "contract_clauses": [
            ("3.1", "Payment terms", "Net-30 from invoice date. Late payment accrues 1.5%/month."),
            ("3.2", "Default",       "Failure to pay within 60 days constitutes material breach."),
            ("9.1", "Remedies",      "Supplier may suspend delivery and pursue recovery without further notice."),
        ],
        "gate_override": {
            "decision": "ALLOW",
            "owner": {"role": "시스템 승인", "action": "Gate passed — proceed to execution"},
            "user_verdict": "청구서를 발송해도 됩니다",
            "user_verdict_sub": "계약이 유효하고, 60일 초과 연체는 중대한 계약 위반입니다",
            "user_reason": (
                "계약 3.2조에 따라 60일 이상 미지급은 중대한 계약 위반(material breach)에 해당합니다. "
                "계약은 현재 유효하고(3.1조), 연체 이자 청구권도 발생해 있습니다. "
                "9.1조에 따라 추가 통보 없이 납품 중단 및 회수 절차를 진행할 수 있습니다."
            ),
            "user_action": "공식 청구서(demand letter)를 발송하세요. 7일 내 무응답 시 9.1조에 따라 납품 중단 및 법적 회수 절차를 개시할 수 있습니다.",
            "reason": "Clause 3.2 — 60+ days overdue = material breach. Contract active (3.1). Recovery rights confirmed (9.1).",
            "unblock": "",
            "financial_impact": "$45,000 overdue + 1.5%/month interest accruing",
            "execution_locked": False,
            "evidence": [
                ("pos", "Clause 3.1 — contract active, payment terms confirmed", "ALLOW signal"),
                ("pos", "Clause 3.2 — 60-day threshold exceeded: material breach", "ALLOW signal"),
                ("pos", "Clause 9.1 — recovery rights active, no further notice needed", "ALLOW signal"),
                ("neutral", "No dispute raised by buyer — uncontested claim", "advisory"),
            ],
            "confidence": 0.93,
            "risk": "low",
        },
    },

    "🔀 Case 3 — Component swap: pin map unconfirmed → execution blocked": {
        "title": "IC Component Replacement — Production Gate",
        "subtitle": "Replacement IC sourced. Pin map not confirmed by engineering. Production about to proceed.",
        "action_label": "🏭  Proceed to Production",
        "domain": "fourm",
        "fourm_type": "M1_material",
        "pin_map_changed": "UNKNOWN",
        "functional_change": "UNKNOWN",
        "phase": "MP",
        "product_type": "EXISTING",
        "component_type": "logic",
        "incident": "INC-001",
        "loss_amount": "$20,000",
        "contract_clauses": [
            ("HR-009", "Engineering gate", "M1 replacement: pin map must be confirmed by engineering — procurement sign-off does not substitute."),
            ("INC-001", "Incident record", "Rohm IC pin mismatch — $20,000 rework loss (2026-04-22). Root cause: no engineering sign-off enforced."),
            ("ECO-4.2", "Execution rule", "Production release blocked if mandatory engineering sign-off not on record."),
        ],
        "gate_override": {
            "decision": "REDIRECT_DEV",
            "owner": {"role": "개발팀 (Engineering)", "action": "Route — 핀맵 검증 및 서명 필수", "why": "핀맵 검증은 개발 고유 권한 — 구매 서명으로 대체 불가 (HR-009)"},
            "user_verdict": "개발팀이 직접 확인해야 합니다 — 지금 생산 진행 불가",
            "user_verdict_sub": "구매팀의 '확인함' 기재는 이 절차를 대체할 수 없습니다",
            "user_reason": (
                "부품을 교체할 때 핀맵(핀 배치)이 기존과 같은지 확인하는 것은 개발팀의 고유 업무입니다. "
                "구매팀이 전화로 확인하거나 체크박스에 표시하는 것으로는 이 절차가 완료되지 않습니다. "
                "실제로 이 구분이 지켜지지 않아 발생한 사고(INC-001)에서 부품 불일치로 $20,000의 재작업 비용이 발생했습니다. "
                "데이터가 부족한 게 아니라, 검증 권한이 없는 사람이 승인한 것이 문제입니다."
            ),
            "user_action": "개발팀에 핀맵 데이터시트 대조 검토를 요청하고, 개발팀 서명을 받은 후에 생산 라인에 투입하세요.",
            "reason":   "HR-009 — M1 replacement with unconfirmed pin map. Procurement verbal confirmation does not satisfy engineering sign-off requirement (INC-001 precedent).",
            "unblock":  "Engineering team must complete pin map datasheet cross-check and sign off before production release.",
            "financial_impact": "INC-001 precedent: identical gap → $20,000 rework",
            "execution_locked": True,
            "evidence": [
                ("neg",     "M1 replacement: pin_map_changed = UNKNOWN (not NO = still HOLD)",           "REDIRECT trigger"),
                ("neg",     "HR-009 — engineering sign-off mandatory, cannot be waived by procurement",  "hard rule"),
                ("neg",     "INC-001 — prior incident: identical gap cost $20k",                         "precedent"),
                ("neutral", "Phase: MP (mass production) — zero tolerance for unverified component swap","context"),
            ],
            "confidence": 0.95,
            "risk": "high",
            "decision_why": (
                "Why REDIRECT — not HOLD or ALLOW",
                "Procurement already wrote 'confirmed' in the spreadsheet. The data isn't missing — the wrong person confirmed it. "
                "Engineering must physically verify pin map compatibility. No amount of additional procurement documentation resolves this. "
                "HOLD would imply 'get more data and come back.' But this is a case where the decision authority itself is wrong. "
                "REDIRECT forces the handoff to the only party qualified to sign off."
            ),
            "fix": {
                "label":  "🔧 Fix it — 검토 요청 + 체크리스트 생성",
                "output_title": "개발팀 검토 요청 (체크리스트 포함)",
                "output": (
                    "Subject: [긴급] 대체 부품 핀맵 검토 요청 — 생산 투입 전 필수\n\n"
                    "개발팀,\n\n"
                    "대체 IC 부품([부품번호]) 생산 투입 전 핀맵 검토 및 서명이 필요합니다.\n"
                    "시스템이 차단 중입니다 (HR-009, INC-001 근거).\n\n"
                    "■ 검토 체크리스트:\n"
                    "  □ 기존 / 대체 부품 데이터시트 대조\n"
                    "  □ 핀맵 1:1 확인 (VCC, GND, 신호핀)\n"
                    "  □ 전기 특성 호환성 확인\n"
                    "  □ 기능적 동등성 판단 (drop-in 여부)\n"
                    "  □ 개발팀 담당자 서명: ___________\n\n"
                    "서명 완료 후 시스템에 재제출하면 생산 잠금이 해제됩니다.\n\n"
                    "참고: INC-001 — 동일 절차 미이행 시 $20,000 재작업 발생 (2026-04-22)\n\n"
                    "[구매 담당자]"
                ),
                "diff": [
                    ("del", "# 기존 프로세스: 구매팀 구두 확인 후 생산 투입"),
                    ("add", "# 변경: 개발팀 서명 필수 (HR-009 적용)"),
                    ("ctx", ""),
                    ("del", "구매팀 확인: '공급사에 전화로 확인함' (체크박스)"),
                    ("add", "개발팀 확인: 데이터시트 대조 + 서명 필수"),
                    ("ctx", ""),
                    ("del", "→ 생산 투입 즉시 가능"),
                    ("add", "→ 개발팀 서명 완료 후 시스템 재제출 → 잠금 해제"),
                    ("ctx", ""),
                    ("ctx", "근거: INC-001 — 구두 확인만으로 투입 → $20,000 재작업"),
                ],
            },
            "route": {
                "label":  "📤 Route — 개발팀장에게 넘기기",
                "output_title": "개발팀장 에스컬레이션",
                "output": (
                    "To: 개발팀장\n"
                    "From: 구매팀\n"
                    "Subject: [에스컬레이션] 대체 부품 핀맵 미확인 — 생산 차단 중\n\n"
                    "Issue:\n"
                    "  대체 IC 부품([부품번호])의 핀맵이 개발팀에 의해 확인되지 않았습니다.\n"
                    "  생산 라인 투입이 시스템에 의해 차단되어 있습니다.\n\n"
                    "차단 근거:\n"
                    "  - HR-009: M1 대체품 핀맵 확인은 개발팀 필수 서명 사항\n"
                    "  - INC-001: 동일 절차 미이행 → $20,000 재작업 사고 (2026-04-22)\n\n"
                    "현재 상황:\n"
                    "  - 구매팀 구두 확인 기재 → 시스템 인정 불가\n"
                    "  - 개발팀 데이터시트 대조 및 서명 필요\n\n"
                    "요청: 개발 담당자 지정 및 검토 일정 확인 부탁드립니다.\n\n"
                    "생산 대기 중 — 빠른 회신 부탁드립니다."
                ),
            },
        },
    },

    "📧 Case 4 — Email draft: clause conflict blocks send": {
        "title": "Pre-Send Contract Gate",
        "subtitle": "Email draft accepts partial delivery and waives further claims. Contract has liability cap + no-waiver clause.",
        "action_label": "📤  Send Email",
        "domain": "send_gate",
        "contract_clauses": [
            ("5.3", "Liability cap",   "Total liability of either party shall not exceed the contract value ($45,000)."),
            ("6.1", "No waiver",       "Failure to enforce any right shall not constitute waiver of future rights."),
            ("7.2", "Written consent", "Any modification of obligations requires written consent of both parties."),
        ],
        "email_draft": (
            "Hi team — given the circumstances, we're happy to accept the partial delivery "
            "and consider the matter closed. No further claims will be raised on our end."
        ),
        "gate_override": {
            "decision": "HOLD",
            "owner": {"role": "작성자 또는 법무팀", "action": "Fix — 위험 표현 제거 후 재검토, 또는 법무팀 Route", "why": "표현 수정은 작성자가 가능 / 권리 포기 판단은 법무 필요"},
            "user_verdict": "이 메일은 지금 보내면 안 됩니다",
            "user_verdict_sub": "문장 두 개가 $10,000 청구권을 포기하는 것으로 해석될 수 있습니다",
            "user_reason": (
                "'consider the matter closed'와 'no further claims' 표현은 법적으로 "
                "권리 포기(waiver)로 해석될 수 있습니다. 계약 6.1조에는 서면 합의 없이는 "
                "어떤 권리도 포기한 것으로 보지 않는다고 명시되어 있는데, 이 표현은 그 조항과 충돌합니다. "
                "5.3조의 책임 상한($45,000)도 이 표현으로 인해 무력화될 위험이 있습니다. "
                "내용 자체(부분 납품 수락)는 문제없지만, 표현 방식이 문제입니다."
            ),
            "user_action": "해당 표현을 다음으로 교체하세요: 'Accepting partial delivery without prejudice to existing claims under Clause 4.2.'",
            "reason":   "Draft language 'consider the matter closed' + 'no further claims' creates implicit waiver risk (Clause 6.1). Contradicts liability cap (Clause 5.3). Sending as-is exposes $10,000 unclaimed penalty.",
            "unblock":  "Remove waiver language. Replace with: 'Accepting partial delivery without prejudice to existing claims under Clause 4.2.'",
            "financial_impact": "$10,000 penalty right forfeited if sent as-is",
            "execution_locked": True,
            "evidence": [
                ("neg",     "'consider the matter closed' — implicit waiver of Clause 4.2 rights", "BLOCK trigger"),
                ("neg",     "'no further claims' — contradicts Clause 5.3 liability cap",          "BLOCK trigger"),
                ("neg",     "No written consent obtained — Clause 7.2 violation risk",             "HOLD trigger"),
                ("neutral", "Partial delivery acceptance itself is valid — wording is the problem", "advisory"),
            ],
            "confidence": 0.88,
            "risk": "high",
            "fix": {
                "label":  "🔧 Fix it — 안전한 초안으로 교체",
                "output_title": "수정된 이메일 초안 (권리 보전)",
                "output": (
                    "Subject: Partial Delivery Acceptance — Without Prejudice\n\n"
                    "Hi [Name],\n\n"
                    "We are prepared to accept the partial delivery on the following basis:\n\n"
                    "  - Acceptance is WITHOUT PREJUDICE to our rights under Clause 4.2.\n"
                    "  - Accrued penalty of $10,000 (12 days × $2,000) remains due.\n"
                    "  - Full delivery required by [DATE]. SLA continues per Clause 8.3.\n\n"
                    "Please confirm remaining delivery schedule.\n\n"
                    "Regards,\n[Your Name]"
                ),
                "diff": [
                    ("del", "given the circumstances, we're happy to accept the partial delivery"),
                    ("add", "We are prepared to accept the partial delivery on the following basis:"),
                    ("ctx", ""),
                    ("del", "and consider the matter closed."),
                    ("add", "  - Acceptance is WITHOUT PREJUDICE to our rights under Clause 4.2."),
                    ("add", "  - Accrued penalty of $10,000 remains due."),
                    ("ctx", ""),
                    ("del", "No further claims will be raised on our end."),
                    ("add", "Please confirm remaining delivery schedule."),
                    ("ctx", ""),
                    ("ctx", "# Clause 6.1 위반 표현 제거 / Clause 5.3 위반 표현 제거"),
                ],
            },
            "route": {
                "label":  "📤 Route — 법무팀에 넘기기",
                "output_title": "법무팀 검토 요청",
                "output": (
                    "To: Legal Team\n"
                    "From: [담당자]\n"
                    "Subject: [검토 요청] 이메일 발송 전 계약 조항 충돌 확인\n\n"
                    "Issue:\n"
                    "  이메일 초안의 표현이 계약 조항과 충돌합니다.\n"
                    "  시스템이 발송을 차단했습니다.\n\n"
                    "충돌 조항:\n"
                    "  - Clause 6.1: 'consider the matter closed' → 권리 포기로 해석\n"
                    "  - Clause 5.3: 'no further claims' → 책임 상한 무력화\n"
                    "  - Clause 7.2: 서면 동의 없는 조건 변경\n\n"
                    "재무 영향: $10,000 패널티 청구권 소멸 위험\n\n"
                    "요청:\n"
                    "  □ 수정 표현 승인 또는 대안 제시\n"
                    "  □ 발송 가능 여부 확인\n\n"
                    "현재 발송 차단 중 — 승인 후 재제출 예정"
                ),
            },
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# GATE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def run_gate(cfg: dict) -> dict:
    override = cfg.get("gate_override", {})
    return {
        "decision":         override["decision"],
        "reason":           override["reason"],
        "unblock":          override.get("unblock", ""),
        "financial_impact": override.get("financial_impact"),
        "execution_locked": override.get("execution_locked", False),
        "evidence":         override.get("evidence", []),
        "confidence":       override.get("confidence", 0.8),
        "risk":             override.get("risk", "high"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _decision_css(d: str) -> str:
    if "ALLOW" in d: return "gate-allow"
    if "REDIRECT" in d: return "gate-redirect"
    return "gate-hold"

def _decision_icon(d: str) -> str:
    return {"ALLOW":"✅","HOLD":"🛑","REDIRECT_DEV":"🔀","REDIRECT_MFG":"🔀","REDIRECT_SQE":"🔀"}.get(d,"⚠️")

def _ev_css(sign: str) -> str:
    return {"pos":"ev-pos","neg":"ev-neg","neutral":"ev-neutral"}.get(sign,"ev-row")

def _ev_icon(sign: str) -> str:
    return {"pos":"🟢","neg":"🔴","neutral":"🟡"}.get(sign,"⚪")


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## ⚡ Echo Decision Gate")
st.markdown("### *If we block it, we assign it.*")
st.markdown("Every blocked decision gets an owner and a next move — not just a warning.")

st.markdown(
    '<div class="hook">'
    'Most tools stop at "warning." This one decides — and when it blocks, it assigns an owner and generates the next action. '
    'Case 3 is a real $20,000 incident. The gate would have stopped it.'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()

# ── WHY THREE OUTCOMES ────────────────────────────────────────────────────────
with st.expander("**Why ALLOW / HOLD / REDIRECT — not just pass/fail?**", expanded=False):
    st.markdown("""
The three outcomes map to three different **accountability destinations** — not just severity levels.

| Outcome | Meaning | Who owns it |
|---|---|---|
| ✅ **ALLOW** | All rules passed. Execution authorized. | Gate system signs off |
| 🛑 **HOLD** | Condition unmet or information missing. Submitter must resolve before retrying. | Submitter |
| 🔀 **REDIRECT** | This person cannot make this decision — authority or expertise is elsewhere. Passing it through would itself be the violation. | Redirected party (e.g. Engineering, Legal) |

**The critical distinction is HOLD vs REDIRECT.**

HOLD = *not yet*. Fix the data, come back.

REDIRECT = *not you*. No amount of data fixes it — the wrong person is deciding.
Case 3 is the real example: procurement verbally confirmed a pin map and wrote "confirmed" in the spreadsheet.
That's not HOLD (missing data) — that's a REDIRECT violation. Engineering must sign off. Procurement cannot substitute.
The gap cost $20,000.

Most advisory tools only have two states: warn or pass. They cannot model responsibility transfer.
A system that can only say "be careful" cannot prevent Case 3.
    """)

st.divider()

# flow diagram
c1,c2,c3,c4,c5,c6,c7 = st.columns([2,.4,2,.4,2,.4,2])
for col,label,body in [
    (c1,"1 · input",    "Situation\nContract fields\nState flags"),
    (c3,"2 · gate",     "Clause lookup\nRule scoring\nHigh-risk check"),
    (c5,"3 · decision", "ALLOW / HOLD\nREDIRECT\nEvidence chain"),
    (c7,"4 · lock",     "Button disabled\nif HOLD/REDIRECT\nAudit trace"),
]:
    col.markdown(f'<div class="step">{label}</div>', unsafe_allow_html=True)
    col.markdown(body)
for col in [c2,c4,c6]:
    col.markdown('<div style="font-size:1.5rem;color:#888;margin-top:20px;text-align:center">→</div>', unsafe_allow_html=True)

st.divider()

# case selector
selected = st.selectbox("**Load a demo case**", list(DEMO_CASES.keys()))
cfg = DEMO_CASES[selected]

if cfg is None:
    st.info("Select a case above to see the gate in action.")
    st.stop()

left, right = st.columns([1, 1], gap="large")

# ── LEFT: INPUT ───────────────────────────────────────────────────────────────
with left:
    st.markdown(f"### {cfg['title']}")
    st.caption(cfg["subtitle"])

    # contract clauses
    if cfg.get("contract_clauses"):
        st.markdown("**Contract / Policy on record**")
        for clause_id, label, text in cfg["contract_clauses"]:
            st.markdown(
                f'<div class="clause-box"><b>§ {clause_id} — {label}</b><br>{text}</div>',
                unsafe_allow_html=True,
            )

    # email draft (Case 4)
    if cfg.get("email_draft"):
        st.markdown("**Email draft submitted for review**")
        st.text_area("Draft", value=cfg["email_draft"], height=100, disabled=True, label_visibility="collapsed")

    # key state fields
    skip = {"title","subtitle","domain","contract_clauses","gate_override","email_draft","incident","loss_amount"}
    field_labels = {
        "dispute_type":"Dispute type","penalty_clause":"Penalty clause",
        "delivery_delay_days":"Delay (days)","penalty_rate_per_day":"Penalty rate/day",
        "waiver_obtained":"Waiver obtained","contract_value":"Contract value",
        "payment_overdue":"Payment overdue","contract_active":"Contract active",
        "single_source":"Single source","alt_supplier_ready":"Alt supplier ready",
        "urgency":"Urgency","supply_risk":"Supply risk",
        "fourm_type":"Change type","pin_map_changed":"Pin map confirmed",
        "phase":"Phase","product_type":"Product type","component_type":"Component",
    }
    rows = [(field_labels.get(k,k), v) for k,v in cfg.items() if k not in skip and v is not None]
    if rows:
        st.markdown("**State inputs**")
        md = "| Field | Value |\n|---|---|\n"
        for lbl, val in rows:
            dv = "✅ Yes" if val is True else ("❌ No" if val is False else f"`{val}`")
            if isinstance(val, (int,float)) and not isinstance(val,bool):
                dv = f"`{val:,}`" if isinstance(val,int) else f"`${val:,.0f}`"
            md += f"| {lbl} | {dv} |\n"
        st.markdown(md)

    if cfg.get("incident"):
        st.error(f"⚠️ Incident on record: **{cfg['incident']}** — Loss: {cfg.get('loss_amount','')}")

# ── RIGHT: RESULT ─────────────────────────────────────────────────────────────
with right:
    st.markdown("### 판단 결과")
    with st.spinner("검토 중..."):
        result = run_gate(cfg)

    decision  = result["decision"]
    reason    = result["reason"]
    unblock   = result["unblock"]
    evidence  = result["evidence"]
    conf      = result["confidence"]
    risk      = result["risk"]
    locked    = result["execution_locked"]
    fin_impact= result["financial_impact"]

    override     = cfg.get("gate_override") or {}
    user_verdict = override.get("user_verdict")
    user_sub     = override.get("user_verdict_sub")
    user_reason  = override.get("user_reason")
    user_action  = override.get("user_action")

    # ── 1. PRIMARY VERDICT: 사용자 언어 ──────────────────────────────────────
    if user_verdict:
        verdict_bg = {"HOLD":"#b71c1c","REDIRECT_DEV":"#4a148c","ALLOW":"#1b5e20"}.get(decision,"#333")
        sub_html = f'<div style="font-size:0.9rem;margin-top:6px;opacity:.85">{user_sub}</div>' if user_sub else ""
        st.markdown(
            f'<div style="background:{verdict_bg};color:#fff;padding:16px 20px;border-radius:8px;margin-bottom:8px">'
            f'<div style="font-size:1.3rem;font-weight:700">{user_verdict}</div>{sub_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="{_decision_css(decision)}">{_decision_icon(decision)} {decision}</div>',
            unsafe_allow_html=True,
        )

    # ── 1b. OWNER 배지 ───────────────────────────────────────────────────────
    _owner_cfg = override.get("owner")
    if not _owner_cfg and decision == "ALLOW":
        _owner_cfg = {"role": "시스템 승인", "action": "게이트 통과 — 실행 가능"}
    if _owner_cfg:
        _owner_color = {
            "HOLD":        "#7f0000",
            "REDIRECT_DEV":"#1a0050",
            "ALLOW":       "#1b5e20",
        }.get(decision, "#333")
        _owner_icon = {"HOLD": "👤", "REDIRECT_DEV": "🔀", "ALLOW": "✅"}.get(decision, "📌")
        _owner_why = _owner_cfg.get("why", "")
        _why_html = (
            f'<div style="font-size:0.78rem;color:#888;margin-top:4px;padding-left:2px">'
            f'왜 이 사람인가: {_owner_why}</div>'
            if _owner_why else ""
        )
        st.markdown(
            f'<div style="margin:6px 0 10px 0">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<div style="background:{_owner_color};color:#fff;padding:4px 12px;'
            f'border-radius:20px;font-size:0.82rem;font-weight:600;white-space:nowrap">'
            f'{_owner_icon} Owner: {_owner_cfg["role"]}</div>'
            f'<div style="font-size:0.82rem;color:#666">{_owner_cfg["action"]}</div>'
            f'</div>{_why_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── 2. 이유 (사용자 언어 우선) ───────────────────────────────────────────
    if user_reason:
        st.markdown(user_reason)
    else:
        st.markdown(f"**{reason}**")

    # ── 3. 재무 영향 ─────────────────────────────────────────────────────────
    if fin_impact:
        st.markdown(
            f'<div class="impact-box">💰 재무 영향: <b>{fin_impact}</b></div>',
            unsafe_allow_html=True,
        )

    # ── 4. 지금 해야 할 일 ───────────────────────────────────────────────────
    display_action = user_action or unblock
    if display_action:
        st.info(f"**지금 해야 할 일:** {display_action}")

    st.divider()

    # ── 5. 실행 잠금 — Streamlit native button (진짜로 클릭 안 됨) ───────────
    action_label = cfg.get("action_label", "✅  실행")
    block_rule   = override.get("reason", reason)[:80] if locked else ""

    # BLOCKED 케이스: 버튼은 disabled + 클릭 시 차단 메시지 (st.button은 disabled=True면 이벤트 자체 없음)
    # ALLOW 케이스: 버튼 활성화, 클릭 시 성공 팝업

    st.markdown("**실행**")

    if locked:
        # disabled=True → Streamlit이 실제로 클릭 불가 처리
        st.button(
            f"🔒  {action_label.lstrip('✅📨🏭📤 ')} — Blocked by Contract Gate",
            disabled=True,
            use_container_width=True,
            help=f"차단 근거: {block_rule}",
        )
        st.markdown(
            f'<div style="background:#b71c1c22;border:1px solid #b71c1c55;border-radius:6px;'
            f'padding:10px 14px;margin-top:6px;font-size:0.88rem">'
            f'🚫 <b>Execution blocked by policy</b><br>'
            f'<span style="color:#555">근거: {override.get("reason", reason)[:120]}...</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _clicked = st.button(
            action_label,
            type="primary",
            use_container_width=True,
        )
        if _clicked:
            st.success(
                f"✅ **실행 승인됨** — 게이트 통과. 감사 기록이 저장되었습니다.\n\n"
                f"신뢰도 {int(conf*100)}% | 위험도 {risk.upper()} | 결정: ALLOW"
            )

    # ── 6. Fix / Route (BLOCKED일 때만) ─────────────────────────────────────
    fix_action   = override.get("fix")
    route_action = override.get("route")

    if locked and (fix_action or route_action):
        st.divider()
        st.markdown("**다음 중 하나를 선택하세요**")
        col_fix, col_route = st.columns(2)

        show_fix   = st.session_state.get(f"show_fix_{selected}", False)
        show_route = st.session_state.get(f"show_route_{selected}", False)

        with col_fix:
            if fix_action:
                if st.button(fix_action["label"], key=f"fix_{selected}", use_container_width=True):
                    st.session_state[f"show_fix_{selected}"]   = True
                    st.session_state[f"show_route_{selected}"] = False

        with col_route:
            if route_action:
                if st.button(route_action["label"], key=f"route_{selected}", use_container_width=True):
                    st.session_state[f"show_route_{selected}"] = True
                    st.session_state[f"show_fix_{selected}"]   = False

        if show_fix and fix_action:
            st.markdown(f"**{fix_action['output_title']}**")
            st.code(fix_action["output"], language=None)

            # ── action buttons ────────────────────────────────────────────────
            _fix_text = fix_action["output"]
            _fix_lines = _fix_text.splitlines()
            _fix_subject = next((l.replace("Subject:","").strip() for l in _fix_lines if l.startswith("Subject:")), fix_action["output_title"])
            _fix_body    = "\n".join(l for l in _fix_lines if not l.startswith("Subject:")).strip()
            import urllib.parse as _up
            _mailto_fix = "mailto:?subject=" + _up.quote(_fix_subject) + "&body=" + _up.quote(_fix_body)

            _btn_style = (
                "display:inline-block;padding:7px 16px;border-radius:6px;font-size:0.85rem;"
                "font-weight:600;text-decoration:none;margin-right:8px;cursor:pointer;"
            )
            st.markdown(
                f'<a href="{_mailto_fix}" target="_blank" style="{_btn_style}background:#1565c0;color:#fff">✉️ Draft Email — Ready to Send</a>'
                f'<span style="font-size:0.78rem;color:#888">← 내용 pre-filled · 검토 후 발송</span>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

            # diff — 항상 펼쳐짐
            diff_lines = fix_action.get("diff", [])
            if diff_lines:
                with st.expander("변경 사항 (before / after)", expanded=True):
                    diff_colors = {"add": "#1b5e20", "del": "#b71c1c", "ctx": "#555"}
                    diff_bg     = {"add": "#f1f8f1", "del": "#fdf1f1", "ctx": "#fafafa"}
                    diff_prefix = {"add": "+ ", "del": "- ", "ctx": "  "}
                    html_rows = ""
                    for kind, line in diff_lines:
                        prefix = diff_prefix.get(kind, "  ")
                        color  = diff_colors.get(kind, "#333")
                        bg     = diff_bg.get(kind, "#fff")
                        html_rows += (
                            f'<div style="background:{bg};color:{color};font-family:monospace;'
                            f'font-size:0.83rem;padding:2px 10px;border-radius:2px">'
                            f'{prefix}{line}</div>'
                        )
                    st.markdown(html_rows, unsafe_allow_html=True)

        if show_route and route_action:
            st.markdown(f"**{route_action['output_title']}**")
            st.code(route_action["output"], language=None)

            # ── action buttons ────────────────────────────────────────────────
            _route_text = route_action["output"]
            _route_lines = _route_text.splitlines()
            _route_to      = next((l.replace("To:","").strip() for l in _route_lines if l.startswith("To:")), "")
            _route_subject = next((l.replace("Subject:","").strip() for l in _route_lines if l.startswith("Subject:")), route_action["output_title"])
            _route_body    = "\n".join(l for l in _route_lines if not l.startswith(("To:","From:","Subject:"))).strip()
            _mailto_route = (
                "mailto:" + _up.quote(_route_to)
                + "?subject=" + _up.quote(_route_subject)
                + "&body=" + _up.quote(_route_body)
            )
            st.markdown(
                f'<a href="{_mailto_route}" target="_blank" style="{_btn_style}background:#4a148c;color:#fff">✉️ Prepare Handoff Email</a>'
                f'<span style="font-size:0.78rem;color:#888">← 수신인 + 내용 pre-filled · 검토 후 발송</span>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── 7. 내부 판단 근거 (개발자/HN용 접이식) ──────────────────────────────
    with st.expander("🔧 내부 판단 근거 보기 (엔진 / 증거 체인)", expanded=False):
        st.markdown(f"**내부 결정 코드:** `{decision}`")
        st.progress(conf, text=f"신뢰도: {int(conf*100)}%  |  위험도: {risk.upper()}")
        st.markdown("")

        _case_why = override.get("decision_why")
        if _case_why:
            _title_why, _body_why = _case_why
        else:
            _generic_why = {
                "ALLOW": (
                    "Why ALLOW — not HOLD or REDIRECT",
                    "All mandatory conditions satisfied. Evidence score positive. Submitter has authority to execute.",
                ),
                "HOLD": (
                    "Why HOLD — not ALLOW or REDIRECT",
                    "Condition unmet or clause violated. Submitter can resolve and resubmit. "
                    "Not REDIRECT — authority stays with submitter, they just need to do more work.",
                ),
            }
            _default = (
                f"Why {decision}",
                "Decision authority does not rest with the submitter. "
                "Gate identified that required expertise or contractual authority belongs to another party.",
            )
            _title_why, _body_why = _generic_why.get(decision, _default)

        st.markdown(
            f'<div style="border-left:3px solid #555;padding:8px 12px;background:#f5f5f5;border-radius:0 4px 4px 0;margin-bottom:8px">'
            f'<b>{_title_why}</b><br>'
            f'<span style="font-size:0.85rem;color:#444">{_body_why}</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Evidence chain**")
        for item in evidence:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                sign, rule_text, eff = item[0], item[1], item[2]
            elif isinstance(item, dict):
                sign, rule_text, eff = item.get("sign","neutral"), item.get("rule",""), item.get("effect","")
            else:
                continue
            st.markdown(
                f'<div class="ev-row {_ev_css(sign)}">{_ev_icon(sign)} {rule_text}'
                f'<span style="float:right;color:#888;font-size:0.8rem">{eff}</span></div>',
                unsafe_allow_html=True,
            )

    # JSON export
    export = {
        "decision": decision, "reason": reason, "unblock": unblock,
        "confidence": conf, "risk": risk, "locked": locked,
        "financial_impact": fin_impact,
        "evidence": [list(e) if isinstance(e,(list,tuple)) else e for e in evidence],
    }
    st.download_button(
        "⬇ Export audit JSON",
        data=json.dumps(export, indent=2, ensure_ascii=False),
        file_name=f"gate_{decision.lower()}.json",
        mime="application/json",
    )

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="font-size:0.78rem;color:#888;text-align:center">
  Echo Decision Gate · rule engine + evidence chain + execution lock<br>
  Verticals: procurement · 4M manufacturing change control · contract enforcement · pre-send gate<br>
  <b>The gate doesn't advise. It decides — and blocks.</b>
</div>
""", unsafe_allow_html=True)
