# Agent Instructions

This project is the **Aura Protocol** toolkit — multi-agent orchestration scripts, slash commands, and protocol documentation for Claude-based AI agent teams.

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Dependencies

Dependencies flow from **leaf work up to the user-facing request**. The leaf tasks (implementation details) must complete first, unblocking higher-level items, until the original request can be closed.

The chain reads left-to-right as "blocked by":

```
REQUEST -> URE -> PROPOSAL -> IMPL PLAN -> slices -> leaf tasks
```

Meaning: REQUEST is blocked by URE, URE is blocked by PROPOSAL, PROPOSAL is blocked by the IMPL PLAN (implementation plan), the IMPL PLAN is blocked by each vertical slice, and each slice is blocked by its individual leaf tasks.

### Correct: `--blocked-by` points at what must finish first

```bash
# "REQUEST is blocked by URE" — URE must complete before REQUEST can close
bd dep add request-id --blocked-by ure-id

# "PROPOSAL is blocked by IMPL PLAN"
bd dep add proposal-id --blocked-by impl-plan-id

# "IMPL PLAN is blocked by each slice"
bd dep add impl-plan-id --blocked-by slice-1-id
bd dep add impl-plan-id --blocked-by slice-2-id

# "slice is blocked by its leaf tasks"
bd dep add slice-1-id --blocked-by leaf-task-a-id
bd dep add slice-1-id --blocked-by leaf-task-b-id
```

Produces the correct tree (leaf work at the bottom, user request at the top):

```
REQUEST
  └── blocked by URE
        └── blocked by PROPOSAL
              └── blocked by IMPL PLAN
                    ├── blocked by slice-1
                    │     ├── blocked by leaf-task-a
                    │     └── blocked by leaf-task-b
                    └── blocked by slice-2
                          ├── blocked by leaf-task-c
                          └── blocked by leaf-task-d
```

### Wrong: reversed direction

```bash
# WRONG — this says "URE is blocked by REQUEST", meaning the request
# must finish before requirements gathering can start (backwards)
bd dep add ure-id --blocked-by request-id
```

**Rule of thumb:** The `--blocked-by` target is always the thing you do *first*. Work flows bottom-up; closure flows top-down.

## Project Structure

```
aura-scripts/
├── aura-swarm              # Epic-based worktree agent launcher (Python)
├── launch-parallel.py      # Parallel agent launcher for tmux sessions (Python)
├── flake.nix               # Nix flake packaging + Home Manager module
├── nix/hm-module.nix       # Home Manager module for config sync
├── protocol/               # Reusable Aura Protocol documentation
│   ├── README.md           # Protocol entry point and quick-start guide
│   ├── CLAUDE.md           # Core agent directive (philosophy, constraints, roles)
│   ├── CONSTRAINTS.md      # Coding standards, checklists, naming conventions
│   ├── PROCESS.md          # Step-by-step workflow (single source of truth)
│   ├── AGENTS.md           # Role taxonomy (phases, tools, handoffs per agent)
│   ├── SKILLS.md           # Command reference (all /aura:* skills by phase)
│   └── schema.xml          # Canonical protocol schema (BCNF)
├── skills/                 # Plugin skills (SKILL.md per directory)
│   └── aura:*.md           # Role-specific agent instructions
├── agents/                 # Custom agent definitions (~/.claude/agents/)
│   └── tester.md           # BDD test writer agent
└── AGENTS.md               # This file
```

## Validation

Before committing changes to this project:

```bash
# Ensure Nix flake evaluates cleanly
nix flake check --no-build 2>&1

# Build the packages (launch-parallel, aura-swarm)
nix build .#launch-parallel --no-link
nix build .#aura-swarm --no-link

# Test CLI help output
nix run .#aura-swarm -- --help
nix run .#launch-parallel -- --help
```

## Agent Orchestration

This project provides two tools for multi-agent coordination. Use the right tool for the right job:

### aura-swarm — Epic-based worktree workflow

Creates an isolated git worktree for an epic, gathers beads task context, and launches a single Claude instance (in a tmux session) that uses Agent Teams internally.

**Use for:** Large epics with multiple implementation slices that need isolated worktrees.

```bash
aura-swarm start --epic <epic-id> --model sonnet
aura-swarm status
aura-swarm attach <epic-id>
aura-swarm stop <epic-id>
aura-swarm merge <epic-id>
aura-swarm cleanup <epic-id>
```

Branch model:
```
main
 └── epic/<epic-id>                 (aura-swarm creates this branch + worktree)
       ├── agent/<task-id-1>         (Claude's Agent Teams creates these)
       ├── agent/<task-id-2>
       └── agent/<task-id-3>
```

### launch-parallel.py — Supervisor/Architect launches

Launches parallel Claude agents in tmux sessions with role-based instructions.

**Use for:** Spawning a separate supervisor or architect to plan and coordinate a new epic. These are long-running agents that need their own tmux session and persistent context.

```bash
# Launch supervisor to coordinate an epic
launch-parallel.py --role supervisor -n 1 --prompt "Coordinate implementation of..."

# Launch architect to propose a plan
launch-parallel.py --role architect -n 1 --prompt "Propose plan for..."

# Dry run (show commands without executing)
launch-parallel.py --role supervisor -n 1 --prompt "..." --dry-run
```

**DO NOT use for reviewer rounds.** Reviewers are short-lived and should use subagents or TeamCreate instead.

### Subagents / TeamCreate — Reviews and short-lived agents

**Use for:** Plan reviews, code reviews, and any short-lived parallel agent work.

Reviewers are spawned as subagents (via the Task tool) or coordinated via TeamCreate. This keeps them in-session, avoids tmux session overhead, and allows direct result collection.

### When to use which

| Scenario | Tool | Why |
|----------|------|-----|
| Epic implementation with worktree isolation | `aura-swarm` | Needs isolated branch + worktree |
| New supervisor/architect for epic planning | `launch-parallel.py` | Long-running, needs own tmux session |
| Plan review (3 reviewers) | Subagents / TeamCreate | Short-lived, results collected in-session |
| Code review (3 reviewers) | Subagents / TeamCreate | Short-lived, results collected in-session |
| Ad-hoc research or exploration | Task tool (Explore agent) | Quick, no orchestration needed |

### Inter-agent communication

Agents coordinate through **beads** (not a dedicated messaging CLI):

```bash
bd comments add <task-id> "Status update: ..."      # Add comments to shared tasks
bd update <task-id> --notes="Blocked on X"           # Update task notes
bd show <task-id>                                    # Read task state
bd update <task-id> --status=in_progress             # Claim work
bd close <task-id>                                   # Signal completion
```

## Review Criteria

All plans and code changes are reviewed against three axes:

### 1. Correctness (spirit and technicality)

- Does the implementation faithfully serve the user's original request?
- Are the technical decisions consistent with the rationale in the proposal?
- Are there gaps where the proposal says one thing but the code does another?

### 2. Test quality

- Favour integration tests over brittle unit tests
- The system under test must NOT be mocked — mock dependencies only
- Use shared fixtures for common test values
- Assert observable outcomes (HTTP status, response bodies), not internal state

### 3. Elegance and complexity matching

- Design the API you know you will need
- Do not over-engineer (premature abstractions, plugin systems for hypothetical futures)
- Do not under-engineer (cutting corners on security or correctness is not simplicity)
- Complexity should be proportional to the innate complexity of the problem domain

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - `nix flake check --no-build 2>&1`
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
