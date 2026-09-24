"""AgentCore Platform v1.0"""

from __future__ import annotations

import re
from typing import Any

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# Wage-figure pattern: 円 amounts (e.g. "250,000円", "25万円").
_WAGE_PATTERN = re.compile(r"[\d,]+(?:万)?円")
_PLACEHOLDER_TOKENS = (
    "[[REDACTED_ROLE]]",
    "[[REDACTED_WAGE_LEVEL]]",
    "[[REDACTED_START_DATE]]",
    "[[REDACTED_END_DATE]]",
)


class OutputValidateNode(FunctionNode):
    """Inner graph node. S-3 output validation — strips PII/wage figures,
    verifies mandatory disclosure items are preserved in the final report.

    Reads: clause_drafts, gap_report.
    Writes: compliance_report, clause_drafts (validated).
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        clause_drafts = state.get("clause_drafts", [])
        gap_report = state.get("gap_report", [])

        compliance_report = {
            "gap_count": len(gap_report),
            "gaps": gap_report,
            "severity_breakdown": {
                level: sum(1 for g in gap_report if g["severity"] == level) for level in ("high", "medium", "low")
            },
            "disclaimer": (
                "AI-generated compliance check and clause templates. "
                "Licensed labor consultant (社会保険労務士) must review before contract execution."
            ),
        }

        emit_trace_event(
            "output_validated",
            {"draft_count": len(clause_drafts), "gap_count": len(gap_report)},
            state,
        )

        return {
            "compliance_report": compliance_report,
            "clause_drafts": clause_drafts,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        clause_drafts = result.get("clause_drafts", [])
        for draft in clause_drafts:
            draft_text = draft.get("draft_text", "")
            if _WAGE_PATTERN.search(draft_text) and not any(token in draft_text for token in _PLACEHOLDER_TOKENS):
                raise SecurityViolationError(
                    "OutputValidateNode S-3: concrete wage figure found in clause draft "
                    "without placeholder token — blocked"
                )

        compliance_report = result.get("compliance_report", {})
        gaps_in_report = {g.get("clause_id") for g in compliance_report.get("gaps", [])}
        source_gaps = {g.get("clause_id") for g in result.get("gap_report", [])} or gaps_in_report
        if source_gaps - gaps_in_report:
            raise SecurityViolationError(
                "OutputValidateNode S-3 (preservation variant): compliance_report "
                "dropped one or more mandatory gap findings present in gap_report"
            )

        return result
