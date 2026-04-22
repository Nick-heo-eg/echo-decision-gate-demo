"""
Echo Decision Gate — Public Demo
"LLMs shouldn't execute. They should pass a gate."

Run: streamlit run ui_demo_gate.py
"""
import sys, json, uuid
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;1,9..144,400&family=JetBrains+Mono:wght@400;600&family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* ── Design tokens ──────────────────────────────────────────────── */
  :root {
    --bg:            #0b0a08;
    --bg-elev-1:     #141210;
    --bg-elev-2:     #1b1815;
    --surface-soft:  #1f1c18;
    --ink:           #f4efe3;
    --ink-dim:       #b5aea1;
    --ink-mute:      #7a7367;
    --gold:          #d4a853;
    --terracotta:    #c17458;
    --sage:          #7a9970;
    --slate:         #7d9dc4;
    --rule:          #2a2620;
    --rule-strong:   #3a342c;
  }

  /* ── Gate verdict cards (left-border style) ─────────────────────── */
  .gate-allow {
    background: rgba(122,153,112,0.12);
    border-left: 3px solid #7a9970;
    color: #f4efe3;
    padding: 14px 22px;
    border-radius: 0 8px 8px 0;
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: .5px;
    font-family: 'Fraunces', serif;
  }
  .gate-hold {
    background: rgba(212,168,83,0.12);
    border-left: 3px solid #d4a853;
    color: #f4efe3;
    padding: 14px 22px;
    border-radius: 0 8px 8px 0;
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: .5px;
    font-family: 'Fraunces', serif;
  }
  .gate-redirect {
    background: rgba(193,116,88,0.12);
    border-left: 3px solid #c17458;
    color: #f4efe3;
    padding: 14px 22px;
    border-radius: 0 8px 8px 0;
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: .5px;
    font-family: 'Fraunces', serif;
  }

  /* ── Evidence rows ──────────────────────────────────────────────── */
  .ev-row {
    border-left: 3px solid #3a342c;
    background: #1b1815;
    color: #b5aea1;
    padding: 7px 12px;
    margin: 3px 0;
    font-size: 0.88rem;
    border-radius: 0 4px 4px 0;
    font-family: 'Public Sans', sans-serif;
  }
  .ev-pos     { border-color: #7a9970; background: rgba(122,153,112,0.10); color: #f4efe3; }
  .ev-neg     { border-color: #c17458; background: rgba(193,116,88,0.10);  color: #f4efe3; }
  .ev-neutral { border-color: #d4a853; background: rgba(212,168,83,0.10);  color: #f4efe3; }

  /* ── Clause box ─────────────────────────────────────────────────── */
  .clause-box {
    background: #1f1c18;
    color: #b5aea1;
    border-left: 2px solid #7d9dc4;
    padding: 10px 16px;
    border-radius: 0 6px 6px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    margin: 8px 0;
  }
  .clause-box b {
    color: #7d9dc4;
  }

  /* ── Hook / banner ──────────────────────────────────────────────── */
  .hook {
    background: rgba(193,116,88,0.14);
    border-left: 3px solid #c17458;
    color: #f4efe3;
    padding: 10px 16px;
    border-radius: 0 6px 6px 0;
    font-size: 0.92rem;
    font-family: 'Fraunces', serif;
    margin-bottom: 12px;
  }

  /* ── Impact box ─────────────────────────────────────────────────── */
  .impact-box {
    background: #1f1c18;
    border-left: 3px solid #d4a853;
    color: #b5aea1;
    padding: 10px 16px;
    border-radius: 0 6px 6px 0;
    font-size: 0.9rem;
    margin: 8px 0;
  }
  .impact-box b { color: #d4a853; }

  /* ── Step label ─────────────────────────────────────────────────── */
  .step {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #7a7367;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 2px;
  }

  /* ── Owner badge ────────────────────────────────────────────────── */
  .owner-badge-hold {
    background: rgba(212,168,83,0.18);
    color: #d4a853;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
    font-family: 'JetBrains Mono', monospace;
  }
  .owner-badge-redirect {
    background: rgba(193,116,88,0.18);
    color: #c17458;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
    font-family: 'JetBrains Mono', monospace;
  }
  .owner-badge-allow {
    background: rgba(122,153,112,0.18);
    color: #7a9970;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
    font-family: 'JetBrains Mono', monospace;
  }

  /* ── Locked button ──────────────────────────────────────────────── */
  .locked-btn {
    background: #1f1c18 !important;
    color: #7a7367 !important;
    cursor: not-allowed !important;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.95rem;
    border: none;
    width: 100%;
  }
  .execute-btn {
    background: rgba(122,153,112,0.20);
    border-left: 3px solid #7a9970;
    color: #f4efe3;
    padding: 10px 20px;
    border-radius: 0 6px 6px 0;
    font-weight: 700;
    font-size: 0.95rem;
    border: none;
    width: 100%;
    cursor: pointer;
  }
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
        "narrative": "Your supplier is 12 days late and just offered to ship 60% of the order now, the rest next week. Your manager wants to accept and move on. The gate runs before you click Accept.",
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
            "owner": {"role": "Procurement Officer", "action": "Fix — draft conditional acceptance letter or request waiver", "why": "Authority to resolve contract clauses rests with submitter — can resubmit after correction"},
            "user_verdict": "You must not accept this right now",
            "user_verdict_sub": "Per the contract, accepting now forfeits your $10,000 claim",
            "user_reason": (
                "Under Clause 4.2, delays beyond 7 days incur a $2,000/day penalty. "
                "Current delay is 12 days = $10,000. "
                "Accepting partial delivery now would be treated as acceptance without a written waiver, "
                "forfeiting this $10,000 claim (Clause 6.1). "
                "Under Clause 8.3, acceptance of partial delivery does not count as full delivery completion, "
                "so the SLA violation clock continues to run."
            ),
            "user_action": "Obtain a written waiver from the supplier before accepting, or reject the partial delivery and request the $10,000 penalty credit.",
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
                "label":  "🔧 Fix it — generate revised draft",
                "output_title": "Revised Acceptance Letter (rights preserved)",
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
                "label":  "📤 Route — escalate to responsible party",
                "output_title": "Legal Team Routing Memo",
                "output": (
                    "To: Legal Team\n"
                    "From: Procurement\n"
                    "Subject: [Review Request] Contract review before partial delivery acceptance\n\n"
                    "Issue:\n"
                    "  Supplier has offered partial delivery after a 12-day delay.\n"
                    "  Contract clause review required before acceptance.\n\n"
                    "At-risk clauses:\n"
                    "  - Clause 4.2: $10,000 penalty accrued (12 days × $2,000)\n"
                    "  - Clause 6.1: claim forfeited if accepted without written waiver\n"
                    "  - Clause 8.3: partial acceptance ≠ full delivery completion\n\n"
                    "Financial impact: risk of forfeiting $10,000 claim\n\n"
                    "Requested actions:\n"
                    "  □ Confirm whether written waiver can be obtained\n"
                    "  □ Review conditional acceptance wording\n"
                    "  □ Reply after approval\n\n"
                    "Decision basis: Contract Gate (Clause 4.2, 6.1, 8.3) — auto-blocked"
                ),
            },
        },
    },

    "✅ Case 2 — Unpaid invoice: contract active, claim clear": {
        "title": "Unpaid Invoice — Demand Letter",
        "subtitle": "Buyer 60 days overdue on $45,000 invoice. Contract in force. No dispute raised.",
        "narrative": "A buyer hasn't paid a $45,000 invoice in 60 days. No dispute was raised, no payment plan requested. You want to issue a formal demand letter. The gate checks whether your claim is legally solid before you send.",
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
        "gate_override": None,  # run real engine
        "user_verdict_live": {
            "ALLOW": {
                "verdict":  "You may issue the demand letter",
                "sub":      "Contract is active and 60-day non-payment constitutes material breach",
                "reason":   (
                    "Under Clause 3.2, failure to pay for 60+ days constitutes material breach. "
                    "The contract is currently active (Clause 3.1) and late payment interest has accrued. "
                    "Under Clause 9.1, delivery suspension and recovery proceedings may be initiated without further notice."
                ),
                "action":   "Issue the formal demand letter. If no response within 7 days, you may suspend delivery and initiate legal recovery under Clause 9.1.",
            },
            "HOLD": {
                "verdict":  "Additional verification required",
                "sub":      "Claim basis is partially incomplete",
                "reason":   "Contract information or payment overdue details are insufficient to confirm the claim basis. Supplement with the contract and invoice records.",
                "action":   "Verify the contract copy, invoice issue date, and receipt confirmation, then resubmit.",
            },
        }
    },

    "🔀 Case 3 — Component swap: pin map unconfirmed → execution blocked": {
        "title": "IC Component Replacement — Production Gate",
        "subtitle": "Replacement IC sourced. Pin map not confirmed by engineering. Production about to proceed.",
        "narrative": "Procurement sourced a replacement IC due to shortage. Someone on the team called the supplier, checked a box in the spreadsheet marked 'confirmed', and production is scheduled for today. This exact sequence caused a $20,000 rework incident (INC-001). The gate runs before the line starts.",
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
            "owner": {"role": "Engineering Team", "action": "Route — pin map verification and sign-off required", "why": "Pin map verification is exclusive to engineering — cannot be substituted by procurement sign-off (HR-009)"},
            "user_verdict": "Engineering must verify directly — production cannot proceed now",
            "user_verdict_sub": "Procurement's 'confirmed' entry cannot substitute this procedure",
            "user_reason": (
                "When replacing a component, verifying that the pin map (pin layout) matches the original is exclusively engineering's responsibility. "
                "Procurement verbally confirming by phone or checking a checkbox does not complete this procedure. "
                "In the actual incident (INC-001) where this distinction was not followed, a component mismatch caused $20,000 in rework costs. "
                "The problem is not missing data — it is that someone without verification authority approved it."
            ),
            "user_action": "Request engineering to cross-check the pin map datasheet, obtain engineering team sign-off, and only then proceed to production.",
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
                "label":  "🔧 Fix it — generate review request + checklist",
                "output_title": "Engineering Review Request (with checklist)",
                "output": (
                    "Subject: [URGENT] Replacement Component Pin Map Review Required — Before Production\n\n"
                    "Engineering Team,\n\n"
                    "Pin map review and sign-off is required before replacement IC component ([part number]) enters production.\n"
                    "System is currently blocking (basis: HR-009, INC-001).\n\n"
                    "■ Review checklist:\n"
                    "  □ Cross-check original / replacement component datasheets\n"
                    "  □ Pin map 1:1 verification (VCC, GND, signal pins)\n"
                    "  □ Electrical characteristic compatibility check\n"
                    "  □ Functional equivalence determination (drop-in or not)\n"
                    "  □ Engineering team sign-off: ___________\n\n"
                    "After sign-off, resubmit to the system to release the production lock.\n\n"
                    "Reference: INC-001 — same procedure skipped → $20,000 rework (2026-04-22)\n\n"
                    "[Procurement Officer]"
                ),
                "diff": [
                    ("del", "# Previous process: procurement verbal confirmation then production"),
                    ("add", "# Changed: engineering sign-off mandatory (HR-009 applied)"),
                    ("ctx", ""),
                    ("del", "Procurement confirmation: 'verified by phone with supplier' (checkbox)"),
                    ("add", "Engineering confirmation: datasheet cross-check + sign-off required"),
                    ("ctx", ""),
                    ("del", "→ production can proceed immediately"),
                    ("add", "→ resubmit to system after engineering sign-off → lock released"),
                    ("ctx", ""),
                    ("ctx", "Basis: INC-001 — verbal confirmation only → $20,000 rework"),
                ],
            },
            "route": {
                "label":  "📤 Route — escalate to Engineering Lead",
                "output_title": "Engineering Lead Escalation",
                "output": (
                    "To: Engineering Lead\n"
                    "From: Procurement\n"
                    "Subject: [Escalation] Replacement component pin map unconfirmed — production blocked\n\n"
                    "Issue:\n"
                    "  The pin map of replacement IC component ([part number]) has not been confirmed by engineering.\n"
                    "  Production line entry is blocked by the system.\n\n"
                    "Block basis:\n"
                    "  - HR-009: M1 replacement pin map confirmation is a mandatory engineering sign-off item\n"
                    "  - INC-001: same procedure skipped → $20,000 rework incident (2026-04-22)\n\n"
                    "Current status:\n"
                    "  - Procurement verbal confirmation recorded → not accepted by system\n"
                    "  - Engineering datasheet cross-check and sign-off required\n\n"
                    "Request: Please assign an engineering contact and confirm the review schedule.\n\n"
                    "Production on hold — prompt response appreciated."
                ),
            },
        },
    },

    "📧 Case 4 — Email draft: clause conflict blocks send": {
        "title": "Pre-Send Contract Gate",
        "subtitle": "Email draft accepts partial delivery and waives further claims. Contract has liability cap + no-waiver clause.",
        "narrative": "You wrote a quick reply to close out a supplier dispute — friendly tone, accepting the partial shipment, saying 'no further claims.' The gate intercepts it before it leaves your outbox and flags two phrases that would forfeit $10,000 in penalty rights.",
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
            "owner": {"role": "Author or Legal Team", "action": "Fix — remove risky language and revise, or Route to Legal", "why": "Author can revise wording / waiver judgment requires legal review"},
            "user_verdict": "This email must not be sent right now",
            "user_verdict_sub": "Two sentences may be interpreted as forfeiting your $10,000 claim",
            "user_reason": (
                "The phrases 'consider the matter closed' and 'no further claims' can be legally "
                "interpreted as a waiver. Clause 6.1 of the contract states that no right shall be "
                "deemed waived without written agreement — these phrases conflict with that clause. "
                "The liability cap under Clause 5.3 ($45,000) also risks being undermined by this language. "
                "The substance (accepting partial delivery) is fine — the wording is the problem."
            ),
            "user_action": "Replace that language with: 'Accepting partial delivery without prejudice to existing claims under Clause 4.2.'",
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
                "label":  "🔧 Fix it — replace with safe draft",
                "output_title": "Revised Email Draft (rights preserved)",
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
                    ("ctx", "# Clause 6.1 violation language removed / Clause 5.3 violation language removed"),
                ],
            },
            "route": {
                "label":  "📤 Route — escalate to Legal Team",
                "output_title": "Legal Team Review Request",
                "output": (
                    "To: Legal Team\n"
                    "From: [Contact]\n"
                    "Subject: [Review Request] Contract clause conflict check before email send\n\n"
                    "Issue:\n"
                    "  The email draft contains language that conflicts with contract clauses.\n"
                    "  System has blocked sending.\n\n"
                    "Conflicting clauses:\n"
                    "  - Clause 6.1: 'consider the matter closed' → interpreted as rights waiver\n"
                    "  - Clause 5.3: 'no further claims' → undermines liability cap\n"
                    "  - Clause 7.2: modification of obligations without written consent\n\n"
                    "Financial impact: risk of forfeiting $10,000 penalty claim\n\n"
                    "Requested actions:\n"
                    "  □ Approve revised wording or provide alternative\n"
                    "  □ Confirm whether sending is permissible\n\n"
                    "Currently blocked — will resubmit after approval"
                ),
            },
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# GATE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _run_procurement_engine(cfg: dict) -> dict:
    try:
        from verticals.procurement.schema import ProcurementCase
        from verticals.procurement.rule_extractor import evaluate
        from verticals.procurement.judgment_adapter import _confidence_to_float, _risk_from_procurement

        pc = ProcurementCase(
            case_id             = str(uuid.uuid4()),
            raw_description     = cfg.get("subtitle", ""),
            dispute_type        = cfg.get("dispute_type", "unknown"),
            supplier_id         = cfg.get("supplier_id"),
            penalty_clause      = cfg.get("penalty_clause"),
            delivery_delay_days = cfg.get("delivery_delay_days"),
            contract_value      = cfg.get("contract_value"),
            payment_overdue     = cfg.get("payment_overdue"),
            contract_active     = cfg.get("contract_active"),
            single_source       = cfg.get("single_source"),
            alt_supplier_ready  = cfg.get("alt_supplier_ready"),
            urgency             = cfg.get("urgency"),
            supply_risk         = cfg.get("supply_risk"),
        )
        r = evaluate(pc)

        decision = "ALLOW" if r.status == "ALLOW" else "HOLD"
        risk_d   = {"supply_risk": cfg.get("supply_risk","medium"), "win_prob_pct": r.win_prob_pct}

        reason_parts = [r.conclusion or ""]
        if r.reasoning:
            reason_parts.append(str(r.reasoning[0]))
        reason = " | ".join(p for p in reason_parts if p)[:300]

        unblock = ""
        if r.hold_reasons:
            h = r.hold_reasons[0]
            unblock = h.get("resume","") if isinstance(h, dict) else str(h)
        elif decision == "ALLOW" and r.actions:
            unblock = str(r.actions[0])

        evidence_raw = [
            (("pos" if ev.effect > 0 else "neg"), ev.reason, f"{'+' if ev.effect>0 else ''}{ev.effect:.3f}")
            for ev in (r.evidence_layer or [])[:5]
        ]

        return {
            "decision": decision,
            "reason":   reason,
            "unblock":  unblock,
            "financial_impact": None,
            "execution_locked": decision == "HOLD",
            "evidence": evidence_raw,
            "confidence": _confidence_to_float(r.confidence),
            "risk":       _risk_from_procurement(risk_d),
        }
    except Exception as e:
        return {
            "decision": "HOLD",
            "reason":   f"Engine error — fail-closed. ({e})",
            "unblock":  "Check input fields and retry.",
            "financial_impact": None,
            "execution_locked": True,
            "evidence": [("neg", str(e)[:100], "error")],
            "confidence": 0.0,
            "risk": "high",
        }


def _run_fourm_engine(cfg: dict) -> dict:
    try:
        from verticals.fourm.judgment_adapter import run_judgment
        case = {
            "id":    str(uuid.uuid4()),
            "domain": "fourm",
            "raw":    cfg.get("subtitle", ""),
            "scope": {
                "fourm_type":        cfg.get("fourm_type", "M1_material"),
                "pin_map_changed":   cfg.get("pin_map_changed", "UNKNOWN"),
                "functional_change": cfg.get("functional_change", "UNKNOWN"),
                "phase":             cfg.get("phase", "MP"),
                "product_type":      cfg.get("product_type", "EXISTING"),
                "comp_type":         cfg.get("component_type", "logic"),
            },
            "fields": {},
        }
        r = run_judgment(case)
        decision = r.get("decision", "HOLD")
        evidence_raw = []
        for ev in (r.get("evidence") or [])[:5]:
            if isinstance(ev, dict):
                eff = ev.get("effect", 0)
                evidence_raw.append(
                    ("pos" if eff > 0 else "neg", ev.get("reason", ev.get("rule_id","")), f"{'+' if eff>0 else ''}{eff:.3f}")
                )
        return {
            "decision": decision,
            "reason":   r.get("reason",""),
            "unblock":  r.get("unblock_action",""),
            "financial_impact": None,
            "execution_locked": decision not in ("ALLOW","CONDITIONAL_ALLOW"),
            "evidence": evidence_raw,
            "confidence": r.get("confidence", 0.5),
            "risk":       r.get("risk","high"),
        }
    except Exception as e:
        return {
            "decision": "HOLD", "reason": f"Engine error ({e})", "unblock": "",
            "financial_impact": None, "execution_locked": True,
            "evidence": [("neg", str(e)[:100], "error")], "confidence":0.0, "risk":"high",
        }


def run_gate(cfg: dict) -> dict:
    override = cfg.get("gate_override")
    if override is not None:
        ev = override.get("evidence", [])
        return {
            "decision":         override["decision"],
            "reason":           override["reason"],
            "unblock":          override.get("unblock",""),
            "financial_impact": override.get("financial_impact"),
            "execution_locked": override.get("execution_locked", False),
            "evidence":         ev,
            "confidence":       override.get("confidence", 0.8),
            "risk":             override.get("risk","high"),
        }
    # live engine
    domain = cfg.get("domain","procurement")
    if domain == "fourm":
        return _run_fourm_engine(cfg)
    return _run_procurement_engine(cfg)


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
st.markdown(
    '<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:4px">'
    '<span style="font-family:Fraunces,serif;font-size:2rem;font-weight:500;color:#f4efe3;letter-spacing:-0.02em">⚡ Echo Decision Gate</span>'
    '<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.75rem;color:#7a7367;letter-spacing:0.14em;text-transform:uppercase">v0.3 · preview</span>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="font-family:Fraunces,serif;font-size:1.1rem;font-weight:300;color:#b5aea1;margin-bottom:18px;font-style:italic">'
    'If we block it, we assign it.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hook">'
    '<b>Case 3:</b> $20,000 loss. Procurement signed off on an engineering decision. '
    'Not a data problem — an authority problem. '
    'HOLD wouldn\'t have caught it. <b>REDIRECT does.</b>'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()

# case selector — default to Case 3 (REDIRECT, the novel state)
_case_keys = list(DEMO_CASES.keys())
_default_idx = next((i for i, k in enumerate(_case_keys) if "Case 3" in k), 0)
selected = st.selectbox("**Select a case**", _case_keys, index=_default_idx)
cfg = DEMO_CASES[selected]

if cfg is None:
    st.info("Select a case above to see the gate in action.")
    st.stop()

left, right = st.columns([1, 1], gap="large")

# ── LEFT: INPUT ───────────────────────────────────────────────────────────────
with left:
    st.markdown(f"### {cfg['title']}")
    st.caption(cfg["subtitle"])

    # narrative — situation in plain language
    if cfg.get("narrative"):
        st.markdown(
            f'<div style="background:rgba(125,157,196,0.08);border-left:2px solid #7d9dc4;'
            f'padding:12px 16px;margin:10px 0 18px 0;font-size:0.9rem;color:#b5aea1;'
            f'line-height:1.6;font-family:\'Fraunces\',serif">'
            f'{cfg["narrative"]}</div>',
            unsafe_allow_html=True,
        )

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
    skip = {"title","subtitle","narrative","domain","contract_clauses","gate_override","email_draft","incident","loss_amount"}
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

    # raw input JSON (collapsed by default)
    _skip_json = {"title","subtitle","narrative","domain","contract_clauses","gate_override",
                  "email_draft","incident","loss_amount","user_verdict_live"}
    _raw_input = {k: v for k, v in cfg.items() if k not in _skip_json and v is not None}
    with st.expander("{ } Raw input passed to gate", expanded=False):
        st.code(json.dumps(_raw_input, indent=2, ensure_ascii=False), language="json")

    if cfg.get("incident"):
        st.error(f"⚠️ Incident on record: **{cfg['incident']}** — Loss: {cfg.get('loss_amount','')}")

# ── RIGHT: RESULT ─────────────────────────────────────────────────────────────
with right:
    st.markdown("### Gate Result")
    with st.spinner("Analyzing..."):
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
    # live engine cases: pick verdict based on actual decision outcome
    _live_map = cfg.get("user_verdict_live", {})
    if _live_map and not override:
        _live = _live_map.get(decision, _live_map.get("HOLD", {}))
        user_verdict = _live.get("verdict")
        user_sub     = _live.get("sub")
        user_reason  = _live.get("reason")
        user_action  = _live.get("action")
    else:
        user_verdict = override.get("user_verdict")
        user_sub     = override.get("user_verdict_sub")
        user_reason  = override.get("user_reason")
        user_action  = override.get("user_action")

    # ── 1. PRIMARY VERDICT: user language ──────────────────────────────────────
    if user_verdict:
        _vdict = {
            "HOLD":         ("rgba(212,168,83,0.13)",  "#d4a853"),
            "REDIRECT_DEV": ("rgba(193,116,88,0.13)",  "#c17458"),
            "ALLOW":        ("rgba(122,153,112,0.13)", "#7a9970"),
        }
        verdict_bg, verdict_border = _vdict.get(decision, ("#1f1c18", "#3a342c"))
        sub_html = f'<div style="font-size:0.9rem;margin-top:6px;color:#b5aea1">{user_sub}</div>' if user_sub else ""
        st.markdown(
            f'<div style="background:{verdict_bg};border-left:3px solid {verdict_border};'
            f'color:#f4efe3;padding:16px 20px;border-radius:0 8px 8px 0;margin-bottom:8px;'
            f'font-family:\'Fraunces\',serif">'
            f'<div style="font-size:1.3rem;font-weight:700">{user_verdict}</div>{sub_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="{_decision_css(decision)}">{_decision_icon(decision)} {decision}</div>',
            unsafe_allow_html=True,
        )

    # ── 1b. OWNER badge ───────────────────────────────────────────────────────
    _owner_cfg = override.get("owner")
    if not _owner_cfg and decision == "ALLOW":
        _owner_cfg = {"role": "System Approved", "action": "Gate passed — execution authorized"}
    if _owner_cfg:
        _badge_class = {
            "HOLD":        "owner-badge-hold",
            "REDIRECT_DEV":"owner-badge-redirect",
            "ALLOW":       "owner-badge-allow",
        }.get(decision, "owner-badge-hold")
        _owner_icon = {"HOLD": "👤", "REDIRECT_DEV": "🔀", "ALLOW": "✅"}.get(decision, "📌")
        _owner_why = _owner_cfg.get("why", "")
        _why_html = (
            f'<div style="font-size:0.78rem;color:#7a7367;margin-top:4px;padding-left:2px;'
            f'font-family:\'JetBrains Mono\',monospace">'
            f'Why this owner: {_owner_why}</div>'
            if _owner_why else ""
        )
        st.markdown(
            f'<div style="margin:6px 0 10px 0">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<div class="{_badge_class}">'
            f'{_owner_icon} Owner: {_owner_cfg["role"]}</div>'
            f'<div style="font-size:0.82rem;color:#b5aea1">{_owner_cfg["action"]}</div>'
            f'</div>{_why_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── 2. Reason (user language preferred) ───────────────────────────────────────
    if user_reason:
        st.markdown(user_reason)
    else:
        st.markdown(f"**{reason}**")

    # ── 3. Financial impact ─────────────────────────────────────────────────────────
    if fin_impact:
        st.markdown(
            f'<div class="impact-box">💰 Financial impact: <b>{fin_impact}</b></div>',
            unsafe_allow_html=True,
        )

    # ── 4. Next Action ───────────────────────────────────────────────────
    display_action = user_action or unblock
    if display_action:
        st.info(f"**Next Action:** {display_action}")

    st.divider()

    # ── 5. Execution lock — Streamlit native button (truly unclickable) ───────────
    action_label = cfg.get("action_label", "✅  Execute")
    block_rule   = override.get("reason", reason)[:80] if locked else ""

    # BLOCKED case: button disabled + block message on click (st.button with disabled=True fires no events)
    # ALLOW case: button active, click shows success popup

    st.markdown("**Execute**")

    if locked:
        # disabled=True → Streamlit actually prevents clicking
        st.button(
            f"🔒  {action_label.lstrip('✅📨🏭📤 ')} — Blocked by Contract Gate",
            disabled=True,
            use_container_width=True,
            help=f"Block basis: {block_rule}",
        )
        st.markdown(
            f'<div style="background:rgba(193,116,88,0.10);border-left:3px solid #c17458;'
            f'border-radius:0 6px 6px 0;'
            f'padding:10px 14px;margin-top:6px;font-size:0.88rem;color:#f4efe3">'
            f'🚫 <b>Execution blocked by policy</b><br>'
            f'<span style="color:#b5aea1">Basis: {override.get("reason", reason)[:120]}...</span>'
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
                f"✅ **Execution authorized** — Gate passed. Audit record saved.\n\n"
                f"Confidence {int(conf*100)}% | Risk {risk.upper()} | Decision: ALLOW"
            )

    # ── 6. Fix / Route (only when BLOCKED) ─────────────────────────────────────
    fix_action   = override.get("fix")
    route_action = override.get("route")

    if locked and (fix_action or route_action):
        st.divider()
        st.markdown("**Choose one of the following**")
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
                "font-family:'Public Sans',sans-serif;"
            )
            st.markdown(
                f'<a href="{_mailto_fix}" target="_blank" style="{_btn_style}background:rgba(125,157,196,0.18);color:#7d9dc4;border:1px solid #7d9dc4">✉️ Draft Email — Ready to Send</a>'
                f'<span style="font-size:0.78rem;color:#7a7367;font-family:\'JetBrains Mono\',monospace">← content pre-filled · review before sending</span>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

            # diff — always expanded
            diff_lines = fix_action.get("diff", [])
            if diff_lines:
                with st.expander("Changes (before / after)", expanded=True):
                    diff_colors = {"add": "#9cc28d", "del": "#d19682", "ctx": "#7a7367"}
                    diff_bg     = {"add": "rgba(122,153,112,0.10)", "del": "rgba(193,116,88,0.09)", "ctx": "transparent"}
                    diff_prefix = {"add": "+ ", "del": "- ", "ctx": "  "}
                    diff_extra  = {"del": "text-decoration:line-through;"}
                    html_rows = ""
                    for kind, line in diff_lines:
                        prefix  = diff_prefix.get(kind, "  ")
                        color   = diff_colors.get(kind, "#b5aea1")
                        bg      = diff_bg.get(kind, "transparent")
                        extra   = diff_extra.get(kind, "")
                        html_rows += (
                            f'<div style="background:{bg};color:{color};font-family:\'JetBrains Mono\',monospace;'
                            f'font-size:0.83rem;padding:2px 10px;border-radius:2px;{extra}">'
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
                f'<a href="{_mailto_route}" target="_blank" style="{_btn_style}background:rgba(193,116,88,0.18);color:#c17458;border:1px solid #c17458">✉️ Prepare Handoff Email</a>'
                f'<span style="font-size:0.78rem;color:#7a7367;font-family:\'JetBrains Mono\',monospace">← recipient + content pre-filled · review before sending</span>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── 7. Internal reasoning (collapsible for developers/HN) ──────────────────────────────
    with st.expander("🔧 View Internal Reasoning (Engine / Evidence Chain)", expanded=False):
        st.markdown(
            '<div style="background:#1f1c18;border-left:3px solid #7d9dc4;padding:7px 12px;'
            'border-radius:0 4px 4px 0;font-size:0.82rem;margin-bottom:12px;color:#b5aea1;'
            'font-family:\'Public Sans\',sans-serif">'
            '⚙️ <b style="color:#f4efe3">Judgment is deterministic</b> (rule-based clause matching — no LLM in the decision path). '
            '<b style="color:#f4efe3">Drafted outputs are AI-assisted</b> (editable before sending).'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**Internal decision code:** `{decision}`")
        st.progress(conf, text=f"Confidence: {int(conf*100)}%  |  Risk: {risk.upper()}")
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
            f'<div style="border-left:3px solid #3a342c;padding:8px 12px;background:#1b1815;'
            f'border-radius:0 4px 4px 0;margin-bottom:8px;color:#f4efe3;'
            f'font-family:\'Public Sans\',sans-serif">'
            f'<b style="font-family:\'Fraunces\',serif">{_title_why}</b><br>'
            f'<span style="font-size:0.85rem;color:#b5aea1">{_body_why}</span></div>',
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

with st.expander("**Why three outcomes — ALLOW / HOLD / REDIRECT?**", expanded=False):
    st.markdown("""
Most guardrails have two states: **pass** or **warn**. This gate has three — because the question isn't just *"is this safe?"* It's *"who has the authority to decide?"*

| Outcome | Meaning | Owner |
|---|---|---|
| ✅ **ALLOW** | All rules passed. Proceed. | Gate signs off |
| 🛑 **HOLD** | Condition unmet. Submitter can fix and retry. | Submitter |
| 🔀 **REDIRECT** | Wrong person deciding. No amount of data changes that. | Redirected party |

**HOLD vs REDIRECT is the key distinction.**

HOLD = *not yet.* Fix the data, come back.

REDIRECT = *not you.* The decision authority belongs elsewhere. Case 3 is the real example: procurement checked "confirmed" in a spreadsheet. That's not a data problem — that's an authority problem. HOLD wouldn't catch it. REDIRECT does. The gap cost $20,000.
""")

st.markdown("""
<div style="font-size:0.78rem;color:#7a7367;text-align:center;font-family:'JetBrains Mono',monospace;margin-top:12px">
  Echo Decision Gate · rule engine + evidence chain + execution lock<br>
  Verticals: procurement · 4M manufacturing change control · contract enforcement · pre-send gate<br>
  <b style="color:#b5aea1">The gate doesn't advise. It decides — and blocks.</b>
  <br><br>
  <span style="color:#3a342c">──────────────────────────────────────────</span><br>
  <span style="color:#7a7367">
  Demo note: contract clauses shown here are pre-defined for illustration.<br>
  In production, a contract PDF is uploaded → clauses are auto-parsed → mapped to gate rules.
  </span>
</div>
""", unsafe_allow_html=True)
