"""E2B(R3) HL7 v3 XML builder.

Constructs ICH E2B(R3) ICSR XML documents from structured data.
Uses the HL7 v3 message format with proper OIDs and namespace declarations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

# Standard OIDs
FDA_RECEIVER_OID = "2.16.840.1.113883.3.989.2.1.3.12"
SENDER_OID = "2.16.840.1.113883.3.989.2.1.3.1"
HL7_NAMESPACE = "urn:hl7-org:v3"
MEDDRA_OID = "2.16.840.1.113883.6.163"


def build_e2b_xml(report_data: dict) -> str:
    """Build an E2B(R3) HL7 v3 XML document from structured report data.

    Args:
        report_data: Dictionary containing safety report fields matching
                     the E2BReport model structure.

    Returns:
        Pretty-printed XML string.
    """
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    msg_id = str(uuid.uuid4())

    # Root element — MCCI_IN200100UV01
    root = Element("MCCI_IN200100UV01")
    root.set("xmlns", HL7_NAMESPACE)
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("ITSVersion", "XML_1.0")

    # Message ID
    _add_id(root, msg_id, SENDER_OID)

    # Creation time
    creation_time = SubElement(root, "creationTime")
    creation_time.set("value", now)

    # Interaction ID
    interaction_id = SubElement(root, "interactionId")
    interaction_id.set("root", "2.16.840.1.113883.1.6")
    interaction_id.set("extension", "MCCI_IN200100UV01")

    # Processing code
    proc_code = SubElement(root, "processingCode")
    proc_code.set("code", "P")  # Production

    # Processing mode
    proc_mode = SubElement(root, "processingModeCode")
    proc_mode.set("code", "T")  # Current processing

    # Accept ack
    accept_ack = SubElement(root, "acceptAckCode")
    accept_ack.set("code", "AL")

    # --- Receiver ---
    receiver = SubElement(root, "receiver")
    receiver.set("typeCode", "RCV")
    recv_device = SubElement(receiver, "device")
    recv_device.set("classCode", "DEV")
    recv_device.set("determinerCode", "INSTANCE")
    _add_id(recv_device, FDA_RECEIVER_OID, "2.16.840.1.113883.3.989.2.1.3.12")

    # --- Sender ---
    sender = SubElement(root, "sender")
    sender.set("typeCode", "SND")
    send_device = SubElement(sender, "device")
    send_device.set("classCode", "DEV")
    send_device.set("determinerCode", "INSTANCE")
    _add_id(send_device, SENDER_OID, "2.16.840.1.113883.3.989.2.1.3.1")

    # --- controlActProcess (contains the safety report) ---
    cap = SubElement(root, "controlActProcess")
    cap.set("classCode", "CACT")
    cap.set("moodCode", "EVN")

    subject = SubElement(cap, "subject")
    subject.set("typeCode", "SUBJ")

    # --- investigationEvent (the ICSR) ---
    inv_event = SubElement(subject, "investigationEvent")
    inv_event.set("classCode", "INVSTG")
    inv_event.set("moodCode", "EVN")

    # Case ID
    sr = report_data.get("safety_report", {})
    _add_id(inv_event, sr.get("case_id", msg_id), SENDER_OID)

    # Report type code
    code = SubElement(inv_event, "code")
    code.set("code", sr.get("report_type", "1"))
    code.set("codeSystem", "2.16.840.1.113883.3.989.2.1.1.2")

    # Seriousness
    _add_observation(inv_event, "seriousness", sr.get("seriousness", "Non-Serious"))

    # --- Patient (recordTarget) ---
    patient_data = sr.get("patient", {})
    record_target = SubElement(inv_event, "recordTarget")
    record_target.set("typeCode", "RCT")
    patient_role = SubElement(record_target, "patientRole")
    patient_role.set("classCode", "PAT")
    patient = SubElement(patient_role, "patient")

    # Age
    age = patient_data.get("age")
    if age is not None:
        _add_observation_value(patient, "age", str(age), "a")
    else:
        _add_null_flavor(patient, "age")

    # Sex
    admin_gender = SubElement(patient, "administrativeGenderCode")
    sex_map = {"M": "1", "F": "2", "UNK": "0"}
    admin_gender.set("code", sex_map.get(patient_data.get("sex", "UNK"), "0"))

    # Weight
    weight = patient_data.get("weight_kg")
    if weight is not None:
        _add_observation_value(patient, "weight", str(weight), "kg")
    else:
        _add_null_flavor(patient, "weight")

    # --- Reactions (Section E) ---
    for reaction in sr.get("reactions", []):
        component = SubElement(inv_event, "component")
        component.set("typeCode", "COMP")
        obs = SubElement(component, "adverseEventAssessment")
        obs.set("classCode", "OBS")
        obs.set("moodCode", "EVN")

        react_code = SubElement(obs, "code")
        react_code.set("code", reaction.get("meddra_code", ""))
        react_code.set("codeSystem", MEDDRA_OID)
        react_code.set("displayName", reaction.get("meddra_pt", ""))

        if reaction.get("onset_date"):
            onset = SubElement(obs, "effectiveTime")
            onset_low = SubElement(onset, "low")
            onset_low.set("value", reaction["onset_date"].replace("-", ""))

        outcome_el = SubElement(obs, "outboundRelationship")
        outcome_el.set("typeCode", "OUTC")
        outcome_obs = SubElement(outcome_el, "observation")
        outcome_val = SubElement(outcome_obs, "value")
        outcome_val.set("xsi:type", "CE")
        outcome_val.set("code", _map_outcome(reaction.get("outcome", "Unknown")))

    # --- Drugs ---
    for drug in sr.get("drugs", []):
        component = SubElement(inv_event, "component")
        component.set("typeCode", "COMP")
        sub_admin = SubElement(component, "substanceAdministration")
        sub_admin.set("classCode", "SBADM")
        sub_admin.set("moodCode", "EVN")

        consumable = SubElement(sub_admin, "consumable")
        manuf_product = SubElement(consumable, "manufacturedProduct")
        manuf_mat = SubElement(manuf_product, "manufacturedMaterial")
        drug_name = SubElement(manuf_mat, "name")
        drug_name.text = drug.get("name", "")

        if drug.get("dose"):
            dose_qty = SubElement(sub_admin, "doseQuantity")
            dose_qty.set("value", drug["dose"])

        # Drug characterization (suspect/concomitant)
        char_el = SubElement(sub_admin, "inboundRelationship")
        char_el.set("typeCode", "CHAR")
        char_obs = SubElement(char_el, "observation")
        char_val = SubElement(char_obs, "value")
        char_val.set("xsi:type", "CE")
        char_val.set("code", drug.get("characterization", "1"))

    # --- Narrative Summary ---
    narrative = sr.get("narrative_summary", "")
    if narrative:
        component = SubElement(inv_event, "component")
        component.set("typeCode", "COMP")
        section = SubElement(component, "section")
        text = SubElement(section, "text")
        text.text = narrative

    # Pretty-print
    raw_xml = tostring(root, encoding="unicode")
    return minidom.parseString(raw_xml).toprettyxml(indent="  ", encoding=None)


def _add_id(parent: Element, extension: str, root_oid: str) -> None:
    id_el = SubElement(parent, "id")
    id_el.set("root", root_oid)
    id_el.set("extension", extension)


def _add_observation(parent: Element, name: str, value: str) -> None:
    component = SubElement(parent, "component")
    component.set("typeCode", "COMP")
    obs = SubElement(component, "observation")
    obs.set("classCode", "OBS")
    obs.set("moodCode", "EVN")
    code = SubElement(obs, "code")
    code.set("code", name)
    val = SubElement(obs, "value")
    val.text = value


def _add_observation_value(parent: Element, name: str, value: str, unit: str) -> None:
    obs = SubElement(parent, "subjectOf")
    obs_inner = SubElement(obs, "observation")
    code = SubElement(obs_inner, "code")
    code.set("code", name)
    val = SubElement(obs_inner, "value")
    val.set("xsi:type", "PQ")
    val.set("value", value)
    val.set("unit", unit)


def _add_null_flavor(parent: Element, name: str) -> None:
    obs = SubElement(parent, "subjectOf")
    obs_inner = SubElement(obs, "observation")
    code = SubElement(obs_inner, "code")
    code.set("code", name)
    val = SubElement(obs_inner, "value")
    val.set("nullFlavor", "NI")


def _map_outcome(outcome: str) -> str:
    mapping = {
        "Recovered": "1",
        "Recovering": "2",
        "Not Recovered": "3",
        "Fatal": "4",
        "Unknown": "5",
    }
    return mapping.get(outcome, "5")
