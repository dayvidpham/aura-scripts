# Cast Review Vote

Cast ACCEPT or REVISE vote on a plan.

## When to Use

Review complete, ready to vote.

## Given/When/Then/Should

**Given** review complete **when** voting **then** choose based on end-user alignment criteria **should never** vote without applying all criteria

**Given** vote **when** recording **then** add comment to Beads task with justification **should never** vote without written rationale

## Vote Options

| Vote | When |
|------|------|
| ACCEPT | Plan addresses end-user needs, checklist complete, no gaps |
| REVISE | Specific issues need addressing (must provide actionable feedback) |

## Consensus

**All 3 reviewers must vote ACCEPT** for plan to be ratified.

## Adding Vote to Beads

```bash
# If accepting:
bd comments add <task-id> "VOTE: ACCEPT - End-user impact clear. MVP scope appropriate. Checklist items verifiable."

# If requesting revision:
bd comments add <task-id> "VOTE: REVISE - Missing: what happens if X fails? Suggestion: add error handling to checklist."
```

## Report Vote

Votes are recorded via beads comments (see "Adding Vote to Beads" above). No separate messaging step is needed.
