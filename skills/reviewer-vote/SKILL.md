# Cast Review Vote

Cast ACCEPT or REVISE vote on a plan or code review.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## When to Use

Review complete, ready to vote.

## Given/When/Then/Should

**Given** review complete **when** voting **then** choose based on end-user alignment criteria **should never** vote without applying all criteria

**Given** vote **when** recording **then** add comment to Beads task with justification **should never** vote without written rationale

**Given** code review **when** voting **then** be aware that findings are tracked via severity tree (BLOCKER/IMPORTANT/MINOR) **should never** duplicate severity findings in vote comment

## Vote Options

| Vote | When |
|------|------|
| ACCEPT | All review criteria satisfied; no BLOCKER items |
| REVISE | BLOCKER issues found; must provide actionable feedback |

Binary only. No intermediate levels.

## Plan Review vs Code Review

- **Plan review (Phase 4, `aura:p4-plan:s4-review`):** ACCEPT/REVISE only. No severity tree.
- **Code review (Phase 10, `aura:p10-impl:s10-review`):** ACCEPT/REVISE vote. Findings tracked via severity tree (3 groups: BLOCKER, IMPORTANT, MINOR created per round).

## Consensus

**All 3 reviewers must vote ACCEPT** for plan to be ratified or code to be approved.

## Adding Vote to Beads

```bash
# If accepting:
bd comments add <task-id> "VOTE: ACCEPT - End-user impact clear. MVP scope appropriate. Checklist items verifiable."

# If requesting revision:
bd comments add <task-id> "VOTE: REVISE - Missing: what happens if X fails? Suggestion: add error handling to checklist."
```

## Report Vote

Votes are recorded via beads comments (see "Adding Vote to Beads" above). No separate messaging step is needed.
