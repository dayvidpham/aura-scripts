---
name: swarm
description: Launch worktree-based or intree agent workflows using aura-swarm. Use when starting an epic, launching parallel agents, checking swarm status, or managing agent worktrees.
---

# Swarm — Unified Agent Orchestration

Orchestrate Claude agent sessions in two modes:
- **Worktree mode** (default): Isolated git worktrees per epic, with beads task discovery and rich prompt generation.
- **Intree mode**: In-place parallel agents (replaces `aura-parallel`). No worktree, prompt required.

## When to Use

- Starting a new epic implementation (`aura-swarm start --epic <id>`)
- Launching parallel in-place agents (`aura-swarm start --swarm-mode intree -n N --prompt "..."`)
- Checking status of running agent sessions (`aura-swarm status`)
- Attaching to a running session (`aura-swarm attach`)
- Merging completed work back to the epic branch (`aura-swarm merge`)
- Launching code review rounds (`aura-swarm review`)
- Cleaning up finished worktrees (`aura-swarm cleanup`)

## Given/When/Then/Should

**Given** an epic needs implementation **when** launching agents **then** use `aura-swarm start --epic <id>` to create an isolated worktree **should never** launch long-running workers as Task tool subagents

**Given** a long-running agent is needed in-place **when** launching **then** use `aura-swarm start --swarm-mode intree --role <role> -n 1 --prompt "..."` **should never** spawn long-running agents as Task tool subagents

**Given** multiple workers are needed in-place **when** distributing tasks **then** use `--task-id` to assign one task per worker **should never** launch workers without task assignments

**Given** reviewers are needed **when** spawning **then** use Task tool subagents or TeamCreate instead **should never** use `aura-swarm start` for reviewer rounds

**Given** agents are running **when** checking progress **then** use `aura-swarm status` to see all active sessions **should never** try to inspect tmux sessions manually

**Given** an epic is complete **when** cleaning up **then** use `aura-swarm cleanup <id>` or `aura-swarm cleanup --done` **should never** manually delete worktrees or branches

## Branch Model (worktree mode)

```
main
 └── epic/<epic-id>                 (aura-swarm creates this branch + worktree)
       ├── agent/<task-id-1>         (Claude's Agent Teams creates these)
       ├── agent/<task-id-2>
       └── agent/<task-id-3>
```

## Commands

### Worktree Mode (default)

```bash
# Start an epic (creates worktree, gathers beads context, launches Claude)
aura-swarm start --epic <epic-id>
aura-swarm start --epic <epic-id> --model opus
aura-swarm start --epic <epic-id> --restart

# Window mode (agents accumulate in one tmux session)
aura-swarm start --epic <epic-id> --tmux-dest window -n 2

# With additional instructions appended to auto-generated prompt
aura-swarm start --epic <epic-id> --prompt-addon "Focus on tests first"
```

### Intree Mode (replaces aura-parallel)

```bash
# Launch a single supervisor
aura-swarm start --swarm-mode intree --role supervisor -n 1 --prompt "..."

# Launch 3 workers with task distribution (1:1 mapping)
aura-swarm start --swarm-mode intree --role worker -n 3 \
  --task-id impl-001 --task-id impl-002 --task-id impl-003 \
  --prompt "Implement the assigned task"

# Launch with skill invocation
aura-swarm start --swarm-mode intree --role reviewer -n 3 \
  --skill aura:reviewer-review-plan --prompt "Review plan aura-xyz"

# Dry run (preview commands without executing)
aura-swarm start --swarm-mode intree --role supervisor -n 1 --prompt "..." --dry-run
```

### Management

```bash
# Check status of all running agent sessions
aura-swarm status

# Attach to a running session's tmux
aura-swarm attach <epic-id-or-session-id>

# Stop a running session (keeps worktree)
aura-swarm stop <epic-id-or-session-id>

# Merge agent branches back to epic branch
aura-swarm merge <epic-id>

# Launch code review round for an epic
aura-swarm review --epic <epic-id>

# Clean up a specific epic's worktree
aura-swarm cleanup <epic-id>

# Clean up all completed epics
aura-swarm cleanup --done

# Clean up everything (including in-progress)
aura-swarm cleanup --all
```

## Options

### Start Options

| Flag | Description |
|------|-------------|
| `--epic` | Epic beads ID (required for worktree mode, optional for intree) |
| `--swarm-mode` | `worktree` (default) or `intree` |
| `--tmux-dest` | `session` (default) or `window` (agents accumulate in one tmux session) |
| `-n/--njobs` | Number of parallel agents (default: 1) |
| `--role` | Agent role: `architect`, `supervisor`, `reviewer`, `worker` (default: supervisor) |
| `--model` | Claude model: `sonnet`, `opus`, `haiku` (default: sonnet) |
| `--prompt` | Prompt text (required for intree mode) |
| `--prompt-file` | Read prompt from file (mutually exclusive with `--prompt`) |
| `--prompt-addon` | Additional instructions appended to auto-generated prompt (worktree mode) |
| `--skill` | Skill to invoke at session start |
| `--task-id` | Beads task IDs (repeatable). Intree: distributed 1:1 across agents |
| `--permission-mode` | `default`, `acceptEdits`, `bypassPermissions`, `plan` (default: acceptEdits) |
| `--restart` | Stop existing session and start fresh |
| `--dry-run` | Preview commands without executing |
| `--attach` | Attach to first session after launching |
| `--session-name` | Override tmux session name |
| `--working-dir` | Working directory (default: git root) |

## Prerequisites

- `aura-swarm` must be on PATH (installed via Nix or symlinked)
- `tmux` and `claude` must be available
- **Worktree mode**: `git` and `bd` (beads CLI) must be available; must be in a git repo with beads initialized
- **Intree mode**: `--prompt` or `--prompt-file` required; `bd` only needed if `--epic` is provided

## Examples

```bash
# Supervisor launches a swarm for an implementation epic
aura-swarm start --epic aura-scripts-xky --model sonnet

# Check progress
aura-swarm status

# When workers finish, merge their branches
aura-swarm merge aura-scripts-xky

# Clean up the worktree
aura-swarm cleanup aura-scripts-xky

# Architect spawns supervisor for handoff (intree mode)
aura-swarm start --swarm-mode intree --role supervisor -n 1 --prompt "$(cat <<'EOF'
Read the handoff document at .git/.aura/handoff/aura-xyz/architect-to-supervisor.md.
Then invoke /aura:supervisor to begin Phase 8 task decomposition.
Epic: aura-xyz
EOF
)"
```

## Migration from aura-parallel

`aura-parallel` is deprecated. All commands translate directly:

```bash
# Old:
aura-parallel --role worker -n 3 --prompt "..."

# New:
aura-swarm start --swarm-mode intree --role worker -n 3 --prompt "..."
```

The `aura-parallel` command still works as a thin wrapper but prints a deprecation warning.
