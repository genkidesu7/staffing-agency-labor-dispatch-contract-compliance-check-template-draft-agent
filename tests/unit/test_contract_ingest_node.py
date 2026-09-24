# SVC-C2-047 — Unit Tests: ContractIngestNode

import pytest
from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus

from src.nodes.contract_ingest_node import MAX_CONTRACT_CHARS, ContractIngestNode


class TestContractIngestNode:
    def setup_method(self):
        self.node = ContractIngestNode()

    def test_success_path_classifies_it_engineer(self, base_state):
        state = {**base_state, "user_input": "システムエンジニアの派遣契約書。第1条 派遣期間。"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["engagement_type"] == "it_engineer"
        assert result["parsed_contract_text"]

    def test_success_path_falls_back_to_general(self, base_state):
        state = {**base_state, "user_input": "一般的な業務委託契約書。"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["engagement_type"] == "general"

    def test_prefers_validated_input_over_user_input(self, base_state):
        state = {
            **base_state,
            "user_input": "raw",
            "validated_input": "製造業務の派遣契約。工場での組立作業。",
        }
        result = self.node.execute(state)
        assert result["engagement_type"] == "manufacturing"

    def test_empty_input_returns_error(self, base_state):
        state = {**base_state, "user_input": ""}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_extra_security_gate_input_rejects_oversized_text(self, base_state):
        state = {**base_state, "user_input": "a" * (MAX_CONTRACT_CHARS + 1)}
        with pytest.raises(SecurityViolationError):
            self.node._extra_security_gate_input(state)

    def test_extra_security_gate_input_accepts_valid_text(self, base_state):
        state = {**base_state, "user_input": "第1条 通常の契約条項。"}
        returned = self.node._extra_security_gate_input(state)
        assert returned is state

    def test_execute_method_signature(self):
        import inspect

        sig = inspect.signature(ContractIngestNode.execute)
        params = list(sig.parameters.keys())
        assert params[1] == "state"
        assert "_invoke_impl" not in ContractIngestNode.__dict__
