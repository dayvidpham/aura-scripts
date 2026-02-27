# Aura Protocol — Architecture

This document covers the system architecture for Aura Protocol v3: the
component topology, module layout, workflow design, activity registration,
child workflow patterns, and the audit trail dependency injection pattern.

For operator setup (running `aurad`, systemd, configuration), see
[aurad.md](aurad.md). For the `aura-msg` CLI and hook integration, see
[aura-msg.md](aura-msg.md).

## Table of Contents

- [System Architecture](#system-architecture)
- [Module Layout](#module-layout)
- [EpochWorkflow](#epochworkflow)
- [Activities](#activities)
- [Child Workflows](#child-workflows)
  - [SliceWorkflow (P9_SLICE)](#sliceworkflow-p9_slice)
  - [ReviewPhaseWorkflow (P10_CODE_REVIEW)](#reviewphaseworkflow-p10_code_review)
- [Audit Trail DI Pattern](#audit-trail-di-pattern)
- [Roadmap](#roadmap)

---

## System Architecture

```
bin/aurad.py
    │
    ├── parse_args()          CLI args + env var fallbacks
    ├── init_audit_trail()    Inject AuditTrail implementation (DI)
    └── run_worker()          Connect to Temporal, register workflows + activities
            │
            ├── EpochWorkflow          (scripts/aura_protocol/workflow.py)
            │       ├── Signals: advance_phase, submit_vote
            │       ├── Queries: current_state, available_transitions
            │       ├── Loop:  wait → drain votes → check constraints → advance → upsert attrs
            │       ├── _run_p9_slices()  → starts N SliceWorkflow children concurrently
            │       └── _run_p10_review() → starts one ReviewPhaseWorkflow child
            │
            ├── SliceWorkflow          (scripts/aura_protocol/workflow.py)
            │       └── run(SliceInput) → SliceResult
            │           Child of EpochWorkflow for P9_SLICE; runs concurrently with
            │           other slices; fail-fast via workflow.wait(FIRST_EXCEPTION).
            │
            ├── ReviewPhaseWorkflow    (scripts/aura_protocol/workflow.py)
            │       ├── Signal: submit_vote(ReviewVoteSignal)
            │       └── run(ReviewInput) → ReviewPhaseResult
            │           Child of EpochWorkflow for P10_CODE_REVIEW; blocks until
            │           all 3 ReviewAxis members (A, B, C) have cast votes.
            │
            └── Activities (module-level @activity.defn functions)
                    ├── check_constraints     (workflow.py)   — constraint checking
                    ├── record_transition     (workflow.py)   — transition audit stub
                    ├── record_audit_event    (audit_activities.py) — persist AuditEvent
                    └── query_audit_events    (audit_activities.py) — query AuditEvents (epoch + phase + role)
```

**Communication model:**

```
Model harness hook → aura-msg <command> → Temporal Client SDK → aurad (EpochWorkflow)
```

The key design invariant is the **Temporal determinism boundary**: all I/O,
external state reads, and non-deterministic operations must happen inside
activities. The workflow itself (`EpochWorkflow.run()`) contains only pure,
deterministic logic so that Temporal can replay it faithfully from event
history.

---

## Module Layout

| File | Responsibility |
|---|---|
| `bin/aurad.py` | Entry point: arg parsing, DI injection, worker startup |
| `scripts/aura_protocol/workflow.py` | `EpochWorkflow` definition + `check_constraints` / `record_transition` activities |
| `scripts/aura_protocol/audit_activities.py` | Audit trail singleton + `record_audit_event` / `query_audit_events` activities |
| `scripts/aura_protocol/state_machine.py` | Pure `EpochStateMachine` — no Temporal dependency |
| `scripts/aura_protocol/interfaces.py` | `AuditTrail` Protocol + A2A types + null stubs |
| `scripts/aura_protocol/types.py` | All shared enums and frozen dataclasses |

---

## EpochWorkflow

`EpochWorkflow` is a Temporal `@workflow.defn` class that wraps `EpochStateMachine`
with durable execution. One workflow instance per epoch; it runs from
`PhaseId.P1_REQUEST` to `PhaseId.COMPLETE`.

**Signal-driven loop (`run()`):**

1. Initialize `EpochStateMachine` and upsert initial search attributes.
2. Wait for a pending signal (`advance_phase` or `submit_vote`).
3. Drain all pending `submit_vote` signals into the state machine.
4. If an `advance_phase` signal is pending:
   - Call `check_constraints` activity with current state and target phase.
   - Call `EpochStateMachine.advance()` (pure, deterministic).
   - Call `record_transition` activity (I/O boundary).
   - Upsert search attributes to reflect the new phase.
5. Repeat until `current_phase == COMPLETE`.
6. Return `EpochResult` with counts and final phase.

**Failed transitions** are recorded in `EpochState.transition_history` with
`success=False` and `condition_met="FAILED: {error}"`. The `last_error` field
on the state captures the error string for diagnostic queries.

**Search attributes** (registered in the Temporal namespace) are kept in sync
on every transition:

| Attribute key | Type | Value |
|---|---|---|
| `AuraEpochId` | text | epoch identifier (immutable, set once) |
| `AuraPhase` | keyword | current `PhaseId` value (e.g. `"p9"`) |
| `AuraRole` | keyword | current `RoleId` value |
| `AuraStatus` | keyword | `"running"` or `"complete"` |
| `AuraDomain` | keyword | domain tag (`"user"`, `"plan"`, `"impl"`, or `""`) |

**Signals:**

| Signal | Payload type | Description |
|---|---|---|
| `advance_phase` | `PhaseAdvanceSignal` | Request a phase transition |
| `submit_vote` | `ReviewVoteSignal` | Record a reviewer vote (ACCEPT or REVISE) |
| `slice_progress` | `SliceProgressSignal` | Receive per-leaf-task progress from a child `SliceWorkflow` |

**Queries:**

| Query | Return type | Description |
|---|---|---|
| `current_state` | `EpochState` | Snapshot of epoch runtime state |
| `available_transitions` | `list[Transition]` | Valid next transitions from current phase |
| `slice_progress_state` | `list[SliceProgressSignal]` | Ordered log of all slice progress events received so far |

**Key signal payload types** (`workflow.py`, all `frozen=True` dataclasses):

```python
@dataclass(frozen=True)
class PhaseAdvanceSignal:
    to_phase: PhaseId          # target phase
    triggered_by: str          # who or what triggered this
    condition_met: str         # condition string from the transition table

@dataclass(frozen=True)
class ReviewVoteSignal:
    axis: ReviewAxis           # CORRECTNESS, TEST_QUALITY, or ELEGANCE
    vote: VoteType             # ACCEPT or REVISE
    reviewer_id: str           # unique reviewer identifier

@dataclass(frozen=True)
class SliceProgressSignal:
    slice_id: str              # which slice emitted this event (e.g. "slice-1")
    leaf_task_id: str          # specific leaf task that completed
    stage_name: str            # human-readable stage name (e.g. "execute")
    completed: bool            # True = leaf task finished; False = in-progress
```

**Design rules (must not be violated):**

- No `datetime.now()` in workflow code — use `workflow.now()` for timestamps.
- No I/O in workflow code — all I/O goes through activities.
- Signal handlers only enqueue; transitions happen in the `run()` loop.

---

## Activities

Activities handle non-deterministic operations so the workflow remains
deterministic and safely replayable. All four activities are **module-level
functions** decorated with `@activity.defn`. This is required: Temporal's
`workflow.execute_activity()` takes a function reference, not a method reference.

**Activities registered by aurad:**

| Activity | Module | Description |
|---|---|---|
| `check_constraints` | `workflow.py` | Run `RuntimeConstraintChecker` against current state and proposed target phase. Returns `list[ConstraintViolation]`. |
| `record_transition` | `workflow.py` | v1 stub: logs the transition. Extension point for v2 durable storage (Beads task comment, database). |
| `record_audit_event` | `audit_activities.py` | Persist an `AuditEvent` via the injected `AuditTrail` implementation. |
| `query_audit_events` | `audit_activities.py` | Query `AuditEvent` records by `epoch_id` with optional `phase` and `role` filters. The `role` filter scopes results to a specific agent role (e.g. `RoleId.SUPERVISOR`, `RoleId.WORKER`); without it, queries that intend to scope by role silently return unfiltered results. |

All four activities are passed by reference in `run_worker()`. All three
workflows (including child workflows) must also be registered so the worker
can execute them when the parent dispatches child workflow tasks:

```python
async with Worker(
    client,
    task_queue=task_queue,
    workflows=[EpochWorkflow, SliceWorkflow, ReviewPhaseWorkflow],
    activities=[
        check_constraints,
        record_transition,
        record_audit_event,
        query_audit_events,
    ],
):
    ...
```

---

## Child Workflows

`EpochWorkflow` spawns two types of child workflows for phases P9 and P10.
Both child workflow classes **must be registered** in `run_worker()` alongside
`EpochWorkflow` (see the Worker registration example above).

### SliceWorkflow (P9_SLICE)

`SliceWorkflow` represents a single implementation slice running concurrently
with other slices in the P9 implementation phase.

- **Parent:** `EpochWorkflow._run_p9_slices()`
- **Input:** `SliceInput(epoch_id, slice_id, phase_spec, parent_workflow_id)`
- **Output:** `SliceResult(slice_id, success, error)`
- **Concurrency:** All slices start together; `workflow.wait(FIRST_EXCEPTION)`
  provides fail-fast semantics — if any slice raises, remaining slices are
  cancelled. `workflow.wait` is the deterministic Temporal replacement for
  `asyncio.wait` and must be used in workflow code.
- **Progress signalling:** Each `SliceWorkflow` sends `slice_progress(SliceProgressSignal)`
  back to the parent `EpochWorkflow` via `get_external_workflow_handle(input.parent_workflow_id)`.
  `parent_workflow_id` is passed explicitly in `SliceInput` (rather than reading
  `workflow.info().parent.workflow_id`) for testability.
- **Status:** R12 stub — `run()` emits a single `SliceProgressSignal` on completion and
  returns `SliceResult(success=True)`. Future implementation will emit one signal per
  leaf task and execute slice agents via activities.

### ReviewPhaseWorkflow (P10_CODE_REVIEW)

`ReviewPhaseWorkflow` coordinates a review phase by collecting votes from
reviewer agents across all three `ReviewAxis` members (A, B, C).

- **Parent:** `EpochWorkflow._run_p10_review()`
- **Input:** `ReviewInput(epoch_id, phase_id)`
- **Output:** `ReviewPhaseResult(phase_id, success, vote_result)`
- **Signal:** `submit_vote(ReviewVoteSignal)` — reviewer agents send votes via this signal
- **Completion:** Blocks via `workflow.wait_condition()` until all 3 axes have
  voted. Returns `ReviewPhaseResult` with `success=True` and the full
  axis-to-vote mapping.

**Note on `ReviewPhaseResult` vs `PhaseResult`:**
`ReviewPhaseResult` (in `workflow.py`) is the return type of `ReviewPhaseWorkflow.run()`.
`PhaseResult` (in `types.py`) is a separate type used for phase child workflow
results in general protocol types. They are distinct — do not conflate them.

---

## Audit Trail DI Pattern

`audit_activities.py` uses a **module-level singleton** to inject the
`AuditTrail` implementation. This pattern allows activities to be plain
module-level functions (required by Temporal) while still accepting a
swappable backend.

```python
# audit_activities.py
_AUDIT_TRAIL: AuditTrail | None = None

def init_audit_trail(trail: AuditTrail) -> None:
    global _AUDIT_TRAIL
    _AUDIT_TRAIL = trail
```

**Injection happens in `main()` before the worker starts:**

```python
# bin/aurad.py — main()
init_audit_trail(InMemoryAuditTrail())
await run_worker(namespace=..., task_queue=..., server_address=...)
```

**If `init_audit_trail()` is never called**, both `record_audit_event` and
`query_audit_events` raise `ApplicationError(non_retryable=True)`. This is
intentional: retrying won't help because the fault is in worker configuration,
not transient I/O.

**`AuditTrail` is a `@runtime_checkable` Protocol** (`interfaces.py`):

```python
class AuditTrail(Protocol):
    async def record_event(self, event: AuditEvent) -> None: ...
    async def query_events(
        self, *, epoch_id: str | None, phase: PhaseId | None, role: RoleId | None
    ) -> list[AuditEvent]: ...
```

Implementations satisfy this via structural subtyping (no inheritance required).

**`InMemoryAuditTrail`** is the development / test implementation. It stores
events in a `list[AuditEvent]` in process memory. Events are not persisted
across worker restarts.

For production deployments, inject an implementation backed by Temporal event
history or a durable store in place of `InMemoryAuditTrail()`.

---

## Roadmap

### SliceWorkflow — Full slice agent execution

**Current state (R12 stub):** `SliceWorkflow.run()` returns
`SliceResult(success=True)` immediately without executing anything. The full
slice agent topology is defined (child workflows, fail-fast semantics,
`SliceInput` fields) but the activity bodies are stubs.

**Design intent:** Each `SliceWorkflow` instance will coordinate a single
implementation slice by dispatching to one or more worker agents. Activities
will be responsible for spawning the agent, monitoring its output, and
collecting the slice result. `phase_spec: str` in `SliceInput` is a
placeholder for a future `SerializablePhaseSpec` type that encodes the full
slice specification in a Temporal-serializable form.

**Required before implementation:**
- `SerializablePhaseSpec` design (unified schema integration)
- Agent execution activity (how aurad launches or signals a worker agent)
- Slice progress signals from child to parent (already scaffolded in
  `EpochWorkflow` via signal infrastructure)

### record_transition — Durable transition storage

**Current state (v1 stub):** `record_transition` logs the transition event to
the Python logger. The transition record is already stored in
`EpochState.transition_history` (in-memory, within the workflow's durable
event history), so no external persistence is done.

**Design intent (v2):** Store each transition as a Beads task comment or in a
dedicated SQLite/Temporal-backed store so transitions survive outside the
Temporal event history. This enables reporting and audit queries that don't
require replaying the full workflow history.

### NullTranscriptRecorder — Unified schema integration

**Current state (R12 stub):** `NullTranscriptRecorder` is a no-op that
ignores all `record_turn()` calls. Defined in `interfaces.py`.

**Design intent:** When the unified-schema project provides a
`TranscriptRecorder` implementation, swap `NullTranscriptRecorder` for it in
the DI wiring. The `TranscriptRecorder` Protocol is already defined in
`interfaces.py` so callers do not need to change.

### NullSecurityGate — agentfilter integration

**Current state (R12 stub):** `NullSecurityGate` always returns
`PermissionDecision(allowed=True)`. Defined in `interfaces.py`.

**Design intent:** When agentfilter is available, inject a real
`SecurityGate` implementation that checks tool-use permissions against
agentfilter's policy engine. The `SecurityGate` Protocol is already defined
in `interfaces.py`.
