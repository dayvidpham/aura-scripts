# Worker: Signal Completion

Signal successful completion to supervisor.

## When to Use

Implementation complete and all checks pass.

## Given/When/Then/Should

**Given** implementation done **when** signaling **then** verify the project's quality gates pass (e.g., `go test -race ./...` or `npm run test`) **should never** report done with failing checks

**Given** validation_checklist **when** completing **then** confirm all items satisfied **should never** complete with unchecked items

**Given** completion **when** reporting **then** update Beads task status **should never** omit Beads update

## Steps

1. Run the project's quality gates (e.g., `go test -race ./...`, `npm run test`, etc.) - must pass
2. Verify type checking passes (if applicable)
3. **Verify production code path via code inspection:**
   - [ ] Tests import production code (not test-only export)
   - [ ] No dual-export anti-pattern
   - [ ] No TODO placeholders in production code
   - [ ] Service wired with real dependencies (not mocks in production)
4. Verify all validation_checklist items satisfied:
   ```bash
   bd show <task-id>  # Review checklist items
   ```
5. Update Beads task:
   ```bash
   bd update <task-id> --status=done
   bd update <task-id> --notes="Implementation complete. Production code verified working."
   ```
6. Send completion message to supervisor

## Report Completion

```bash
# Close the task and add completion notes
bd close <task-id>
bd comments add <task-id> "Implementation complete. Quality gates pass. Production code verified."
```
