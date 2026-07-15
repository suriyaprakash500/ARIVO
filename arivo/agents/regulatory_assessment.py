"""Regulatory Assessment Agent.

Evaluates manufacturing changes against SUPAC and EMA guidelines.
Uses deterministic rules for classification + LLM for gap analysis narrative.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from arivo.config import settings
from arivo.agents.state import ArivoState
from arivo.tools.regulatory_rules import classify_ema, classify_supac


_SYSTEM_PROMPT = """You are a senior regulatory affairs specialist working in CMC (Chemistry, Manufacturing, and Controls) for pharmaceutical post-approval changes.

You are evaluating a manufacturing change that has been classified under FDA SUPAC guidelines. Your task is to write a concise regulatory gap analysis and strategy recommendation.

You MUST:
1. Reference the specific SUPAC guidance applicable to this dosage form
2. Explain why the change falls into the assigned level
3. Identify any additional testing or documentation needed
4. Note if any special considerations apply (e.g., semisolid microstructure, bioequivalence waivers)
5. If the product is marketed in the EU, note the corresponding EMA variation type
6. Keep the response focused, professional, and suitable for a regulatory submission strategy document

Do NOT hallucinate regulatory requirements. Stick to what SUPAC and EMA guidelines actually require."""


def regulatory_assessment_node(state: ArivoState) -> dict[str, Any]:
    """Assess the regulatory impact of the extracted change control."""
    now = datetime.now(timezone.utc).isoformat()
    qms_data = state.get("qms_data", {})

    if not qms_data:
        return {
            "regulatory_assessment": {},
            "current_agent": "regulatory_assessment",
            "messages": [AIMessage(content="[Regulatory Assessment] No QMS data available for assessment.")],
            "audit_trail": [{"timestamp": now, "agent": "regulatory_assessment", "action": "SKIPPED", "detail": "No QMS data"}],
        }

    # --- Deterministic classification ---
    dosage_form = ""
    products = qms_data.get("affected_products", [])
    if products:
        dosage_form = products[0].get("dosage_form", "")

    supac_result = classify_supac(
        change_category=qms_data.get("change_category", ""),
        dosage_form=dosage_form,
        change_description=qms_data.get("description", ""),
    )

    ema_result = classify_ema(supac_result["filing_type"])

    # Determine overall risk
    risk_map = {"Annual Report": "Low", "CBE-0": "Low", "CBE-30": "Medium", "PAS": "High"}
    overall_risk = risk_map.get(supac_result["filing_type"], "High")

    # Affected CTD sections based on change type
    affected_sections = ["2.3.2", "2.3.4"]  # Always Module 2.3
    change_type = qms_data.get("change_type", "")
    if "site" in change_type.lower() or "manufacturing" in change_type.lower():
        affected_sections.extend(["3.2.S.2", "3.2.S.4", "3.2.S.7"])
    if "formulation" in change_type.lower() or "composition" in change_type.lower():
        affected_sections.extend(["3.2.P.1", "3.2.P.3", "3.2.P.5"])
    if "analytical" in change_type.lower():
        affected_sections.extend(["3.2.S.4", "3.2.P.5"])
    if "process" in change_type.lower():
        affected_sections.extend(["3.2.P.3", "3.2.P.5"])

    # --- LLM gap analysis ---
    gap_analysis = ""
    strategy_summary = ""
    try:
        llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.1)
        prompt = f"""Analyze the following pharmaceutical manufacturing change and provide a regulatory gap analysis:

CHANGE CONTROL: {qms_data.get('change_control_id', '')}
TITLE: {qms_data.get('title', '')}
DESCRIPTION: {qms_data.get('description', '')}
CHANGE TYPE: {qms_data.get('change_type', '')}
DOSAGE FORM: {dosage_form}
CURRENT STATE: {qms_data.get('current_state', '')}
PROPOSED STATE: {qms_data.get('proposed_state', '')}
JUSTIFICATION: {qms_data.get('justification', '')}

SUPAC CLASSIFICATION:
- Guidance: {supac_result['guidance']}
- Level: {supac_result['level']}
- Filing Type: {supac_result['filing_type']}
- Required Tests: {', '.join(supac_result['required_tests'])}
- Level Description: {supac_result['level_description']}

EMA CLASSIFICATION: {ema_result['variation_type']}

MARKETS: {', '.join(products[0].get('markets', [])) if products else 'US'}

Provide:
1. A GAP ANALYSIS paragraph explaining the regulatory rationale
2. A STRATEGY SUMMARY paragraph with the recommended filing approach"""

        response = llm.invoke([
            HumanMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        # Split response into gap analysis and strategy
        full_text = response.content
        if "STRATEGY SUMMARY" in full_text.upper():
            parts = full_text.upper().split("STRATEGY SUMMARY")
            gap_idx = full_text.upper().find("STRATEGY SUMMARY")
            gap_analysis = full_text[:gap_idx].replace("GAP ANALYSIS", "").replace("1.", "").strip().strip(":")
            strategy_summary = full_text[gap_idx:].replace("STRATEGY SUMMARY", "").strip().strip(":")
        else:
            gap_analysis = full_text
            strategy_summary = f"Recommended filing: {supac_result['filing_type']} based on SUPAC Level {supac_result['level']} classification."
    except Exception as e:
        gap_analysis = f"LLM analysis unavailable ({e}). Deterministic classification applied."
        strategy_summary = f"Recommended filing: {supac_result['filing_type']} based on SUPAC Level {supac_result['level']} classification."

    assessment = {
        "change_control_id": qms_data.get("change_control_id", ""),
        "supac": supac_result,
        "ema": ema_result,
        "overall_risk": overall_risk,
        "recommended_submission": supac_result["filing_type"],
        "affected_ctd_sections": affected_sections,
        "gap_analysis": gap_analysis,
        "strategy_summary": strategy_summary,
        "citations": [
            f"SUPAC Guidance: {supac_result['guidance']}",
            f"Classification Rule: Level {supac_result['level']} — {supac_result['level_description']}",
            f"EMA Mapping: {supac_result['filing_type']} → {ema_result['variation_type']}",
        ],
    }

    summary = (
        f"[Regulatory Assessment] Completed assessment for {qms_data.get('change_control_id', '')}.\n"
        f"SUPAC Classification: Level {supac_result['level']} ({supac_result['filing_type']})\n"
        f"EMA Classification: {ema_result['variation_type']}\n"
        f"Overall Risk: {overall_risk}\n"
        f"Affected CTD Sections: {', '.join(affected_sections)}\n"
        f"Required Tests: {', '.join(supac_result['required_tests'])}\n\n"
        f"Gap Analysis:\n{gap_analysis}\n\n"
        f"Strategy:\n{strategy_summary}"
    )

    return {
        "regulatory_assessment": assessment,
        "current_agent": "regulatory_assessment",
        "messages": [AIMessage(content=summary)],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "regulatory_assessment",
                "action": "ASSESSMENT_COMPLETE",
                "detail": f"SUPAC Level {supac_result['level']} → {supac_result['filing_type']}. Risk: {overall_risk}.",
                "citations": assessment["citations"],
            }
        ],
    }
