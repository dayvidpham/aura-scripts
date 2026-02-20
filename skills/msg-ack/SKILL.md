# Acknowledge Received Messages

Acknowledge task updates after processing.

## When to Use

After reviewing a task update or completing an assigned action.

## Given/When/Then/Should

**Given** task reviewed **when** acknowledging **then** add a comment confirming receipt **should never** leave coordination ambiguous

**Given** action completed **when** reporting **then** update task status and add notes **should never** silently complete without updating beads

## Commands

```bash
# Acknowledge a review request
bd comments add <task-id> "Acknowledged — starting review"

# Acknowledge completion of a dependency
bd comments add <task-id> "Confirmed: dependency <dep-id> complete, proceeding"

# Acknowledge and update status
bd update <task-id> --status=in_progress
bd comments add <task-id> "Claimed — beginning work"
```
