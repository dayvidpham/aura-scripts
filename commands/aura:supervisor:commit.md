# Supervisor: Commit

Create atomic commit when layer complete.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-12-landing)** <- Phase 12

## When to Use

All workers for a layer have completed successfully.

## Given/When/Then/Should

**Given** all files ready **when** committing **then** run checks first **should never** commit without quality gates passing

**Given** commit **when** formatting **then** reference Beads task IDs **should never** use vague messages

## Steps

1. Run quality gates (type checking + tests) - must pass
2. Stage changed files
3. Create commit with format below
4. Close Beads tasks
5. Update IMPL_PLAN progress

## Commit Format

```
feat|fix|docs|refactor(scope): Description

Files: file1.ts, file2.ts
Task: aura-xxx, aura-yyy
Ratified-Plan: <ratified-plan-id>

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Close Beads Tasks

```bash
bd close aura-xxx aura-yyy --reason="Committed in <commit-hash>"
```

## Update IMPL_PLAN

```bash
bd update <impl-plan-id> --notes="SLICE-N complete: aura-xxx, aura-yyy"
```

## Commands

```bash
git add <files>
git agent-commit -m "..."
```
