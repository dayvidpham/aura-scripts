---
name: impl:slice
description: Vertical slice assignment and tracking for workers
tools: Bash, Task
---

# Implementation Slice (Phase 9)

Manage vertical slice assignment to workers and track their progress.

## Given/When/Then/Should

**Given** impl-plan complete **when** assigning slices **then** create slice tasks with full specs **should never** leave specs vague

**Given** slice assigned **when** creating task **then** chain dependency to impl-plan **should never** create orphan slices

**Given** worker starts **when** tracking **then** update task to in_progress **should never** leave status as open

**Given** slice complete **when** verifying **then** add completion comments **should never** close the task

## Slice Structure

Each vertical slice contains:
- **slice_id**: Identifier (A, B, C, ...)
- **slice_name**: Human-readable name
- **slice_spec**: Detailed implementation specification
- **slice_files**: Files owned by this slice

## Creating Slices

After supervisor decomposes the ratified plan:

```bash
# Create slice A
bd create --labels aura:impl:slice,slice-A \
  --title "SLICE-A: {{slice name}}" \
  --description "## Specification
{{detailed implementation spec}}

## Files Owned
{{list of files this slice owns}}

## Acceptance Criteria
{{criteria from ratified plan}}

## Validation Checklist
- [ ] Types defined
- [ ] Tests written (import production code)
- [ ] Implementation complete
- [ ] Wiring complete
- [ ] Production code path verified" \
  --design='{"validation_checklist":["Types defined","Tests written (import production code)","Implementation complete","Wiring complete","Production code path verified"],"acceptance_criteria":[{"given":"X","when":"Y","then":"Z"}],"ratified_plan":"<ratified-plan-id>"}' \
  --assignee worker-1

bd dep add {{impl-plan-id}} --blocked-by {{slice-A-id}}
```

## Assigning Workers via Slots

```bash
# Assign slice to worker's hook
bd slot set worker-1 hook {{slice-A-id}}
bd slot set worker-2 hook {{slice-B-id}}
bd slot set worker-3 hook {{slice-C-id}}

# Worker checks their assignment
bd slot show worker-1
# hook: bd-xxx.slice-A
```

## Tracking Progress

```bash
# Worker starts
bd update {{slice-id}} --status in_progress

# Check all slice status
bd list --labels aura:impl:slice --status open
bd list --labels aura:impl:slice --status in_progress

# Worker completes (add comment, don't close)
bd comments add {{slice-id}} "COMPLETE: All checklist items verified. Production code path working."
bd label add {{slice-id}} aura:impl:slice:complete
```

## Slice Dependencies

Slices can have dependencies on each other (sync points):

```bash
# Slice B depends on Slice A completing first
bd dep add {{slice-A-id}} --blocked-by {{slice-B-id}}
```

Minimize inter-slice dependencies when possible.

## Aggregation

The `impl-aggregate` step waits for all slices to complete before code review:

```bash
# Check if all slices have complete label
bd list --labels aura:impl:slice --label-any aura:impl:slice:complete

# Compare to total slices
bd list --labels aura:impl:slice
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
    { "id": "A", "name": "Auth Module", "spec": "...", "files": "src/auth/*" },
    { "id": "B", "name": "API Layer", "spec": "...", "files": "src/api/*" }
  ]
}
```
