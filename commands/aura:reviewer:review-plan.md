# Reviewer: Review Plan

Review PROPOSAL-N task using end-user alignment criteria. Plan reviews use ACCEPT/REVISE only — no severity tree.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-4-plan-review)**

## When to Use

Assigned to review a plan specification (Phase 4, `aura:p4-plan:s4-review`).

## Given/When/Then/Should

**Given** plan assignment **when** reviewing **then** apply end-user alignment criteria **should never** focus only on technical details

**Given** issues found **when** voting **then** vote REVISE with specific feedback **should never** vote REVISE without actionable suggestions

**Given** review complete **when** documenting **then** add comment to Beads task **should never** vote without written justification

**Given** plan review **when** assessing **then** use ACCEPT/REVISE binary vote only **should never** create severity tree for plan reviews

## End-User Alignment Criteria

Ask these questions for every plan:

1. **Who are the end-users?**
2. **What would end-users want?**
3. **How would this affect them?**
4. **Are there implementation gaps?**
5. **Does MVP scope make sense?**
6. **Is validation checklist complete and correct?**

## Production Code Path Questions

When reviewing plans, explicitly ask:

**Given** plan proposal **when** reviewing **then** identify production code paths **should never** approve plans without clear entry points

1. **What are the production code paths?**
   - CLI commands: Entry points users will run
   - API endpoints: HTTP handlers, services
   - Background jobs: Daemon processes

2. **How will production code be tested?**
   - Do Layer 2 tests import the actual CLI/API?
   - Or do they test a separate test-only export? (anti-pattern)

3. **What needs to be wired together?**
   - Service instantiation with real dependencies?
   - CLI command registration?
   - Entry point hookup?

4. **Are implementation tasks explicit about production code?**
   - Does the plan include tasks to wire production code?
   - Or are they only testing isolated units?

**Red flag:** Plan shows "Layer 2: service.test.ts" but no task for "wire service into CLI command"

**Green flag:** Plan shows "Layer 3: Wire CLI command with createService + real deps"

## Steps

1. Read the PROPOSAL-N task and URD:
   ```bash
   bd show <proposal-id>
   bd show <urd-id>   # Read URD for user requirements context
   ```

2. Apply end-user alignment criteria (check against URD requirements)

3. Check validation_checklist items are verifiable

4. Check BDD acceptance criteria are complete

5. Create review task:
   ```bash
   bd create --labels "aura:p4-plan:s4-review" \
     --title "PROPOSAL-1-REVIEW-1: <feature>" \
     --description "---
   references:
     proposal: <proposal-id>
     urd: <urd-id>
   ---
   VOTE: <ACCEPT|REVISE> - <justification>"
   bd dep add <proposal-id> --blocked-by <review-id>
   ```

6. Add vote comment:
   ```bash
   # If accepting:
   bd comments add <proposal-id> "VOTE: ACCEPT - End-user impact clear. MVP scope appropriate. Checklist items verifiable."

   # If requesting revision:
   bd comments add <proposal-id> "VOTE: REVISE - Missing: what happens if X fails? Suggestion: add error handling to checklist."
   ```

## Vote Options

| Vote | When |
|------|------|
| ACCEPT | All 6 criteria satisfied; no BLOCKER items |
| REVISE | BLOCKER issues found; must provide actionable feedback |

Binary only. No severity tree for plan reviews.

## Consensus

All 3 reviewers must vote ACCEPT for plan to be ratified.
