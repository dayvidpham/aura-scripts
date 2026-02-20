# Worker: Signal Completion

Signal successful completion to supervisor.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

Implementation complete and all checks pass.

## Given/When/Then/Should

**Given** implementation done **when** signaling **then** verify the project's quality gates pass **should never** report done with failing checks

**Given** validation_checklist **when** completing **then** confirm all items satisfied **should never** complete with unchecked items

**Given** completion **when** reporting **then** update Beads task status **should never** omit Beads update

**Given** completion **when** handing off to reviewer **then** create handoff document at `.git/.aura/handoff/<request-task-id>/worker-<N>-to-reviewer.md` **should never** skip handoff for actor transitions

## Steps

1. Run the project's quality gates (type checking + tests) - must pass
2. **Verify production code path via code inspection:**
   - [ ] Tests import production code (not test-only export)
   - [ ] No dual-export anti-pattern
   - [ ] No TODO placeholders in production code
   - [ ] Service wired with real dependencies (not mocks in production)
3. Verify all validation_checklist items satisfied:
   ```bash
   bd show <task-id>  # Review checklist items
   ```
4. Update Beads task:
   ```bash
   bd update <task-id> --status=done
   bd update <task-id> --notes="Implementation complete. Production code verified working."
   ```
5. Create handoff document for reviewer transition

## Handoff Template (Worker → Reviewer)

**Storage:** `.git/.aura/handoff/<request-task-id>/worker-<N>-to-reviewer.md`

```markdown
# Handoff: Worker <N> → Reviewer

## Context
- Request: <request-task-id>
- URD: <urd-task-id>
- Slice: SLICE-<N>
- Task ID: <slice-task-id>

## What Was Implemented
- Production Code Path: <what end users run>
- Files Changed: <list of files>

## Key Decisions
- <decision 1>: <rationale>
- <decision 2>: <rationale>

## Quality Gates
- Type checking: PASS
- Tests: PASS
- Production code inspection: PASS (no TODOs, real deps wired)

## Areas of Concern
- <any areas the reviewer should pay special attention to>
```

## Report Completion

```bash
# Close the task and add completion notes
bd close <task-id>
bd comments add <task-id> "Implementation complete. Quality gates pass. Production code verified."
```
