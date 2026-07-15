"""Dossier Structuring Agent (M4Q-R2).

Drafts CTD Module 2.3 (Quality Overall Summary) and Module 3 (Body of Data)
content using the DMCS ontology: Description, Manufacture, Control, Storage.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from arivo.config import settings
from arivo.agents.state import ArivoState
from arivo.tools.dossier_templates import (
    get_module_2_3_template,
    get_module_3_ds_template,
    get_module_3_dp_template,
    get_module_3_validation_template,
)


_SYSTEM_PROMPT = """You are a senior CMC regulatory writer drafting sections for an eCTD submission under ICH M4Q(R2) guidelines.

You MUST organize all content using the DMCS ontology:
- Description: Material identification, nomenclature, structural characteristics
- Manufacture: Manufacturing process, process controls, critical process parameters
- Control: Specifications, analytical methods, validation, batch analysis data
- Storage: Container closure system, stability studies, shelf life, storage conditions

Rules:
1. Module 2.3 contains the OVERALL CONTROL STRATEGY and DEVELOPMENT JUSTIFICATION — high-level, strategic content
2. Module 3 contains the DETAILED DATA — raw validation data, batch records, technical reports
3. Do NOT duplicate data between Module 2.3 and Module 3. Module 2.3 summarizes; Module 3 provides evidence.
4. Use formal regulatory language appropriate for an FDA/EMA submission
5. Reference specific ICH guidelines where applicable (Q1A, Q2, Q3, Q6A, Q7, Q8-Q14)
6. Keep each section focused and concise (2-4 paragraphs per DMCS pillar)"""


def dossier_structuring_node(state: ArivoState) -> dict[str, Any]:
    """Draft M4Q(R2) dossier sections based on the regulatory assessment."""
    now = datetime.now(timezone.utc).isoformat()
    qms_data = state.get("qms_data", {})
    assessment = state.get("regulatory_assessment", {})

    if not qms_data or not assessment:
        return {
            "dossier_sections": {},
            "current_agent": "dossier_structuring",
            "messages": [AIMessage(content="[Dossier Structuring] Insufficient data for drafting.")],
            "audit_trail": [{"timestamp": now, "agent": "dossier_structuring", "action": "SKIPPED", "detail": "Missing data"}],
        }

    products = qms_data.get("affected_products", [])
    product_name = products[0]["product_name"] if products else "Unknown Product"
    dosage_form = products[0].get("dosage_form", "") if products else ""
    supac = assessment.get("supac", {})

    prompt = f"""Draft the M4Q(R2) dossier sections for the following post-approval change:

CHANGE CONTROL: {qms_data.get('change_control_id', '')}
TITLE: {qms_data.get('title', '')}
PRODUCT: {product_name} ({dosage_form})
CHANGE TYPE: {qms_data.get('change_type', '')}
CURRENT STATE: {qms_data.get('current_state', '')}
PROPOSED STATE: {qms_data.get('proposed_state', '')}
JUSTIFICATION: {qms_data.get('justification', '')}
FILING TYPE: {supac.get('filing_type', 'PAS')} (SUPAC Level {supac.get('level', 'N/A')})
REQUIRED TESTS: {', '.join(supac.get('required_tests', []))}
GAP ANALYSIS: {assessment.get('gap_analysis', '')}

Please provide the following sections in the EXACT format below. Use the headers exactly as shown:

=== MODULE 2.3.2: OVERALL CONTROL STRATEGY ===
[Write 2-3 paragraphs on the control strategy for this change]

=== MODULE 2.3.4: DEVELOPMENT JUSTIFICATION ===
[Write 2-3 paragraphs justifying the change from a development perspective]

=== CORE QUALITY INFORMATION ===
[Write 1-2 paragraphs on core quality information affected by this change]

=== DRUG SUBSTANCE DESCRIPTION ===
[Write about the drug substance identity and characteristics]

=== DRUG SUBSTANCE MANUFACTURE ===
[Write about manufacturing process details relevant to this change]

=== DRUG SUBSTANCE CONTROL ===
[Write about control strategy, specifications, and testing]

=== DRUG SUBSTANCE STORAGE ===
[Write about stability and storage considerations]

=== DRUG PRODUCT DESCRIPTION ===
[Write about the drug product characteristics]

=== DRUG PRODUCT MANUFACTURE ===
[Write about drug product manufacturing]

=== DRUG PRODUCT CONTROL ===
[Write about drug product testing and specifications]

=== DRUG PRODUCT STORAGE ===
[Write about drug product stability and storage]

=== VALIDATION DATA ===
[Describe validation studies needed/conducted]

=== BATCH ANALYSES ===
[Describe batch analysis data]

=== TECHNICAL REPORTS ===
[List and describe technical reports supporting this change]"""

    # Default content
    dossier = {
        "change_control_id": qms_data.get("change_control_id", ""),
        "module_2_3": {
            "section_2_3_2": "",
            "section_2_3_4": "",
            "core_quality_information": "",
        },
        "module_3": {
            "drug_substance": {"description": "", "manufacture": "", "control": "", "storage": ""},
            "drug_product": {"description": "", "manufacture": "", "control": "", "storage": ""},
            "validation_data": "",
            "batch_analyses": "",
            "technical_reports": "",
        },
        "affected_sections_summary": f"Affected CTD sections: {', '.join(assessment.get('affected_ctd_sections', []))}",
        "dmcs_compliance_notes": [],
    }

    try:
        llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.2)
        response = llm.invoke([
            HumanMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        full_text = response.content

        # Parse sections by headers
        section_map = {
            "MODULE 2.3.2": ("module_2_3", "section_2_3_2"),
            "OVERALL CONTROL STRATEGY": ("module_2_3", "section_2_3_2"),
            "CONTROL STRATEGY": ("module_2_3", "section_2_3_2"),
            "MODULE 2.3.4": ("module_2_3", "section_2_3_4"),
            "DEVELOPMENT JUSTIFICATION": ("module_2_3", "section_2_3_4"),
            "CORE QUALITY INFORMATION": ("module_2_3", "core_quality_information"),
            "DRUG SUBSTANCE DESCRIPTION": ("module_3.drug_substance", "description"),
            "DRUG SUBSTANCE MANUFACTURE": ("module_3.drug_substance", "manufacture"),
            "DRUG SUBSTANCE CONTROL": ("module_3.drug_substance", "control"),
            "DRUG SUBSTANCE STORAGE": ("module_3.drug_substance", "storage"),
            "DRUG PRODUCT DESCRIPTION": ("module_3.drug_product", "description"),
            "DRUG PRODUCT MANUFACTURE": ("module_3.drug_product", "manufacture"),
            "DRUG PRODUCT CONTROL": ("module_3.drug_product", "control"),
            "DRUG PRODUCT STORAGE": ("module_3.drug_product", "storage"),
            "VALIDATION DATA": ("module_3", "validation_data"),
            "BATCH ANALYSES": ("module_3", "batch_analyses"),
            "TECHNICAL REPORTS": ("module_3", "technical_reports"),
        }

        # Robust parser: handles ===, ###, **, numbered headers, etc.
        lines = full_text.split("\n")
        current_key = None
        current_content: list[str] = []

        for line in lines:
            # Normalize: strip markdown/delimiter formatting
            cleaned = line.strip()
            cleaned = cleaned.strip("=").strip("#").strip("*").strip("-").strip()
            # Also remove leading numbers like "1." or "1)"
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
            cleaned = cleaned.strip(":").strip()

            matched_key = None
            upper = cleaned.upper()
            for header, key_path in section_map.items():
                if header in upper and len(cleaned) < len(header) + 30:
                    matched_key = key_path
                    break

            if matched_key:
                if current_key:
                    _set_nested(dossier, current_key, "\n".join(current_content).strip())
                current_key = matched_key
                current_content = []
            elif current_key:
                current_content.append(line)

        # Save last section
        if current_key:
            _set_nested(dossier, current_key, "\n".join(current_content).strip())

        # Check DMCS compliance
        for material in ["drug_substance", "drug_product"]:
            mat_data = dossier["module_3"].get(material, {})
            for pillar in ["description", "manufacture", "control", "storage"]:
                if not mat_data.get(pillar):
                    dossier["dmcs_compliance_notes"].append(
                        f"WARNING: {material}.{pillar} is empty — DMCS compliance gap"
                    )

    except Exception as e:
        dossier["dmcs_compliance_notes"].append(f"LLM drafting failed: {e}. Templates used as fallback.")
        dossier["module_2_3"]["section_2_3_2"] = f"Control strategy for {qms_data.get('title', '')} pending detailed drafting."
        dossier["module_2_3"]["section_2_3_4"] = f"Development justification for {qms_data.get('title', '')} pending detailed drafting."

    # Build rendered templates for display
    m23_rendered = get_module_2_3_template().format(
        control_strategy=dossier["module_2_3"]["section_2_3_2"],
        development_justification=dossier["module_2_3"]["section_2_3_4"],
        core_quality_info=dossier["module_2_3"]["core_quality_information"],
    )
    m3_ds_rendered = get_module_3_ds_template().format(
        name=product_name,
        **dossier["module_3"]["drug_substance"],
    )
    m3_dp_rendered = get_module_3_dp_template().format(
        name=product_name,
        **dossier["module_3"]["drug_product"],
    )
    m3_val_rendered = get_module_3_validation_template().format(
        validation_data=dossier["module_3"]["validation_data"],
        batch_analyses=dossier["module_3"]["batch_analyses"],
        technical_reports=dossier["module_3"]["technical_reports"],
    )

    full_dossier_text = f"{m23_rendered}\n\n---\n\n{m3_ds_rendered}\n\n{m3_dp_rendered}\n\n{m3_val_rendered}"

    summary = (
        f"[Dossier Structuring] Drafted M4Q(R2) sections for {qms_data.get('change_control_id', '')}.\n"
        f"Module 2.3: Sections 2.3.2 (Control Strategy) and 2.3.4 (Development Justification)\n"
        f"Module 3: Drug Substance DMCS, Drug Product DMCS, Validation Data, Batch Analyses\n"
        f"DMCS Compliance Notes: {len(dossier['dmcs_compliance_notes'])} items\n\n"
        f"{full_dossier_text}"
    )

    return {
        "dossier_sections": dossier,
        "current_agent": "dossier_structuring",
        "messages": [AIMessage(content=summary)],
        "audit_trail": [
            {
                "timestamp": now,
                "agent": "dossier_structuring",
                "action": "DOSSIER_DRAFTED",
                "detail": f"M4Q(R2) content drafted for {qms_data.get('change_control_id', '')}. DMCS notes: {len(dossier['dmcs_compliance_notes'])}.",
                "citations": [
                    "ICH M4Q(R2) Quality Guidelines",
                    "DMCS Ontology: Description, Manufacture, Control, Storage",
                    f"Regulatory Assessment: {assessment.get('recommended_submission', 'N/A')}",
                ],
            }
        ],
    }


def _set_nested(d: dict, key_path: tuple[str, str], value: str) -> None:
    """Set a value in a nested dict using a (parent, child) key tuple."""
    parent_key, child_key = key_path
    if "." in parent_key:
        parts = parent_key.split(".")
        target = d
        for p in parts:
            target = target.setdefault(p, {})
        target[child_key] = value
    else:
        d.setdefault(parent_key, {})[child_key] = value
