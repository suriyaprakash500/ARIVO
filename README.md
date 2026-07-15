# ARIVO — Agentic Regulatory Intelligence & Variation Orchestrator

A multi-agent AI system that automates the translation of pharmaceutical quality events into regulatory actions.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your GROQ_API_KEY

# 4. Run
python -m arivo.api.app
```

Open http://localhost:8000 in your browser.

## Docker

```bash
docker-compose up --build
```

## Architecture

ARIVO uses LangGraph to orchestrate 5 specialized agents:

1. **Supervisor** — Routes tasks, maintains state
2. **QMS Extraction** — Pulls change control data from Veeva Vault (mocked)
3. **Regulatory Assessment** — SUPAC/EMA classification
4. **Dossier Structuring** — M4Q(R2) Module 2.3 + Module 3 drafting
5. **PV E2B(R3)** — Pharmacovigilance XML generation (conditional)

A **Critic** node validates all outputs before human review.
