# Architect: Request Review

Send PROPOSAL-N task to reviewers for feedback.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## When to Use

Plan draft complete, ready for review.

## Given/When/Then/Should

**Given** plan ready **when** requesting review **then** spawn 3 axis-specific reviewers (A=Correctness, B=Test quality, C=Elegance) **should never** spawn reviewers without axis assignment

**Given** reviewers **when** assigning **then** provide Beads task ID and context **should never** expect reviewers to search

## REVIEW Naming

Reviews are named `PROPOSAL-N-REVIEW-{axis}-{round}` where:
- N = proposal number (matches PROPOSAL-N)
- axis = reviewer criteria axis (A, B, or C)
- round = review round number (1, 2, ...)

### Review Axes

| Axis | Focus | Key Questions |
|------|-------|---------------|
| **A** | Correctness (spirit and technicality) | Does it faithfully serve the user? Are technical decisions consistent with rationale? |
| **B** | Test quality | Integration over unit? SUT not mocked? Shared fixtures? Assert outcomes? |
| **C** | Elegance and complexity matching | Right API? Not over/under-engineered? Complexity proportional to problem? |

## Steps

1. Verify PROPOSAL-N task is complete with all sections
2. Spawn three reviewers with the task ID and URD reference:

```
Task(description: "Reviewer A: correctness", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). You are Reviewer A (Correctness). Focus: Does it faithfully serve the user? Are technical decisions consistent with rationale? Create review task titled PROPOSAL-1-REVIEW-A-1...", subagent_type: "reviewer")
Task(description: "Reviewer B: test quality", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). You are Reviewer B (Test quality). Focus: Integration over unit? SUT not mocked? Shared fixtures? Assert outcomes? Create review task titled PROPOSAL-1-REVIEW-B-1...", subagent_type: "reviewer")
Task(description: "Reviewer C: elegance", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). You are Reviewer C (Elegance). Focus: Right API? Not over/under-engineered? Complexity proportional to problem? Create review task titled PROPOSAL-1-REVIEW-C-1...", subagent_type: "reviewer")
```

3. Wait for all 3 reviewers to vote ACCEPT

## Consensus

**All 3 reviewers must vote ACCEPT.** Max revision rounds until consensus.

## Checking Reviews

```bash
bd show <proposal-id>
bd comments <proposal-id>
```

## Coordination

```bash
# Add comment to notify that review is ready
bd comments add <proposal-id> "Review requested — 3 reviewers spawned"

# Check for review votes
bd comments <proposal-id>
```

## Follow-up Proposal Reviews (FOLLOWUP_PROPOSAL-N)

For FOLLOWUP_PROPOSAL-N reviews, use the same procedure:
- **Review task naming:** `FOLLOWUP_PROPOSAL-N-REVIEW-{axis}-{round}`
- Same 3 axes (A/B/C), same binary ACCEPT/REVISE vote
- No severity tree for plan reviews (same as original plan reviews)
- Reviewers should also verify that FOLLOWUP_PROPOSAL addresses the specific IMPORTANT/MINOR findings scoped in FOLLOWUP_URE/URD
