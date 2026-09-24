# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: `SvcC2047StaffingContractComplianceAgent`
- **L1 Base**: AgentBaseGraph (outer graph, Cat 2 — GraphNode wraps an inner `BaseGraph` domain workflow)
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

Cat 2 two-layer composition, per `docs/01_proposal.md` §Cat Self-Assessment:

- **Outer graph** (`src/graph/graph.py`) — inherits `AgentBaseGraph`. Fixed 5-node
  backbone (`initialize → pre_process → main → post_process → finalize`). The `main`
  slot holds `ComplianceWorkflowGraphNode`, which wraps the inner domain graph.
- **Inner graph** (`src/graph/domain_workflow_graph.py`) — inherits `BaseGraph`
  (fully custom topology, 7 nodes, linear pipeline). Implements the actual
  contract-compliance business logic.

### Node Configuration — Outer Graph

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | Set schema_version, session_id, trust_level | — | `session_id`, `trust_level` | InitializeNode (default) |
| pre_process | Validate/sanitize raw contract text input, enforce S-1 5000-char limit | `user_input` | `validated_input` | PreProcessNode |
| main | Run the 7-step compliance pipeline via inner graph | `validated_input` | `compliance_report`, `clause_drafts`, `result` | `ComplianceWorkflowGraphNode` (GraphNode) |
| post_process | Format final response payload, emit audit summary | `compliance_report`, `clause_drafts` | `result` (formatted) | PostProcessNode |
| finalize | Build response_metadata, total_time_ms | — | `response_metadata` | FinalizeNode (default) |

### Node Configuration — Inner Graph (`ComplianceWorkflow`)

| Node | Responsibility | Input State | Output State |
|------|---------------|-------------|---------------|
| contract_ingest | Parse contract text, classify engagement type (IT engineer 派遣, manufacturing 派遣, etc.) | `validated_input` (fallback: `user_input`) | `engagement_type`, `parsed_contract_text` |
| clause_extract | Segment contract text into discrete clause units mappable to 第26条 sub-items | `parsed_contract_text` | `extracted_clauses` (list[dict]) |
| labor_law_retrieve | Vector KB retrieval of 労働者派遣法 第26条 mandatory items, 厚労省 ガイド, 同一労働同一賃金 model clauses, scoped by `engagement_type` | `extracted_clauses`, `engagement_type` | `retrieved_statute_context` (list[dict]) |
| compliance_check | LLM-driven clause-by-clause comparison against retrieved statute text | `extracted_clauses`, `retrieved_statute_context` | `compliance_verdicts` (list[dict]) |
| gap_analyze | Classify gaps (missing / non-compliant / ambiguous), assign severity by audit/risk exposure | `compliance_verdicts` | `gap_report` (list[dict]) |
| template_draft | Dual-path generation (職務給方式 / 労使協定方式) of compliant clause text using placeholder tokens | `gap_report` | `clause_drafts` (list[dict]) |
| output_validate | Regex + LLM scan to strip/reject worker PII, client names, wage figures (S-3 preservation-variant gate) | `clause_drafts`, `gap_report` | `compliance_report`, `clause_drafts` (validated) |

### Data Flow

```
Outer:  START → initialize → pre_process → main → {route} → post_process → finalize → END
                                              ↓ (retry, max 3)
                                            pre_process

Inner (inside `main` via ComplianceWorkflowGraphNode):
  START → contract_ingest → clause_extract → labor_law_retrieve → compliance_check
        → gap_analyze → template_draft → output_validate → END
```

Linear topology — no branching required; every clause flows through the same 7 steps.
`route()` is implemented per BaseGraph ABC contract but is never invoked (no
conditional edges).

### State Definition

State extends `AgentState` (outer) and is shared by the inner graph via `State`
(same class — the inner graph's `state_schema` returns the same `State`, so both
graphs read/write compatible keys; inner graph's `contract_ingest` node falls back
`validated_input` → `user_input` per the GraphNode fresh-state contract).

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `engagement_type` | `str` | Classified dispatch engagement (e.g. "it_engineer", "manufacturing") | No (defaults to "general") |
| `parsed_contract_text` | `str` | Normalized contract text after ingest | No |
| `extracted_clauses` | `list[dict]` | Segmented clause units: `{clause_id, text, topic}` | No |
| `retrieved_statute_context` | `list[dict]` | Retrieved statute passages: `{source, article, text, score}` | No |
| `compliance_verdicts` | `list[dict]` | Per-clause verdicts: `{clause_id, verdict, citation}` | No |
| `gap_report` | `list[dict]` | Gap findings: `{clause_id, gap_type, severity, explanation}` | No |
| `clause_drafts` | `list[dict]` | Generated compliant clause drafts: `{clause_id, draft_text, path}` | No |
| `compliance_report` | `dict` | Final formatted compliance summary returned to caller | No |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle) — used by `labor_law_retrieve` (vector KB connection) and `compliance_check`/`template_draft` (LLM calls) via `config["configurable"]["invocation_context"].credential_handle`
- [x] ConnectionPolicy (retry/timeout strategy) — applied to the vector KB client in `LaborLawKbService`
- [x] SecurityViolationError — raised by `pre_process` on S-1 input-limit violation (>5000 chars) or by `_extra_security_gate_input` if PII appears outside expected fields
- [x] S-2: `_extra_security_gate_input()` — domain-specific input check hook
      implemented on `contract_ingest`'s wrapping `FunctionNode`-based pre_process:
      enforces the 5000-char contract-text limit and rejects input containing
      obvious worker/client identifying fields before ingestion proceeds
      (defense-in-depth in addition to the framework's default PII scan)
- [x] S-3: `_extra_security_gate_output()` — domain-specific output check hook
      implemented on `output_validate`'s wrapping node: regex + PII scan across
      `compliance_report` and `clause_drafts` for worker names, client company
      names, and wage figures; **preservation variant** — also rejects output
      that drops a mandatory 第26条 disclosure item present in the gap report
      (would silently under-report a compliance risk)
- [x] S-4: `emit_trace_event()` — at least one domain-specific event inside each `execute()`:
      `contract_ingest` emits `contract_classified` (engagement_type); `clause_extract`
      emits `clauses_extracted` (count); `labor_law_retrieve` emits `statute_retrieved`
      (source count, kb version); `compliance_check` emits `compliance_checked`
      (verdict counts); `gap_analyze` emits `gaps_identified` (severity breakdown);
      `template_draft` emits `drafts_generated` (count, path used); `output_validate`
      emits `output_validated` (redaction count, preservation check result)

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

Outer `pre_process` and `post_process` are `FunctionNode` subclasses (standard S-2/S-3
`@final` gates + `_extra_*` hooks as above). The outer `main` slot is a `GraphNode`
(deliberate S-2/S-3 no-op — the inner graph's own `contract_ingest`/`output_validate`
`FunctionNode`s already apply their gates). Inner graph nodes are all `FunctionNode`
subclasses.

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — `ComplianceWorkflowGraphNode` wraps
  `ComplianceWorkflowGraph` (inner `BaseGraph`)
- **Composition target**: `src/graph/domain_workflow_graph.py` → `ComplianceWorkflowGraph`
- **Error propagation strategy**: `propagate` — any inner-graph failure (e.g. vector KB
  unreachable, LLM error) raises `SubgraphError` to the outer graph, which routes to
  `ERROR` status rather than returning a partially-generated compliance report. A
  partial/silent-failure compliance check is worse than a hard error, given the
  legal/audit stakes described in `docs/01_proposal.md`.

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | **AgentBaseGraph** | Fixed, auditable 7-step compliance pipeline — no self-directed reasoning loop or open-ended termination needed; matches Cat 2 judgment in `docs/01_proposal.md`. |
| Inner graph base | BaseGraph (custom topology) | AgentBaseGraph (5-node pipeline) | **BaseGraph** | 7 domain-specific linear steps do not map onto the pre_process/main/post_process 3-slot shape without forcing an artificial grouping; `BaseGraph` gives full control over node names and a clean 1:1 mapping to the proposal's workflow diagram. |
| Composition pattern | Standalone (all 7 steps as outer nodes) | GraphNode wrapping inner BaseGraph | **GraphNode + inner BaseGraph** | Keeps the outer graph's backbone framework-standard (unmodified `add_edges()`) while isolating all domain complexity in one clearly-scoped inner graph, per CoE Cat 2 guidance. |
| Error propagation | propagate | handle (graceful degradation) | **propagate** | A gap-analysis result that silently omits a failed retrieval or check step creates legal/compliance risk (per proposal §Risks) worse than a hard failure the caller can retry or escalate. |
| Retrieval scope key | Global KB search | `engagement_type`-scoped KB search | **engagement_type-scoped** | `contract_ingest` classifies engagement type first so `labor_law_retrieve` can narrow retrieval (e.g. IT engineer 派遣 vs manufacturing 派遣 have different disclosure nuances), improving retrieval precision. |
| Draft generation path | Single generic clause template | Dual-path (職務給方式 / 労使協定方式) | **Dual-path** | Proposal explicitly requires both 同一労働同一賃金 wage-determination methods to be supported; a single generic path would miss the 労使協定方式 case entirely. |
