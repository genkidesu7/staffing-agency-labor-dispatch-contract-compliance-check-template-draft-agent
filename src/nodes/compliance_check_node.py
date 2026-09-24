"""AgentCore Platform v1.0"""

from __future__ import annotations

from typing import Any

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.mock_mode import mock_mode_enabled

# Article sub-items that MUST appear in a compliant 派遣契約 disclosure set.
_MANDATORY_TOPICS = ("wage", "equal_pay", "dispatch_period", "safety_health")


class ComplianceCheckNode(FunctionNode):
    """Inner graph node. Compares extracted clauses against retrieved statute text.

    Reads: extracted_clauses, retrieved_statute_context.
    Writes: compliance_verdicts.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        extracted_clauses = state.get("extracted_clauses", [])
        retrieved_statute_context = state.get("retrieved_statute_context", [])
        if not retrieved_statute_context:
            return {
                "status": AgentStatus.ERROR.value,
                "error": "ComplianceCheckNode: retrieved_statute_context missing",
                "error_log": ["ComplianceCheckNode: retrieved_statute_context missing"],
            }

        ctx = InvocationContext.from_state(state)
        # LLM credential resolved via handle; grounding logic below is
        # rule-based for determinism (LLM call point noted for future wiring).
        _ = "mock" if mock_mode_enabled() else ctx.secrets.require("AZURE_OPENAI_API_KEY")

        covered_topics = {clause["topic"] for clause in extracted_clauses}
        verdicts = []
        for clause in extracted_clauses:
            matching_passages = [p for p in retrieved_statute_context if _topic_matches(clause["topic"], p)]
            verdict = "compliant" if matching_passages else "ambiguous"
            verdicts.append(
                {
                    "clause_id": clause["clause_id"],
                    "verdict": verdict,
                    "citation": matching_passages[0]["article"] if matching_passages else None,
                }
            )

        for topic in _MANDATORY_TOPICS:
            if topic not in covered_topics:
                verdicts.append(
                    {
                        "clause_id": None,
                        "verdict": "missing",
                        "citation": None,
                        "missing_topic": topic,
                    }
                )

        emit_trace_event(
            "compliance_checked",
            {
                "verdict_counts": {
                    v: sum(1 for item in verdicts if item["verdict"] == v)
                    for v in ("compliant", "ambiguous", "missing")
                }
            },
            state,
        )

        return {
            "compliance_verdicts": verdicts,
            "status": AgentStatus.SUCCESS.value,
        }


def _topic_matches(clause_topic: str, passage: dict[str, Any]) -> bool:
    topic_keywords = {
        "wage": ("賃金", "同一労働同一賃金"),
        "equal_pay": ("同一労働同一賃金", "労使協定"),
        "dispatch_period": ("派遣期間", "期間"),
        "safety_health": ("安全", "衛生"),
        "general_disclosure": ("明示", "記載事項"),
    }
    keywords = topic_keywords.get(clause_topic, ())
    return any(kw in passage.get("text", "") for kw in keywords)
