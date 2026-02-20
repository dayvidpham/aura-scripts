# Supervisor: Track Progress

Monitor worker completion status via Beads.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

Workers spawned, monitoring for completions and blockers.

## Given/When/Then/Should

**Given** workers running **when** monitoring **then** check Beads status **should never** poll aggressively

**Given** worker complete **when** all slices for phase done **then** proceed to code review or commit **should never** commit partial work

**Given** worker blocked **when** handling **then** resolve or reassign immediately **should never** leave workers waiting

**Given** requirements question arises **when** resolving **then** consult the URD (`bd show <urd-id>`) for the single source of truth **should never** guess at user intent without checking URD

**Given** all slices complete **when** transitioning to review **then** check for BLOCKER resolution tracking **should never** skip severity awareness

## Beads Status Queries

```bash
# Check all implementation slices
bd list --labels="aura:p9-impl:s9-slice" --status=in_progress

# Check for blocked slices
bd list --labels="aura:p9-impl:s9-slice" --status=blocked

# Check specific task
bd show <task-id>

# Check completed slices
bd list --labels="aura:p9-impl:s9-slice" --status=done

# Check BLOCKER severity groups (during/after review)
bd list --labels="aura:severity:blocker" --status=open

# Check follow-up epic
bd list --labels="aura:epic-followup"
```

## Tracking via Beads

All coordination happens through beads task status and comments:

```bash
# Check for task updates
bd show <task-id>

# Review comments for status updates
bd comments <task-id>

# Add coordination notes
bd comments add <task-id> "All slices complete — proceeding to Phase 10 (code review)"
```

## Status Patterns

| Status | Action |
|--------|--------|
| `done` | Mark slice progress, check if all slices complete |
| `blocked` | Review `bd show <id>` for blocker details, resolve or reassign |
| `in_progress` | Worker is actively working |

## Severity Awareness (Phase 10)

When tracking review progress, monitor severity groups:

| Severity | Blocks Slice? | Action |
|----------|---------------|--------|
| BLOCKER | Yes | Must resolve before proceeding to Phase 11 |
| IMPORTANT | No | Goes to follow-up epic (`aura:epic-followup`) |
| MINOR | No | Goes to follow-up epic (`aura:epic-followup`) |
