# SVC-C2-047 — Unit Tests: GapAnalyzeNode

from framework.schemas.agent_status import AgentStatus

from src.nodes.gap_analyze_node import GapAnalyzeNode


class TestGapAnalyzeNode:
    def setup_method(self):
        self.node = GapAnalyzeNode()

    def test_success_path_assigns_high_severity_to_equal_pay_gap(self, base_state):
        state = {
            **base_state,
            "compliance_verdicts": [
                {"clause_id": None, "verdict": "missing", "citation": None, "missing_topic": "equal_pay"},
                {"clause_id": "clause_2", "verdict": "compliant", "citation": "第26条"},
            ],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["gap_report"]) == 1
        assert result["gap_report"][0]["severity"] == "high"
        assert result["gap_report"][0]["gap_type"] == "missing"

    def test_ambiguous_verdict_becomes_low_severity_gap(self, base_state):
        state = {
            **base_state,
            "compliance_verdicts": [{"clause_id": "clause_1", "verdict": "ambiguous", "citation": None}],
        }
        result = self.node.execute(state)
        assert result["gap_report"][0]["severity"] == "low"
        assert result["gap_report"][0]["gap_type"] == "ambiguous"

    def test_all_compliant_yields_empty_gap_report(self, base_state):
        state = {
            **base_state,
            "compliance_verdicts": [{"clause_id": "clause_1", "verdict": "compliant", "citation": "第26条"}],
        }
        result = self.node.execute(state)
        assert result["gap_report"] == []

    def test_missing_verdicts_returns_error(self, base_state):
        state = {**base_state, "compliance_verdicts": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value
