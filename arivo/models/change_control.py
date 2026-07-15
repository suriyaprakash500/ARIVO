"""Pydantic models for QMS change control records."""

from __future__ import annotations

from pydantic import BaseModel


class ManufacturingSite(BaseModel):
    site_id: str
    name: str
    address: str
    country: str
    role: str  # e.g. "Drug Substance", "Drug Product", "Packaging"


class AffectedProduct(BaseModel):
    product_id: str
    product_name: str
    dosage_form: str
    strength: str
    nda_number: str
    markets: list[str]


class DeviationRecord(BaseModel):
    deviation_id: str
    description: str
    root_cause: str
    batch_numbers: list[str]
    batch_disposition: str  # "Released", "Quarantined", "Rejected"
    analytical_results: dict[str, str]


class AdverseEventData(BaseModel):
    ae_id: str
    patient_age: int
    patient_sex: str  # "M", "F", "UNK"
    patient_weight_kg: float | None = None
    reaction_description: str
    meddra_pt: str  # MedDRA Preferred Term
    meddra_code: str
    onset_date: str
    outcome: str  # "Recovered", "Not Recovered", "Fatal", "Unknown"
    seriousness: str  # "Serious", "Non-Serious"
    reporter_type: str  # "Healthcare Professional", "Consumer"
    suspect_drug: str
    dose: str
    route: str
    indication: str


class ChangeControl(BaseModel):
    change_control_id: str
    title: str
    description: str
    change_type: str  # "Manufacturing Site", "Process", "Formulation", "Analytical Method"
    change_category: str  # SUPAC category
    current_state: str
    proposed_state: str
    justification: str
    affected_products: list[AffectedProduct]
    current_site: ManufacturingSite | None = None
    proposed_site: ManufacturingSite | None = None
    deviation: DeviationRecord | None = None
    adverse_event: AdverseEventData | None = None
    capa_references: list[str] = []
    attachments: list[str] = []
    status: str = "Approved"
    created_date: str = ""
    approved_date: str = ""
