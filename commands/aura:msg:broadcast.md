# Broadcast Message to Multiple Agents

Communicate a status change to all agents working on related tasks.

## When to Use

- State change announcements (e.g., layer complete, ready for review)
- Notifying all workers of a blocking issue
- Notifying all reviewers that a proposal is ready

For single recipient, use `/aura:msg:send`.

## Given/When/Then/Should

**Given** broadcast needed **when** communicating **then** add comments to each relevant task **should never** assume a messaging CLI exists

**Given** state change **when** announcing **then** update beads task status and add comment **should never** leave agents unaware of state transitions

## Commands

```bash
# Add comments to multiple tasks
bd comments add <task-id-1> "Layer 1 complete — Layer 2 tasks are unblocked"
bd comments add <task-id-2> "Layer 1 complete — Layer 2 tasks are unblocked"
bd comments add <task-id-3> "Layer 1 complete — Layer 2 tasks are unblocked"

# Or update status on multiple tasks
bd update <task-id-1> --status=in_progress
bd update <task-id-2> --status=in_progress
```

## Example

```bash
# Announce that review is ready (comment on each reviewer's task)
bd comments add <review-1-id> "Proposal ready for review: bd show <proposal-id>"
bd comments add <review-2-id> "Proposal ready for review: bd show <proposal-id>"
bd comments add <review-3-id> "Proposal ready for review: bd show <proposal-id>"
```
