"""Mock Veeva Vault REST API client.

Simulates the Veeva Vault API endpoints used by ARIVO:
- Authentication (session-based)
- VQL queries on change_control__c objects
- Attachment retrieval
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CHANGE_CONTROLS: Optional[list[dict[str, Any]]] = None


def _load_change_controls() -> list[dict[str, Any]]:
    global _CHANGE_CONTROLS
    if _CHANGE_CONTROLS is None:
        with open(_DATA_DIR / "mock_change_controls.json", encoding="utf-8") as f:
            _CHANGE_CONTROLS = json.load(f)
    return _CHANGE_CONTROLS


def authenticate(username: str = "arivo_service", password: str = "***") -> dict[str, Any]:
    """Simulate POST /api/v24.1/auth — returns a mock session."""
    return {
        "responseStatus": "SUCCESS",
        "sessionId": "MOCK-SESSION-7F3A2B1C-E4D5-6789-ABCD-EF0123456789",
        "userId": 12345,
        "vaultId": 67890,
        "vaultIds": [{"id": 67890, "name": "PharmaCorp QMS Vault"}],
    }


def query_change_control(change_control_id: str) -> dict[str, Any]:
    """Simulate VQL query: SELECT * FROM change_control__c WHERE id = :id

    Returns the full change control record or an error response.
    """
    records = _load_change_controls()
    for record in records:
        if record["change_control_id"] == change_control_id:
            return {
                "responseStatus": "SUCCESS",
                "responseDetails": {
                    "total": 1,
                    "object": "change_control__c",
                    "url": f"/api/v24.1/vobjects/change_control__c/{change_control_id}",
                },
                "data": [record],
            }
    return {
        "responseStatus": "FAILURE",
        "errors": [{"type": "INVALID_DATA", "message": f"No record found for {change_control_id}"}],
    }


def list_change_controls() -> list[dict[str, str]]:
    """Return a summary list of all available change controls for the dashboard."""
    records = _load_change_controls()
    return [
        {
            "change_control_id": r["change_control_id"],
            "title": r["title"],
            "change_type": r["change_type"],
            "status": r["status"],
            "has_adverse_event": r.get("adverse_event") is not None,
        }
        for r in records
    ]


def get_attachments(change_control_id: str) -> list[str]:
    """Simulate GET /api/v24.1/vobjects/change_control__c/{id}/attachments"""
    records = _load_change_controls()
    for record in records:
        if record["change_control_id"] == change_control_id:
            return record.get("attachments", [])
    return []
