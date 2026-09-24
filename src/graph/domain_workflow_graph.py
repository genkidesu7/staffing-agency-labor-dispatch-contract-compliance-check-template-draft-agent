"""AgentCore Platform v1.0"""

# src/graph/domain_workflow_graph.py — inner graph for the Cat 2 compliance
# workflow. Instantiated by ComplianceWorkflowGraphNode.get_subgraph() in
# graph.py. Inherits BaseGraph directly (fully custom 7-node topology).

from typing import Any

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_status import AgentStatus
from src.nodes.clause_extract_node import ClauseExtractNode
from src.nodes.compliance_check_node import ComplianceCheckNode
from src.nodes.contract_ingest_node import ContractIngestNode
from src.nodes.gap_analyze_node import GapAnalyzeNode
from src.nodes.labor_law_retrieve_node import LaborLawRetrieveNode
from src.nodes.output_validate_node import OutputValidateNode
from src.nodes.template_draft_node import TemplateDraftNode
from src.schemas.state import State


class ComplianceWorkflowGraph(BaseGraph):
    """Inner graph for the SVC-C2-047 contract-compliance domain workflow.

    Pipeline (linear):
        START → contract_ingest → clause_extract → labor_law_retrieve
              → compliance_check → gap_analyze → template_draft
              → output_validate → END
    """

    @property
    def name(self) -> str:
        return "svc_c2_047_compliance_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        """No mandatory config keys for this inner graph."""
        pass

    def register_nodes(self) -> None:
        # No super() call — BaseGraph.register_nodes() is abstract.
        # initialize/finalize are outer-graph concerns.
        self._nodes["contract_ingest"] = ContractIngestNode()
        self._nodes["clause_extract"] = ClauseExtractNode()
        self._nodes["labor_law_retrieve"] = LaborLawRetrieveNode()
        self._nodes["compliance_check"] = ComplianceCheckNode()
        self._nodes["gap_analyze"] = GapAnalyzeNode()
        self._nodes["template_draft"] = TemplateDraftNode()
        self._nodes["output_validate"] = OutputValidateNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "contract_ingest")
        self._sg.add_edge("contract_ingest", "clause_extract")
        self._sg.add_edge("clause_extract", "labor_law_retrieve")
        self._sg.add_edge("labor_law_retrieve", "compliance_check")
        self._sg.add_edge("compliance_check", "gap_analyze")
        self._sg.add_edge("gap_analyze", "template_draft")
        self._sg.add_edge("template_draft", "output_validate")
        self._sg.add_edge("output_validate", END)

    def route(self, state: State) -> str:
        """Required by BaseGraph ABC; never invoked (linear topology, no conditional edges)."""
        return END if state.get("status") == AgentStatus.ERROR.value else "output_validate"

    def get_output(self, state: State) -> dict[str, Any]:
        """Shape the sub_result dict consumed by ComplianceWorkflowGraphNode.merge_output()."""
        return {
            "compliance_report": state.get("compliance_report", {}),
            "clause_drafts": state.get("clause_drafts", []),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
            "error_log": state.get("error_log", []),
        }
