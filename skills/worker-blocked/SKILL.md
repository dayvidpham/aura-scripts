# Worker: Handle Blockers

Report blocker preventing progress.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

Cannot proceed due to missing dependency, unclear requirement, or need changes in another file.

## Given/When/Then/Should

**Given** a blocker **when** reporting **then** update Beads task status and document details **should never** guess or work around

**Given** blocker sent **when** waiting **then** wait for supervisor response **should never** continue with incomplete info

## Steps

1. Identify what's blocking (missing type, unclear requirement, file dependency)

2. Update Beads task:
   ```bash
   bd update <task-id> --status=blocked
   bd update <task-id> --notes="Blocked: <reason>. Missing: <dependency or clarification needed>"
   ```

3. Document the blocker in the task:
   ```bash
   bd comments add <task-id> "BLOCKED: <reason>. Need: <dependency or clarification>"
   ```

4. Wait for supervisor or dependency resolution — check with `bd show <task-id>`

## Common Blockers

- Missing type definition from another file
- Unclear requirement in acceptance_criteria
- Need interface defined in dependent file
- Conflicting constraints in validation_checklist
