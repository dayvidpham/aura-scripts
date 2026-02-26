# Aura Protocol Worker

`bin/worker.py` is the Temporal worker entry point for the Aura Protocol v3
epoch lifecycle. It connects to a Temporal server, registers `EpochWorkflow`
and all associated activities, then blocks until interrupted.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Developer Guide](#developer-guide)
  - [Module Layout](#module-layout)
  - [EpochWorkflow](#epochworkflow)
  - [Activities](#activities)
  - [Audit Trail DI Pattern](#audit-trail-di-pattern)
  - [Adding a New Activity](#adding-a-new-activity)
  - [Testing](#testing)
- [Operator Guide](#operator-guide)
  - [CLI Reference](#cli-reference)
  - [Environment Variables](#environment-variables)
  - [Running Locally](#running-locally)
  - [systemd User Service (NixOS / home-manager)](#systemd-user-service-nixos--home-manager)

---

## Architecture Overview

```
bin/worker.py
    │
    ├── parse_args()          CLI args + env var fallbacks
    ├── init_audit_trail()    Inject AuditTrail implementation (DI)
    └── run_worker()          Connect to Temporal, register workflow + activities
            │
            ├── EpochWorkflow          (scripts/aura_protocol/workflow.py)
            │       ├── Signals: advance_phase, submit_vote
            │       ├── Queries: current_state, available_transitions
            │       └── Loop:  wait → drain votes → check constraints → advance → upsert attrs
            │
            └── Activities (module-level @activity.defn functions)
                    ├── check_constraints     (workflow.py)   — constraint checking
                    ├── record_transition     (workflow.py)   — transition audit stub
                    ├── record_audit_event    (audit_activities.py) — persist AuditEvent
                    └── query_audit_events    (audit_activities.py) — query AuditEvents
```

The key design invariant is the **Temporal determinism boundary**: all I/O,
external state reads, and non-deterministic operations must happen inside
activities. The workflow itself (`EpochWorkflow.run()`) contains only pure,
deterministic logic so that Temporal can replay it faithfully from event
history.

---

## Developer Guide

### Module Layout

| File | Responsibility |
|---|---|
| `bin/worker.py` | Entry point: arg parsing, DI injection, worker startup |
| `scripts/aura_protocol/workflow.py` | `EpochWorkflow` definition + `check_constraints` / `record_transition` activities |
| `scripts/aura_protocol/audit_activities.py` | Audit trail singleton + `record_audit_event` / `query_audit_events` activities |
| `scripts/aura_protocol/state_machine.py` | Pure `EpochStateMachine` — no Temporal dependency |
| `scripts/aura_protocol/interfaces.py` | `AuditTrail` Protocol + null stubs |
| `scripts/aura_protocol/types.py` | All shared enums and frozen dataclasses |

### EpochWorkflow

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

**Queries:**

| Query | Return type | Description |
|---|---|---|
| `current_state` | `EpochState` | Snapshot of epoch runtime state |
| `available_transitions` | `list[Transition]` | Valid next transitions from current phase |

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
```

**Design rules (must not be violated):**

- No `datetime.now()` in workflow code — use `workflow.now()` for timestamps.
- No I/O in workflow code — all I/O goes through activities.
- Signal handlers only enqueue; transitions happen in the `run()` loop.

### Activities

Activities handle non-deterministic operations so the workflow remains
deterministic and safely replayable. All four activities are **module-level
functions** decorated with `@activity.defn`. This is required: Temporal's
`workflow.execute_activity()` takes a function reference, not a method reference.

**Activities registered by the worker:**

| Activity | Module | Description |
|---|---|---|
| `check_constraints` | `workflow.py` | Run `RuntimeConstraintChecker` against current state and proposed target phase. Returns `list[ConstraintViolation]`. |
| `record_transition` | `workflow.py` | v1 stub: logs the transition. Extension point for v2 durable storage (Beads task comment, database). |
| `record_audit_event` | `audit_activities.py` | Persist an `AuditEvent` via the injected `AuditTrail` implementation. |
| `query_audit_events` | `audit_activities.py` | Query `AuditEvent` records by `epoch_id` with optional `phase` filter. |

All four activities are passed by reference in `run_worker()`:

```python
async with Worker(
    client,
    task_queue=task_queue,
    workflows=[EpochWorkflow],
    activities=[
        check_constraints,
        record_transition,
        record_audit_event,
        query_audit_events,
    ],
):
    ...
```

### Audit Trail DI Pattern

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
# bin/worker.py — main()
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

### Adding a New Activity

Follow these steps to add a new activity to the worker:

**Step 1: Define the function with `@activity.defn`.**

Add it in the appropriate module. If the activity relates to the audit trail,
put it in `audit_activities.py`. If it relates to the epoch state machine or
protocol constraints, put it in `workflow.py`. For new concerns, create a new
module under `scripts/aura_protocol/`.

```python
# scripts/aura_protocol/my_module.py
from temporalio import activity

@activity.defn
async def my_new_activity(arg1: str, arg2: int) -> str:
    # Non-deterministic work here (I/O, external calls, etc.)
    return f"result: {arg1} {arg2}"
```

**Step 2: Import and add to the `activities=` list in `run_worker()`.**

```python
# bin/worker.py
from aura_protocol.my_module import my_new_activity

async with Worker(
    client,
    task_queue=task_queue,
    workflows=[EpochWorkflow],
    activities=[
        check_constraints,
        record_transition,
        record_audit_event,
        query_audit_events,
        my_new_activity,          # <- add here
    ],
):
    ...
```

**Step 3: Call from `EpochWorkflow` using `workflow.execute_activity()`.**

```python
# Inside EpochWorkflow.run() or a signal handler
result = await workflow.execute_activity(
    my_new_activity,
    args=["hello", 42],
    start_to_close_timeout=timedelta(seconds=10),
)
```

**Step 4: Test with `ActivityEnvironment` (no running Temporal needed).**

```python
from temporalio.testing import ActivityEnvironment
from aura_protocol.my_module import my_new_activity

async def test_my_new_activity():
    env = ActivityEnvironment()
    result = await env.run(my_new_activity, "hello", 42)
    assert result == "result: hello 42"
```

### Testing

**Unit testing activities** — use `temporalio.testing.ActivityEnvironment`.
No running Temporal server is required. The environment simulates the Temporal
activity context (heartbeat, info, etc.):

```python
from temporalio.testing import ActivityEnvironment
from aura_protocol.audit_activities import record_audit_event, init_audit_trail, InMemoryAuditTrail

async def test_record_event():
    trail = InMemoryAuditTrail()
    init_audit_trail(trail)
    event = AuditEvent(epoch_id="e1", ...)

    env = ActivityEnvironment()
    await env.run(record_audit_event, event)

    stored = await trail.query_events(epoch_id="e1")
    assert event in stored
```

**Unit testing the worker entry point** — `parse_args()` accepts an explicit
`argv` list, so tests never need to patch `sys.argv`:

```python
# Pass argv directly — no sys.argv patching
args = module.parse_args(["--namespace", "prod", "--task-queue", "my-queue"])
assert args.namespace == "prod"
```

Env var isolation uses plain dict operations on `os.environ` (save/restore);
no mocking framework is required. See `tests/test_worker.py` for the
`_clean_env()` context manager pattern.

**Integration testing workflows** — use `temporalio.testing.WorkflowEnvironment`
to start an in-process Temporal test server:

```python
from temporalio.testing import WorkflowEnvironment

async def test_epoch_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue="test", workflows=[EpochWorkflow],
                          activities=[...]):
            handle = await env.client.start_workflow(
                EpochWorkflow.run,
                EpochInput(epoch_id="test-epoch", request_description="..."),
                id="test-epoch",
                task_queue="test",
            )
            # Send signals, query state, await result
```

Existing tests live in:

| Test file | What it covers |
|---|---|
| `tests/test_worker.py` | `parse_args()` defaults, CLI overrides, env var fallbacks, `--help` output |
| `tests/test_audit_activities.py` | `InMemoryAuditTrail`, `init_audit_trail()`, `record_audit_event`, `query_audit_events`, `ApplicationError` on uninitialized state |
| `tests/test_workflow.py` | `EpochWorkflow` signal/query/run behavior |

Run the test suite (from the repo root, with the Python venv activated):

```bash
PYTHONPATH=scripts .venv/bin/pytest tests/ --tb=short -q \
  --ignore=tests/test_gen_schema.py \
  --ignore=tests/test_gen_skills.py
```

---

## Operator Guide

### CLI Reference

```
bin/worker.py [--namespace NS] [--task-queue QUEUE] [--server-address ADDR]
```

| Flag | Metavar | Default | Description |
|---|---|---|---|
| `--namespace` | `NS` | `"default"` | Temporal namespace to connect to |
| `--task-queue` | `QUEUE` | `"aura"` | Task queue name the worker listens on |
| `--server-address` | `ADDR` | `"localhost:7233"` | Temporal server host:port |

**Priority (highest to lowest):**

1. Explicit CLI flag (e.g. `--namespace my-ns`)
2. Environment variable (e.g. `TEMPORAL_NAMESPACE=my-ns`)
3. Built-in default (`"default"`, `"aura"`, `"localhost:7233"`)

### Environment Variables

| Variable | CLI equivalent | Default |
|---|---|---|
| `TEMPORAL_NAMESPACE` | `--namespace` | `default` |
| `TEMPORAL_TASK_QUEUE` | `--task-queue` | `aura` |
| `TEMPORAL_ADDRESS` | `--server-address` | `localhost:7233` |

### Running Locally

**Prerequisites:**

1. A running Temporal dev server (see systemd service below, or run manually).
2. Python venv activated with `temporalio` and `aura_protocol` dependencies.

**Start the Temporal dev server manually:**

```bash
temporal server start-dev --port 7233 --ui-port 8233
```

**Run the worker with defaults (namespace `default`, queue `aura`):**

```bash
PYTHONPATH=scripts python bin/worker.py
```

**Run with explicit arguments:**

```bash
PYTHONPATH=scripts python bin/worker.py \
  --namespace dev \
  --task-queue aura \
  --server-address localhost:7233
```

**Run via environment variables:**

```bash
TEMPORAL_NAMESPACE=prod \
TEMPORAL_TASK_QUEUE=aura-prod \
TEMPORAL_ADDRESS=temporal.example.com:7233 \
PYTHONPATH=scripts python bin/worker.py
```

**Show help:**

```bash
PYTHONPATH=scripts python bin/worker.py --help
```

The worker runs until it receives `SIGINT` (Ctrl-C) or `SIGTERM`. The
`asyncio.Event().wait()` at the end of `run_worker()` blocks indefinitely;
Temporal's `Worker` context manager handles graceful shutdown on signal receipt.

**Startup log output** (INFO level):

```
2026-02-26 12:00:00,000 INFO __main__ Audit trail initialized (InMemoryAuditTrail).
2026-02-26 12:00:00,001 INFO __main__ Worker running: namespace='default' task_queue='aura' server='localhost:7233'
```

### systemd User Service (NixOS / home-manager)

`nix/temporal-service.nix` provides a home-manager module that runs
`temporal server start-dev` as a systemd user service. This keeps a Temporal
dev server available without manual intervention.

**The module is exported from `flake.nix`:**

```nix
# flake.nix outputs
homeManagerModules = {
  temporal-service = import ./nix/temporal-service.nix;
};
```

**Enable the service in `home.nix`:**

```nix
imports = [ inputs.aura-plugins.homeManagerModules.temporal-service ];

services.temporal-dev-server = {
  enable    = true;
  port      = 7233;    # gRPC frontend (default)
  uiPort    = 8233;    # Web UI (default)
};
```

**Full option reference:**

| Option | Type | Default | Description |
|---|---|---|---|
| `enable` | bool | `false` | Enable the systemd user service |
| `port` | port | `7233` | gRPC frontend port |
| `uiPort` | port | `8233` | HTTP Web UI port |
| `namespace` | string | `"default"` | Namespace to create and serve. Must match `TEMPORAL_NAMESPACE` used by the worker. |
| `dbPath` | string | `""` | Path to SQLite file for persistence. Empty = in-memory (data lost on restart). |
| `package` | package | `pkgs.temporal-cli` | The temporal CLI package. Override to pin a specific version. |

**Example: persistent storage with a custom namespace:**

```nix
services.temporal-dev-server = {
  enable    = true;
  namespace = "aura";
  dbPath    = "/home/user/.local/share/temporal/temporal.db";
};
```

When `dbPath` is set, the service passes `--db-filename` to
`temporal server start-dev`, so workflow history survives restarts.

**Accessing the Web UI:**

With default ports, the Temporal Web UI is available at
`http://localhost:8233` after the service starts.

**Service management:**

```bash
# Check status
systemctl --user status temporal-dev-server

# View logs
journalctl --user -u temporal-dev-server -f

# Restart
systemctl --user restart temporal-dev-server
```

**Namespace alignment:** The `namespace` option on the service and the
`--namespace` flag (or `TEMPORAL_NAMESPACE` env var) on the worker must match.
Mismatches cause the worker to connect to a namespace the dev server is not
serving, resulting in connection or registration errors.
