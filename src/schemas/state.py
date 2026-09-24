"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict (see ADR-005 for the prohibited
# alternatives). LangGraph checkpoints use msgpack serialization, so only
# plain serializable fields are allowed. Do NOT add credentials or secrets.

from typing import Any

from framework.schemas.agent_state import AgentState


class State(AgentState):
    """Agent state.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, etc.) are inherited from AgentState.
    """

    engagement_type: str
    parsed_contract_text: str
    extracted_clauses: list[dict[str, Any]]
    retrieved_statute_context: list[dict[str, Any]]
    compliance_verdicts: list[dict[str, Any]]
    gap_report: list[dict[str, Any]]
    clause_drafts: list[dict[str, Any]]
    compliance_report: dict[str, Any]
