"""Pydantic models for E2B(R3) ICSR data elements."""

from __future__ import annotations

from pydantic import BaseModel


class E2BMessageHeader(BaseModel):
    message_id: str = ""
    sender_id: str = ""
    receiver_id: str = ""  # FDA OID: 2.16.840.1.113883.3.989.2.1.3.12
    message_date: str = ""


class E2BBatchHeader(BaseModel):
    batch_id: str = ""
    batch_sender_id: str = ""
    batch_receiver_id: str = ""
    batch_date: str = ""


class E2BPatient(BaseModel):
    age: int | None = None
    sex: str = "UNK"  # M, F, UNK
    weight_kg: float | None = None
    medical_history: str = ""


class E2BReaction(BaseModel):
    meddra_pt: str = ""
    meddra_code: str = ""
    onset_date: str = ""
    outcome: str = ""  # 1=Recovered, 2=Recovering, 3=Not recovered, 4=Fatal, 5=Unknown
    seriousness_criteria: list[str] = []


class E2BDrug(BaseModel):
    name: str = ""
    dose: str = ""
    route: str = ""
    indication: str = ""
    start_date: str = ""
    end_date: str = ""
    characterization: str = "1"  # 1=Suspect, 2=Concomitant, 3=Interacting


class E2BSafetyReport(BaseModel):
    case_id: str = ""
    report_type: str = "1"  # 1=Spontaneous, 2=Study
    seriousness: str = ""
    reporter_type: str = ""
    patient: E2BPatient = E2BPatient()
    reactions: list[E2BReaction] = []
    drugs: list[E2BDrug] = []
    narrative_summary: str = ""


class E2BReport(BaseModel):
    message_header: E2BMessageHeader = E2BMessageHeader()
    batch_header: E2BBatchHeader = E2BBatchHeader()
    safety_report: E2BSafetyReport = E2BSafetyReport()
