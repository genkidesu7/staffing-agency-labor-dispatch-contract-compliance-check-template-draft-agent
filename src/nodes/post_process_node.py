"""AgentCore Platform v1.0"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_WAGE_PATTERN_KEYS = ("wage", "salary", "amount")


class PostProcessNode(FunctionNode):
    """Format the compliance report + clause drafts into the final response payload."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        compliance_report = state.get("compliance_report", {})
        clause_drafts = state.get("clause_drafts", [])

        formatted_output = {
            "compliance_report": compliance_report,
            "clause_drafts": clause_drafts,
        }

        emit_trace_event(
            "output_formatted",
            {"gap_count": compliance_report.get("gap_count", 0)},
            state,
        )

        return {
            "formatted_output": formatted_output,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        # Defense-in-depth re-check: OutputValidateNode (inner graph) already
        # stripped wage figures/PII; this hook confirms no such key leaked
        # into the outer formatted payload through a future field addition.
        formatted_output = result.get("formatted_output", {})
        if isinstance(formatted_output, dict):
            for key in list(formatted_output.keys()):
                if any(marker in key.lower() for marker in _WAGE_PATTERN_KEYS):
                    formatted_output.pop(key, None)
        return result
