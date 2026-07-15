"""Critic / Reflection Node.

Validates all agent outputs before human review:
- M4Q(R2) dossier: DMCS completeness, section structure
- E2B(R3) XML: well-formedness, required fields
- Assessment: completeness check

If issues found, signals graph to loop back for correction (max 2 loops).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage

from arivo.agents.state import ArivoState
from arivo.tools.e2b_validator import validate_e2b_xml


def critic_node(state: ArivoState) -> dict[str, Any]:
    """Validate all pipeline outputs and provide feedback."""
    now = datetime.now(timezone.utc).isoformat()
    feedback: list[str] = []
    reflection_count = state.get("reflection_count", 0)

    # 1. Validate regulatory assessment
    assessment = state.get("regulatory_assessment", {})
    if not assessment:
        feedback.append("CRITICAL: No regulatory assessment generated.")
    else:
        if not assessment.get("gap_analysis"):
            feedback.append("WARNING: Gap analysis is empty.")
        if not assessment.get("strategy_summary"):
            feedback.append("WARNING: Strategy summary is empty.")
        if not assessment.get("supac"):
            feedback.append("CRITICAL: SUPAC classification missing.")

    # 2. Validate dossier sections
    dossier = state.get("dossier_sections", {})
    if not dossier:
        feedback.append("CRITICAL: No dossier sections generated.")
    else:
        m23 = dossier.get("module_2_3", {})
        if not m23.get("section_2_3_2"):
            feedback.append("WARNING: Module 2.3.2 (Control Strategy) is empty.")
        if not m23.get("section_2_3_4"):
            feedback.append("WARNING: Module 2.3.4 (Development Justification) is empty.")

        m3 = dossier.get("module_3", {})
        for material in ["drug_substance", "drug_product"]:
            mat = m3.get(material, {})
            for pillar in ["description", "manufacture", "control", "storage"]:
                if not mat.get(pillar):
                    feedback.append(f"WARNING: Module 3 {material}.{pillar} (DMCS) is empty.")

        # Propagate existing compliance notes
        for note in dossier.get("dmcs_compliance_notes", []):
            if note not in feedback:
                feedback.append(note)

    # 3. Validate E2B XML (if applicable)
    e2b_xml = state.get("e2b_xml", "")
    if state.get("has_adverse_event") and e2b_xml:
        validation = validate_e2b_xml(e2b_xml)
        for err in validation.get("errors", []):
            feedback.append(f"E2B ERROR: {err}")
        for warn in validation.get("warnings", []):
            feedback.append(f"E2B WARNING: {warn}")
    elif state.get("has_adverse_event") and not e2b_xml:
        feedback.append("CRITICAL: Adverse event detected but no E2B XML generated.")

    # Determine if we pass
    critical_count = sum(1 for f in feedback if f.startswith("CRITICAL"))
    is_pass = critical_count == 0 and reflection_count >= 1  # Allow at least one review cycle
    # On first pass, always pass if no critical issues
    if reflection_count == 0 and critical_count == 0:
        is_pass = True

    # Cap reflection loops
    if reflection_count >= 2:
        is_pass = True
        feedback.append("NOTE: Maximum reflection loops (2) reached. Proceeding to review.")

    status = "review" if is_pass else "running"

    summary_parts = [
        f"[Critic] Validation {'PASSED' if is_pass else 'FAILED'} (Reflection #{reflection_count + 1})",
        f"Findings: {len(feedback)} items ({critical_count} critical)",
    ]
    for f in feedback:
        summary_parts.append(f"  • {f}")

    if is_pass:
        summary_parts.append("\n✅ Pipeline outputs validated. Ready for human review and sign-off.")
    else:
        summary_parts.append("\n🔄 Routing back to agents for correction.")

    return {
        "critic_feedback": feedback,
        "critic_pass": is_pass,
        "reflection_count": reflection_count + 1,
        "status": status,
        "current_agent": "critic",
        "messages": [AIMessage(content="\n".join(summary_parts))],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "critic",
                "action": "VALIDATION_COMPLETE",
                "detail": f"Pass: {is_pass}. Items: {len(feedback)}. Critical: {critical_count}. Reflection: {reflection_count + 1}.",
            }
        ],
    }
