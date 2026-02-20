# Leave Feedback

Provide structured feedback on plan or code review.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## Format

```markdown
## Feedback: {task-id}

**Reviewer:** {your-role}
**Date:** {timestamp}
**Vote:** {ACCEPT | REVISE}

### Comments

#### {BLOCKER | IMPORTANT | MINOR}: {Title}
**Location:** {file:line or proposal section}
**Issue:** {description}
**Suggestion:** {how to fix}

### Summary
{Overall assessment}
```

## Vote Options

| Vote | When |
|------|------|
| ACCEPT | All review criteria satisfied; no BLOCKER items |
| REVISE | BLOCKER issues found; must provide actionable feedback |

Binary only. No intermediate levels.

## Severity Vocabulary

| Severity | When to Use | Blocks? |
|----------|-------------|---------|
| BLOCKER | Security, type errors, test failures, broken production code paths | Yes |
| IMPORTANT | Performance, missing validation, architectural concerns | No (follow-up epic) |
| MINOR | Style, optional optimizations, naming improvements | No (follow-up epic) |

## Steps

1. Ask what to review (proposal, code changes, slice)
2. Read content thoroughly
3. Read the URD for requirements context: `bd show <urd-id>`
4. Apply relevant review criteria (see `CONSTRAINTS.md`)
5. Format feedback using the template
6. Add feedback via Beads: `bd comments add <task-id> "VOTE: ..."`
7. Be specific and actionable
