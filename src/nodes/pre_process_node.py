"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Read input_context via state.get("input_context", {}) — read-only [C1]
#  - Never import from mediator/, api/, or other agents

from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

MAX_CONTRACT_CHARS = 5000


class PreProcessNode(FunctionNode):
    """Validate and sanitize the raw draft contract text before compliance processing."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        if not isinstance(user_input, str):
            raise SecurityViolationError("PreProcessNode: user_input must be a plain string")
        if len(user_input) > MAX_CONTRACT_CHARS:
            raise SecurityViolationError(f"PreProcessNode: user_input exceeds {MAX_CONTRACT_CHARS} chars (S-1 limit)")
        return state

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        input_context = state.get("input_context", {})  # read-only [C1]

        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PreProcessNode: user_input is empty or missing"],
            }

        emit_trace_event(
            "input_validated",
            {"channel": input_context.get("channel", "unknown"), "length": len(user_input)},
            state,
        )

        return {
            "validated_input": user_input.strip(),
            "status": AgentStatus.SUCCESS.value,
        }
