# Leave Structured Review Comment

Leave structured feedback via Beads comments.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## When to Use

Documenting review findings for the permanent record.

## Given/When/Then/Should

**Given** findings **when** documenting **then** use structured format with severity levels **should never** leave unstructured feedback

**Given** comment **when** creating **then** add via `bd comments add` **should never** create standalone files for review comments

## Steps

1. Identify the task to comment on (`bd show <task-id>`)
2. Categorize findings by severity
3. Add structured comment via Beads

## Comment via Beads

```bash
# Plan review comment (no severity tree)
bd comments add <proposal-id> "VOTE: ACCEPT - End-user alignment confirmed. MVP scope achievable."

# Code review comment (with severity references)
bd comments add <review-id> "VOTE: REVISE - 1 BLOCKER found (see severity tree). Suggestion: fix type error in auth middleware."
```

## Format

```markdown
VOTE: {ACCEPT | REVISE}

## Findings

### BLOCKER Issues
{list or "None"}

### IMPORTANT Issues
{list or "None"}

### MINOR Issues
{list or "None"}

## Conclusion
{assessment and next steps}
```

## Severity Vocabulary

| Severity | When to Use | Blocks? |
|----------|-------------|---------|
| BLOCKER | Security, type errors, test failures, broken production code paths | Yes (code review only) |
| IMPORTANT | Performance, missing validation, architectural concerns | No (follow-up epic) |
| MINOR | Style, optional optimizations, naming improvements | No (follow-up epic) |

## Plan Review vs Code Review

- **Plan review (Phase 4, `aura:p4-plan:s4-review`):** ACCEPT/REVISE only. No severity tree. Findings are described inline in the vote comment.
- **Code review (Phase 10, `aura:p10-impl:s10-review`):** ACCEPT/REVISE vote + full severity tree with EAGER creation (3 groups per round). Findings are tracked as child tasks of severity groups.
