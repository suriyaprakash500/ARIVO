"""Pydantic models for M4Q(R2) dossier outputs."""

from __future__ import annotations

from pydantic import BaseModel


class DMCSSection(BaseModel):
    """A section organized by the DMCS pillars."""
    description: str = ""
    manufacture: str = ""
    control: str = ""
    storage: str = ""


class Module23Content(BaseModel):
    """Module 2.3 — Quality Overall Summary."""
    section_2_3_2: str = ""  # Overall Control Strategy
    section_2_3_4: str = ""  # Development Justification
    core_quality_information: str = ""


class Module3Content(BaseModel):
    """Module 3 — Body of Data."""
    drug_substance: DMCSSection = DMCSSection()
    drug_product: DMCSSection = DMCSSection()
    excipients: list[DMCSSection] = []
    validation_data: str = ""
    batch_analyses: str = ""
    technical_reports: str = ""


class DossierOutput(BaseModel):
    change_control_id: str
    module_2_3: Module23Content = Module23Content()
    module_3: Module3Content = Module3Content()
    affected_sections_summary: str = ""
    dmcs_compliance_notes: list[str] = []
