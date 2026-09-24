# Test Specification

## Test Strategy
- Coverage target: 80%
- Test types: Unit / Integration / Proof-of-Boundary

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | Type check pass, no Pydantic/dataclass | Pass — `tests/proof_of_boundary/test_state_safety.py` |
| TC-02 | SecurityViolationError fires on invalid input | Error raised | Pass — `test_contract_ingest_node.py::test_extra_security_gate_input_rejects_oversized_text`, `test_outer_pre_post_process_nodes.py::TestPreProcessNode::test_extra_security_gate_input_rejects_oversized_text`, `test_output_validate_node.py` (3 cases) |
| TC-03 | No JWT/Credential in State | CI `gate-credential-scan`: 0 violations (S-5 enforced in CI) | Pass — no credential-named fields in `src/schemas/state.py`; `test_state_safety.py` |
| TC-04 | InvocationContext via configurable only | Direct access raises error | Pass — all nodes use `InvocationContext.from_state(state)` / `ctx.secrets.require()`; no `os.environ` credential reads (verified by code review) |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start` / `node_complete` / `node_error` absent from `execute()` body | Pass — code review of all 9 node `execute()` bodies confirms only domain events emitted |
| TC-06 | S-2: `_security_gate_input()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | Pass — all `FunctionNode` subclasses import and compile cleanly (enforced by `__init_subclass__`); confirmed by successful test collection |
| TC-07 | S-3: `_security_gate_output()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | Pass — same as TC-06 |
| TC-08 | `required_trust_level` enforced | Insufficient trust → refused | Pass — `test_graph_invoke.py::TestOuterGraphInvoke::test_s1_trust_gate_denies_anonymous_caller`; `tests/proof_of_boundary/test_pb_invoke_order.py` |
| TC-09 | S-2: `_extra_security_gate_input()` non-trivial when domain checks needed | Domain-specific input checks execute correctly (e.g. PII scan on additional fields, consent validation, business rules) | Pass — `ContractIngestNode`/`PreProcessNode` enforce 5000-char S-1 limit; `test_contract_ingest_node.py`, `test_outer_pre_post_process_nodes.py` |
| TC-10 | S-3: `_extra_security_gate_output()` non-trivial when domain checks needed | Domain-specific output checks execute correctly (e.g. nested credential scan, PII re-check, content filtering, preservation verification) | Pass — `OutputValidateNode` implements both wage-figure redaction and preservation-variant gap-report check; `test_output_validate_node.py` (4 cases) |
| TC-11 | S-4: at least one domain `emit_trace_event()` inside each `execute()` | Domain event emitted on every invocation path | Pass — all 9 nodes call `emit_trace_event()` at least once (contract_classified, clauses_extracted, statute_retrieved, compliance_checked, gaps_identified, drafts_generated, output_validated, input_validated, output_formatted) |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | Pass — covered by TC-11 + `test_pb_invoke_order.py` (node_start/node_complete events observed) |
| PB-2 | State serialization | Post-invoke State is primitives only | No Pydantic/dataclass | Pass — `tests/proof_of_boundary/test_state_safety.py` |
| PB-3 | Level 2 → External service | Real external service connection | Data retrieved | N/A for this stage — `LaborLawKbService` mock mode used (`USE_MOCK=true`); real vector KB wiring deferred per Task 2 `NotImplementedError` in `_call_external`. Verified in mock mode via `test_labor_law_kb_service.py` |
| PB-4 | Import isolation | No Level 0 imports | AST scan: 0 violations | Pass — `tests/proof_of_boundary/test_import_isolation.py` |
| PB-5 | Checkpoint safety | No JWT/Pydantic in checkpoint | Inspection pass | Pass — same scan as PB-2, `test_state_safety.py` |
| PB-6 | Invoke execution order | `__call__()`: S-1 trust gate → S-4 `node_start` → S-2 `_security_gate_input` → `execute()` → S-3 `_security_gate_output` → S-4 `node_complete` | Order verified | Pass — `tests/proof_of_boundary/test_pb_invoke_order.py` verified for all 9 concrete node classes under `src/nodes/` |

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | ContractIngestNode classifies engagement type | IT engineer / manufacturing / general contract text | Correct `engagement_type` set | Pass — `test_contract_ingest_node.py` (3 cases) |
| BL-02 | ClauseExtractNode segments and topic-tags clauses | Multi-clause contract text | `extracted_clauses` list with correct topics (wage, equal_pay, dispatch_period, safety_health) | Pass — `test_clause_extract_node.py` (4 cases) |
| BL-03 | LaborLawRetrieveNode retrieves statute passages, safe under running event loop | Extracted clauses + engagement type | Non-empty `retrieved_statute_context`; no `asyncio.run()` RuntimeError under a running loop (regression test) | Pass — `test_labor_law_retrieve_node.py` (3 cases) |
| BL-04 | ComplianceCheckNode flags missing mandatory topics | Clauses covering only "wage" | `equal_pay`/`dispatch_period`/`safety_health` verdicts = "missing" | Pass — `test_compliance_check_node.py` (3 cases) |
| BL-05 | GapAnalyzeNode assigns severity by risk topic | Missing "equal_pay" vs ambiguous clause | "equal_pay" gap = high severity; ambiguous = low severity | Pass — `test_gap_analyze_node.py` (4 cases) |
| BL-06 | TemplateDraftNode generates dual-path clause drafts | Gap report with equal_pay gap | Both 職務給方式 and 労使協定方式 drafts generated, using placeholder tokens only | Pass — `test_template_draft_node.py` (3 cases) |
| BL-07 | OutputValidateNode S-3 preservation + redaction | Draft with concrete wage figure; compliance_report dropping a gap | `SecurityViolationError` raised in both cases; placeholder-token wage text allowed | Pass — `test_output_validate_node.py` (4 cases) |
| BL-08 | Outer PreProcessNode/PostProcessNode | Whitespace input; wage-like formatted_output key | Input trimmed; wage-like keys stripped from formatted_output without mutation-during-iteration error (regression test) | Pass — `test_outer_pre_post_process_nodes.py` (5 cases) |
| BL-09 | LaborLawKbService mock mode | engagement_type + clause topics | Deterministic fixture passages returned; empty credential_handle raises ValueError | Pass — `test_labor_law_kb_service.py` (3 cases) |
| BL-10 | End-to-end outer graph `.compile()` + `.invoke()` | Sample 派遣契約 text, VERIFIED_EXTERNAL caller | `status: success`, full node_history, non-empty compliance_report + clause_drafts | Pass — `tests/integration/test_graph_invoke.py::TestOuterGraphInvoke` (3 cases) + manual `uvicorn` smoke test via `/invoke` |
| BL-11 | End-to-end inner `ComplianceWorkflowGraph` `.compile()` + `.invoke()` | Sample 派遣契約 text | All 7 inner nodes present in node_history; `validated_input`→`user_input` fallback verified | Pass — `tests/integration/test_graph_invoke.py::TestInnerGraphInvoke` (2 cases) |

## Test Execution Summary
- Execution date: 2026-07-11
- Total tests: 44
- Pass: 44 / Fail: 0 / Skip: 0
- Coverage: 89% (`src/` — `pytest tests/ --cov=src --cov-report=term-missing`); uncovered lines are `src/api/server.py` (exercised manually via live `uvicorn` + `curl` `/health` and `/invoke` calls, not in the automated suite) and two defensive `except`/edge branches noted in coverage output
