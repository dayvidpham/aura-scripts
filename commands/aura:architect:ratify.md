# Architect: Ratify Plan

Create RATIFIED_PLAN task after all reviewers reach consensus.

## When to Use

All 3 reviewers have voted ACCEPT on the PROPOSE_PLAN task.

## Given/When/Then/Should

**Given** all 3 reviewers voted ACCEPT **when** ratifying **then** create RATIFIED_PLAN task with final version **should never** ratify with any REVISE votes outstanding

**Given** ratification **when** documenting **then** include all reviewer sign-offs in task **should never** ratify without audit trail

## Consensus Requirement

**All 3 reviewers must vote ACCEPT.** If any reviewer votes REVISE:
1. Architect creates REVISION task addressing feedback
2. Reviewers re-review
3. Repeat until all ACCEPT

## Steps

1. Check all reviews on PROPOSE_PLAN task:
   ```bash
   bd show <propose-plan-id>
   bd comments <propose-plan-id>
   ```

2. Verify all 3 votes are ACCEPT

3. Create RATIFIED_PLAN task:
   ```bash
   bd create --type=feature \
     --labels="aura:ratified-plan" \
     --title="Ratified: <feature name>" \
     --description="<final plan content>" \
     --design='{"validation_checklist":[...],"signoffs":["reviewer-1","reviewer-2","reviewer-3"],"acceptance_criteria":[...]}'

   bd dep add <propose-plan-id> --blocked-by <ratified-plan-id>
   ```

4. Update URD with ratification:
   ```bash
   bd comments add <urd-id> "Ratified: scope confirmed. Ratified plan: <ratified-plan-id>"
   bd dep relate <urd-id> <ratified-plan-id>
   ```

5. Close PROPOSE_PLAN task:
   ```bash
   bd close <propose-plan-id> --reason="Ratified as <ratified-plan-id>"
   ```

## Next Steps

After creating RATIFIED_PLAN:
1. **Ask for user approval** - Present the ratified plan summary and ask the user if they want to proceed with implementation
2. **Prepare handoff** - If approved, run `/aura:architect:handoff` to create IMPLEMENTATION_PLAN and spawn supervisor

**IMPORTANT:** Do NOT start implementation yourself. The architect's role ends at ratification. Implementation is handled by the supervisor and workers spawned during handoff.
