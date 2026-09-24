"""AgentCore Platform v1.0"""

# Cat 2 outer graph. Fixed 5-node backbone (initialize → pre_process → main
# → post_process → finalize). Domain complexity lives in the `main` slot via
# ComplianceWorkflowGraphNode, which wraps the inner ComplianceWorkflowGraph
# (src/graph/domain_workflow_graph.py). Do NOT override add_edges() here.

from typing import TYPE_CHECKING, Any, ClassVar

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State

if TYPE_CHECKING:
    from src.graph.domain_workflow_graph import ComplianceWorkflowGraph


class ComplianceWorkflowGraphNode(GraphNode):
    """Wraps the inner ComplianceWorkflowGraph; assigned to the `main` slot."""

    # Fail fast: a partial/silently-degraded compliance report is worse than
    # a hard error, given the legal/audit stakes (docs/02_design.md decision record).
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def get_subgraph(self) -> "ComplianceWorkflowGraph":
        from src.graph.domain_workflow_graph import ComplianceWorkflowGraph

        return ComplianceWorkflowGraph(config=self._parent_config())

    def extract_input(self, state: AgentState) -> str:
        return str(state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "compliance_report": sub_result.get("compliance_report", {}),
            "clause_drafts": sub_result.get("clause_drafts", []),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {}


class SvcC2047StaffingContractComplianceAgent(AgentBaseGraph):
    """SVC-C2-047 — Staffing Agency 労働者派遣法 Contract Compliance Check &
    Template Draft Agent. Cat 2: outer AgentBaseGraph backbone + GraphNode
    wrapping the 7-node inner compliance workflow.
    """

    @property
    def name(self) -> str:
        return "svc_c2_047_staffing_contract_compliance_agent"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects: initialize, finalize
        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = ComplianceWorkflowGraphNode()
        self._nodes["post_process"] = PostProcessNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.
