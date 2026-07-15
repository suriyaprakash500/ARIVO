"""Shared LangGraph workflow state schema."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ArivoState(dict):
    """Global state flowing through the LangGraph pipeline.

    Uses TypedDict-style annotations for LangGraph StateGraph.
    Handles messages with LangGraph's add_messages reducer.
    """

    __annotations__ = {
        # --- Messages (LangGraph standard) ---
        "messages": Annotated[list[AnyMessage], add_messages],

        # --- Trigger input ---
        "change_control_id": str,

        # --- QMS Extraction output ---
        "qms_data": dict,
        "has_adverse_event": bool,

        # --- Regulatory Assessment output ---
        "regulatory_assessment": dict,

        # --- Dossier Structuring output ---
        "dossier_sections": dict,

        # --- PV E2B(R3) output ---
        "e2b_xml": str,

        # --- Critic / Reflection ---
        "critic_feedback": Annotated[list, operator.add],
        "critic_pass": bool,
        "reflection_count": int,

        # --- Pipeline control ---
        "current_agent": str,
        "next_agent": str,
        "status": str,

        # --- ALCOA+ Audit Trail ---
        "audit_trail": Annotated[list, operator.add],
    }
