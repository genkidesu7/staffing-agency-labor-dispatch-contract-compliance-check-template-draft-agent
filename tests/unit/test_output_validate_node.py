# SVC-C2-047 — Unit Tests: OutputValidateNode

import pytest
from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus

from src.nodes.output_validate_node import OutputValidateNode


class TestOutputValidateNode:
    def setup_method(self):
        self.node = OutputValidateNode()

    def test_success_path_builds_compliance_report(self, base_state):
        state = {
            **base_state,
            "clause_drafts": [{"clause_id": "c1", "draft_text": "職務給方式に基づき...", "path": "職務給方式"}],
            "gap_report": [{"clause_id": "c1", "gap_type": "missing", "severity": "high", "explanation": "..."}],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["compliance_report"]["gap_count"] == 1
        assert "disclaimer" in result["compliance_report"]

    def test_extra_security_gate_output_blocks_concrete_wage_figure(self, base_state):
        result = {
            "clause_drafts": [{"clause_id": "c1", "draft_text": "賃金は月額250,000円とする。", "path": "職務給方式"}],
            "compliance_report": {"gaps": []},
            "gap_report": [],
        }
        with pytest.raises(SecurityViolationError):
            self.node._extra_security_gate_output(result)

    def test_extra_security_gate_output_allows_placeholder_wage(self, base_state):
        result = {
            "clause_drafts": [
                {
                    "clause_id": "c1",
                    "draft_text": "賃金水準（[[REDACTED_WAGE_LEVEL]]）以上の賃金を支払う。250,000円",
                    "path": "労使協定方式",
                }
            ],
            "compliance_report": {"gaps": []},
            "gap_report": [],
        }
        returned = self.node._extra_security_gate_output(result)
        assert returned is result

    def test_preservation_variant_blocks_dropped_gap(self, base_state):
        result = {
            "clause_drafts": [],
            "compliance_report": {"gaps": []},  # dropped the gap below
            "gap_report": [{"clause_id": "c1", "gap_type": "missing", "severity": "high", "explanation": "..."}],
        }
        with pytest.raises(SecurityViolationError):
            self.node._extra_security_gate_output(result)
