"""QMS Extraction Agent.

Interfaces with the mock Veeva Vault QMS to extract change control
metadata and unstructured narratives. Sets the adverse event routing flag.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage

from arivo.agents.state import ArivoState
from arivo.tools import veeva_client


def qms_extraction_node(state: ArivoState) -> dict[str, Any]:
    """Extract change control data from the QMS.

    This is a deterministic node — no LLM needed. It queries the mock
    Veeva API and structures the response into the workflow state.
    """
    cc_id = state["change_control_id"]
    now = datetime.now(timezone.utc).isoformat()

    # Authenticate with Veeva
    auth = veeva_client.authenticate()
    session_id = auth["sessionId"]

    # Query the change control record
    response = veeva_client.query_change_control(cc_id)

    if response["responseStatus"] != "SUCCESS":
        return {
            "qms_data": {},
            "status": "error",
            "current_agent": "qms_extraction",
            "messages": [AIMessage(content=f"[QMS Extraction] Failed to retrieve {cc_id}: {response}")],
            "audit_trail": [
                {
                    "timestamp": now,
                    "agent": "qms_extraction",
                    "action": "QUERY_FAILED",
                    "detail": f"Change control {cc_id} not found in QMS",
                    "source_system": "Veeva Vault QMS",
                    "session_id": session_id,
                }
            ],
        }

    record = response["data"][0]

    # Determine if adverse event exists
    has_ae = record.get("adverse_event") is not None

    # Get attachments list
    attachments = veeva_client.get_attachments(cc_id)

    # Build extraction summary
    summary_parts = [
        f"[QMS Extraction] Successfully extracted change control {cc_id}.",
        f"Title: {record['title']}",
        f"Type: {record['change_type']} | Category: {record['change_category']}",
        f"Current State: {record['current_state']}",
        f"Proposed State: {record['proposed_state']}",
        f"Justification: {record['justification']}",
        f"Affected Products: {', '.join(p['product_name'] for p in record.get('affected_products', []))}",
        f"Attachments: {', '.join(attachments) if attachments else 'None'}",
        f"Adverse Event Detected: {'YES — routing to PV E2B(R3) agent' if has_ae else 'No'}",
    ]

    if record.get("deviation"):
        dev = record["deviation"]
        summary_parts.extend([
            f"\nDeviation: {dev['deviation_id']}",
            f"Root Cause: {dev['root_cause']}",
            f"Batch Disposition: {dev['batch_disposition']}",
        ])

    if has_ae:
        ae = record["adverse_event"]
        summary_parts.extend([
            f"\nAdverse Event: {ae['ae_id']}",
            f"Reaction: {ae['reaction_description']}",
            f"MedDRA PT: {ae['meddra_pt']} ({ae['meddra_code']})",
            f"Seriousness: {ae['seriousness']}",
        ])

    summary = "\n".join(summary_parts)

    # Build citations for ALCOA+ traceability
    citations = [
        f"Veeva Vault QMS: change_control__c/{cc_id}",
        f"API endpoint: /api/v24.1/vobjects/change_control__c/{cc_id}",
        f"Session: {session_id}",
        f"Extraction timestamp: {now}",
    ]

    return {
        "qms_data": record,
        "has_adverse_event": has_ae,
        "current_agent": "qms_extraction",
        "messages": [AIMessage(content=summary)],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "qms_extraction",
                "action": "DATA_EXTRACTED",
                "detail": f"Extracted {cc_id} with {len(record.get('affected_products', []))} affected products. AE={'Yes' if has_ae else 'No'}.",
                "source_system": "Veeva Vault QMS",
                "session_id": session_id,
                "citations": citations,
            }
        ],
    }
