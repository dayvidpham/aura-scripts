# Receive Messages from Inbox

Check beads tasks for updates and new assignments.

## When to Use

- Workers checking for task assignments
- Supervisors checking for completions/blockers
- Architects checking for review results

## Given/When/Then/Should

**Given** checking for updates **when** polling **then** use `bd show` or `bd list` to check task state **should never** assume a messaging CLI exists

**Given** task assigned **when** starting **then** mark as in_progress before beginning work **should never** leave assigned tasks in pending state

## Commands

```bash
# Check your assigned tasks
bd list --pretty --status=open --assignee="<your-name>"

# Check for blocked tasks
bd blocked

# Check specific task for updates
bd show <task-id>

# Find ready work (no blockers)
bd ready
```

## Workflow

1. Check `bd ready` or `bd list` for assigned/available tasks
2. Read task details with `bd show <task-id>`
3. Mark as in_progress: `bd update <task-id> --status=in_progress`
4. Do the work
5. Mark complete: `bd close <task-id>`
