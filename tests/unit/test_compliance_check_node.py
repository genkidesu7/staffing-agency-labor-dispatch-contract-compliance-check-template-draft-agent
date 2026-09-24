# SVC-C2-047 — Unit Tests: ComplianceCheckNode

from framework.schemas.agent_status import AgentStatus
from framework.secrets.base import MissingSecret

from src.nodes.compliance_check_node import ComplianceCheckNode


class TestComplianceCheckNode:
    def setup_method(self):
        self.node = ComplianceCheckNode()

    def test_success_path_flags_missing_mandatory_topics(self, base_state, bound_test_secrets):
        state = {
            **base_state,
            "extracted_clauses": [{"clause_id": "clause_1", "text": "賃金は月額25万円。", "topic": "wage"}],
            "retrieved_statute_context": [
                {"source": "労働者派遣法", "article": "第26条", "text": "賃金に関する事項を明示すること。", "score": 0.9}
            ],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        verdicts = result["compliance_verdicts"]
        # equal_pay, dispatch_period, safety_health are not covered -> missing
        missing_topics = {v.get("missing_topic") for v in verdicts if v["verdict"] == "missing"}
        assert "equal_pay" in missing_topics

    def test_missing_statute_context_returns_error(self, base_state, bound_test_secrets):
        state = {**base_state, "extracted_clauses": [], "retrieved_statute_context": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_compliant_clause_matches_statute(self, base_state, bound_test_secrets):
        state = {
            **base_state,
            "extracted_clauses": [{"clause_id": "clause_1", "text": "安全衛生教育。", "topic": "safety_health"}],
            "retrieved_statute_context": [
                {"source": "労働安全衛生法", "article": "第1条", "text": "安全衛生に関する措置を講じること。", "score": 0.9}
            ],
        }
        result = self.node.execute(state)
        clause_verdict = next(v for v in result["compliance_verdicts"] if v["clause_id"] == "clause_1")
        assert clause_verdict["verdict"] == "compliant"

    def test_succeeds_with_no_secret_bound_in_mock_mode(self, base_state, monkeypatch):
        """Regression test: a fresh CI checkout has no env/ secret files at all.
        Mock mode must not depend on AZURE_OPENAI_API_KEY being resolvable."""
        monkeypatch.setenv("USE_MOCK", "true")
        state = {
            **base_state,
            "extracted_clauses": [{"clause_id": "clause_1", "text": "賃金は月額25万円。", "topic": "wage"}],
            "retrieved_statute_context": [
                {"source": "労働者派遣法", "article": "第26条", "text": "賃金に関する事項を明示すること。", "score": 0.9}
            ],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value

    def test_raises_missing_secret_when_not_mock_and_no_secret_bound(self, base_state, monkeypatch):
        monkeypatch.delenv("USE_MOCK", raising=False)
        monkeypatch.delenv("STG_MOCK_MODE", raising=False)
        state = {
            **base_state,
            "extracted_clauses": [{"clause_id": "clause_1", "text": "賃金は月額25万円。", "topic": "wage"}],
            "retrieved_statute_context": [
                {"source": "労働者派遣法", "article": "第26条", "text": "賃金に関する事項を明示すること。", "score": 0.9}
            ],
        }
        try:
            self.node.execute(state)
            raise AssertionError("expected MissingSecret to propagate out of execute()")
        except MissingSecret:
            pass
