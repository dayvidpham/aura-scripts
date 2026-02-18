# Send Message to Agent

Communicate with another agent via beads task comments.

## When to Use

- Task assignments to workers
- Completion reports to supervisor
- Review results to architect
- Clarification requests

For multiple recipients, use `/aura:msg:broadcast`.

## Given/When/Then/Should

**Given** message **when** sending **then** add a comment on the shared beads task **should never** assume a messaging CLI exists

**Given** status update **when** communicating **then** use `bd comments add` or `bd update --notes` **should never** leave coordination implicit

## Commands

```bash
# Add a comment to a shared task (visible to all agents watching that task)
bd comments add <task-id> "Status: implementation complete for slice A"

# Update task notes with current state
bd update <task-id> --notes="Blocked: waiting for types from slice B"

# Update task status
bd update <task-id> --status=in_progress
```

## Common Patterns

| Action | Command |
|--------|---------|
| Assign work | `bd update <task-id> --assignee "<agent-name>"` |
| Report completion | `bd close <task-id>` |
| Report blocker | `bd update <task-id> --notes="Blocked: <reason>"` |
| Request review | `bd comments add <task-id> "Ready for review"` |
| Send feedback | `bd comments add <task-id> "VOTE: REVISE - <feedback>"` |
