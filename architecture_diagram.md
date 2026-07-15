# ARIVO — System Architecture

> Agentic Regulatory Intelligence & Variation Orchestrator

---

## 1. System Architecture

The multi-layered architecture separates concerns across User, API, Orchestration, Agent, and Data layers.

![System Architecture](docs/images/system_architecture.png)

**Key design decision**: The Supervisor uses **deterministic routing** (not LLM-based) so that the pipeline flow is predictable, reproducible, and auditable — a requirement for GxP-regulated environments.

---

## 2. Pipeline Flow

Each pipeline run follows a supervisor-driven loop. Agents execute sequentially and return control to the Supervisor, which determines the next step.

![Pipeline Flow](docs/images/pipeline_flow.png)

### Agent Execution Order

| Step | Agent | Type | Purpose |
|------|-------|------|---------|
| 1 | **Supervisor** | Deterministic | Route to next agent based on state |
| 2 | **QMS Extraction** | Deterministic | Fetch change control from Veeva Vault API |
| 3 | **Regulatory Assessment** | Hybrid | SUPAC/EMA rules (deterministic) + LLM gap analysis |
| 4 | **Dossier Structuring** | LLM-Powered | Draft M4Q(R2) Module 2.3 + Module 3 content |
| 5 | **PV E2B(R3)** | Deterministic | Build HL7 v3 XML *(only if adverse event detected)* |
| 6 | **Critic** | Deterministic | Validate all outputs; loop back if issues found (max 2x) |

---

## 3. Data Flow

Shows how a QMS change control is transformed through classification, AI analysis, and document generation into regulatory-ready outputs.

![Data Flow](docs/images/data_flow_sequence.png)

### Input → Output Mapping

| Input | Processing | Output |
|-------|-----------|--------|
| Change Control (QMS) | SUPAC/EMA deterministic rules | Classification: Level, Filing Type, Variation |
| Change description + justification | LLM (Groq llama-3.3-70b) | Gap analysis + regulatory strategy |
| Assessment + change data | LLM with DMCS ontology | eCTD Module 2.3 + Module 3 dossier sections |
| Adverse event data (if present) | Deterministic XML template | E2B(R3) ICSR in HL7 v3 format |
| All agent actions | Automatic logging | ALCOA+ audit trail with citations |

---

## 4. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Orchestration** | LangGraph (StateGraph) | Conditional routing, checkpointing, human-in-the-loop |
| **LLM** | Groq `llama-3.3-70b-versatile` | Fast inference, open-source model |
| **Classification** | Custom rules engine (JSON) | Deterministic, auditable, GxP-friendly |
| **XML Generation** | Python `xml.etree.ElementTree` | Standard library, zero dependencies |
| **API** | FastAPI + Jinja2 | Async, auto-docs, server-side rendered templates |
| **Real-time** | WebSocket (native) | Live pipeline event streaming |
| **Data Models** | Pydantic v2 | Runtime validation and serialization |
| **Deployment** | Docker + Compose | Reproducible demo environment |

---

## 5. GxP Compliance Design

| Principle | Implementation |
|-----------|---------------|
| **ALCOA+ Audit Trail** | Every agent action logged with timestamp, agent ID, action type, and citations |
| **Deterministic Classification** | SUPAC/EMA rules are JSON-based, not LLM-generated |
| **Human-in-the-Loop** | Pipeline stops at `review` status; requires explicit e-signature to proceed |
| **21 CFR Part 11** | Electronic signature with signer identity + ISO 8601 timestamp |
| **Source Traceability** | Audit entries cite ICH guidelines, MedDRA codes, and API endpoints |
| **Reflection Loop** | Critic validates all outputs; max 2 correction cycles before escalation |
| **Separation of Concerns** | LLMs draft narrative only; structure and classification are deterministic |

---

## 6. Directory Structure

```
ARIVO/
├── arivo/
│   ├── agents/           # LangGraph agent nodes
│   │   ├── state.py      # Shared pipeline state schema
│   │   ├── graph.py      # StateGraph compilation
│   │   ├── supervisor.py # Deterministic router
│   │   ├── qms_extraction.py
│   │   ├── regulatory_assessment.py
│   │   ├── dossier_structuring.py
│   │   ├── pv_e2b.py
│   │   └── critic.py
│   ├── api/              # FastAPI server
│   │   ├── app.py        # Application factory
│   │   ├── routes.py     # REST endpoints
│   │   └── websocket.py  # Live updates
│   ├── data/             # Mock fixtures & rules
│   │   ├── mock_change_controls.json
│   │   ├── supac_rules.json
│   │   ├── ema_variation_rules.json
│   │   └── meddra_sample.json
│   ├── models/           # Pydantic schemas
│   └── tools/            # Business logic
│       ├── veeva_client.py
│       ├── regulatory_rules.py
│       ├── dossier_templates.py
│       ├── e2b_builder.py
│       └── e2b_validator.py
├── frontend/
│   ├── templates/        # Jinja2 HTML pages
│   └── static/           # CSS + JS
├── docs/images/          # Architecture diagrams
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
