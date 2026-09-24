# SVC-C2-047 — Unit Tests: LaborLawRetrieveNode

from framework.schemas.agent_status import AgentStatus

from src.nodes.labor_law_retrieve_node import LaborLawRetrieveNode

from framework.secrets.base import MissingSecret


class TestLaborLawRetrieveNode:
    def setup_method(self):
        self.node = LaborLawRetrieveNode()

    def test_success_path_retrieves_passages(self, base_state, bound_test_secrets):
        state = {
            **base_state,
            "engagement_type": "it_engineer",
            "extracted_clauses": [{"clause_id": "clause_1", "text": "...", "topic": "wage"}],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["retrieved_statute_context"]) > 0

    def test_missing_clauses_returns_error(self, base_state, bound_test_secrets):
        state = {**base_state, "engagement_type": "general", "extracted_clauses": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_runs_safely_inside_a_running_event_loop(self, base_state, bound_test_secrets):
        """Regression: asyncio.run() raises RuntimeError when called from a thread
        that already has a running loop (e.g. under uvicorn/FastAPI)."""
        import asyncio

        state = {
            **base_state,
            "engagement_type": "manufacturing",
            "extracted_clauses": [{"clause_id": "clause_1", "text": "...", "topic": "safety_health"}],
        }

        async def _invoke_from_loop():
            return self.node.execute(state)

        result = asyncio.run(_invoke_from_loop())
        assert result["status"] == AgentStatus.SUCCESS.value

    def test_succeeds_with_no_secret_bound_in_mock_mode(self, base_state, monkeypatch):
        """Regression test: a fresh CI checkout has no env/ secret files at all.
        Mock mode must not depend on LABOR_LAW_KB_API_KEY being resolvable."""
        monkeypatch.setenv("USE_MOCK", "true")
        # No bound_secrets() context at all — current_secrets() falls back to NullProvider.
        state = {
            **base_state,
            "engagement_type": "it_engineer",
            "extracted_clauses": [{"clause_id": "clause_1", "text": "...", "topic": "wage"}],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value

    def test_raises_missing_secret_when_not_mock_and_no_secret_bound(self, base_state, monkeypatch):
        """Negative test: clear every accepted mock-mode alias so the real path
        is actually exercised (implementation_rule.md §2)."""
        monkeypatch.delenv("USE_MOCK", raising=False)
        monkeypatch.delenv("STG_MOCK_MODE", raising=False)
        state = {
            **base_state,
            "engagement_type": "it_engineer",
            "extracted_clauses": [{"clause_id": "clause_1", "text": "...", "topic": "wage"}],
        }
        try:
            self.node.execute(state)
            raise AssertionError("expected MissingSecret to propagate out of execute()")
        except MissingSecret:
            pass
