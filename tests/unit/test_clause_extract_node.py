# SVC-C2-047 — Unit Tests: ClauseExtractNode

from framework.schemas.agent_status import AgentStatus

from src.nodes.clause_extract_node import ClauseExtractNode


class TestClauseExtractNode:
    def setup_method(self):
        self.node = ClauseExtractNode()

    def test_success_path_extracts_multiple_clauses(self, base_state):
        state = {
            **base_state,
            "parsed_contract_text": "第1条 派遣期間は2026年4月1日から2027年3月31日までとする。第2条 賃金は月額25万円とする。",
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["extracted_clauses"]) >= 2
        assert all("clause_id" in c and "topic" in c for c in result["extracted_clauses"])

    def test_missing_input_returns_error(self, base_state):
        state = {**base_state, "parsed_contract_text": ""}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_topic_inference_wage(self, base_state):
        state = {**base_state, "parsed_contract_text": "賃金は月額25万円とする。"}
        result = self.node.execute(state)
        assert any(c["topic"] == "wage" for c in result["extracted_clauses"])

    def test_topic_inference_equal_pay(self, base_state):
        state = {**base_state, "parsed_contract_text": "同一労働同一賃金に基づき労使協定を締結する。"}
        result = self.node.execute(state)
        assert any(c["topic"] == "equal_pay" for c in result["extracted_clauses"])
