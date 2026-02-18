# Supervisor: Spawn Worker

Launch worker for a vertical slice assignment.

## When to Use

Implementation tasks ready, spawning workers for parallel execution.

## Given/When/Then/Should

**Given** implementation tasks **when** spawning **then** use Task tool with `run_in_background: true` **should never** block on worker completion

**Given** multiple workers **when** launching **then** spawn all in layer in parallel **should never** spawn sequentially

**Given** worker assignment **when** providing context **then** include Beads task ID and full context **should never** omit checklist or criteria

## Task Call

```
Task(
  description: "Worker: implement vertical slice",
  prompt: "Call Skill(/aura:worker) and implement the assigned slice.\n\nBeads Task ID: <task-id>\n\nRead full requirements: bd show <task-id>",
  subagent_type: "general-purpose",
  run_in_background: true
)
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
