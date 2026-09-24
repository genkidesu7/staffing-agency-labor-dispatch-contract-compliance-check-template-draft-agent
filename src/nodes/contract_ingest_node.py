"""AgentCore Platform v1.0"""

from __future__ import annotations

import re
from typing import Any

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

MAX_CONTRACT_CHARS = 5000

_ENGAGEMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "it_engineer": ("システムエンジニア", "IT エンジニア", "ITエンジニア", "プログラマ"),
    "manufacturing": ("製造", "工場", "組立", "検査業務"),
}


class ContractIngestNode(FunctionNode):
    """Inner graph node. Parses raw contract text and classifies engagement type.

    Reads: validated_input (falls back to user_input — inner graph fresh state).
    Writes: parsed_contract_text, engagement_type.
    """

    required_trust_level = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        text = state.get("validated_input") or state.get("user_input") or ""
        if not isinstance(text, str):
            raise SecurityViolationError("ContractIngestNode: input must be a plain string")
        if len(text) > MAX_CONTRACT_CHARS:
            raise SecurityViolationError(f"ContractIngestNode: input exceeds {MAX_CONTRACT_CHARS} chars (S-1 limit)")
        return state

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        contract_text = state.get("validated_input", state.get("user_input", ""))
        if not contract_text:
            return {
                "status": AgentStatus.ERROR.value,
                "error": "ContractIngestNode: no contract text provided",
                "error_log": ["ContractIngestNode: no contract text provided"],
            }

        parsed_text = re.sub(r"\s+", " ", contract_text).strip()
        engagement_type = "general"
        for label, keywords in _ENGAGEMENT_KEYWORDS.items():
            if any(kw in parsed_text for kw in keywords):
                engagement_type = label
                break

        emit_trace_event(
            "contract_classified",
            {"engagement_type": engagement_type, "text_length": len(parsed_text)},
            state,
        )

        return {
            "parsed_contract_text": parsed_text,
            "engagement_type": engagement_type,
            "status": AgentStatus.SUCCESS.value,
        }
