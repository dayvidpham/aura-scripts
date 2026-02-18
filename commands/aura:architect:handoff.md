# Architect: Handoff to Supervisor

Pass RATIFIED_PLAN to supervisor for implementation.

## When to Use

Plan ratified and user has approved proceeding with implementation.

## Given/When/Then/Should

**Given** RATIFIED_PLAN task **when** handing off **then** create IMPLEMENTATION_PLAN task **should never** hand off without linking to ratified plan

**Given** handoff **when** spawning supervisor **then** use `launch-parallel.py --role supervisor` from aura-scripts **should never** spawn supervisor as Task tool subagent

**Given** implementation planning **when** handing off **then** let supervisor create layer-cake tasks **should never** create implementation tasks as architect

## Steps

1. Create IMPLEMENTATION_PLAN placeholder task:
   ```bash
   bd create --type=epic \
     --labels="aura:impl-plan" \
     --title="Implementation: <feature name>" \
     --description="Placeholder - supervisor will fill in layer structure and spawn workers"

   bd dep add <impl-plan-id> <ratified-plan-id>
   ```

   **Note:** This is intentionally minimal. The supervisor reads the RATIFIED_PLAN and fills in the IMPLEMENTATION_PLAN with the actual layer-cake structure and task breakdown.

2. Launch supervisor using the Python script:
   ```bash
   # Dry run first to verify prompt
   ~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "..." --dry-run

   # Launch in tmux session
   ~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "..."
   ```

   The script will:
   - Load supervisor instructions from `.claude/commands/aura:supervisor.md`
   - Launch Claude in a tmux session with `--append-system-prompt` (preserves Task tool for workers)

3. Monitor supervisor progress:
   ```bash
   # Attach to supervisor session (format: supervisor--1--<hex4>)
   tmux attach -t supervisor--1-<hex4>

   # Or check beads status
   bd list --status=in_progress
   ```

## Example Prompt

```
Implement the ratified plan for <feature name>.

## Context
- RATIFIED_PLAN: <ratified-plan-id>
- IMPLEMENTATION_PLAN: <impl-plan-id>
- Plan file: <path if applicable>

## Summary
<1-2 sentence summary of what needs to be implemented>

## Key Files
<list main files to be created/modified from the ratified plan>

## Acceptance Criteria
<Given/When/Then criteria from the ratified plan>

Read the ratified plan with `bd show <ratified-plan-id>` to understand the full layer structure and validation checklist.
```

Pass the prompt to the script:

```bash
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "$(cat <<'EOF'
Implement the ratified plan for User Authentication.

## Context
- RATIFIED_PLAN: david-agent-data-leverage.git-abc
- IMPLEMENTATION_PLAN: david-agent-data-leverage.git-xyz
- Plan file: /home/user/.claude/plans/auth-feature.md

## Summary
Add JWT-based authentication with login/logout endpoints and middleware.

## Key Files
- src/auth/jwt.ts
- src/auth/middleware.ts
- src/routes/auth.ts
- tests/unit/auth.test.ts

## Acceptance Criteria
Given a valid JWT token when accessing protected routes then allow access
Given an expired token when accessing protected routes then return 401

Read the ratified plan with `bd show david-agent-data-leverage.git-abc` to understand the full layer structure and validation checklist.
EOF
)"
```

## Script Options

```bash
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "..."             # Launch supervisor
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role reviewer -n 3 --prompt "..."               # Launch 3 reviewers
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role worker -n 2 --task-id id1 --task-id id2    # Workers with tasks
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "..." --dry-run   # Preview without launching
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt-file prompt.md    # Read prompt from file
```

## IMPORTANT

- **DO NOT** spawn supervisor as a Task tool subagent - use `~/codebases/dayvidpham/aura-scripts/launch-parallel.py`
- **DO NOT** create implementation tasks yourself - the supervisor creates layer-cake tasks
- **DO NOT** implement the plan yourself - your role is handoff and monitoring
- The supervisor reads the ratified plan and determines layer structure
- Architect monitors for blockers or escalations
