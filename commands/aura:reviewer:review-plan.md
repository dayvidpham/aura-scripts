# Reviewer: Review Plan

Review PROPOSE_PLAN task using end-user alignment criteria.

## When to Use

Assigned to review a plan specification.

## Given/When/Then/Should

**Given** plan assignment **when** reviewing **then** apply end-user alignment criteria **should never** focus only on technical details

**Given** issues found **when** voting **then** vote REVISE with specific feedback **should never** vote REVISE without actionable suggestions

**Given** review complete **when** documenting **then** add comment to Beads task **should never** vote without written justification

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
   - Does Layer 3/4 include tasks to wire production code?
   - Or are they only testing isolated units?

**Red flag:** Plan shows "Layer 2: service.test.ts" but no task for "wire service into CLI command"

**Green flag:** Plan shows "Layer 3: Wire CLI command with createService + real deps"

## Steps

1. Read the PROPOSE_PLAN task:
   ```bash
   bd show <task-id>
   ```

2. Apply end-user alignment criteria

3. Check validation_checklist items are verifiable

4. Check BDD acceptance criteria are complete

5. Add review comment with vote:
   ```bash
   # If accepting:
   bd comments add <task-id> "VOTE: ACCEPT - End-user impact clear. MVP scope appropriate. Checklist items verifiable."

   # If requesting revision:
   bd comments add <task-id> "VOTE: REVISE - Missing: what happens if X fails? Suggestion: add error handling to checklist."
   ```

## Vote Options

| Vote | When |
|------|------|
| ACCEPT | Plan addresses end-user needs, checklist complete, no gaps |
| REVISE | Specific issues need addressing before ratification |

## Consensus

All 3 reviewers must vote ACCEPT for plan to be ratified.
