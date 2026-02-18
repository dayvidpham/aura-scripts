# Run Tests

Run project test suite.

## Commands

| Command | Description |
|---------|-------------|
| `npm run typecheck` | Type checking (run first) |
| `npm run test:unit` | Unit tests (fast) |
| `npm run test:integration` | Integration tests |
| `npm run test:all` | All tests |
| `npm run test:coverage` | With coverage |

## Steps

1. Run `npm run typecheck` first
2. Run appropriate test command
3. If failures, analyze and suggest fixes
4. Report: passed/failed/skipped counts

## On Failure

- List each failing test with error
- Identify root cause
- Suggest specific fixes
- Do NOT auto-fix without approval
