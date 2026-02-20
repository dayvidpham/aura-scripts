---
name: impl:slice
description: Vertical slice assignment and tracking for workers
tools: Bash, Task
---

# Implementation Slice (Phase 9)

Manage vertical slice assignment to workers and track their progress.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

See `CONSTRAINTS.md` for coding standards.

## Given/When/Then/Should

**Given** IMPL_PLAN complete **when** assigning slices **then** create SLICE-N tasks with full specs **should never** leave specs vague

**Given** slice assigned **when** creating task **then** chain dependency to IMPL_PLAN: `bd dep add <impl-plan-id> --blocked-by <slice-id>` **should never** create orphan slices

**Given** worker starts **when** tracking **then** update task to in_progress **should never** leave status as open

**Given** slice complete **when** verifying **then** add completion label and comments **should never** close the task prematurely

## Slice Structure

Each vertical slice contains:
- **slice_id**: Identifier (SLICE-1, SLICE-2, SLICE-3, ...)
- **slice_name**: Human-readable name
- **slice_spec**: Detailed implementation specification
- **slice_files**: Files owned by this slice

## Creating Slices

After supervisor decomposes the ratified plan:

```bash
# Create SLICE-1
bd create --labels "aura:p9-impl:s9-slice" \
  --title "SLICE-1: <slice name>" \
  --description "---
references:
  impl_plan: <impl-plan-task-id>
  urd: <urd-task-id>
---
## Specification
<detailed implementation spec>

## Files Owned
<list of files this slice owns>

## Acceptance Criteria
<criteria from ratified plan>

## Validation Checklist
- [ ] Types defined
- [ ] Tests written (import production code)
- [ ] Implementation complete
- [ ] Wiring complete
- [ ] Production code path verified" \
  --design='{"validation_checklist":["Types defined","Tests written (import production code)","Implementation complete","Wiring complete","Production code path verified"],"acceptance_criteria":[{"given":"X","when":"Y","then":"Z"}],"ratified_plan":"<ratified-plan-id>"}' \
  --assignee worker-1

bd dep add <impl-plan-id> --blocked-by <slice-1-id>
```

## Assigning Workers

```bash
bd update <slice-1-id> --assignee="worker-1"
bd update <slice-2-id> --assignee="worker-2"
bd update <slice-3-id> --assignee="worker-3"
```

## Tracking Progress

```bash
# Worker starts
bd update <slice-id> --status in_progress

# Check all slice status
bd list --labels="aura:p9-impl:s9-slice" --status=open
bd list --labels="aura:p9-impl:s9-slice" --status=in_progress

# Worker completes (add comment and label)
bd comments add <slice-id> "COMPLETE: All checklist items verified. Production code path working."
bd label add <slice-id> aura:p9-impl:slice-complete
```

## Slice Dependencies

Slices can have dependencies on each other (sync points):

```bash
# SLICE-2 depends on SLICE-1 completing first
bd dep add <slice-2-id> --blocked-by <slice-1-id>
```

Minimize inter-slice dependencies when possible.

## Aggregation

The aggregation step waits for all slices to complete before code review:

```bash
# Check if all slices have complete label
bd list --labels="aura:p9-impl:slice-complete"

# Compare to total slices
bd list --labels="aura:p9-impl:s9-slice"
```

## Dynamic Bonding (Formula-Based)

If using formulas, slices are bonded dynamically via `on_complete`:

```json
{
  "on_complete": {
    "for_each": "output.slices",
    "bond": "aura-slice",
    "vars": {
      "slice_id": "{item.id}",
      "slice_name": "{item.name}",
      "slice_spec": "{item.spec}",
      "slice_files": "{item.files}"
    },
    "parallel": true
  }
}
```

The supervisor's output defines the slices:
```json
{
  "slices": [
    { "id": "1", "name": "Auth Module", "spec": "...", "files": "src/auth/*" },
    { "id": "2", "name": "API Layer", "spec": "...", "files": "src/api/*" }
  ]
}
```
