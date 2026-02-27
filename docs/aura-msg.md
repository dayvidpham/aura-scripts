# aura-msg — CLI Reference

`aura-msg` (`bin/aura-msg.py`) is the programmatic CLI for interacting with
Aura Protocol v3 workflows. It is the intended interface for model harness
hooks to send signals, query state, and advance phase transitions without
needing to speak the Temporal Client SDK directly.

**Current state:** `aura-msg` is a stub that accepts `--help` only. No
subcommands are implemented. See [Roadmap](#roadmap) for the planned command
surface.

For the `aurad` daemon that processes these commands, see [aurad.md](aurad.md).
For system architecture and the communication model, see
[architecture.md](architecture.md).

## Table of Contents

- [Communication Model](#communication-model)
- [Current State](#current-state)
- [Planned Subcommands](#planned-subcommands)
- [Hook Integration Vision](#hook-integration-vision)
- [Roadmap](#roadmap)

---

## Communication Model

```
Model harness hook → aura-msg <command> → Temporal Client SDK → aurad (EpochWorkflow)
```

`aura-msg` acts as a thin CLI wrapper over the Temporal Client SDK. Each
subcommand translates a user-visible operation into a Temporal signal, query,
or workflow start call. `aurad` handles all workflow execution on the other side.

This separation means:

- Model harness hooks do not need to embed Temporal client code.
- `aura-msg` can be called from shell scripts, Claude Code hooks, or any
  process that can exec a subprocess.
- `aurad` (the daemon) remains the single owner of all workflow state.

---

## Current State

`aura-msg` currently provides `--help` only:

```bash
$ aura-msg --help
usage: aura-msg [-h] {start-epoch,signal-vote,query-state,advance-phase} ...

aura-msg — Aura Protocol v3 CLI.

Programmatic interface for model harness hooks to interact with EpochWorkflow
running inside aurad.

Planned subcommands (not yet implemented):
  start-epoch      Start a new epoch workflow
  signal-vote      Submit a reviewer vote to ReviewPhaseWorkflow
  query-state      Query the current state of a running epoch
  advance-phase    Request a phase transition via PhaseAdvanceSignal

positional arguments:
  {start-epoch,signal-vote,query-state,advance-phase}

options:
  -h, --help  show this help message and exit
```

The stub is packaged as `packages.aura-msg` in `flake.nix` and included in
`packages.default` (the `symlinkJoin` that puts `aura-msg` in PATH).

---

## Planned Subcommands

These subcommands are designed but not yet implemented. The `--help` output
above lists them to signal intent and allow tooling to check for availability.

### `start-epoch`

Start a new `EpochWorkflow` in `aurad`.

```
aura-msg start-epoch --epoch-id ID --description TEXT [--namespace NS] [--task-queue QUEUE]
```

| Flag | Description |
|---|---|
| `--epoch-id` | Unique epoch identifier (used as Temporal workflow ID) |
| `--description` | Human-readable epoch description |
| `--namespace` | Temporal namespace (default: `TEMPORAL_NAMESPACE` env or `default`) |
| `--task-queue` | Task queue (default: `TEMPORAL_TASK_QUEUE` env or `aura`) |

Translates to: `client.start_workflow(EpochWorkflow.run, EpochInput(...))`.

### `signal-vote`

Submit a reviewer vote to a running `ReviewPhaseWorkflow`.

```
aura-msg signal-vote --epoch-id ID --axis AXIS --vote VOTE --reviewer-id RID
```

| Flag | Description |
|---|---|
| `--epoch-id` | Epoch workflow ID to target |
| `--axis` | Review axis: `A` (correctness), `B` (test_quality), or `C` (elegance) |
| `--vote` | Vote: `accept` or `revise` |
| `--reviewer-id` | Unique reviewer identifier |

Translates to: `handle.signal(EpochWorkflow.submit_vote, ReviewVoteSignal(...))`.

### `query-state`

Query the current state of a running epoch.

```
aura-msg query-state --epoch-id ID [--format json|text]
```

| Flag | Description |
|---|---|
| `--epoch-id` | Epoch workflow ID to query |
| `--format` | Output format: `json` (default) or `text` |

Translates to: `handle.query(EpochWorkflow.current_state)`.

Outputs `EpochState` fields including current phase, transition history, last
error, and available transitions.

### `advance-phase`

Request a phase transition via `PhaseAdvanceSignal`.

```
aura-msg advance-phase --epoch-id ID --to-phase PHASE --triggered-by WHO --condition TEXT
```

| Flag | Description |
|---|---|
| `--epoch-id` | Epoch workflow ID to signal |
| `--to-phase` | Target phase identifier (e.g. `p10`) |
| `--triggered-by` | Who or what is requesting the transition |
| `--condition` | Condition string from the transition table |

Translates to: `handle.signal(EpochWorkflow.advance_phase, PhaseAdvanceSignal(...))`.

---

## Hook Integration Vision

Claude Code provides pre-tool-use and post-tool-use hooks that execute shell
commands at defined points in the model harness lifecycle. `aura-msg` is
designed to be the bridge between those hooks and the Aura Protocol workflow.

**Example hook flows (planned):**

```
# Pre-tool-use hook: check permission before tool execution
aura-msg query-state --epoch-id $EPOCH_ID | jq '.current_phase'

# Post-tool-use hook: record a completed slice
aura-msg advance-phase \
  --epoch-id $EPOCH_ID \
  --to-phase p10 \
  --triggered-by "worker-3" \
  --condition "all slices complete"

# Reviewer hook: submit vote after code review
aura-msg signal-vote \
  --epoch-id $EPOCH_ID \
  --axis C \
  --vote accept \
  --reviewer-id "reviewer-c"
```

This model means each hook is a single shell command. The hook author does not
need to understand Temporal SDK internals; they compose `aura-msg` calls the
same way they compose any other CLI tool.

---

## Roadmap

### Implement planned subcommands

**Current state (R12 stub):** All four planned subcommands (`start-epoch`,
`signal-vote`, `query-state`, `advance-phase`) are listed in `--help` but
raise `NotImplementedError` or exit with an error when invoked.

**Design intent:** Each subcommand should:

1. Accept the flags listed above.
2. Read connection settings from env vars (`TEMPORAL_NAMESPACE`,
   `TEMPORAL_TASK_QUEUE`, `TEMPORAL_ADDRESS`) with CLI overrides.
3. Construct the appropriate Temporal Client call.
4. Output structured JSON on success (exit 0) or a human-readable error on
   failure (exit non-zero).

Implementation order follows hook integration priority: `query-state` first
(read-only, lowest risk), then `signal-vote` (needed for reviewer hooks), then
`advance-phase`, then `start-epoch`.

### Connection configuration

**Design intent:** Add a shared `--config` flag (or `AURA_CONFIG` env var)
pointing to a TOML file with connection defaults. This avoids repeating
`--namespace` / `--task-queue` / `--server-address` on every call in hook
scripts.

```toml
# ~/.config/aura/config.toml
[temporal]
namespace     = "aura"
task_queue    = "aura"
server_address = "localhost:7233"
```

### Structured output and exit codes

**Design intent:** All subcommands should emit machine-readable JSON to stdout
on success and a structured error object to stderr on failure. Exit codes
should follow Unix conventions:

| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error (bad arguments, workflow not found) |
| 2 | Connection error (Temporal server unreachable) |
| 3 | Workflow error (signal rejected, constraint violation) |

This allows hook scripts to branch on `$?` without parsing stderr.

### aura-msg as the primary model harness interface

**Long-term design intent:** As more protocol phases are automated,
`aura-msg` becomes the single programmatic entry point for all model harness
interactions with the Aura Protocol:

- Agents register their role with `aura-msg register --role worker-3`.
- Agents report leaf task completion with `aura-msg complete-task --task-id ...`.
- Agents query active constraints with `aura-msg list-constraints --phase p9`.
- The harness advances phases and collects votes entirely through `aura-msg`
  subcommands, with `aurad` as the authoritative state machine behind it.
