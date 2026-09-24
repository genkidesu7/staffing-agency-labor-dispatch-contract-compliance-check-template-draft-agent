# SVC-C2-047 — Unit Tests: outer PreProcessNode / PostProcessNode

import pytest
from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus

from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import MAX_CONTRACT_CHARS, PreProcessNode


class TestPreProcessNode:
    def setup_method(self):
        self.node = PreProcessNode()

    def test_success_path_trims_input(self, base_state):
        state = {**base_state, "user_input": "  第1条 契約条項。  ", "input_context": {}}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["validated_input"] == "第1条 契約条項。"

    def test_empty_input_returns_error(self, base_state):
        state = {**base_state, "user_input": "", "input_context": {}}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_extra_security_gate_input_rejects_oversized_text(self, base_state):
        state = {**base_state, "user_input": "a" * (MAX_CONTRACT_CHARS + 1)}
        with pytest.raises(SecurityViolationError):
            self.node._extra_security_gate_input(state)


class TestPostProcessNode:
    def setup_method(self):
        self.node = PostProcessNode()

    def test_success_path_formats_output(self, base_state):
        state = {
            **base_state,
            "compliance_report": {"gap_count": 1},
            "clause_drafts": [{"clause_id": "c1", "draft_text": "...", "path": "職務給方式"}],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["formatted_output"]["compliance_report"]["gap_count"] == 1

    def test_extra_security_gate_output_strips_wage_like_keys(self):
        result = {"formatted_output": {"wage_amount": "250000", "compliance_report": {}}}
        cleaned = self.node._extra_security_gate_output(result)
        assert "wage_amount" not in cleaned["formatted_output"]
        assert "compliance_report" in cleaned["formatted_output"]
