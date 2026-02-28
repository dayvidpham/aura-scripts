# Agent Instructions

This project is the **Aura Protocol** toolkit — multi-agent orchestration scripts, slash commands, and protocol documentation for Claude-based AI agent teams.

This project uses **bd** (beads) for issue tracking. Run `bd prime` to get started.

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
aura-plugins/
├── bin/                    # Operational tooling (add to PATH)
│   ├── aura-parallel       # Parallel agent launcher for tmux sessions (Python)
│   ├── aura-release        # Version bump, changelog, and git tag (Python)
│   └── aura-swarm          # Epic-based worktree agent launcher (Python)
├── scripts/                # Python packages
│   ├── aura_protocol/      # Protocol engine (see Protocol Engine section below)
│   │   ├── types.py        # Typed enums, frozen dataclass specs, canonical dicts
│   │   ├── state_machine.py # 12-phase EpochStateMachine
│   │   ├── constraints.py  # RuntimeConstraintChecker — all 26 C-* validators
│   │   ├── context_injection.py # Role/phase context builders + prompt renderers
│   │   ├── schema_parser.py # XML → Python spec parser (SchemaParseError)
│   │   ├── gen_schema.py   # Python → schema.xml code generator (diff mode)
│   │   ├── gen_skills.py   # SKILL.md header generator (Jinja2, diff mode)
│   │   ├── gen_types.py    # Bootstrap codegen for types.py
│   │   ├── audit_activities.py # Temporal search attribute definitions
│   │   ├── workflow.py     # Temporal workflow wrapper
│   │   ├── interfaces.py   # Protocol interfaces + A2A content types
│   │   └── __init__.py     # Public API re-exports
│   └── validate_schema.py  # 3-layer schema.xml validation
├── tests/                  # Test suite (1370+ tests)
│   ├── test_aura_types.py
│   ├── test_schema_types_sync.py
│   ├── test_state_machine.py
│   ├── test_constraints.py
│   ├── test_workflow.py
│   ├── test_interfaces.py
│   ├── test_validate_schema.py
│   └── conftest.py
├── flake.nix               # Nix flake packaging + Home Manager module
├── nix/hm-module.nix       # Home Manager module for config sync
├── skills/                 # Plugin skills (SKILL.md per directory)
│   ├── protocol/           # Reusable Aura Protocol documentation
│   │   ├── README.md       # Protocol entry point and quick-start guide
│   │   ├── CLAUDE.md       # Core agent directive (philosophy, constraints, roles)
│   │   ├── CONSTRAINTS.md  # Coding standards, checklists, naming conventions
│   │   ├── PROCESS.md      # Step-by-step workflow (single source of truth)
│   │   ├── AGENTS.md       # Role taxonomy (phases, tools, handoffs per agent)
│   │   ├── SKILLS.md       # Command reference (all /aura:* skills by phase)
│   │   └── schema.xml      # Canonical protocol schema (BCNF)
│   └── */SKILL.md          # Role-specific agent instructions (38 skills)
├── agents/                 # Custom agent definitions (~/.claude/agents/)
│   └── tester.md           # BDD test writer agent
└── AGENTS.md               # This file
```

## Protocol Engine (`scripts/aura_protocol/`)

The `aura_protocol` Python package is the programmatic backbone of the Aura
protocol. It provides machine-executable enforcement of workflow state
transitions, constraint validation, and Temporal-backed durable execution.

### Version Roadmap

| Version | Scope | Status |
|---------|-------|--------|
| v1 (v0.4.3) | State machine + Temporal workflow + 26 C-* constraint validators | Done |
| v2 | Schema-driven code generation + runtime context injection (Python as SoT) | Done |
| v3 | Full Temporal workflow engine (phases as workflows, handoffs as signals) | Future |

### Modules

| Module | Purpose |
|--------|---------|
| `types.py` | All enums (StrEnum), frozen dataclasses, canonical dicts. Source of truth for protocol type definitions. Includes `StepSlug`, `SkillRef`, 26 `ConstraintContext` entries. |
| `state_machine.py` | `EpochStateMachine` — pure Python 12-phase lifecycle with consensus gates, blocker gates, and review vote tracking. No Temporal dependency. |
| `constraints.py` | `RuntimeConstraintChecker` — all 26 C-* constraint validators from schema.xml. DI-friendly (accepts optional specs dicts). Returns `list[ConstraintViolation]`. |
| `context_injection.py` | `get_role_context()`, `get_phase_context()` — build typed context objects from canonical dicts. `render_role_context_as_text()` / `render_role_context_as_xml()` for prompt injection. |
| `schema_parser.py` | Parses `schema.xml` → Python spec objects. Raises `SchemaParseError` on missing `<instruction>` elements. |
| `gen_schema.py` | Generates `skills/protocol/schema.xml` from `types.py`. Prints unified diff before writing. Run with `PYTHONPATH=scripts uv run python -m aura_protocol.gen_schema`. |
| `gen_skills.py` | Generates SKILL.md headers for role skills from `skill_header.j2` template. Prints unified diff before writing. Run with `PYTHONPATH=scripts uv run python -m aura_protocol.gen_skills`. |
| `gen_types.py` | Bootstrap codegen for `types.py` (one-time use). |
| `audit_activities.py` | Temporal search attribute definitions for forensic workflow lookup. |
| `workflow.py` | Temporal workflow wrapping `EpochStateMachine`. Signals for phase advances and votes, queries for state inspection, search attributes for forensic lookup. |
| `interfaces.py` | `typing.Protocol` interfaces for cross-project integration: `ConstraintValidatorInterface`, `TranscriptRecorder`, `SecurityGate`, `AuditTrail`. Plus A2A content types and `ModelId`. |

### Running Tests

```bash
# Full suite (1370+ tests)
uv run pytest tests/ --tb=short -q

# With Temporal sandbox tests (requires Temporal test server)
TEMPORAL_REQUIRED=1 uv run pytest tests/ --tb=short -q

# Schema validation
PYTHONPATH=scripts uv run python scripts/validate_schema.py skills/protocol/schema.xml
```

### Regenerating Skill Headers

Role SKILL.md files (`supervisor`, `worker`, `reviewer`, `architect`) have a
generated section between `<!-- BEGIN GENERATED FROM aura schema -->` and
`<!-- END GENERATED FROM aura schema -->` markers. After editing `types.py`,
`context_injection.py`, `schema.xml`, or `skill_header.j2`, regenerate with:

```bash
# Regenerate all role SKILL.md headers (shows diff, writes in-place)
PYTHONPATH=scripts uv run python -m aura_protocol.gen_skills

# Also regenerate schema.xml from types.py if types changed
PYTHONPATH=scripts uv run python -m aura_protocol.gen_schema
```

The generators print a unified diff before writing. If there are no changes,
they print nothing. The hand-authored body below the END marker is preserved.

## Validation

Before committing changes to this project:

```bash
# Ensure Nix flake evaluates cleanly
nix flake check --no-build 2>&1

# Build the packages (aura-parallel, aura-swarm)
nix build .#aura-parallel --no-link
nix build .#aura-swarm --no-link

# Test CLI help output
nix run .#aura-swarm -- --help
nix run .#aura-parallel -- --help

# Check version consistency across manifests
bin/aura-release --check
```

## Releasing

Use `bin/aura-release` to create releases. It bumps the version across all
manifest files (pyproject.toml, plugin.json, marketplace.json), auto-generates
CHANGELOG.md, commits, and creates an annotated git tag.

```bash
# Check version consistency
bin/aura-release --check

# Preview a release
bin/aura-release patch --dry-run

# Create a patch release (fix drift if needed)
bin/aura-release patch --sync

# Push after release
git push && git push --tags
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

### aura-parallel — Supervisor/Architect launches

Launches parallel Claude agents in tmux sessions with role-based instructions.

**Use for:** Spawning a separate supervisor or architect to plan and coordinate a new epic. These are long-running agents that need their own tmux session and persistent context.

```bash
# Launch supervisor to coordinate an epic
aura-parallel --role supervisor -n 1 --prompt "Coordinate implementation of..."

# Launch architect to propose a plan
aura-parallel --role architect -n 1 --prompt "Propose plan for..."

# Dry run (show commands without executing)
aura-parallel --role supervisor -n 1 --prompt "..." --dry-run
```

**DO NOT use for reviewer rounds.** Reviewers are short-lived and should use subagents or TeamCreate instead.

### Subagents / TeamCreate — Reviews and short-lived agents

**Use for:** Plan reviews, code reviews, and any short-lived parallel agent work.

Reviewers are spawned as `general-purpose` subagents (via the Task tool, `subagent_type: "general-purpose"`) and instructed to invoke the relevant `/aura:*` skill to load their role instructions. This keeps them in-session, avoids tmux session overhead, and allows direct result collection.

> **Skills are not subagent types.** `/aura:reviewer`, `/aura:worker`, etc. are
> Skills invoked via the Skill tool — they load role-specific instructions from
> `skills/*/SKILL.md` into the agent's context. They are NOT values for the Task
> tool's `subagent_type` parameter. Always use `subagent_type: "general-purpose"`
> when spawning agents via the Task tool, then have the agent invoke the
> appropriate `/aura:*` skill as its first action.

```
# Correct: general-purpose subagent + skill invocation
Task(
  subagent_type: "general-purpose",
  prompt: "First invoke /aura:reviewer to load your role. Then review PROPOSAL-1..."
)

# Wrong: "reviewer" is not a valid subagent_type
Task(subagent_type: "reviewer", prompt: "Review PROPOSAL-1...")
```

### When to use which

| Scenario | Tool | Why |
|----------|------|-----|
| Epic implementation with worktree isolation | `aura-swarm` | Needs isolated branch + worktree |
| New supervisor/architect for epic planning | `aura-parallel` | Long-running, needs own tmux session |
| Plan review (3 reviewers) | `general-purpose` subagents | Short-lived, invoke `/aura:reviewer` skill |
| Code review (3 reviewers) | `general-purpose` subagents | Short-lived, invoke `/aura:reviewer` skill |
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

### 4. Actionable errors and messages

- All errors, exceptions, and user-facing messages must be actionable
- Each error must describe: (1) what went wrong, (2) why it happened, (3) where it failed (file location, module, or function), (4) when it failed (step, operation, or timestamp), (5) what it means for the caller, and (6) how to fix it
- Never raise generic or opaque errors (e.g., "invalid input", "operation failed") without guidance toward resolution
- Error messages are part of the public API — treat them with the same care as function signatures

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

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
