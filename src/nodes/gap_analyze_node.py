"""AgentCore Platform v1.0"""

from __future__ import annotations

from typing import Any

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# Topics whose absence carries the highest license-revocation audit risk.
_HIGH_RISK_TOPICS = {"equal_pay", "wage"}


class GapAnalyzeNode(FunctionNode):
    """Inner graph node. Classifies gaps and assigns severity.

    Reads: compliance_verdicts.
    Writes: gap_report.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        compliance_verdicts = state.get("compliance_verdicts", [])
        if not compliance_verdicts:
            return {
                "status": AgentStatus.ERROR.value,
                "error": "GapAnalyzeNode: compliance_verdicts missing",
                "error_log": ["GapAnalyzeNode: compliance_verdicts missing"],
            }

        gap_report = []
        for item in compliance_verdicts:
            verdict = item["verdict"]
            if verdict == "compliant":
                continue

            gap_type = "missing" if verdict == "missing" else "ambiguous"
            topic = item.get("missing_topic")
            severity = (
                "high"
                if (gap_type == "missing" and topic in _HIGH_RISK_TOPICS)
                else ("medium" if gap_type == "missing" else "low")
            )
            gap_report.append(
                {
                    "clause_id": item.get("clause_id"),
                    "gap_type": gap_type,
                    "severity": severity,
                    "explanation": (
                        f"Mandatory disclosure topic '{topic}' not found in contract"
                        if gap_type == "missing"
                        else f"Clause {item.get('clause_id')} could not be matched to statute text with confidence"
                    ),
                }
            )

        severity_breakdown = {
            level: sum(1 for g in gap_report if g["severity"] == level) for level in ("high", "medium", "low")
        }
        emit_trace_event("gaps_identified", {"severity_breakdown": severity_breakdown}, state)

        return {
            "gap_report": gap_report,
            "status": AgentStatus.SUCCESS.value,
        }
