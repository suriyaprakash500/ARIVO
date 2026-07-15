"""Deterministic SUPAC / EMA regulatory classification engine.

Uses rules from supac_rules.json and ema_variation_rules.json to classify
manufacturing changes. This is NOT an LLM — it's a rules engine that
provides deterministic, auditable classifications.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_SUPAC_RULES: Optional[dict] = None
_EMA_RULES: Optional[dict] = None


def _load_supac() -> dict:
    global _SUPAC_RULES
    if _SUPAC_RULES is None:
        with open(_DATA_DIR / "supac_rules.json") as f:
            _SUPAC_RULES = json.load(f)
    return _SUPAC_RULES


def _load_ema() -> dict:
    global _EMA_RULES
    if _EMA_RULES is None:
        with open(_DATA_DIR / "ema_variation_rules.json") as f:
            _EMA_RULES = json.load(f)
    return _EMA_RULES


# Map change_category strings to SUPAC rule keys
_CATEGORY_MAP = {
    "Components and Composition": "components_composition",
    "Site Change": "manufacturing_site",
    "Manufacturing Site": "manufacturing_site",
    "Scale": "scale",
    "Manufacturing Process": "manufacturing_process",
    "Process": "manufacturing_process",
    "In-Process Controls and Specifications": "components_composition",
}

# Map dosage form to SUPAC guidance
_DOSAGE_FORM_MAP = {
    "Semisolid": "supac_ss",
    "Cream": "supac_ss",
    "Gel": "supac_ss",
    "Ointment": "supac_ss",
    "Solid Oral": "supac_ir",
    "Tablet": "supac_ir",
    "Capsule": "supac_ir",
}


def _get_supac_guidance(dosage_form: str) -> str:
    """Determine which SUPAC guidance applies based on dosage form."""
    for key, guidance in _DOSAGE_FORM_MAP.items():
        if key.lower() in dosage_form.lower():
            return guidance
    return "supac_ir"  # default


def classify_supac(
    change_category: str,
    dosage_form: str,
    change_description: str,
) -> dict[str, Any]:
    """Classify a change under SUPAC rules.

    Uses deterministic rules to map change category + dosage form to a
    SUPAC level and filing type. The level is inferred from the description
    keywords as a heuristic for the MVP.
    """
    rules = _load_supac()
    guidance_key = _get_supac_guidance(dosage_form)
    guidance = rules.get(guidance_key, rules["supac_ss"])
    category_key = _CATEGORY_MAP.get(change_category, "components_composition")
    category_rules = guidance.get("categories", {}).get(category_key, {})

    # Heuristic level detection based on description keywords
    desc_lower = change_description.lower()
    if any(kw in desc_lower for kw in ["different city", "different country", "new site", "transfer"]):
        level = 3
    elif any(kw in desc_lower for kw in ["different campus", "beyond", "change in"]):
        level = 2
    else:
        level = 1

    level_key = f"level_{level}"
    level_rules = category_rules.get(level_key, {})

    return {
        "guidance": guidance.get("name", guidance_key),
        "change_category": change_category,
        "level": level,
        "filing_type": level_rules.get("filing", "PAS"),
        "required_tests": level_rules.get("tests", []),
        "documentation_required": level_rules.get("documentation", []),
        "level_description": level_rules.get("description", ""),
        "multi_change_rule": rules["supac_ss"].get("multi_change_rule", ""),
    }


def classify_ema(supac_filing: str) -> dict[str, Any]:
    """Map SUPAC filing type to EMA variation classification."""
    rules = _load_ema()
    mapping = rules.get("mapping_from_supac", {})
    ema_type_key = mapping.get(supac_filing, "Type II")

    # Map display name to JSON key
    key_map = {"Type IA": "type_ia", "Type IB": "type_ib", "Type II": "type_ii"}
    rule_key = key_map.get(ema_type_key, "type_ii")
    ema_rule = rules.get(rule_key, {})

    return {
        "variation_type": ema_rule.get("name", ema_type_key),
        "description": ema_rule.get("description", ""),
        "examples": ema_rule.get("examples", []),
    }


def apply_multi_change_rule(classifications: list[dict[str, Any]]) -> dict[str, Any]:
    """When multiple changes are made, the highest level determines filing.

    Returns the classification with the highest risk level.
    """
    if not classifications:
        return {}

    rules = _load_supac()
    hierarchy = rules.get("filing_hierarchy", ["Annual Report", "CBE-0", "CBE-30", "PAS"])

    highest = classifications[0]
    for c in classifications[1:]:
        if hierarchy.index(c.get("filing_type", "PAS")) > hierarchy.index(highest.get("filing_type", "Annual Report")):
            highest = c

    return highest
