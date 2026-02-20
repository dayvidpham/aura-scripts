---
name: impl-review
description: Code review across all implementation slices (Phase 10)
---

# Implementation Code Review (Phase 10)

Conduct code review across ALL implementation slices. Each of 3 reviewers reviews every slice.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-10-code-review)** <- Phase 10

See `CONSTRAINTS.md` for coding standards and severity definitions.

## Given/When/Then/Should

**Given** all slices complete **when** starting review **then** spawn 3 reviewers for ALL slices **should never** assign reviewers to single slices

**Given** reviewer assigned **when** reviewing **then** check each slice against criteria **should never** skip any slice

**Given** review round **when** creating severity groups **then** ALWAYS create 3 severity groups (BLOCKER, IMPORTANT, MINOR) per round even if empty **should never** lazily create groups only when findings exist

**Given** BLOCKER finding **when** wiring dependencies **then** add dual-parent: blocks BOTH severity group AND slice **should never** wire BLOCKER to only one parent

**Given** IMPORTANT or MINOR finding **when** categorizing **then** add to severity group only (NOT to slice) — these go to follow-up epic **should never** block slices on non-BLOCKER findings

**Given** review complete with IMPORTANT/MINOR **when** finishing **then** supervisor creates EPIC_FOLLOWUP immediately (NOT gated on BLOCKER resolution) **should never** wait for BLOCKERs to resolve before creating follow-up

## Severity Tree (EAGER Creation)

**ALWAYS create 3 severity group tasks per review round**, even if some groups have no findings:

```bash
# Step 1: Create all 3 severity groups immediately (EAGER)
BLOCKER_ID=$(bd create --title "SLICE-1-REVIEW-A-1 BLOCKER" \
  --labels "aura:severity:blocker,aura:p10-impl:s10-review" \
  --description "---
references:
  slice: <slice-1-id>
  review_round: 1
---
BLOCKER findings from Reviewer A (Correctness) on SLICE-1.")

IMPORTANT_ID=$(bd create --title "SLICE-1-REVIEW-A-1 IMPORTANT" \
  --labels "aura:severity:important,aura:p10-impl:s10-review" \
  --description "---
references:
  slice: <slice-1-id>
  review_round: 1
---
IMPORTANT findings from Reviewer A (Correctness) on SLICE-1.")

MINOR_ID=$(bd create --title "SLICE-1-REVIEW-A-1 MINOR" \
  --labels "aura:severity:minor,aura:p10-impl:s10-review" \
  --description "---
references:
  slice: <slice-1-id>
  review_round: 1
---
MINOR findings from Reviewer A (Correctness) on SLICE-1.")

# Step 2: Wire severity groups to the review round
bd dep add <review-round-id> --blocked-by $BLOCKER_ID
bd dep add <review-round-id> --blocked-by $IMPORTANT_ID
bd dep add <review-round-id> --blocked-by $MINOR_ID

# Step 3: Close empty groups immediately
# If a group has no findings, close it right away
bd close $IMPORTANT_ID   # if no IMPORTANT findings
bd close $MINOR_ID        # if no MINOR findings
```

### Naming Convention

```
SLICE-{N}-REVIEW-{axis}-{round}
```

Where axis = A (Correctness), B (Test quality), C (Elegance).

Examples:
- `SLICE-1-REVIEW-A-1` — Reviewer A (Correctness), Round 1, SLICE-1
- `SLICE-2-REVIEW-C-2` — Reviewer C (Elegance), Round 2, SLICE-2

Severity groups:
- `SLICE-1-REVIEW-A-1 BLOCKER`
- `SLICE-1-REVIEW-A-1 IMPORTANT`
- `SLICE-1-REVIEW-A-1 MINOR`

## Dual-Parent BLOCKER Relationship

BLOCKER findings have **two parents**:
1. The severity group task (`aura:severity:blocker`) — for categorization
2. The slice they block — for dependency tracking

```bash
# Create a BLOCKER finding
FINDING_ID=$(bd create --title "BLOCKER: Missing error handling in auth flow" \
  --labels "aura:p10-impl:s10-review" \
  --description "---
references:
  slice: <slice-1-id>
  reviewer: reviewer-A
  round: 1
---
Missing error handling causes silent failure in auth flow.")

# Wire dual-parent: finding blocks BOTH severity group AND slice
bd dep add $BLOCKER_ID --blocked-by $FINDING_ID
bd dep add <slice-1-id> --blocked-by $FINDING_ID
```

**IMPORTANT and MINOR findings only block their severity group (NOT the slice):**

```bash
# IMPORTANT finding — blocks severity group only
IMPORTANT_FINDING_ID=$(bd create --title "IMPORTANT: Add request timeout" \
  --labels "aura:p10-impl:s10-review" \
  --description "---
references:
  slice: <slice-1-id>
  reviewer: reviewer-A
  round: 1
---
API calls should have configurable timeouts.")

# Only blocks the IMPORTANT severity group (NOT the slice)
bd dep add $IMPORTANT_ID --blocked-by $IMPORTANT_FINDING_ID
```

## Review Structure

Each reviewer (A, B, C) reviews EVERY slice:

```
Reviewer A (Correctness): Reviews SLICE-1, SLICE-2, SLICE-3 →
  Creates: SLICE-1-REVIEW-A-1, SLICE-2-REVIEW-A-1, SLICE-3-REVIEW-A-1
  Each review has 3 severity groups (BLOCKER/IMPORTANT/MINOR)

Reviewer B (Test quality): Reviews SLICE-1, SLICE-2, SLICE-3 →
  Creates: SLICE-1-REVIEW-B-1, SLICE-2-REVIEW-B-1, SLICE-3-REVIEW-B-1

Reviewer C (Elegance): Reviews SLICE-1, SLICE-2, SLICE-3 →
  Creates: SLICE-1-REVIEW-C-1, SLICE-2-REVIEW-C-1, SLICE-3-REVIEW-C-1
```

## Spawning Reviewers

Supervisor spawns 3 parallel reviewers as **subagents** (via the Task tool) or via **TeamCreate**. Reviewers are short-lived — keep them in-session.

```
// Spawn 3 reviewers (one per axis)
Task({
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: `You are Reviewer A (Correctness).
URD: <urd-id> (read with bd show <urd-id> for user requirements context)
Focus: Does implementation faithfully serve the user? Are technical decisions consistent with rationale?
Review ALL slices: <slice-1-id>, <slice-2-id>, <slice-3-id>
For each slice, run: bd show <slice-id>
Create severity groups (BLOCKER/IMPORTANT/MINOR) for each slice. Title: SLICE-N-REVIEW-A-1
Call Skill(/aura:reviewer-review-code) for the review procedure.`
})
```

**Handoff:** Before spawning each reviewer, create a handoff document:
```
.git/.aura/handoff/<request-task-id>/supervisor-to-reviewer-<N>.md
```

### Supervisor → Reviewer Handoff Template

```markdown
# Handoff: Supervisor → Reviewer <N>

## Context
- Request: <request-task-id>
- URD: <urd-task-id>
- IMPL_PLAN: <impl-plan-task-id>
- Ratified Proposal: <proposal-task-id>

## Slices to Review
| Slice | Task ID | Description | Worker |
|-------|---------|-------------|--------|
| SLICE-1 | <id> | <description> | worker-1 |
| SLICE-2 | <id> | <description> | worker-2 |

## Review Procedure
1. For each slice: `bd show <slice-id>`
2. Create 3 severity groups per slice (EAGER)
3. Add findings as children of severity groups
4. BLOCKER findings: dual-parent (severity group + slice)
5. Close empty severity groups immediately
6. Vote ACCEPT or REVISE per slice
```

## Review Criteria

Each reviewer checks each slice for:

1. **Requirements Alignment (check URD)**
   - Does implementation match ratified plan?
   - Are all acceptance criteria met?
   - Read URD (`bd show <urd-id>`) for requirements traceability

2. **User Vision (check URD)**
   - Does it fulfill the user's original request (as documented in URD)?
   - Does it match UAT expectations?

3. **MVP Scope**
   - Is scope appropriate (not over/under engineered)?

4. **Codebase Quality**
   - Follows project style/constraints?
   - No TODO placeholders?
   - Tests import production code?

5. **Validation Checklist**
   - All items from slice checklist verified?

## Voting: ACCEPT vs REVISE (Binary Only)

| Vote | Requirement |
|------|-------------|
| **ACCEPT** | All 5 criteria satisfied; no BLOCKER items |
| **REVISE** | BLOCKER issues found; must provide actionable feedback |

**Documentation (via Beads comments):**
```bash
bd comments add <slice-id> "VOTE: ACCEPT - [reason]"
# OR
bd comments add <slice-id> "VOTE: REVISE - [specific issue]. Suggest: [fix]"
```

## Consensus Check

All reviews across all slices must be ACCEPT:

```bash
# Check for any REVISE votes
bd list --labels="aura:p10-impl:s10-review" --desc-contains "VOTE: REVISE"

# Check for unresolved BLOCKERs
bd list --labels="aura:severity:blocker" --status=open

# If any REVISE or open BLOCKERs, return to implementation
# If all ACCEPT and BLOCKERs resolved, proceed to Phase 11 (UAT)
```

## Handling REVISE

If any reviewer votes REVISE on any slice:

1. **Document issues** in the review task description
2. **Return slice to worker** for fixes
3. **Re-review** after fixes complete (new review round)

```bash
# Mark slice as needing revision
bd comments add <slice-id> "REVISION NEEDED: <specific issues>"

# After worker fixes, start new review round
# New severity groups are created fresh for the new round
```

## Follow-up Epic (EPIC_FOLLOWUP)

**Trigger:** Review round completion + ANY IMPORTANT or MINOR findings exist.
**NOT gated on BLOCKER resolution.** Supervisor creates it immediately.

### Step 1: Create the follow-up epic

```bash
bd create --type=epic --priority=3 \
  --title="FOLLOWUP: Non-blocking improvements from code review" \
  --description="---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  review_round: <review-round-ids>
---
Aggregated IMPORTANT and MINOR findings from code review." \
  --add-label "aura:epic-followup"

# Link IMPORTANT/MINOR severity groups
bd dep add <followup-epic-id> --blocked-by <important-group-id>
bd dep add <followup-epic-id> --blocked-by <minor-group-id>
```

### Step 2: Follow-up lifecycle (same protocol, FOLLOWUP_* prefix)

The follow-up epic runs the same protocol phases with FOLLOWUP_* prefixed task types:

```
FOLLOWUP epic (aura:epic-followup)
  ├── relates_to: original URD
  ├── relates_to: original REVIEW-A/B/C tasks
  └── blocked-by: FOLLOWUP_URE         (Phase 2: scope which findings to address)
        └── blocked-by: FOLLOWUP_URD   (Phase 2: requirements for follow-up)
              └── blocked-by: FOLLOWUP_PROPOSAL-1  (Phase 3: proposal for follow-up)
                    └── blocked-by: FOLLOWUP_IMPL_PLAN  (Phase 8: decompose into slices)
                          ├── blocked-by: FOLLOWUP_SLICE-1  (Phase 9)
                          │     ├── blocked-by: important-leaf-task-...
                          │     └── blocked-by: minor-leaf-task-...
                          └── blocked-by: FOLLOWUP_SLICE-2
```

```bash
# Create follow-up lifecycle tasks
FOLLOWUP_URE_ID=$(bd create \
  --title "FOLLOWUP_URE: Scope follow-up for <feature>" \
  --labels "aura:p2-user:s2_1-elicit" \
  --description "---
references:
  followup_epic: <followup-epic-id>
  original_urd: <original-urd-id>
---
Scoping URE: determine which IMPORTANT/MINOR findings to address.")
bd dep add <followup-epic-id> --blocked-by $FOLLOWUP_URE_ID

FOLLOWUP_URD_ID=$(bd create \
  --title "FOLLOWUP_URD: Requirements for <feature> follow-up" \
  --labels "aura:p2-user:s2_2-urd,aura:urd" \
  --description "---
references:
  followup_epic: <followup-epic-id>
  original_urd: <original-urd-id>
---
Follow-up requirements. References original URD.")
bd dep add $FOLLOWUP_URE_ID --blocked-by $FOLLOWUP_URD_ID
```

### Step 3: Leaf task adoption (dual-parent)

When the supervisor creates FOLLOWUP_SLICE-N tasks, the IMPORTANT/MINOR leaf tasks from the original review gain a second parent:

```bash
# Leaf task gets dual-parent: original severity group + follow-up slice
bd dep add <followup-slice-id> --blocked-by <important-leaf-task-id>
bd dep add <followup-slice-id> --blocked-by <minor-leaf-task-id>
# Leaf task already has: bd dep add <severity-group-id> --blocked-by <leaf-task-id>
```

### Reviewer → Followup Handoff (h5)

The h5 handoff **starts** the follow-up lifecycle. Create this handoff document:
```
.git/.aura/handoff/<request-task-id>/reviewer-to-followup.md
```

```markdown
# Handoff: Reviewer → Follow-up Epic

## Context
- Request: <request-task-id>
- Follow-up Epic: <followup-epic-id>

## IMPORTANT Findings
| Finding | Slice | Severity Group | Description |
|---------|-------|---------------|-------------|
| <id> | SLICE-1 | <important-group-id> | <summary> |

## MINOR Findings
| Finding | Slice | Severity Group | Description |
|---------|-------|---------------|-------------|
| <id> | SLICE-2 | <minor-group-id> | <summary> |

## Recommended Priority Order
1. <highest-priority IMPORTANT finding>
2. <next>
```

### Follow-up Handoff Chain

Inside the follow-up lifecycle, the same handoff types (h1-h4) apply but scoped to the follow-up epic:

| Order | Handoff | Transition |
|-------|---------|------------|
| 1 | h5 | Reviewer → Followup: **Starts** the follow-up lifecycle |
| 2 | *(none)* | Supervisor creates FOLLOWUP_URE (same actor) |
| 3 | *(none)* | Supervisor creates FOLLOWUP_URD (same actor) |
| 4 | h6 | Supervisor → Architect: Hands off FOLLOWUP_URE + FOLLOWUP_URD for FOLLOWUP_PROPOSAL |
| 5 | h1 | Architect → Supervisor: After FOLLOWUP_PROPOSAL ratified |
| 6 | h2 | Supervisor → Worker: FOLLOWUP_SLICE-N with adopted leaf task IDs |
| 7 | h3 | Supervisor → Reviewer: Code review of follow-up slices |
| 8 | h4 | Worker → Reviewer: Follow-up slice completion |

Follow-up handoff storage: `.git/.aura/handoff/{followup-epic-id}/{source}-to-{target}.md`

See `HANDOFF_TEMPLATE.md` for full follow-up handoff examples and field requirements.

## Proceeding to UAT

Only when ALL reviews are ACCEPT and all BLOCKERs are resolved:

```bash
# Verify consensus — no open BLOCKERs
bd list --labels="aura:severity:blocker" --status=open
# Should return 0 results

# Proceed to Phase 11 (Implementation UAT)
Skill(/aura:user-uat)
```
