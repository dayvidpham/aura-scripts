# Supervisor: Spawn Worker — Ride the Wave

Launch the wave of workers for parallel vertical slice implementation, reviewed by persistent Cartographers.

**-> [Full workflow in PROCESS.md](../protocol/PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

Implementation tasks ready. Cartographers already spawned and standing by (see supervisor SKILL.md § Cartographers).

## Ride the Wave — Overview

The supervisor executes Phases 8-10 as a single coordinated cycle called **Ride the Wave**:

```
1. PLAN  → supervisor-plan-tasks: decompose into slices + integration points
2. MAP   → 3 Cartographers (TeamCreate, /aura:explore): map codebase, persist
3. BUILD → N Workers (TeamCreate, /aura:worker): implement slices in parallel, persist
4. REVIEW → Cartographers switch to /aura:reviewer: review ALL slices
5. FIX   → Workers fix BLOCKERs + IMPORTANTs from review
6. RE-REVIEW → Cartographers re-review fixed slices
7. REPEAT → Steps 5-6 up to MAX 3 cycles total
8. TRACK → IMPORTANT/MINOR findings → FOLLOWUP epic
9. NEXT  → If clean or 3 cycles exhausted → Phase 11 (UAT)
```

**Key rules:**
- Cartographers and workers are **never shut down** between stages — they persist for the full wave
- Slices are **never closed** until reviewed at least once
- Max **3 worker-reviewer cycles** — remaining IMPORTANT goes to FOLLOWUP

## Given/When/Then/Should

**Given** implementation tasks **when** spawning **then** use Task tool with `run_in_background: true` **should never** block on worker completion

**Given** multiple workers **when** launching **then** spawn all slices in parallel as a single wave **should never** spawn sequentially

**Given** worker assignment **when** providing context **then** include Beads task ID, full context, and handoff document **should never** omit checklist or criteria

**Given** worker handoff **when** creating **then** store at `.git/.aura/handoff/<request-task-id>/supervisor-to-worker-<N>.md` **should never** skip handoff document

**Given** workers complete their slices **when** first wave finishes **then** do NOT close slices — Cartographers must review ALL slices first **should never** close a slice that has not been reviewed at least once

**Given** Cartographers finish reviewing **when** BLOCKERs or IMPORTANT findings exist **then** send findings to workers for fixing, then have Cartographers re-review **should never** skip re-review after fixes

**Given** worker-reviewer cycle **when** counting iterations **then** limit to a MAXIMUM of 3 cycles **should never** exceed 3 cycles — if IMPORTANT findings remain after cycle 3, move to UAT and track remaining in FOLLOWUP epic

**Given** IMPORTANT findings remain after 3 cycles **when** deciding next step **then** proceed to Phase 11 (UAT) — all remaining IMPORTANT and MINOR findings must be tracked in the FOLLOWUP Beads epic **should never** block UAT on non-BLOCKER findings after 3 cycles

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

## Persistence
Do NOT shut down after implementation. You will receive review feedback
and may need to fix BLOCKERs and IMPORTANT findings. Stay alive for the
full Ride the Wave cycle.
```

## Task Call

```
Task({
  description: "Worker: implement SLICE-N",
  prompt: `Call Skill(/aura:worker) and implement the assigned slice.

Beads Task ID: <task-id>
Read full requirements: bd show <task-id>
Handoff doc: .git/.aura/handoff/<request-task-id>/supervisor-to-worker-<N>.md

Do NOT shut down after implementation. You will receive review feedback and may need to fix issues.`,
  subagent_type: "general-purpose",
  run_in_background: true
})
```

**Important:** Use `subagent_type: "general-purpose"`, not a custom agent type. The worker skill is invoked inside the agent via `Skill(/aura:worker)`.

## TeamCreate: SendMessage Assignment

When workers are spawned via TeamCreate, they receive context through SendMessage instead of a Task prompt. The message MUST be self-contained — teammates have **no prior context**:

```
SendMessage({
  type: "message",
  recipient: "worker-1",
  content: `You are assigned SLICE-1. Start by calling Skill(/aura:worker).

Your Beads task ID: <slice-task-id>
Run this to get full requirements: bd show <slice-task-id>
Handoff document: .git/.aura/handoff/<request-task-id>/supervisor-to-worker-1.md

Key references (run bd show on each for full context):
- Request: <request-task-id>
- URD: <urd-task-id>
- IMPL_PLAN: <impl-plan-task-id>
- Ratified Proposal: <proposal-task-id>

Read the handoff doc and your Beads task before starting implementation.

IMPORTANT: Do NOT shut down after completing implementation. You will receive
review feedback from Cartographers and may need to fix BLOCKERs and IMPORTANT
findings. Stay alive for the full Ride the Wave cycle.`,
  summary: "SLICE-1 assignment with Beads context"
})
```

**Critical:** Never send bare instructions like "implement SLICE-1" without Beads task IDs and `bd show` commands. Teammates cannot see your conversation or task tree.

## Worker Persistence (Ride the Wave)

Workers are **never shut down** after completing their first implementation pass. They stay alive for the review-fix cycle:

1. Worker completes slice → notifies supervisor
2. Supervisor does **NOT** close the slice or shut down the worker
3. Cartographers review the slice
4. If BLOCKERs or IMPORTANT findings: supervisor sends fix assignment to worker
5. Worker fixes issues → notifies supervisor
6. Cartographers re-review
7. Repeat steps 4-6 up to MAX 3 cycles total
8. After 3 cycles or all clean: supervisor shuts down worker

### Fix Assignment Message Template

```
SendMessage({
  type: "message",
  recipient: "worker-1",
  content: `Review cycle <N> found issues in your slice (SLICE-1).

BLOCKERs (must fix — blocks slice closure):
- <finding-id>: <description> (bd show <finding-id>)

IMPORTANT (must fix this cycle):
- <finding-id>: <description> (bd show <finding-id>)

After fixing all items:
  bd comments add <slice-id> "Fixes applied for review cycle <N>"

Do NOT shut down. Cartographers will re-review.`,
  summary: "Review cycle <N> fixes for SLICE-1"
})
```

## Worker Should Update Beads Status

- On start: `bd update <task-id> --status=in_progress`
- On implementation complete (NOT slice close): `bd comments add <task-id> "Implementation complete, awaiting review"`
- On blocked: `bd update <task-id> --notes="Blocked: <reason>"`
- Slice closure: **only the supervisor** closes slices after review passes

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
