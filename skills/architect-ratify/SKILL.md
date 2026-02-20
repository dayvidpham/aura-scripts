# Architect: Ratify Plan

Add `aura:p6-plan:s6-ratify` label to accepted PROPOSAL-N after consensus and UAT.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-6-ratification)**

## When to Use

All 3 reviewers have voted ACCEPT on PROPOSAL-N and user has approved via UAT.

## Given/When/Then/Should

**Given** all 3 reviewers voted ACCEPT **when** ratifying **then** add `aura:p6-plan:s6-ratify` label to PROPOSAL-N **should never** ratify with any REVISE votes outstanding

**Given** ratification **when** documenting **then** add comment with reviewer sign-offs and UAT reference **should never** ratify without audit trail

**Given** previous proposals exist **when** ratifying new version **then** mark old proposals as `aura:superseded` **should never** leave old proposals without superseded marking

## Consensus Requirement

**All 3 reviewers must vote ACCEPT.** If any reviewer votes REVISE:
1. Architect creates PROPOSAL-N+1 addressing feedback
2. Marks PROPOSAL-N as `aura:superseded`
3. Reviewers re-review PROPOSAL-N+1
4. Repeat until all ACCEPT

## Steps

1. Check all reviews on PROPOSAL-N task:
   ```bash
   bd show <proposal-id>
   bd comments <proposal-id>
   ```

2. Verify all 3 votes are ACCEPT

3. Add ratify label to PROPOSAL-N (do NOT create a new task):
   ```bash
   bd label add <proposal-id> aura:p6-plan:s6-ratify
   bd comments add <proposal-id> "RATIFIED: All 3 reviewers ACCEPT, UAT passed (<uat-task-id>)"
   ```

4. Mark all previous proposals as superseded:
   ```bash
   bd label add <old-proposal-id> aura:superseded
   bd comments add <old-proposal-id> "Superseded by PROPOSAL-N (<ratified-proposal-id>)"
   ```

5. Update URD with ratification:
   ```bash
   bd comments add <urd-id> "Ratified: scope confirmed. Ratified proposal: <ratified-proposal-id>"
   ```

## Next Steps

After ratifying PROPOSAL-N:
1. **Prepare handoff** — Run `/aura:architect-handoff` to create handoff document and spawn supervisor

**IMPORTANT:** Do NOT start implementation yourself. The architect's role ends at handoff. Implementation is handled by the supervisor and workers spawned during handoff.

## Follow-up Proposals (FOLLOWUP_PROPOSAL-N)

When ratifying a FOLLOWUP_PROPOSAL-N, the next step is the same h1 handoff but scoped to the follow-up epic:
- **Storage:** `.git/.aura/handoff/{followup-epic-id}/architect-to-supervisor.md`
- The supervisor then creates FOLLOWUP_IMPL_PLAN and FOLLOWUP_SLICE-N tasks
- Original IMPORTANT/MINOR leaf tasks are adopted as dual-parent children of FOLLOWUP_SLICE-N
