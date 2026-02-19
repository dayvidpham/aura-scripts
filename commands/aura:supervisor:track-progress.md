# Supervisor: Track Progress

Monitor worker completion status via Beads and messaging.

## When to Use

Workers spawned, monitoring for completions and blockers.

## Given/When/Then/Should

**Given** workers running **when** monitoring **then** check Beads status and inbox **should never** poll aggressively

**Given** worker complete **when** all files for layer done **then** proceed to next layer or commit **should never** commit partial work

**Given** worker blocked **when** handling **then** resolve or reassign immediately **should never** leave workers waiting

**Given** requirements question arises **when** resolving **then** consult the URD (`bd show <urd-id>`) for the single source of truth **should never** guess at user intent without checking URD

## Beads Status Queries

```bash
# Check all implementation tasks
bd list --labels="aura:impl" --status=in_progress

# Check for blocked tasks
bd list --labels="aura:impl" --status=blocked

# Check specific task
bd show <task-id>

# Check completed tasks
bd list --labels="aura:impl" --status=done
```

## Tracking via Beads

All coordination happens through beads task status and comments:

```bash
# Check for task updates
bd show <task-id>

# Review comments for status updates
bd comments <task-id>

# Add coordination notes
bd comments add <task-id> "Layer 1 complete — proceeding to Layer 2"
```

## Status Patterns

| Status | Action |
|--------|--------|
| `done` | Mark layer progress, check if layer complete |
| `blocked` | Review `bd show <id>` for blocker details, resolve or reassign |
| `in_progress` | Worker is actively working |
