"""FastAPI API routes for ARIVO."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from arivo.agents.graph import compiled_graph
from arivo.tools.veeva_client import list_change_controls


router = APIRouter(prefix="/api")

# In-memory store for pipeline runs
_pipeline_runs: dict[str, dict[str, Any]] = {}


class TriggerRequest(BaseModel):
    change_control_id: str


class TriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


@router.get("/change-controls")
async def get_change_controls() -> list[dict[str, Any]]:
    """List available change controls for the dashboard."""
    return list_change_controls()


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pipeline(req: TriggerRequest) -> TriggerResponse:
    """Trigger the ARIVO pipeline for a change control ID."""
    run_id = str(uuid.uuid4())[:8]
    thread_id = f"arivo-{run_id}"

    # Store the run
    _pipeline_runs[run_id] = {
        "run_id": run_id,
        "change_control_id": req.change_control_id,
        "thread_id": thread_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "state": None,
        "events": [],
    }

    # Execute the graph
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"change_control_id": req.change_control_id}

    try:
        final_state = None
        events = []

        for event in compiled_graph.stream(initial_state, config, stream_mode="updates"):
            events.append(event)
            # Each event is {node_name: state_update}
            for node_name, update in event.items():
                current_agent = update.get("current_agent", node_name)
                # Broadcast via websocket connections
                from arivo.api.websocket import broadcast_event
                await broadcast_event(run_id, {
                    "agent": current_agent,
                    "status": update.get("status", "running"),
                    "message": _extract_message(update),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Get final state from checkpointer
        final_state = compiled_graph.get_state(config)

        _pipeline_runs[run_id]["status"] = final_state.values.get("status", "review")
        _pipeline_runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _pipeline_runs[run_id]["state"] = _serialize_state(final_state.values)
        _pipeline_runs[run_id]["events"] = [_serialize_event(e) for e in events]

    except Exception as e:
        _pipeline_runs[run_id]["status"] = "error"
        _pipeline_runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _pipeline_runs[run_id]["state"] = {"error": str(e)}
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")

    return TriggerResponse(
        run_id=run_id,
        status=_pipeline_runs[run_id]["status"],
        message=f"Pipeline completed for {req.change_control_id}",
    )


@router.get("/pipeline/{run_id}")
async def get_pipeline_state(run_id: str) -> dict[str, Any]:
    """Get the current state of a pipeline run."""
    if run_id not in _pipeline_runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return _pipeline_runs[run_id]


@router.get("/pipeline/{run_id}/dossier")
async def get_dossier(run_id: str) -> dict[str, Any]:
    """Get the generated M4Q(R2) dossier content."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    state = run.get("state", {})
    return state.get("dossier_sections", {})


@router.get("/pipeline/{run_id}/e2b")
async def get_e2b_xml(run_id: str) -> dict[str, Any]:
    """Get the generated E2B(R3) XML."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    state = run.get("state", {})
    xml = state.get("e2b_xml", "")
    return {"xml": xml, "has_xml": bool(xml)}


@router.get("/audit/{run_id}")
async def get_audit_trail(run_id: str) -> list[dict[str, Any]]:
    """Get the ALCOA+ audit trail for a pipeline run."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    state = run.get("state", {})
    return state.get("audit_trail", [])


@router.post("/review/{run_id}/approve")
async def approve_pipeline(run_id: str) -> dict[str, str]:
    """Human sign-off — simulates 21 CFR Part 11 electronic signature."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if run["status"] != "review":
        raise HTTPException(status_code=400, detail=f"Run {run_id} is not in review status (current: {run['status']})")

    now = datetime.now(timezone.utc).isoformat()
    run["status"] = "approved"
    run["approved_at"] = now

    # Add approval to audit trail
    state = run.get("state", {})
    audit = state.get("audit_trail", [])
    audit.append({
        "timestamp": now,
        "agent": "human_reviewer",
        "action": "ELECTRONIC_SIGNATURE",
        "detail": "Regulatory lead reviewed and approved the AI-generated assessment. 21 CFR Part 11 compliant e-signature applied.",
        "signer": "Regulatory Lead (simulated)",
    })
    state["audit_trail"] = audit
    state["status"] = "approved"

    return {"status": "approved", "message": "Pipeline approved with electronic signature.", "approved_at": now}


@router.get("/runs")
async def list_runs() -> list[dict[str, Any]]:
    """List all pipeline runs."""
    return [
        {
            "run_id": r["run_id"],
            "change_control_id": r["change_control_id"],
            "status": r["status"],
            "started_at": r["started_at"],
            "completed_at": r.get("completed_at"),
        }
        for r in _pipeline_runs.values()
    ]


def _extract_message(update: dict[str, Any]) -> str:
    """Extract the text content from a state update's messages."""
    messages = update.get("messages", [])
    if messages:
        msg = messages[-1]
        return msg.content if hasattr(msg, "content") else str(msg)
    return ""


def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Serialize LangGraph state to JSON-compatible dict."""
    result = {}
    for key, value in state.items():
        if key == "messages":
            result[key] = [
                {"role": getattr(m, "type", "unknown"), "content": getattr(m, "content", str(m))}
                for m in value
            ]
        else:
            result[key] = value
    return result


def _serialize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Serialize a stream event for storage."""
    result = {}
    for node_name, update in event.items():
        serialized = {}
        for k, v in update.items():
            if k == "messages":
                serialized[k] = [
                    {"role": getattr(m, "type", "unknown"), "content": getattr(m, "content", str(m))}
                    for m in v
                ]
            else:
                serialized[k] = v
        result[node_name] = serialized
    return result
