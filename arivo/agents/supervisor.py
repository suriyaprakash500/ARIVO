"""Supervisor / Orchestrator Agent.

Central node that receives the trigger and routes tasks to specialist agents.
Uses deterministic routing (not LLM-based) for predictable GxP workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage

from arivo.agents.state import ArivoState


def supervisor_node(state: ArivoState) -> dict[str, Any]:
    """Determine the next agent to execute based on current pipeline state.

    Routing logic (deterministic):
    1. If no QMS data extracted → route to qms_extraction
    2. If QMS data exists but no assessment → route to regulatory_assessment
    3. If assessment exists but no dossier → route to dossier_structuring
    4. If adverse event exists and no E2B XML → route to pv_e2b
    5. If all drafting complete → route to critic
    6. If critic passed → route to END (human review)
    7. If critic failed → route back to dossier_structuring (re-draft)
    """
    now = datetime.now(timezone.utc).isoformat()

    # Determine next agent
    has_qms = bool(state.get("qms_data"))
    has_assessment = bool(state.get("regulatory_assessment"))
    has_dossier = bool(state.get("dossier_sections"))
    has_ae = state.get("has_adverse_event", False)
    has_e2b = bool(state.get("e2b_xml"))
    critic_pass = state.get("critic_pass", False)
    current = state.get("current_agent", "")

    if not has_qms:
        next_agent = "qms_extraction"
        reason = "No QMS data available — initiating extraction"
    elif not has_assessment:
        next_agent = "regulatory_assessment"
        reason = "QMS data extracted — initiating regulatory assessment"
    elif not has_dossier:
        next_agent = "dossier_structuring"
        reason = "Assessment complete — initiating M4Q(R2) dossier drafting"
    elif has_ae and not has_e2b:
        next_agent = "pv_e2b"
        reason = "Adverse event detected — routing to PV E2B(R3) formatting"
    elif current == "critic" and not critic_pass:
        next_agent = "dossier_structuring"
        reason = "Critic found issues — routing back for correction"
    elif current != "critic":
        next_agent = "critic"
        reason = "All drafting complete — routing to critic for validation"
    else:
        next_agent = "END"
        reason = "Critic passed — pipeline complete, awaiting human review"

    message = f"[Supervisor] Routing decision: {reason} → {next_agent}"

    return {
        "next_agent": next_agent,
        "current_agent": "supervisor",
        "status": "running" if next_agent != "END" else "review",
        "messages": [AIMessage(content=message)],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "supervisor",
                "action": "ROUTING_DECISION",
                "detail": f"{reason}. Next: {next_agent}.",
            }
        ],
    }
