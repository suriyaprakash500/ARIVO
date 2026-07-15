"""Pydantic models for regulatory assessment outputs."""

from __future__ import annotations

from pydantic import BaseModel


class SUPACClassification(BaseModel):
    change_category: str  # "Components/Composition", "Manufacturing Site", "Scale", "Process"
    level: int  # 1, 2, or 3
    filing_type: str  # "Annual Report", "CBE-0", "CBE-30", "PAS"
    required_tests: list[str]
    documentation_required: list[str]
    rationale: str


class EMAVariation(BaseModel):
    variation_type: str  # "Type IA", "Type IB", "Type II"
    classification_code: str
    description: str
    conditions: list[str]


class RegulatoryAssessment(BaseModel):
    change_control_id: str
    supac: SUPACClassification
    ema: EMAVariation | None = None
    overall_risk: str  # "Low", "Medium", "High"
    recommended_submission: str  # e.g. "Prior Approval Supplement (PAS)"
    affected_ctd_sections: list[str]
    gap_analysis: str  # AI-generated narrative
    strategy_summary: str
    citations: list[str]  # Source references for ALCOA+
