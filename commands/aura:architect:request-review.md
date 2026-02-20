# Architect: Request Review

Send PROPOSAL-N task to reviewers for feedback.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## When to Use

Plan draft complete, ready for review.

## Given/When/Then/Should

**Given** plan ready **when** requesting review **then** spawn 3 generic reviewers (all use same end-user alignment criteria) **should never** spawn specialized reviewers

**Given** reviewers **when** assigning **then** provide Beads task ID and context **should never** expect reviewers to search

## REVIEW Naming

Reviews are named PROPOSAL-N-REVIEW-M where:
- N = proposal number (matches PROPOSAL-N)
- M = reviewer number (1, 2, 3)

## Steps

1. Verify PROPOSAL-N task is complete with all sections
2. Spawn three reviewers with the task ID and URD reference:

```
Task(description: "Reviewer 1: review plan", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). Apply end-user alignment criteria. Create review task titled PROPOSAL-1-REVIEW-1...", subagent_type: "reviewer")
Task(description: "Reviewer 2: review plan", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). Apply end-user alignment criteria. Create review task titled PROPOSAL-1-REVIEW-2...", subagent_type: "reviewer")
Task(description: "Reviewer 3: review plan", prompt: "Review PROPOSAL-1 task <task-id>. URD: <urd-id> (read for requirements context). Apply end-user alignment criteria. Create review task titled PROPOSAL-1-REVIEW-3...", subagent_type: "reviewer")
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
