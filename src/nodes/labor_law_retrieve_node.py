"""AgentCore Platform v1.0"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, TypeVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.labor_law_kb_service import LaborLawKbService
from src.services.mock_mode import mock_mode_enabled

_T = TypeVar("_T")


def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async call from sync node code, safe whether or not the
    calling thread already has a running event loop (e.g. under uvicorn).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


class LaborLawRetrieveNode(FunctionNode):
    """Inner graph node. Retrieves relevant labor-law statute passages.

    Reads: extracted_clauses, engagement_type.
    Writes: retrieved_statute_context.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self) -> None:
        super().__init__()
        self._service = LaborLawKbService()

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        extracted_clauses = state.get("extracted_clauses", [])
        engagement_type = state.get("engagement_type", "general")
        if not extracted_clauses:
            return {
                "status": AgentStatus.ERROR.value,
                "error": "LaborLawRetrieveNode: extracted_clauses missing",
                "error_log": ["LaborLawRetrieveNode: extracted_clauses missing"],
            }

        ctx = InvocationContext.from_state(state)
        credential_handle = "mock" if mock_mode_enabled() else ctx.secrets.require("LABOR_LAW_KB_API_KEY")

        clause_topics = [clause["topic"] for clause in extracted_clauses]

        try:
            passages = _run_async(self._service.retrieve(engagement_type, clause_topics, credential_handle))
        except Exception as exc:  # transient KB failure — allow retry
            return {
                "status": AgentStatus.RETRY.value,
                "error": str(exc),
                "error_log": [f"LaborLawRetrieveNode: [RETRY] {exc}"],
            }

        emit_trace_event(
            "statute_retrieved",
            {"source_count": len(passages), "engagement_type": engagement_type},
            state,
        )

        return {
            "retrieved_statute_context": passages,
            "status": AgentStatus.SUCCESS.value,
        }
