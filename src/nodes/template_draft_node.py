"""AgentCore Platform v1.0"""

from __future__ import annotations

from typing import Any

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.mock_mode import mock_mode_enabled

_JOB_BASED_TEMPLATE = (
    "職務給方式に基づき、[[REDACTED_ROLE]]の業務内容・責任の程度に照らし、"
    "同種の業務に従事する一般労働者の平均的な賃金水準以上の賃金を支払う。"
)
_LABOR_AGREEMENT_TEMPLATE = (
    "労使協定方式に基づき、労使協定に定める賃金水準（[[REDACTED_WAGE_LEVEL]]）以上の賃金を、"
    "[[REDACTED_ROLE]]に対して支払う。"
)

_DEFAULT_DRAFTS = {
    "equal_pay": (_JOB_BASED_TEMPLATE, _LABOR_AGREEMENT_TEMPLATE),
    "wage": (_JOB_BASED_TEMPLATE, _LABOR_AGREEMENT_TEMPLATE),
    "dispatch_period": (
        "派遣可能期間は、[[REDACTED_START_DATE]]から[[REDACTED_END_DATE]]までとする。",
        None,
    ),
    "safety_health": (
        "派遣先は、[[REDACTED_ROLE]]に対し、労働安全衛生法に定める安全衛生教育を実施する。",
        None,
    ),
}


class TemplateDraftNode(FunctionNode):
    """Inner graph node. Generates compliant clause drafts for identified gaps.

    Reads: gap_report.
    Writes: clause_drafts.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        gap_report = state.get("gap_report", [])
        if not gap_report:
            emit_trace_event("drafts_generated", {"draft_count": 0}, state)
            return {"clause_drafts": [], "status": AgentStatus.SUCCESS.value}

        ctx = InvocationContext.from_state(state)
        # LLM credential resolved via handle; template lookup below is
        # rule-based for determinism (LLM call point noted for future wiring).
        _ = "mock" if mock_mode_enabled() else ctx.secrets.require("AZURE_OPENAI_API_KEY")

        clause_drafts = []
        for gap in gap_report:
            topic = gap.get("explanation", "")
            matched_topic = next((t for t in _DEFAULT_DRAFTS if t in topic), "wage")
            job_based, labor_agreement = _DEFAULT_DRAFTS.get(matched_topic, _DEFAULT_DRAFTS["wage"])

            clause_drafts.append(
                {
                    "clause_id": gap.get("clause_id"),
                    "draft_text": job_based,
                    "path": "職務給方式",
                }
            )
            if labor_agreement:
                clause_drafts.append(
                    {
                        "clause_id": gap.get("clause_id"),
                        "draft_text": labor_agreement,
                        "path": "労使協定方式",
                    }
                )

        emit_trace_event("drafts_generated", {"draft_count": len(clause_drafts)}, state)

        return {
            "clause_drafts": clause_drafts,
            "status": AgentStatus.SUCCESS.value,
        }
