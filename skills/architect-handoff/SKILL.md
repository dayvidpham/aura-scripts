# Architect: Handoff to Supervisor

Pass ratified PROPOSAL-N to supervisor for implementation.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-7-handoff)**

## When to Use

Plan ratified and user has approved proceeding with implementation.

## Given/When/Then/Should

**Given** ratified PROPOSAL-N task **when** handing off **then** create handoff document and HANDOFF task **should never** hand off without linking to ratified proposal

**Given** handoff **when** spawning supervisor **then** use `aura-parallel --role supervisor` or `aura-swarm start --epic <id>` **should never** spawn supervisor as Task tool subagent

**Given** implementation planning **when** handing off **then** let supervisor create vertical slice tasks **should never** create implementation tasks as architect

## Handoff Template

Storage: `.git/.aura/handoff/{request-task-id}/architect-to-supervisor.md`

```markdown
# Handoff: Architect → Supervisor

## References
- REQUEST: <request-task-id>
- URD: <urd-task-id> (read with `bd show <urd-id>`)
- RATIFIED PROPOSAL: <ratified-proposal-id> (read with `bd show <proposal-id>`)

## Summary
<1-2 sentence summary of what needs to be implemented>

## Key Files
<list main files to be created/modified from the ratified plan>

## Validation Checklist
<validation checklist from the ratified proposal>

## BDD Acceptance Criteria
<Given/When/Then criteria from the ratified plan>

## Implementation Notes
<any special considerations, known risks, or constraints>
```

## Steps

1. Create the handoff document:
   ```bash
   mkdir -p .git/.aura/handoff/<request-task-id>/
   # Write architect-to-supervisor.md with the template above
   ```

2. Create HANDOFF Beads task:
   ```bash
   bd create --type=task --priority=2 \
     --title="HANDOFF: Architect → Supervisor for REQUEST" \
     --description="---
   references:
     request: <request-task-id>
     urd: <urd-task-id>
     proposal: <ratified-proposal-id>
   ---
   Handoff from architect to supervisor. See handoff document at
   .git/.aura/handoff/<request-task-id>/architect-to-supervisor.md" \
     --add-label "aura:p7-plan:s7-handoff"

   bd dep add <request-id> --blocked-by <handoff-id>
   ```

3. Launch supervisor:
   ```bash
   # Using aura-parallel (for long-running supervisor in tmux session)
   aura-parallel --role supervisor -n 1 --prompt "..."

   # Or using aura-swarm (for epic-based worktree workflow)
   aura-swarm start --epic <id>
   ```

4. Monitor supervisor progress:
   ```bash
   # Check beads status
   bd list --status=in_progress

   # Or attach to supervisor session (if using aura-parallel)
   tmux attach -t supervisor--1-<hex4>
   ```

## Example Prompt

```
Implement the ratified plan for <feature name>.

## Context
- REQUEST: <request-task-id>
- URD: <urd-task-id> (read with `bd show <urd-id>` for user requirements)
- RATIFIED PROPOSAL: <ratified-proposal-id>
- HANDOFF: <handoff-task-id>
- Handoff document: .git/.aura/handoff/<request-task-id>/architect-to-supervisor.md

## Summary
<1-2 sentence summary of what needs to be implemented>

## Key Files
<list main files to be created/modified from the ratified plan>

## Acceptance Criteria
<Given/When/Then criteria from the ratified plan>

Read the ratified plan with `bd show <ratified-proposal-id>` and the URD with `bd show <urd-id>`.
```

Pass the prompt to the script:

```bash
aura-parallel --role supervisor -n 1 --prompt "$(cat <<'EOF'
Implement the ratified plan for User Authentication.

## Context
- REQUEST: project-abc
- URD: project-xyz
- RATIFIED PROPOSAL: project-prop1
- Handoff document: .git/.aura/handoff/project-abc/architect-to-supervisor.md

## Summary
Add JWT-based authentication with login/logout endpoints and middleware.

## Key Files
- pkg/auth/jwt.go
- pkg/auth/middleware.go
- cmd/api/auth.go

## Acceptance Criteria
Given a valid JWT token when accessing protected routes then allow access
Given an expired token when accessing protected routes then return 401

Read the ratified plan with `bd show project-prop1` and URD with `bd show project-xyz`.
EOF
)"
```

## Script Options

```bash
aura-parallel --role supervisor -n 1 --prompt "..."             # Launch supervisor
aura-parallel --role supervisor -n 1 --prompt "..." --dry-run   # Preview without launching
aura-parallel --role supervisor -n 1 --prompt-file prompt.md    # Read prompt from file
```

## IMPORTANT

- **DO NOT** spawn supervisor as a Task tool subagent - use `aura-parallel` or `aura-swarm`
- **DO NOT** create implementation tasks yourself - the supervisor creates vertical slice tasks
- **DO NOT** implement the plan yourself - your role is handoff and monitoring
- The supervisor reads the ratified plan and determines vertical slice structure
- Architect monitors for blockers or escalations

## Follow-up Lifecycle (h1 Reuse)

This handoff (h1: Architect → Supervisor) also occurs after FOLLOWUP_PROPOSAL is ratified. In follow-up context:

- **Storage:** `.git/.aura/handoff/{followup-epic-id}/architect-to-supervisor.md`
- **References:** Include both original URD and FOLLOWUP_URD task IDs
- **Context:** Summary of FOLLOWUP_PROPOSAL ratification and outstanding leaf tasks from original review
- **Next step:** Supervisor creates FOLLOWUP_IMPL_PLAN and FOLLOWUP_SLICE-N tasks, adopting original IMPORTANT/MINOR leaf tasks as dual-parent children
