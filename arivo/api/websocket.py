"""WebSocket endpoint for live pipeline updates."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Active WebSocket connections keyed by run_id
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str) -> None:
    """WebSocket connection for real-time pipeline updates."""
    await websocket.accept()
    _connections.setdefault(run_id, []).append(websocket)
    try:
        # Keep connection open until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.get(run_id, []).remove(websocket)
        if not _connections.get(run_id):
            _connections.pop(run_id, None)


async def broadcast_event(run_id: str, event: dict[str, Any]) -> None:
    """Broadcast an event to all WebSocket connections for a run."""
    connections = _connections.get(run_id, [])
    dead: list[WebSocket] = []
    for ws in connections:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)
