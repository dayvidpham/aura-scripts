# Supervisor: Spawn Worker

Launch worker for a vertical slice assignment.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

Implementation tasks ready, spawning workers for parallel execution.

## Given/When/Then/Should

**Given** implementation tasks **when** spawning **then** use Task tool with `run_in_background: true` **should never** block on worker completion

**Given** multiple workers **when** launching **then** spawn all slices in parallel **should never** spawn sequentially

**Given** worker assignment **when** providing context **then** include Beads task ID, full context, and handoff document **should never** omit checklist or criteria

**Given** worker handoff **when** creating **then** store at `.git/.aura/handoff/<request-task-id>/supervisor-to-worker-<N>.md` **should never** skip handoff document

## Handoff Template (Supervisor → Worker)

Before spawning each worker, create a handoff document:

**Storage:** `.git/.aura/handoff/<request-task-id>/supervisor-to-worker-<N>.md`

```markdown
# Handoff: Supervisor → Worker <N>

## Context
- Request: <request-task-id>
- URD: <urd-task-id>
- IMPL_PLAN: <impl-plan-task-id>
- Ratified Proposal: <proposal-task-id>

## Your Slice
- Slice: SLICE-<N>
- Task ID: <slice-task-id>
- Production Code Path: <what end users run>

## Key Files
| File | What You Own |
|------|-------------|
| pkg/feature/types.go | ListOptions, ListEntry types |
| cmd/feature/list_test.go | List command tests |
| pkg/feature/service.go | ListItems() method |
| cmd/feature/list.go | list subcommand wiring |

## Implementation Order
1. Layer 1: Types (your slice only)
2. Layer 2: Tests (import production code — will FAIL, expected)
3. Layer 3: Implementation + Wiring (make tests PASS)

## Validation Checklist
- [ ] Production code verified via code inspection
- [ ] Tests import actual CLI (not test-only export)
- [ ] No dual-export anti-pattern
- [ ] No TODO placeholders
- [ ] Service wired with real dependencies
```

## Task Call

```
Task({
  description: "Worker: implement SLICE-N",
  prompt: `Call Skill(/aura:worker) and implement the assigned slice.

Beads Task ID: <task-id>
Read full requirements: bd show <task-id>
Handoff doc: .git/.aura/handoff/<request-task-id>/supervisor-to-worker-<N>.md`,
  subagent_type: "general-purpose",
  run_in_background: true
})
```

**Important:** Use `subagent_type: "general-purpose"`, not a custom agent type. The worker skill is invoked inside the agent via `Skill(/aura:worker)`.

## Worker Should Update Beads Status

- On start: `bd update <task-id> --status=in_progress`
- On complete: `bd close <task-id>`
- On blocked: `bd update <task-id> --notes="Blocked: <reason>"`

## Assign via Beads

```bash
bd update <task-id> --assignee="<worker-agent-name>"
bd update <task-id> --status=in_progress
```

## Follow-up Slice Handoff (FOLLOWUP_SLICE-N)

For follow-up slices, the handoff template extends with additional fields:

**Storage:** `.git/.aura/handoff/{followup-epic-id}/supervisor-to-worker-<N>.md`

```markdown
# Handoff: Supervisor → Worker <N> (Follow-up)

## Context
- Original Request: <request-task-id>
- Follow-up Epic: <followup-epic-id>
- FOLLOWUP_URD: <followup-urd-id>
- FOLLOWUP_IMPL_PLAN: <followup-impl-plan-id>

## Your Slice
- Slice: FOLLOWUP_SLICE-<N>
- Task ID: <slice-task-id>

## Adopted Leaf Tasks
| Leaf Task ID | Severity | Original Slice | Description |
|---|---|---|---|
| <leaf-id-1> | IMPORTANT | SLICE-1 | <description> |
| <leaf-id-2> | MINOR | SLICE-2 | <description> |

## Acceptance Criteria
- Both adopted leaf tasks resolved (tests pass, production code path verified)
- See bd task <slice-task-id> for full validation_checklist
```
