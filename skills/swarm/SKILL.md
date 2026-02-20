---
name: swarm
description: Launch worktree-based agent workflows for epics using aura-swarm. Use when starting an epic, checking swarm status, or managing agent worktrees.
---

# Swarm — Worktree Agent Workflow

Orchestrate multi-agent epics using isolated git worktrees. Each epic gets its own worktree branch, and Claude's Agent Teams coordinate workers internally.

## When to Use

- Starting a new epic implementation (`aura-swarm start`)
- Checking status of running agent sessions (`aura-swarm status`)
- Attaching to a running session (`aura-swarm attach`)
- Merging completed work back to the epic branch (`aura-swarm merge`)
- Launching code review rounds (`aura-swarm review`)
- Cleaning up finished worktrees (`aura-swarm cleanup`)

## Given/When/Then/Should

**Given** an epic needs implementation **when** launching agents **then** use `aura-swarm start --epic <id>` to create an isolated worktree **should never** launch long-running workers as Task tool subagents

**Given** agents are running **when** checking progress **then** use `aura-swarm status` to see all active sessions **should never** try to inspect tmux sessions manually

**Given** an epic is complete **when** cleaning up **then** use `aura-swarm cleanup <id>` or `aura-swarm cleanup --done` **should never** manually delete worktrees or branches

## Branch Model

```
main
 └── epic/<epic-id>                 (aura-swarm creates this branch + worktree)
       ├── agent/<task-id-1>         (Claude's Agent Teams creates these)
       ├── agent/<task-id-2>
       └── agent/<task-id-3>
```

## Commands

```bash
# Start an epic (creates worktree, gathers beads context, launches Claude)
aura-swarm start --epic <epic-id> --model sonnet

# Check status of all running agent sessions
aura-swarm status

# Attach to a running session's tmux
aura-swarm attach <epic-id>

# Stop a running session
aura-swarm stop <epic-id>

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

## Prerequisites

- `aura-swarm` must be on PATH (installed via Nix or symlinked)
- `git`, `tmux`, `bd` (beads CLI), and `claude` must be available
- The current directory must be inside a git repository with beads initialized

## Example

```bash
# Supervisor launches a swarm for an implementation epic
aura-swarm start --epic aura-scripts-xky --model sonnet

# Check progress
aura-swarm status

# When workers finish, merge their branches
aura-swarm merge aura-scripts-xky

# Clean up the worktree
aura-swarm cleanup aura-scripts-xky
```
