# Beads Workflow Context

> **Context Recovery**: Run `bd prime` after compaction, clear, or new session
> Hooks auto-call this in Claude Code when .beads/ detected

# 🚨 SESSION CLOSE PROTOCOL 🚨

**CRITICAL**: Before saying "done" or "complete", you MUST run this checklist:

```
[ ] 1. git status              (check what changed)
[ ] 2. git add <files>         (stage code changes)
[ ] 4. git agent-commit -m "..."     (commit code changes)
```

**Note:** This is a feature branch. Code is merged to your feature branch. Do NOT merge into `main` or `develop` without user permission.

## Core Rules
- **Default**: Use beads for ALL task tracking (`bd create`, `bd ready`, `bd close`)
- **Prohibited**: Do NOT use TodoWrite, TaskCreate, or markdown files for task tracking
- **Workflow**: Create beads issue BEFORE writing code, mark in_progress when starting
- Persistence you don't need beats lost context
- Session management: check `bd ready` for available work

## Essential Commands

### Finding Work
- `bd ready` - Show issues ready to work (no blockers)
- `bd list --status=open` - All open issues
- `bd list --status=in_progress` - Your active work
- `bd show <id>` - Detailed issue view with dependencies

### Creating & Updating
- `bd create --title="Summary of this issue" --description="Why this issue exists and what needs to be done" --type=task|bug|feature --priority=2` - New issue
  - Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog). NOT "high"/"medium"/"low"
- `bd update <id> --status=in_progress` - Claim work
- `bd update <id> --assignee=username` - Assign to someone
- `bd update <id> --title/--description/--notes/--design` - Update fields inline
- `bd close <id>` - Mark complete
- `bd close <id1> <id2> ...` - Close multiple issues at once (more efficient)
- `bd close <id> --reason="explanation"` - Close with reason
- **Tip**: When creating multiple issues/tasks/epics, use parallel subagents for efficiency
- **WARNING**: Do NOT use `bd edit` - it opens $EDITOR (vim/nano) which blocks agents

### Dependencies & Blocking
- `bd dep add <issue-id> --blocked-by <blocker-issue-id>` - Add dependency (<issue-id> is blocked by <blocker-issue-id>)
- `bd dep tree --direction=both --show-all-paths <issue-id>` - Show the tree of issues that block this one, and the issues that depend on this one
- `bd blocked` - Show all blocked issues
- `bd show <id>` - See what's blocking/blocked by this issue

The canonical dependency chain flows top-down (parents blocked by children):

```
REQUEST
  └── blocked by ELICIT
        └── blocked by PROPOSAL-1
              └── blocked by IMPL_PLAN
                    ├── blocked by SLICE-1
                    │     ├── blocked by leaf-task-a
                    │     └── blocked by leaf-task-b
                    └── blocked by SLICE-2

URD ← referenced via frontmatter in (REQUEST, ELICIT, PROPOSAL, IMPL_PLAN, UAT)
```

### Sync & Collaboration
- `bd search <query>` - Search issues by keyword

### Project Health
- `bd stats` - Project statistics (open/closed/blocked counts)
- `bd doctor` - Check for issues (sync problems, missing hooks)

## Common Workflows

**Starting work:**
```bash
bd ready           # Find available work
bd show <id>       # Review issue details
bd update <id> --status=in_progress  # Claim it
```

**Completing work:**
```bash
bd close <id1> <id2> ...    # NOT performed by workers; performed by the supervisor
git add . && git agent-commit -m "..."  # Commit your changes
# Merge to main when ready (local merge, not push)
```

**Creating dependent work:**
```bash
# Run bd create commands in parallel (use subagents for many items)
bd create --title="Implement feature X" --labels="<label-1>,<label-2>" --description="Why this issue exists and what needs to be done" --type=feature
bd create --title="Write tests for X" --labels="<label-a>,<label-b>" --description="Why this issue exists and what needs to be done" --type=task
bd dep add beads-yyy --blocked-by beads-xxx  # beads-yyy blocked by beads-xxx
```

