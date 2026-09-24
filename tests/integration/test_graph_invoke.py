# SVC-C2-047 — Integration Tests: real .compile() + .invoke() path
#
# Per docs/07_test_stage.md's Definition of Done: unit tests that stub state
# and call execute()/route() directly do not prove the compiled LangGraph
# behaves correctly (schema projection can silently differ). These tests
# exercise the actual compiled graph end-to-end for both the outer graph
# (Cat 2 backbone) and the inner ComplianceWorkflowGraph.

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.domain_workflow_graph import ComplianceWorkflowGraph
from src.graph.graph import SvcC2047StaffingContractComplianceAgent

SAMPLE_CONTRACT = (
    "第1条 派遣期間は2026年4月1日から2027年3月31日までとする。"
    "第2条 賃金は月額25万円とする。"
    "第3条 安全衛生教育を実施する。"
)

_VERIFIED_CTX = InvocationContext(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL)


class TestOuterGraphInvoke:
    def test_compile_and_invoke_end_to_end_success(self, bound_test_secrets):
        agent = SvcC2047StaffingContractComplianceAgent(config={"max_retry": 1})
        agent.compile()
        agent.provision_secrets(bound_test_secrets)

        result = agent.invoke(SAMPLE_CONTRACT, ctx=_VERIFIED_CTX)

        assert result["status"] == "success"
        assert "InitializeNode" in result["node_history"]
        assert "ComplianceWorkflowGraphNode" in result["node_history"]
        assert "PostProcessNode" in result["node_history"]
        assert "FinalizeNode" in result["node_history"]
        assert result["output"]["compliance_report"]["gap_count"] >= 0
        assert isinstance(result["output"]["clause_drafts"], list)

    def test_s1_trust_gate_denies_anonymous_caller(self, bound_test_secrets):
        agent = SvcC2047StaffingContractComplianceAgent(config={"max_retry": 1})
        agent.compile()
        agent.provision_secrets(bound_test_secrets)

        result = agent.invoke(SAMPLE_CONTRACT)  # default ANONYMOUS trust

        assert result["status"] == "error"

    def test_empty_input_routes_to_error_without_crashing(self, bound_test_secrets):
        agent = SvcC2047StaffingContractComplianceAgent(config={"max_retry": 1})
        agent.compile()
        agent.provision_secrets(bound_test_secrets)

        result = agent.invoke("", ctx=_VERIFIED_CTX)

        assert result["status"] == "error"


class TestInnerGraphInvoke:
    def test_compile_and_invoke_inner_graph_directly(self, bound_test_secrets):
        inner = ComplianceWorkflowGraph(config={})
        inner.compile()
        inner.provision_secrets(bound_test_secrets)

        result = inner.invoke(SAMPLE_CONTRACT, ctx=_VERIFIED_CTX)

        assert result["status"] == "success"
        expected_nodes = [
            "ContractIngestNode",
            "ClauseExtractNode",
            "LaborLawRetrieveNode",
            "ComplianceCheckNode",
            "GapAnalyzeNode",
            "TemplateDraftNode",
            "OutputValidateNode",
        ]
        for node_name in expected_nodes:
            assert node_name in result["node_history"], f"{node_name} missing from node_history"

    def test_inner_graph_falls_back_to_user_input_when_validated_input_absent(self, bound_test_secrets):
        """Regression: inner graph's fresh initial_state only contains user_input —
        every inner node consuming input text must fall back correctly (sdk-expertise
        'Cat 2 composition' gotcha)."""
        inner = ComplianceWorkflowGraph(config={})
        inner.compile()
        inner.provision_secrets(bound_test_secrets)

        result = inner.invoke(SAMPLE_CONTRACT, ctx=_VERIFIED_CTX)

        assert result["status"] == "success"
        assert result["compliance_report"]["gap_count"] >= 0
