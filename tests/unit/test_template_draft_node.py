# SVC-C2-047 — Unit Tests: TemplateDraftNode

from framework.schemas.agent_status import AgentStatus
from framework.secrets.base import MissingSecret

from src.nodes.template_draft_node import TemplateDraftNode


class TestTemplateDraftNode:
    def setup_method(self):
        self.node = TemplateDraftNode()

    def test_success_path_generates_dual_path_drafts_for_equal_pay(self, base_state, bound_test_secrets):
        state = {
            **base_state,
            "gap_report": [
                {
                    "clause_id": None,
                    "gap_type": "missing",
                    "severity": "high",
                    "explanation": "Mandatory disclosure topic 'equal_pay' not found in contract",
                }
            ],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        paths = {d["path"] for d in result["clause_drafts"]}
        assert "職務給方式" in paths
        assert "労使協定方式" in paths

    def test_empty_gap_report_yields_no_drafts(self, base_state, bound_test_secrets):
        state = {**base_state, "gap_report": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["clause_drafts"] == []

    def test_drafts_use_placeholder_tokens_not_real_entities(self, base_state, bound_test_secrets):
        state = {
            **base_state,
            "gap_report": [
                {"clause_id": "c1", "gap_type": "missing", "severity": "medium", "explanation": "wage gap"}
            ],
        }
        result = self.node.execute(state)
        for draft in result["clause_drafts"]:
            assert "[[REDACTED" in draft["draft_text"]

    def test_succeeds_with_no_secret_bound_in_mock_mode(self, base_state, monkeypatch):
        """Regression test: a fresh CI checkout has no env/ secret files at all.
        Mock mode must not depend on AZURE_OPENAI_API_KEY being resolvable."""
        monkeypatch.setenv("USE_MOCK", "true")
        state = {
            **base_state,
            "gap_report": [
                {
                    "clause_id": None,
                    "gap_type": "missing",
                    "severity": "high",
                    "explanation": "Mandatory disclosure topic 'equal_pay' not found in contract",
                }
            ],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value

    def test_raises_missing_secret_when_not_mock_and_no_secret_bound(self, base_state, monkeypatch):
        monkeypatch.delenv("USE_MOCK", raising=False)
        monkeypatch.delenv("STG_MOCK_MODE", raising=False)
        state = {
            **base_state,
            "gap_report": [
                {"clause_id": "c1", "gap_type": "missing", "severity": "medium", "explanation": "wage gap"}
            ],
        }
        try:
            self.node.execute(state)
            raise AssertionError("expected MissingSecret to propagate out of execute()")
        except MissingSecret:
            pass
