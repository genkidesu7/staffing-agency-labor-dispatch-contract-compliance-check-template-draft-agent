# PB-7: HITL Interrupt Propagation Verification (conditional on hitl.enabled: true)
# Verifies that interrupt() called inside execute() raises GraphInterrupt, and that
# BaseNode.__call__() lets it bubble up to the LangGraph engine rather than catching
# it as a generic error (status must NOT become "error").

from __future__ import annotations

import pathlib

import pytest
import yaml

_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "agent.yaml"


def _hitl_enabled() -> bool:
    """Read config/agent.yaml and return hitl.enabled (default False when absent)."""
    if not _CONFIG_PATH.exists():
        return False
    manifest = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
    agent = manifest.get("agent", manifest)
    hitl = (agent or {}).get("hitl", {}) or {}
    return bool(hitl.get("enabled", False))


pytestmark = pytest.mark.skipif(
    not _hitl_enabled(),
    reason="PB-7 applies only when config/agent.yaml sets hitl.enabled: true",
)


class TestHitlInterruptPropagation:
    """PB-7: GraphInterrupt from interrupt() must reach the LangGraph engine unmodified."""

    def test_interrupt_propagates_through_call_and_invoke(self):
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.errors import GraphInterrupt
        from langgraph.graph import END, START, StateGraph
        from langgraph.types import interrupt

        from framework.nodes.function_node import FunctionNode
        from framework.schemas.agent_state import AgentState

        class ReviewNode(FunctionNode):
            def execute(self, state: AgentState) -> dict:
                draft = "draft-result"
                feedback = interrupt({"draft": draft, "reason": "low confidence"})
                return {**state, "hitl_draft": draft, "hitl_feedback": feedback}

        graph = StateGraph(AgentState)
        graph.add_node("review", ReviewNode())
        graph.add_edge(START, "review")
        graph.add_edge("review", END)
        app = graph.compile(checkpointer=MemorySaver())

        config = {"configurable": {"thread_id": "pb7-interrupt-test"}}
        initial_state = {
            "caller_trust_level": ReviewNode.required_trust_level.value,
            "correlation_id": "pb7-interrupt-test",
        }

        result = app.invoke(initial_state, config=config)

        # LangGraph catches GraphInterrupt at the engine boundary and surfaces it
        # as an `__interrupt__` entry — it must NOT have been swallowed by
        # BaseNode.__call__() into a generic status: error result.
        assert "__interrupt__" in result
        assert result.get("status") != "error"

    def test_graph_interrupt_is_not_caught_as_generic_error(self):
        """Directly exercise __call__(): GraphInterrupt must re-raise, not be masked."""
        from langgraph.errors import GraphInterrupt

        from framework.nodes.function_node import FunctionNode
        from framework.schemas.agent_state import AgentState

        class RaisingNode(FunctionNode):
            def execute(self, state: AgentState) -> dict:
                raise GraphInterrupt([{"value": {"draft": "x"}}])

        node = RaisingNode()
        state = {
            "caller_trust_level": RaisingNode.required_trust_level.value,
            "correlation_id": "pb7-direct-call-test",
        }

        with pytest.raises(GraphInterrupt):
            node(state)
