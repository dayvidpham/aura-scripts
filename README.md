# aura-plugins

Multi-agent orchestration toolkit for the [Aura Protocol](skills/protocol/PROCESS.md).
Provides CLI tools for launching Claude agents in isolated worktrees and tmux
sessions, role-based slash commands, and a Home Manager module for declarative
distribution.

## Overview

aura-plugins solves two problems in multi-agent Claude workflows:

1. **Isolation.** Parallel agents editing the same repo need separate working
   trees and branches to avoid conflicts. `aura-swarm` creates per-epic git
   worktrees with automatic Beads context gathering.

2. **Coordination.** Agents need structured roles (architect, supervisor,
   worker, reviewer) with different toolsets and instructions. Both CLI tools
   inject role-specific system prompts from `skills/*/SKILL.md` files.

All inter-agent coordination flows through [Beads](https://github.com/dayvidpham/beads)
task status and comments &mdash; there is no separate messaging system.

## Quick Start — Plugin Install

### Claude Code

```bash
# 1. Add the aura-plugins marketplace
claude plugin marketplace add dayvidpham/aura-plugins

# 2. Install the aura plugin (user-wide)
claude plugin install aura@aura-plugins

# Or install for a specific project only
claude plugin install aura@aura-plugins --scope project

# Validate (optional)
claude plugin validate /path/to/aura-plugins
```

After installing, restart Claude Code. Skills are auto-discovered and invocable as `/aura:<skill-name>` (e.g. `/aura:epoch`, `/aura:user-request`).

```bash
# Update to latest
claude plugin update aura@aura-plugins

# Local development (from a checkout, no install needed)
claude plugin marketplace add /path/to/aura-plugins
claude plugin install aura@aura-plugins
```

### OpenCode

OpenCode natively reads `skills/*/SKILL.md`. Clone into your project's `.claude/` or configure via OpenCode's plugin system.

---

## Installation (CLI Tools)

### Nix Flake (recommended)

Add as a flake input:

```nix
# flake.nix
{
  inputs.aura-plugins.url = "github:dayvidpham/aura-plugins";
}
```

Then reference the packages:

```nix
# In your system or home-manager config:
aura-plugins.packages.${system}.aura-parallel
aura-plugins.packages.${system}.aura-swarm
aura-plugins.packages.${system}.default  # both tools
```

### Home Manager Module

The flake exports a Home Manager module that syncs commands, agents, and
protocol docs into `~/.claude/`:

```nix
# home.nix
{
  imports = [ aura-plugins.homeManagerModules.aura-config-sync ];

  CUSTOM.programs.aura-config-sync = {
    packages.enable = true;              # install CLI tools

    commands.enable = true;              # install slash commands
    commands.roles = {                   # toggle per-role
      architect = true;
      supervisor = true;
      worker = true;
      reviewer = true;
      epoch = true;
    };
    # commands.enableAll = true;         # shorthand for all roles

    agents.enable = true;               # install custom agents

    protocol.enable = false;             # install skills/protocol/ docs (off by default)
  };
}
```

Core commands (`aura:plan`, `aura:status`, `aura:test`, `aura:feedback`,
`aura:msg:*`, `aura:impl:*`, `aura:user:*`) are always installed when
`commands.enable = true`, regardless of role selection.

### Manual

Both scripts are standalone Python 3.10+ with no external dependencies:

```bash
git clone https://github.com/dayvidpham/aura-plugins
cd aura-plugins
chmod +x bin/aura-swarm bin/aura-parallel
# Add bin/ to PATH or symlink into a PATH directory
```

## Prerequisites

Both tools check for these on startup and exit with an error if any are missing:

| Tool    | Purpose                          |
|---------|----------------------------------|
| `git`   | Worktree and branch management   |
| `tmux`  | Agent session hosting            |
| `bd`    | Beads issue tracking             |
| `claude`| Claude CLI (agent runtime)       |

Python 3.10+ (stdlib only, no pip dependencies).

---

## aura-swarm

Creates an isolated git worktree for a Beads epic, gathers task context from the
dependency graph, and launches a single Claude instance in a tmux session. The
agent uses Claude's Agent Teams internally to spawn workers on sub-branches.

### Branch model

```
main
 └── epic/<epic-id>                   aura-swarm creates this branch + worktree
       ├── agent/<task-id-1>          Claude Agent Teams creates sub-branches
       ├── agent/<task-id-2>
       └── agent/<task-id-3>
```

### Usage

```bash
aura-swarm <subcommand> [options]
```

### Subcommands

#### `start` &mdash; Launch an epic session

Creates (or reuses) a worktree, discovers tasks and URD from the Beads
dependency graph, builds a context-rich prompt, and launches Claude in a
detached tmux session.

```bash
aura-swarm start --epic <epic-id> [options] [task-id ...]
```

| Option              | Default          | Description                                      |
|---------------------|------------------|--------------------------------------------------|
| `--epic`            | *(required)*     | Beads epic ID                                    |
| `--role`            | `supervisor`     | Agent role: `architect`, `supervisor`, `reviewer`, `worker` |
| `--model`           | `sonnet`         | Model: `sonnet`, `opus`, `haiku`                 |
| `--skill`           | &mdash;          | Skill to invoke at start (e.g. `aura:supervisor`) |
| `--prompt-addon`    | &mdash;          | Extra instructions appended to the auto-generated prompt |
| `--permission-mode` | `acceptEdits`    | `default`, `acceptEdits`, `bypassPermissions`, `plan` |
| `--urd`             | *(auto-discovered)* | Explicit URD task ID (overrides graph walk)    |
| `--restart`         | `false`          | Kill existing session and start fresh             |
| `--worktree-dir`    | `worktree`       | Root directory for worktrees (relative to repo)   |
| `--dry-run`         | `false`          | Preview prompt and commands without launching     |
| `task-id ...`       | *(auto-discovered)* | Explicit task IDs (overrides dependency walk)  |

**Task discovery.** When no explicit task IDs are given, `aura-swarm` walks the
epic's Beads dependency graph two levels deep, classifying each task as a
*blocker* (must finish first) or *dependent* (downstream work). The discovered
tasks are formatted into a markdown table in the generated prompt.

**URD discovery.** The User Requirements Document is identified by the
`aura:user:reqs` label or a `[aura:user:reqs]` title prefix. If `--urd` is not
set, the script searches the epic's first- and second-level dependencies.

**Examples:**

```bash
# Typical: launch a supervisor for an epic, let it discover tasks from Beads
aura-swarm start --epic aura-dyu --model sonnet

# Use opus for complex architectural work
aura-swarm start --epic aura-dyu --role architect --model opus

# Explicitly pass tasks instead of auto-discovery
aura-swarm start --epic aura-dyu impl-001 impl-002 impl-003

# Preview what would be launched (inspect the generated prompt)
aura-swarm start --epic aura-dyu --dry-run

# Restart a stuck session
aura-swarm start --epic aura-dyu --restart
```

#### `status` &mdash; List active sessions

```bash
aura-swarm status
```

Prints a table of all tracked sessions for the current repository:

```
epic-id            tmux session         alive?   worktree                  branch                  # tasks
aura-dyu           epic-dyu--a3d5       yes      worktree/aura-dyu         epic/aura-dyu           3
```

#### `attach` &mdash; Attach to an epic's tmux session

```bash
aura-swarm attach <epic-id>
```

Replaces the current process with `tmux attach -t <session>`. Detach with
`Ctrl-b d` as usual.

#### `stop` &mdash; Kill session, keep worktree

```bash
aura-swarm stop <epic-id>
aura-swarm stop <epic-id> --dry-run
```

Kills the tmux session and removes the session record. The worktree and branch
are preserved for inspection or manual cleanup.

#### `merge` &mdash; Merge epic branch into main

```bash
aura-swarm merge <epic-id>
aura-swarm merge <epic-id> --dry-run
```

Runs `git merge epic/<epic-id> --no-ff` from the repository root. Fails if the
worktree has uncommitted changes. On merge conflict, automatically aborts the
merge and lists conflicting files.

#### `review` &mdash; Generate a review document

```bash
aura-swarm review --epic <epic-id>
aura-swarm review --epic <epic-id> --dry-run
```

Generates a markdown review document at `docs/review-<epic-id>.md` containing
the epic description, task breakdown, diff stats against main, and a review
checklist. Also creates a Beads task labeled `[REVIEW]` for tracking.

#### `cleanup` &mdash; Remove worktrees and branches

```bash
# Clean up a specific epic
aura-swarm cleanup <epic-id>

# Remove all merged epic branches
aura-swarm cleanup --done

# Interactive removal of all worktrees (prompts for confirmation)
aura-swarm cleanup --all

# Force removal even if worktree is dirty
aura-swarm cleanup <epic-id> --force

# Preview what would be removed
aura-swarm cleanup <epic-id> --dry-run
```

Kills any live tmux session, removes the worktree (`git worktree remove`),
deletes the branch, and cleans up the session record. Skips dirty worktrees
unless `--force` is set.

### State management

Session state persists in `~/.aura/swarm/<repo-hash>/sessions.json`, where
`<repo-hash>` is the first 16 characters of the SHA-256 of the repository root
path. Each entry records:

| Field          | Example                          |
|----------------|----------------------------------|
| `epic_id`      | `aura-dyu`                       |
| `epic_branch`  | `epic/aura-dyu`                  |
| `worktree`     | `/home/user/repo/worktree/aura-dyu` |
| `tmux_session` | `epic-dyu--a3d5`                 |
| `started_at`   | `2026-02-18T14:30:00`            |
| `model`        | `sonnet`                         |
| `task_ids`     | `["impl-001", "impl-002"]`       |

Stale sessions (record exists but tmux is dead) are detected automatically and
can be overwritten with `--restart`.

**Prompt files.** The generated prompt is written to
`~/.local/share/aura/aura-swarm/prompts/<repo-hash>-<timestamp>-prompt.md` before
launch. The tmux command references this file via `$(cat ...)` shell expansion
rather than embedding the prompt inline, avoiding tmux's command length limit.
Role instructions (from `skills/<role>/SKILL.md`) are referenced by
their original path. Prompt files persist as an audit trail.

### Tmux session naming

Format: `epic-<suffix>--<hex4>`, where `<suffix>` is extracted from the epic ID
(e.g. `aura-dyu` &rarr; `dyu`) and `<hex4>` is a random 4-character hex token
for uniqueness. Retries up to 5 times on collision.

---

## aura-parallel

Launches one or more Claude agents in parallel tmux sessions with role-based
system prompts. Designed for long-running supervisor and architect agents that
need persistent context in their own sessions.

### Usage

```bash
aura-parallel --role <role> -n <count> --prompt <text> [options]
```

### Arguments

| Argument            | Default          | Description                                         |
|---------------------|------------------|-----------------------------------------------------|
| `--role`            | *(required)*     | `architect`, `supervisor`, `reviewer`, `worker`     |
| `-n`, `--njobs`     | *(required)*     | Number of parallel instances (>= 1)                 |
| `--prompt`          | &mdash;          | Prompt text (mutually exclusive with `--prompt-file`) |
| `--prompt-file`     | &mdash;          | Read prompt from file                               |
| `--model`           | `sonnet`         | `sonnet`, `opus`, `haiku`                           |
| `--skill`           | &mdash;          | Skill to invoke at start (auto-prefixes `aura:` if needed) |
| `--task-id`         | &mdash;          | Beads task ID (repeatable, see distribution below)  |
| `--working-dir`     | git root or cwd  | Working directory for all sessions                  |
| `--permission-mode` | `acceptEdits`    | `default`, `acceptEdits`, `bypassPermissions`, `plan` |
| `--session-name`    | *(auto-generated)* | Override session name (suffixed with `--N` when n>1) |
| `--attach`          | `false`          | Attach to first session after launch                |
| `--dry-run`         | `false`          | Preview commands without executing                  |

One of `--prompt` or `--prompt-file` is required.

### Task distribution

How `--task-id` values are distributed depends on `--njobs`:

| Scenario           | Behavior                         | Example                        |
|--------------------|----------------------------------|--------------------------------|
| `-n 1`, 3 task IDs | All task IDs go to one agent     | Agent sees all 3 in its prompt |
| `-n 3`, 3 task IDs | 1:1 &mdash; each agent gets one  | Agent 1 &rarr; task 1, etc.   |
| `-n 3`, 2 task IDs | Partial &mdash; last agent has none | Agent 3 gets no task ID     |

### Prompt construction

The final prompt sent to each agent is assembled in order:

1. **Skill invocation** (if `--skill` is set): `1. Use Skill(/aura:<skill>)\n`
2. **Base prompt** from `--prompt` or `--prompt-file`
3. **Task context**: `Task ID: <id>` (single) or a bulleted list (multiple)

### Role instructions

Instructions are loaded from `skills/<role>/SKILL.md`:

1. First checks `<working-dir>/skills/<role>/SKILL.md`
2. Falls back to `~/skills/<role>/SKILL.md`

The script exits with an error if no instructions file is found at either
location, printing both paths that were checked.

Instructions are injected via `claude --append-system-prompt`, which preserves
the default Claude system prompt (including Task tool access for subagent
spawning).

### Tmux session naming

Format: `<role>--<num>--<hex4>[--<task-id>]`

```
supervisor--1--a7f2
reviewer--1--c3e1--proposal-123
worker--2--d9b4--impl-001
```

Retries up to 3 times on name collision.

### Examples

```bash
# Launch a supervisor to coordinate an epic
aura-parallel --role supervisor -n 1 \
  --prompt "Read ratified plan aura-xyz and decompose into vertical slices"

# Launch an architect with the opus model
aura-parallel --role architect -n 1 --model opus \
  --prompt "Propose a plan for the authentication feature"

# Distribute 3 tasks across 3 workers
aura-parallel --role worker -n 3 \
  --task-id impl-001 --task-id impl-002 --task-id impl-003 \
  --prompt "Implement your assigned vertical slice"

# Launch reviewers with a skill invocation
aura-parallel --role reviewer -n 3 \
  --skill aura:reviewer:review-plan \
  --prompt "Review proposal-123 for end-user alignment"

# Dry run: inspect generated commands and prompts
aura-parallel --role supervisor -n 1 \
  --prompt "Coordinate implementation" --dry-run

# Launch and immediately attach to the session
aura-parallel --role supervisor -n 1 \
  --prompt "Start supervision" --attach

# Custom working directory
aura-parallel --role supervisor -n 1 \
  --working-dir /path/to/project \
  --prompt "Supervise implementation in this repo"
```

### Security

The `dangerously-skip-permissions` mode is explicitly forbidden. The script
rejects any `--permission-mode` value containing "dangerously" or "skip" and
exits with a security error.

### Signal handling

`Ctrl-C` (SIGINT) sets a flag that completes the current session launch and
skips all remaining sessions, rather than terminating immediately. This prevents
half-initialized tmux sessions.

---

## Beads Integration

Both tools integrate with [Beads](https://github.com/dayvidpham/beads) for task
tracking and inter-agent coordination.

### How aura-swarm uses Beads

`aura-swarm start` queries the epic's dependency graph via `bd show <id> --json`
to:

- **Discover tasks** &mdash; walks `dependencies` (blockers) and `dependents`
  (downstream) two levels deep
- **Find the URD** &mdash; searches for tasks labeled `aura:user:reqs` in the
  dependency chain
- **Build context** &mdash; formats task details into a markdown table embedded
  in the agent's prompt

The generated prompt includes `bd show <id>` commands for each discovered task,
so the launched agent can retrieve full details at runtime.

### Inter-agent coordination patterns

Agents coordinate exclusively through Beads &mdash; there is no dedicated
messaging API:

```bash
# Assignment
bd update <task-id> --assignee=<worker>

# Status updates
bd update <task-id> --status=in_progress
bd update <task-id> --notes="Blocked on missing type definition"

# Comments (visible to all agents reading the task)
bd comments add <task-id> "Layer 1 complete, proceeding to Layer 2"
bd comments add <task-id> "VOTE: ACCEPT - End-user alignment verified"

# Completion
bd close <task-id>

# Dependency chaining
bd dep add <parent-id> --blocked-by <child-id>
```

### Dependency direction

The `--blocked-by` target is always what must finish **first**. Work flows
bottom-up; closure flows top-down:

```
REQUEST                    ← stays open longest
  └── blocked by URE
        └── blocked by PROPOSAL
              └── blocked by IMPL_PLAN
                    └── blocked by SLICE   ← leaf work, closes first
```

```bash
# Correct: REQUEST stays open until URE finishes
bd dep add request-id --blocked-by ure-id

# Wrong: inverts the relationship
bd dep add ure-id --blocked-by request-id
```

---

## Choosing the Right Tool

| Scenario                                | Tool                       | Why                                                |
|-----------------------------------------|----------------------------|----------------------------------------------------|
| Epic with multiple slices               | `aura-swarm start`         | Needs isolated worktree + automatic task discovery  |
| New supervisor/architect for planning    | `aura-parallel`            | Long-running, needs its own tmux session            |
| Plan review (3 reviewers)               | `general-purpose` subagents | Short-lived, results collected in-session           |
| Code review (3 reviewers)               | `general-purpose` subagents | Short-lived, results collected in-session           |
| Ad-hoc research or exploration          | Task tool (Explore agent)  | Quick, no orchestration needed                      |

**Rule of thumb:** if the agent needs its own persistent tmux session and
long-running context, use `aura-swarm` or `aura-parallel`. If the agent is
short-lived and you need to collect its result, use `general-purpose` subagents
(Task tool) or TeamCreate.

### How skills and subagents interact

There are three ways to launch an Aura agent, and each loads role instructions
differently:

| Launch method | Role instruction loading | When to use |
|---------------|--------------------------|-------------|
| `aura-swarm` / `aura-parallel` | Injected automatically via `--append-system-prompt` from `skills/<role>/SKILL.md` | Long-running agents needing tmux sessions |
| Task tool subagent | Agent invokes `/aura:<role>` skill (Skill tool) as its first action | Short-lived in-session agents (reviewers, research) |
| TeamCreate | Same as Task tool &mdash; each teammate invokes the relevant skill | Coordinated multi-agent work within a session |

> **Skills are not subagent types.** `/aura:reviewer`, `/aura:worker`, etc. are
> Skills &mdash; they load role-specific instructions from `skills/*/SKILL.md`
> into the agent's context via the Skill tool. They are NOT valid values for
> the Task tool's `subagent_type` parameter. Always use
> `subagent_type: "general-purpose"` when spawning agents via the Task tool,
> then instruct the agent to invoke the appropriate `/aura:*` skill.

```
# Correct: general-purpose subagent invokes skill to load role
Task(
  subagent_type: "general-purpose",
  prompt: "Invoke /aura:reviewer to load your role. Then review PROPOSAL-1..."
)

# Wrong: "reviewer" is not a valid subagent_type
Task(subagent_type: "reviewer", prompt: "Review PROPOSAL-1...")
```

---

## Protocol Documentation

The `skills/protocol/` directory contains the reusable Aura Protocol specification.
These files are designed to be copied or symlinked into any project using the
protocol.

| File                                                              | Purpose                                              |
|-------------------------------------------------------------------|------------------------------------------------------|
| [`skills/protocol/README.md`](skills/protocol/README.md)          | Protocol entry point and quick-start guide            |
| [`skills/protocol/CLAUDE.md`](skills/protocol/CLAUDE.md)          | Core agent directive: philosophy, constraints, roles  |
| [`skills/protocol/CONSTRAINTS.md`](skills/protocol/CONSTRAINTS.md) | Coding standards, checklists, naming conventions  |
| [`skills/protocol/PROCESS.md`](skills/protocol/PROCESS.md)        | Step-by-step workflow execution (single source of truth) |
| [`skills/protocol/AGENTS.md`](skills/protocol/AGENTS.md)          | Role taxonomy: phases, tools, handoffs per agent      |
| [`skills/protocol/SKILLS.md`](skills/protocol/SKILLS.md)          | Command reference: all `/aura:*` skills by phase      |
| [`skills/protocol/UAT_TEMPLATE.md`](skills/protocol/UAT_TEMPLATE.md) | User Acceptance Test structured output template |
| [`skills/protocol/UAT_EXAMPLE.md`](skills/protocol/UAT_EXAMPLE.md) | Worked UAT example                               |
| [`skills/protocol/schema.xml`](skills/protocol/schema.xml)        | Canonical protocol schema (BCNF): entities, relationships, mappings |

### Workflow phases (v2, 12-phase)

```
Phase 1:  REQUEST (classify → research || explore)
Phase 2:  ELICIT (URE survey) → URD (single source of truth)
Phase 3:  PROPOSAL-N (architect proposes)
Phase 4:  PROPOSAL-N-REVIEW-{axis}-{round} (3 reviewers: A/B/C, ACCEPT/REVISE)
            ↺ revise → PROPOSAL-N+1 if any REVISE
Phase 5:  Plan UAT (user acceptance test)
Phase 6:  Ratification (old proposals marked aura:superseded)
Phase 7:  Handoff (architect → supervisor)
Phase 8:  IMPL_PLAN (supervisor decomposes into vertical slices)
Phase 9:  SLICE-N (parallel workers, each owns one production code path)
            Within each slice: Types (L1) → Tests (L2, fail expected) → Impl (L3, tests pass)
Phase 10: Code review (3 reviewers, severity tree: BLOCKER/IMPORTANT/MINOR)
Phase 11: Implementation UAT
Phase 12: Landing (commit, push, hand off)
```

---

## Skills (Slash Commands)

Each `skills/*/SKILL.md` file defines a **Skill** that can be invoked via the
Skill tool as `/aura:<skill-name>`. When invoked, the skill's SKILL.md content
is loaded into the agent's context, providing role-specific instructions,
workflows, and constraints.

Skills serve two purposes depending on the launch method:

- **CLI tools** (`aura-swarm`, `aura-parallel`): Role instructions are injected
  automatically via `--append-system-prompt`. The `--skill` flag can invoke an
  additional skill at startup.
- **Task tool subagents**: The agent must invoke the skill itself (e.g.
  `/aura:reviewer`) as its first action to load role instructions.

### Roles

These top-level role skills load the full agent persona (workflow, constraints,
voting procedures, etc.):

| Skill                  | Description                                           |
|------------------------|-------------------------------------------------------|
| `/aura:architect`      | Specification writer and implementation designer      |
| `/aura:supervisor`     | Task coordinator, spawns workers, manages execution   |
| `/aura:worker`         | Vertical slice implementer (full production code path)|
| `/aura:reviewer`       | End-user alignment reviewer for plans and code        |
| `/aura:epoch`          | Master orchestrator for full 12-phase workflow        |

### Architect sub-skills

| Skill                              | Phase | Description                     |
|------------------------------------|-------|---------------------------------|
| `/aura:architect-propose-plan`     | 3     | Create PROPOSAL-N task          |
| `/aura:architect-request-review`   | 4     | Spawn 3 axis-specific reviewers |
| `/aura:architect-ratify`           | 6     | Ratify proposal (label `aura:p6-plan:s6-ratify`) |
| `/aura:architect-handoff`          | 7     | Hand off to supervisor          |

### Supervisor sub-skills

| Skill                              | Phase | Description                      |
|------------------------------------|-------|----------------------------------|
| `/aura:supervisor-plan-tasks`      | 8     | Decompose plan into slices       |
| `/aura:supervisor-spawn-worker`    | 9     | Launch workers for slices        |
| `/aura:supervisor-track-progress`  | 9-10  | Monitor layer completion         |
| `/aura:supervisor-commit`          | 9-10  | Atomic commit per layer          |

### Worker sub-skills

| Skill                    | Description                       |
|--------------------------|-----------------------------------|
| `/aura:worker-implement` | Implement assigned vertical slice |
| `/aura:worker-complete`  | Signal task completion            |
| `/aura:worker-blocked`   | Report blocker to supervisor      |

### Reviewer sub-skills

| Skill                         | Description                          |
|-------------------------------|--------------------------------------|
| `/aura:reviewer-review-plan`  | Evaluate proposal against 6 criteria |
| `/aura:reviewer-review-code`  | Review implementation slices         |
| `/aura:reviewer-comment`      | Leave structured feedback via Beads  |
| `/aura:reviewer-vote`         | Cast ACCEPT or REVISE vote           |

### Cross-role skills

| Skill                | Description                                        |
|----------------------|----------------------------------------------------|
| `/aura:plan`         | Plan coordination across roles                     |
| `/aura:status`       | Project status and monitoring                      |
| `/aura:test`         | Run tests (BDD patterns)                           |
| `/aura:feedback`     | Leave structured feedback                          |
| `/aura:impl-slice`   | Vertical slice assignment and tracking             |
| `/aura:impl-review`  | Code review across all implementation slices       |
| `/aura:user-request` | Capture user feature request (Phase 1)             |
| `/aura:user-elicit`  | User requirements elicitation survey (Phase 2)     |
| `/aura:user-uat`     | User acceptance testing (Phase 5/11)               |

---

## Project Structure

```
aura-plugins/
├── .claude-plugin/            Plugin manifests
│   ├── marketplace.json
│   └── plugin.json
├── bin/                       Operational tooling (add to PATH)
│   ├── aura-parallel          Parallel tmux session launcher
│   └── aura-swarm             Epic-based worktree agent launcher
├── skills/                    Plugin skills (SKILL.md per directory)
│   ├── architect/             Architect orchestrator
│   ├── epoch/                 Master orchestrator
│   ├── protocol/              Reusable protocol documentation
│   │   ├── PROCESS.md         Workflow execution (single source of truth)
│   │   ├── CLAUDE.md          Core agent directive
│   │   ├── CONSTRAINTS.md     Coding standards and checklists
│   │   ├── AGENTS.md          Role taxonomy
│   │   ├── SKILLS.md          Skill reference by phase
│   │   ├── schema.xml         Canonical protocol schema
│   │   └── ...                Templates, examples, migration docs
│   ├── reviewer/              Reviewer orchestrator
│   ├── supervisor/            Supervisor orchestrator
│   ├── worker/                Worker orchestrator
│   └── .../                   35+ role-specific skills
├── flake.nix                  Nix packaging + Home Manager module entry
├── nix/hm-module.nix          Home Manager module implementation
├── pyproject.toml             Python project metadata
├── agents/                    Custom agent definitions
│   └── tester.md              BDD test writer agent
├── AGENTS.md                  Agent orchestration guide
└── README.md
```

## Validation

```bash
# Verify Nix flake evaluates cleanly
nix flake check --no-build 2>&1

# Build both packages
nix build .#aura-parallel --no-link
nix build .#aura-swarm --no-link

# Test CLI help output
nix run .#aura-swarm -- --help
nix run .#aura-parallel -- --help
```

## License

MIT
