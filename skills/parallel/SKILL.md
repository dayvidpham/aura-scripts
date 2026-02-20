---
name: parallel
description: Launch parallel Claude agents in tmux sessions using aura-parallel. Use when spawning multiple agents for the same role (reviewers, workers) or a single long-running agent (supervisor, architect).
---

# Parallel — Launch Parallel Claude Agents

Launch N parallel Claude agent instances in isolated tmux sessions. Each agent gets role-specific instructions and can be given a unique task assignment.

## When to Use

- Launching a single long-running supervisor or architect agent
- Spawning multiple workers for parallel slice implementation
- **NOT for reviewers** — use Task tool subagents or TeamCreate for short-lived reviewers

## Given/When/Then/Should

**Given** a long-running agent is needed **when** launching **then** use `aura-parallel --role <role> -n 1 --prompt "..."` **should never** spawn long-running agents as Task tool subagents

**Given** multiple workers are needed **when** distributing tasks **then** use `--task-id` to assign one task per worker **should never** launch workers without task assignments

**Given** reviewers are needed **when** spawning **then** use Task tool subagents or TeamCreate instead **should never** use `aura-parallel` for reviewer rounds

## Commands

```bash
# Launch a single supervisor
aura-parallel --role supervisor -n 1 --prompt "Coordinate epic aura-xyz..."

# Launch 3 workers with task distribution (1:1 mapping)
aura-parallel --role worker -n 3 \
  --task-id impl-001 --task-id impl-002 --task-id impl-003 \
  --prompt "Implement the assigned task"

# Launch with skill invocation
aura-parallel --role reviewer -n 3 --skill aura:reviewer-review-plan \
  --prompt "Review plan aura-xyz"

# Dry run (preview commands without executing)
aura-parallel --role supervisor -n 1 --prompt "..." --dry-run
```

## Options

| Flag | Description |
|------|-------------|
| `--role` | Agent role: `architect`, `supervisor`, `reviewer`, `worker` |
| `-n` | Number of parallel agents to launch |
| `--prompt` | Prompt text for the agent |
| `--prompt-file` | Read prompt from a file instead |
| `--skill` | Skill to invoke at session start |
| `--task-id` | Beads task IDs to assign (repeatable, 1:1 with agents or all to one) |
| `--model` | Claude model: `sonnet`, `opus`, `haiku` |
| `--dry-run` | Preview commands without executing |

## Prerequisites

- `aura-parallel` must be on PATH (installed via Nix or symlinked)
- `tmux` and `claude` must be available
- Role instructions loaded from `skills/{role}/SKILL.md` in the working directory

## Example

```bash
# Architect spawns supervisor for handoff
aura-parallel --role supervisor -n 1 --prompt "$(cat <<'EOF'
Read the handoff document at .git/.aura/handoff/aura-xyz/architect-to-supervisor.md.
Then invoke /aura:supervisor to begin Phase 8 task decomposition.
Epic: aura-xyz
EOF
)"
```
