"""PV E2B(R3) Formatting Agent.

Triggers only when an adverse event is detected. Maps unstructured
narrative data into HL7 v3 XML format for E2B(R3) ICSR submission.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage

from arivo.agents.state import ArivoState
from arivo.tools.e2b_builder import build_e2b_xml
from arivo.tools.e2b_validator import validate_e2b_xml


def pv_e2b_node(state: ArivoState) -> dict[str, Any]:
    """Build and validate an E2B(R3) XML document from adverse event data.

    This is a deterministic node — the XML construction is template-based,
    not LLM-generated, to ensure structural compliance.
    """
    now = datetime.now(timezone.utc).isoformat()
    qms_data = state.get("qms_data", {})
    ae_data = qms_data.get("adverse_event")

    if not ae_data:
        return {
            "e2b_xml": "",
            "current_agent": "pv_e2b",
            "messages": [AIMessage(content="[PV E2B(R3)] No adverse event data — skipping E2B generation.")],
            "audit_trail": [{"timestamp": now, "agent": "pv_e2b", "action": "SKIPPED", "detail": "No adverse event data"}],
        }

    # Map change control data to E2B report structure
    products = qms_data.get("affected_products", [])
    product_name = products[0]["product_name"] if products else "Unknown"

    report_data = {
        "safety_report": {
            "case_id": ae_data.get("ae_id", ""),
            "report_type": "1",  # Spontaneous
            "seriousness": ae_data.get("seriousness", "Non-Serious"),
            "reporter_type": ae_data.get("reporter_type", ""),
            "patient": {
                "age": ae_data.get("patient_age"),
                "sex": ae_data.get("patient_sex", "UNK"),
                "weight_kg": ae_data.get("patient_weight_kg"),
                "medical_history": "",
            },
            "reactions": [
                {
                    "meddra_pt": ae_data.get("meddra_pt", ""),
                    "meddra_code": ae_data.get("meddra_code", ""),
                    "onset_date": ae_data.get("onset_date", ""),
                    "outcome": ae_data.get("outcome", "Unknown"),
                    "seriousness_criteria": [],
                }
            ],
            "drugs": [
                {
                    "name": ae_data.get("suspect_drug", product_name),
                    "dose": ae_data.get("dose", ""),
                    "route": ae_data.get("route", ""),
                    "indication": ae_data.get("indication", ""),
                    "characterization": "1",  # Suspect
                }
            ],
            "narrative_summary": ae_data.get("reaction_description", ""),
        }
    }

    # Build XML
    xml_string = build_e2b_xml(report_data)

    # Validate
    validation = validate_e2b_xml(xml_string)

    summary_parts = [
        f"[PV E2B(R3)] Generated E2B(R3) ICSR for adverse event {ae_data.get('ae_id', '')}.",
        f"Case ID: {ae_data.get('ae_id', '')}",
        f"Patient: {ae_data.get('patient_age', 'UNK')} y/o {ae_data.get('patient_sex', 'UNK')}",
        f"Reaction: {ae_data.get('meddra_pt', '')} (MedDRA: {ae_data.get('meddra_code', '')})",
        f"Suspect Drug: {ae_data.get('suspect_drug', '')}",
        f"Outcome: {ae_data.get('outcome', '')}",
        f"Seriousness: {ae_data.get('seriousness', '')}",
        f"\nValidation: {'PASSED' if validation['valid'] else 'FAILED'}",
    ]
    if validation["errors"]:
        summary_parts.append(f"Errors: {'; '.join(validation['errors'])}")
    if validation["warnings"]:
        summary_parts.append(f"Warnings: {'; '.join(validation['warnings'])}")

    summary_parts.append(f"\nXML Length: {len(xml_string)} characters")

    return {
        "e2b_xml": xml_string,
        "current_agent": "pv_e2b",
        "messages": [AIMessage(content="\n".join(summary_parts))],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "pv_e2b",
                "action": "E2B_GENERATED",
                "detail": f"E2B(R3) XML for {ae_data.get('ae_id', '')}. Valid: {validation['valid']}. Errors: {len(validation['errors'])}. Warnings: {len(validation['warnings'])}.",
                "citations": [
                    f"ICH E2B(R3) Implementation Guide",
                    f"FDA Receiver OID: 2.16.840.1.113883.3.989.2.1.3.12",
                    f"MedDRA Code: {ae_data.get('meddra_code', '')} ({ae_data.get('meddra_pt', '')})",
                ],
            }
        ],
    }
