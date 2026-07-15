"""E2B(R3) XML validator.

Validates E2B(R3) XML documents against structural and business rules.
Uses a simplified validation approach (not full XSD) suitable for the MVP.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


REQUIRED_ELEMENTS = [
    "id",
    "creationTime",
    "receiver",
    "sender",
    "controlActProcess",
]

REQUIRED_SAFETY_REPORT_SECTIONS = [
    "recordTarget",  # Patient data
]

FDA_RECEIVER_OID = "2.16.840.1.113883.3.989.2.1.3.12"


def validate_e2b_xml(xml_string: str) -> dict:
    """Validate an E2B(R3) XML string.

    Returns:
        dict with keys:
        - valid: bool
        - errors: list of error strings
        - warnings: list of warning strings
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Well-formedness check
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"valid": False, "errors": [f"XML parse error: {e}"], "warnings": []}

    # 2. Root element check
    local_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if local_name != "MCCI_IN200100UV01":
        errors.append(f"Expected root element MCCI_IN200100UV01, got {local_name}")

    # 3. Required top-level elements
    ns = {"hl7": "urn:hl7-org:v3"}
    for elem_name in REQUIRED_ELEMENTS:
        # Search with and without namespace
        found = root.find(elem_name) or root.find(f"hl7:{elem_name}", ns)
        if found is None:
            errors.append(f"Missing required element: {elem_name}")

    # 4. Receiver OID check
    receiver = root.find(".//receiver//id") or root.find(f".//hl7:receiver//hl7:id", ns)
    if receiver is not None:
        oid = receiver.get("root", "")
        if FDA_RECEIVER_OID not in (oid, receiver.get("extension", "")):
            warnings.append(f"Receiver OID '{oid}' does not match FDA OID ({FDA_RECEIVER_OID})")
    else:
        warnings.append("Could not verify receiver OID")

    # 5. Safety report structure check
    cap = root.find("controlActProcess") or root.find(f"hl7:controlActProcess", ns)
    if cap is not None:
        inv_event = (
            cap.find(".//investigationEvent")
            or cap.find(f".//hl7:investigationEvent", ns)
        )
        if inv_event is None:
            errors.append("Missing investigationEvent in controlActProcess")
        else:
            # Check for patient data
            record_target = (
                inv_event.find("recordTarget")
                or inv_event.find(f"hl7:recordTarget", ns)
            )
            if record_target is None:
                errors.append("Missing recordTarget (patient data) in safety report")

            # Check for at least one reaction
            components = inv_event.findall("component") or inv_event.findall(f"hl7:component", ns)
            has_reaction = any(
                c.find("adverseEventAssessment") is not None
                or c.find(f"hl7:adverseEventAssessment", ns) is not None
                for c in components
            )
            if not has_reaction:
                warnings.append("No adverse event assessment (reaction) found in report")

            # Check for at least one drug
            has_drug = any(
                c.find("substanceAdministration") is not None
                or c.find(f"hl7:substanceAdministration", ns) is not None
                for c in components
            )
            if not has_drug:
                warnings.append("No substance administration (drug) found in report")
    else:
        errors.append("Missing controlActProcess element")

    # 6. Creation time format check
    ct = root.find("creationTime") or root.find(f"hl7:creationTime", ns)
    if ct is not None:
        ct_val = ct.get("value", "")
        if len(ct_val) < 8:
            errors.append(f"Invalid creationTime format: {ct_val}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
