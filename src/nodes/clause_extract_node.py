"""AgentCore Platform v1.0"""

from __future__ import annotations

import re
from typing import Any

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# Sentence-ish clause boundary: split on Japanese full-stop / newline / numbered item.
_CLAUSE_SPLIT_RE = re.compile(r"(?:(?<=[。])|(?:\n)|(?:第[0-9〇一二三四五六七八九十]+条))")


class ClauseExtractNode(FunctionNode):
    """Inner graph node. Segments contract text into discrete clause units.

    Reads: parsed_contract_text.
    Writes: extracted_clauses.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        parsed_text = state.get("parsed_contract_text", "")
        if not parsed_text:
            return {
                "status": AgentStatus.ERROR.value,
                "error": "ClauseExtractNode: parsed_contract_text missing",
                "error_log": ["ClauseExtractNode: parsed_contract_text missing"],
            }

        raw_segments = [seg.strip() for seg in _CLAUSE_SPLIT_RE.split(parsed_text) if seg.strip()]
        extracted_clauses = [
            {
                "clause_id": f"clause_{idx + 1}",
                "text": segment,
                "topic": _infer_topic(segment),
            }
            for idx, segment in enumerate(raw_segments)
        ]

        emit_trace_event(
            "clauses_extracted",
            {"clause_count": len(extracted_clauses)},
            state,
        )

        return {
            "extracted_clauses": extracted_clauses,
            "status": AgentStatus.SUCCESS.value,
        }


def _infer_topic(clause_text: str) -> str:
    if "同一労働同一賃金" in clause_text or "労使協定" in clause_text:
        return "equal_pay"
    if "賃金" in clause_text or "給与" in clause_text:
        return "wage"
    if "派遣期間" in clause_text or "期間" in clause_text:
        return "dispatch_period"
    if "安全" in clause_text or "衛生" in clause_text:
        return "safety_health"
    return "general_disclosure"
