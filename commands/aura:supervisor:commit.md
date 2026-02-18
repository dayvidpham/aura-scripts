# Supervisor: Commit

Create atomic commit when layer complete.

## When to Use

All workers for a layer have completed successfully.

## Given/When/Then/Should

**Given** all files ready **when** committing **then** run checks first **should never** commit without `typecheck` and `test:unit` passing

**Given** commit **when** formatting **then** reference Beads task IDs **should never** use vague messages

## Steps

1. Run `npm run typecheck` - must pass
2. Run `npm run test:unit` - must pass
3. Stage changed files
4. Create commit with format below
5. Close Beads tasks
6. Update IMPLEMENTATION_PLAN progress

## Commit Format

```
feat|fix|docs|refactor(scope): Description

Files: file1.ts, file2.ts
Task: impl-xxx-001, impl-xxx-002
Ratified-Plan: <ratified-plan-id>

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Close Beads Tasks

```bash
bd close impl-xxx-001 impl-xxx-002 --reason="Committed in <commit-hash>"
```

## Update IMPLEMENTATION_PLAN

```bash
bd update <impl-plan-id> --notes="Layer N complete: impl-xxx-001, impl-xxx-002"
```

## Commands

```bash
git add <files>
git agent-commit -m "..."
```
