"""M4Q(R2) dossier section templates.

Provides template structures for Module 2.3 (Quality Overall Summary)
and Module 3 (Body of Data) organized by the DMCS ontology.
"""

from __future__ import annotations

MODULE_2_3_TEMPLATE = """
## Module 2.3 — Quality Overall Summary

### 2.3.2 Overall Control Strategy

{control_strategy}

### 2.3.4 Development and Manufacture Justification

{development_justification}

### Core Quality Information (CQI)

{core_quality_info}
"""

MODULE_3_DRUG_SUBSTANCE_TEMPLATE = """
## Module 3 — Drug Substance: {name}

### 3.2.S.1 — Description
{description}

### 3.2.S.2 — Manufacture
{manufacture}

### 3.2.S.4 — Control
{control}

### 3.2.S.7 — Storage / Stability
{storage}
"""

MODULE_3_DRUG_PRODUCT_TEMPLATE = """
## Module 3 — Drug Product: {name}

### 3.2.P.1 — Description
{description}

### 3.2.P.3 — Manufacture
{manufacture}

### 3.2.P.5 — Control
{control}

### 3.2.P.7 — Storage / Container Closure
{storage}
"""

MODULE_3_VALIDATION_TEMPLATE = """
## Module 3 — Supporting Data

### Validation Data
{validation_data}

### Batch Analyses
{batch_analyses}

### Technical Reports
{technical_reports}
"""


def get_module_2_3_template() -> str:
    return MODULE_2_3_TEMPLATE


def get_module_3_ds_template() -> str:
    return MODULE_3_DRUG_SUBSTANCE_TEMPLATE


def get_module_3_dp_template() -> str:
    return MODULE_3_DRUG_PRODUCT_TEMPLATE


def get_module_3_validation_template() -> str:
    return MODULE_3_VALIDATION_TEMPLATE
