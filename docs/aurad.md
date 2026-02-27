# aurad — Aura Daemon Operator Guide

`aurad` (`bin/aurad.py`) is the Temporal worker daemon for Aura Protocol v3.
It connects to a Temporal server, registers `EpochWorkflow`, `SliceWorkflow`,
`ReviewPhaseWorkflow`, and all associated activities, then blocks until
interrupted.

For system architecture and workflow internals, see [architecture.md](architecture.md).
For the `aura-msg` CLI, see [aura-msg.md](aura-msg.md).

## Table of Contents

- [CLI Reference](#cli-reference)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [systemd User Service (NixOS / home-manager)](#systemd-user-service-nixos--home-manager)
- [Adding a New Activity](#adding-a-new-activity)
- [Testing](#testing)
- [Roadmap](#roadmap)

---

## CLI Reference

When installed via Nix (`packages.aurad`), run the daemon directly:

```
aurad [--namespace NS] [--task-queue QUEUE] [--server-address ADDR]
```

When running from source:

```
PYTHONPATH=scripts python bin/aurad.py [OPTIONS]
```

| Flag | Metavar | Default | Description |
|---|---|---|---|
| `--namespace` | `NS` | `"default"` | Temporal namespace to connect to |
| `--task-queue` | `QUEUE` | `"aura"` | Task queue name the daemon listens on |
| `--server-address` | `ADDR` | `"localhost:7233"` | Temporal server host:port |

**Priority (highest to lowest):**

1. Explicit CLI flag (e.g. `--namespace my-ns`)
2. Environment variable (e.g. `TEMPORAL_NAMESPACE=my-ns`)
3. Built-in default (`"default"`, `"aura"`, `"localhost:7233"`)

---

## Environment Variables

| Variable | CLI equivalent | Default |
|---|---|---|
| `TEMPORAL_NAMESPACE` | `--namespace` | `default` |
| `TEMPORAL_TASK_QUEUE` | `--task-queue` | `aura` |
| `TEMPORAL_ADDRESS` | `--server-address` | `localhost:7233` |

---

## Running Locally

**Prerequisites:**

1. A running Temporal dev server (see systemd service below, or run manually).
2. Python venv activated with `temporalio` and `aura_protocol` dependencies.

**Start the Temporal dev server manually:**

```bash
temporal server start-dev --port 7233 --ui-port 8233
```

**Run the daemon with defaults (namespace `default`, queue `aura`):**

```bash
PYTHONPATH=scripts python bin/aurad.py
```

**Run with explicit arguments:**

```bash
PYTHONPATH=scripts python bin/aurad.py \
  --namespace dev \
  --task-queue aura \
  --server-address localhost:7233
```

**Run via environment variables:**

```bash
TEMPORAL_NAMESPACE=prod \
TEMPORAL_TASK_QUEUE=aura-prod \
TEMPORAL_ADDRESS=temporal.example.com:7233 \
PYTHONPATH=scripts python bin/aurad.py
```

**Show help:**

```bash
PYTHONPATH=scripts python bin/aurad.py --help
```

The daemon runs until it receives `SIGINT` (Ctrl-C) or `SIGTERM`. The
`asyncio.Event().wait()` at the end of `run_worker()` blocks indefinitely;
Temporal's `Worker` context manager handles graceful shutdown on signal receipt.

**Startup log output** (INFO level):

```
2026-02-26 12:00:00,000 INFO __main__ Audit trail initialized (InMemoryAuditTrail).
2026-02-26 12:00:00,001 INFO __main__ Worker running: namespace='default' task_queue='aura' server='localhost:7233'
```

---

## systemd User Service (NixOS / home-manager)

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
| `namespace` | string | `"default"` | Namespace to create and serve. Must match `TEMPORAL_NAMESPACE` used by `aurad`. |
| `dbPath` | string | `""` | Path to SQLite file for persistence. Empty (default) = XDG-resolved path at runtime. |
| `package` | package | `pkgs.temporal-cli` | The temporal CLI package. Override to pin a specific version. |

**Persistent storage (XDG default):**

When `dbPath` is empty (the default), the service resolves the database path
at startup using `ExecStartPre`:

```
${XDG_DATA_HOME:-$HOME/.local/share}/aura/plugin/temporal.db
```

The parent directory is created automatically (`mkdir -p`). This means workflow
history survives service restarts without any manual configuration.

To use a custom path instead:

```nix
services.temporal-dev-server = {
  enable    = true;
  namespace = "aura";
  dbPath    = "/home/user/.local/share/temporal/temporal.db";
};
```

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
`--namespace` flag (or `TEMPORAL_NAMESPACE` env var) on `aurad` must match.
Mismatches cause `aurad` to connect to a namespace the dev server is not
serving, resulting in connection or registration errors.

---

## Adding a New Activity

Follow these steps to add a new activity to `aurad`:

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
# bin/aurad.py
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

---

## Testing

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

**Unit testing the daemon entry point** — `parse_args()` accepts an explicit
`argv` list, so tests never need to patch `sys.argv`:

```python
# Pass argv directly — no sys.argv patching
args = module.parse_args(["--namespace", "prod", "--task-queue", "my-queue"])
assert args.namespace == "prod"
```

Env var isolation uses plain dict operations on `os.environ` (save/restore);
no mocking framework is required. See `tests/test_aurad.py` for the
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
| `tests/test_aurad.py` | `parse_args()` defaults, CLI overrides, env var fallbacks, `--help` output |
| `tests/test_audit_activities.py` | `InMemoryAuditTrail`, `init_audit_trail()`, `record_audit_event`, `query_audit_events`, `ApplicationError` on uninitialized state |
| `tests/test_workflow.py` | `EpochWorkflow` signal/query/run behavior |

Run the test suite (from the repo root, with the Python venv activated):

```bash
PYTHONPATH=scripts .venv/bin/pytest tests/ --tb=short -q \
  --ignore=tests/test_gen_schema.py \
  --ignore=tests/test_gen_skills.py
```

---

## Roadmap

### aurad systemd user service (R2)

**Current state:** `aurad` is packaged as `packages.aurad` in `flake.nix` and
runs manually or via the Nix package. There is no dedicated `systemd` user
service for `aurad` itself yet.

**Design intent:** Add `nix/aurad-service.nix`, a home-manager module
providing a `systemd` user service that:

- Runs `aurad` as a long-running daemon.
- Depends on the Temporal dev server
  (`After = ["network.target" "temporal-dev-server.service"]`).
- Owns `home.packages = [aurad]` (so installing the module brings in the binary).
- Exposes options for `namespace`, `taskQueue`, `serverAddress`, and
  `auditTrailBackend`.

The service is intentionally separate from `temporal-service.nix` (which owns
the Temporal dev server) to allow each to be enabled independently.

### Durable AuditTrail backend

**Current state:** `init_audit_trail(InMemoryAuditTrail())` is hardcoded in
`bin/aurad.py`. Events are lost when `aurad` restarts.

**Design intent:** Add a `--audit-trail` CLI flag (or `AURA_AUDIT_TRAIL` env
var) to select the backend:

- `memory` (default, current behaviour)
- `sqlite:<path>` — SQLite-backed trail persisting to a local file
- `temporal` — store events as Temporal signals/memos (query without separate DB)

The `AuditTrail` Protocol in `interfaces.py` is already the right abstraction;
only the injection wiring in `main()` needs updating.
