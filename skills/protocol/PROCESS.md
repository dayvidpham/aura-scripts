# Aura Protocol - Process Guide

**This is the single source of truth for Aura workflow execution.**

For agent role definitions and detailed tool references, see `skills/`.

---

## Quick Start (60 seconds)

**The Aura Protocol runs through 12 phases:**

```
Phase 1:  REQUEST         (classify, research, explore)
Phase 2:  ELICIT + URD    (URE survey, user requirements document)
Phase 3:  PROPOSAL-N      (architect proposes)
Phase 4:  REVIEW          (parallel reviewers, ACCEPT/REVISE)
Phase 5:  Plan UAT        (user acceptance test)
Phase 6:  Ratification    (supersede old proposals)
Phase 7:  Handoff         (architect → supervisor)
Phase 8:  IMPL_PLAN       (supervisor decomposes into slices)
Phase 9:  SLICE-N         (parallel workers)
Phase 10: Code Review     (severity tree: BLOCKER/IMPORTANT/MINOR)
Phase 11: Impl UAT        (user acceptance test)
Phase 12: Landing         (commit, push, hand off)
```

**Check current progress:**
```bash
bd stats                                                  # Project overview
bd list --labels="aura:p3-plan:s3-propose"                # Active proposals
bd list --labels="aura:p9-impl:s9-slice" --status=in_progress  # Implementation progress
```

**Full sections below.** For detailed steps, see agent files in `skills/`.

---

## Phase 1: REQUEST (`aura:p1-user`)

### When to Trigger Planning

Start planning when:
- User submits a new feature request
- A blocker requires architectural decision
- Multi-phase work needs coordination

### Sub-steps

Phase 1 expands into 3 sub-steps:

| Sub-step | Label | Description | Parallel? |
|----------|-------|-------------|-----------|
| s1_1-classify | `aura:p1-user:s1_1-classify` | Capture and classify user request | Sequential (first) |
| s1_2-research | `aura:p1-user:s1_2-research` | Research existing solutions and patterns | Parallel with s1_3 |
| s1_3-explore | `aura:p1-user:s1_3-explore` | Explore codebase for integration points | Parallel with s1_2 |

### REQUEST Task

**What:** Capture user's problem statement as a Beads task.

```bash
bd create --type=feature --priority=2 \
  --title="REQUEST: Brief description of need" \
  --description="Full user request with context, acceptance criteria" \
  --add-label "aura:p1-user:s1_1-classify"
```

**Who:** Usually user or coordinator creates this.

**Next:** After classification, research and exploration happen in parallel. Then proceed to Phase 2 (Elicitation).

See: [../user-request/SKILL.md](../user-request/SKILL.md)

---

## Phase 2: ELICIT & URD (`aura:p2-user`)

### Sub-steps

| Sub-step | Label | Description |
|----------|-------|-------------|
| s2_1-elicit | `aura:p2-user:s2_1-elicit` | URE survey — structured requirements elicitation |
| s2_2-urd | `aura:p2-user:s2_2-urd` (also `aura:urd`) | Create URD — single source of truth for requirements |

### URE Survey (s2_1)

Architect runs `/aura:user-elicit` for structured requirements elicitation.

Capture results using the same structured format as
[UAT_TEMPLATE.md](UAT_TEMPLATE.md) — each question must include the exact
question text, ALL options with their descriptions, and the user's verbatim
response. See [UAT_EXAMPLE.md](UAT_EXAMPLE.md) for an example of the recording
quality expected.

### User Requirements Document (s2_2)

**What:** A single Beads task (label `aura:urd`) that serves as the single source of truth for user requirements, priorities, design choices, MVP goals, and end-vision goals.

**Lifecycle:**
- **Created** in Phase 2 with structured requirements from the URE survey
- **Referenced** via description frontmatter in PROPOSAL, IMPL_PLAN, UAT, and other tasks
- **Updated** via `bd comments add` whenever requirements/scope change (UAT results, ratification, user feedback)
- **Consulted** by architects, reviewers, and supervisors as the single source of truth for "what does the user want?"

```bash
# Create URD after elicitation
bd create --labels "aura:urd,aura:p2-user:s2_2-urd" \
  --title "URD: {{feature name}}" \
  --description "---
references:
  request: <request-task-id>
  elicit: <elicit-task-id>
---
## Requirements
{{structured requirements from URE survey}}

## Priorities
{{user-stated priorities}}

## Design Choices
{{design decisions from elicitation}}

## MVP Goals
{{minimum viable scope}}

## End-Vision Goals
{{user's ultimate vision}}"
```

**Don't Forget About the URD!** Every agent should consult the URD before making decisions. When in doubt about requirements, `bd show <urd-id>` is your first stop.

### Dependencies

The canonical dependency chain flows top-down (parents blocked by children):

```
REQUEST
  └── blocked by ELICIT
        └── blocked by PROPOSAL-1
              └── blocked by IMPL_PLAN
                    ├── blocked by SLICE-1
                    │     ├── blocked by leaf-task-a
                    │     └── blocked by leaf-task-b
                    └── blocked by SLICE-2

URD ← referenced via frontmatter in (REQUEST, ELICIT, PROPOSAL, IMPL_PLAN, UAT)
```

**Rule:** `bd dep add <stays-open> --blocked-by <must-finish-first>`. The `--blocked-by` target is always the thing you do first. Work flows bottom-up; closure flows top-down.

**Next:** Architect spawns `/aura:architect-propose-plan` skill to explore and propose.

---

## Phase 3: PROPOSAL-N (`aura:p3-plan`)

### PROPOSAL-N Task

**What:** Architect's full technical proposal including tradeoffs, interfaces, validation checklist, and BDD criteria. N starts at 1 and increments with each revision.

**PROPOSAL-N must include:**

| Item | Purpose | Example |
|------|---------|---------|
| **Problem Space** | Map the engineering axes (parallelism, distribution, frequency) | "Is this distributed? How much parallelism?" |
| **Tradeoffs** | Document why we chose Option A over B | "Chose Redis over in-memory because..." |
| **Interfaces** | Define all public types, enums, methods | `type FooService interface { DoThing(...) }` |
| **Validation Checklist** | Testable items per phase | `[ ] Type checking passes, [ ] All tests pass` |
| **BDD Criteria** | Acceptance criteria in Given/When/Then format | `Given <state> When <action> Then <outcome>` |
| **MVP Scope** | What's in MVP vs Phase 2 | "MVP: core flow only. Phase 2: parallel workers" |

**Creation:**
```bash
bd create --type=feature --priority=2 \
  --title="PROPOSAL-1: Technical proposal for feature" \
  --description="---
references:
  request: <request-task-id>
  urd: <urd-task-id>
---
..." \
  --design="validation_checklist: [...], acceptance_criteria: [...]" \
  --add-label "aura:p3-plan:s3-propose"
```

Link dependency:
```bash
bd dep add <request-id> --blocked-by <proposal-id>
```

**Next:** Architect runs `/aura:architect-request-review` to spawn 3 reviewers in **PARALLEL**.

See: [../architect-propose-plan/SKILL.md](../architect-propose-plan/SKILL.md)

---

## Phase 4: Plan Review (`aura:p4-plan`)

### Spawning Reviewers

Architect spawns **3 independent reviewers** in parallel (not sequentially).

Spawn reviewers as `general-purpose` subagents (via the Task tool, `subagent_type: "general-purpose"`) and instruct each to invoke the `/aura:reviewer` skill to load its role instructions. `/aura:reviewer` is a **Skill** (invoked via the Skill tool), not a subagent type — it provides the reviewer's workflow, severity tree, and voting procedures. Reviewers are short-lived — keep them in-session for direct result collection. Do NOT use `aura-swarm start` for reviewer rounds.

> **CRITICAL: No Fake Reviews**
>
> The architect **MUST** spawn actual independent reviewer subagents. The architect **CANNOT**:
> - Write review comments pretending to be reviewers
> - Simulate votes by adding comments from the same actor
> - Skip the review phase by self-approving
>
> If the architect lacks permission to spawn subagents, it **MUST** ask the user for help rather than faking reviews. Reviews from the same actor do not count as independent consensus.

**Reviewer Selection:**
- **Plan Review (Phase 4):** Use generic end-user alignment perspective (NOT technical specialization)
- **Code Review (Phase 10):** Optional specialized reviewers (security, performance, etc.)

### Review Criteria (6 Questions)

Each reviewer assesses **end-user alignment**, not technical taste:

1. **Who are the end-users?** Can you name them?
2. **What do end-users want?** What problem does this solve for them?
3. **How will this affect them?** Positively? Any downsides?
4. **Are there implementation gaps?** Will the code actually deliver what's promised?
5. **Does MVP scope make sense?** Is it achievable without taking on too much?
6. **Is validation checklist complete?** Can each item be tested independently?

### Voting: ACCEPT vs REVISE (Binary Only)

| Vote | Requirement |
|------|-------------|
| **ACCEPT** | All 6 criteria satisfied; no BLOCKER items |
| **REVISE** | BLOCKER issues found; must provide actionable feedback (not just criticism) |

**Plan reviews do NOT use a severity tree.** Plan reviews use binary ACCEPT/REVISE votes only. The severity tree is reserved for code reviews (Phase 10).

**Documentation (via Beads comments):**
```bash
bd comments add <task-id> "VOTE: ACCEPT - [reason]"
# OR
bd comments add <task-id> "VOTE: REVISE - [specific issue]. Suggest: [fix]"
```

### Revision Loop

If any reviewer votes REVISE:

1. Architect reads feedback in task comments
2. Creates PROPOSAL-N+1 task (increment N) with fixes
3. Marks PROPOSAL-N as `aura:superseded` with a comment explaining why
4. Re-spawns all 3 reviewers to re-assess the new proposal
5. Loop until all 3 vote ACCEPT

**Max Revision Rounds:** No hard limit; use common sense. If > 3 rounds, escalate to user for decision.

**Next (All 3 ACCEPT):** Proceed to Phase 5 (Plan UAT)

See: [../reviewer/SKILL.md](../reviewer/SKILL.md)

---

## Phase 5: Plan UAT (`aura:p5-user`)

### User Approval (Required!)

**DO NOT auto-proceed.** Present the accepted proposal to the user for explicit approval.

The idea here is: the plan and the implementation MUST match with the user's end vision for the project.
The architect should also plan out several MVP milestones, in order to reach the user's vision.

**Questions must split the engineering design space on its ambiguous boundaries
to extract maximum information — like a decision tree, where each question
bisects the remaining uncertainty.** Questions must NOT be general.

**BAD example:**
> "exactly matches feedback, mostly matches feedback, requires revisions, ..."
> "Does this match your vision?" with options like "Yes exactly", "Mostly", "No"

These fail because the options are approval levels, not engineering alternatives.
They don't help the architect make better decisions.

**GOOD example:**
> "Should this be statically-allocated or allocated at runtime? Static: catches
> errors at compile time, more boilerplate. Dynamic: flexible, errors at runtime."
>
> "Which of these variants we chose are appropriate, and why? Variant 1, main
> tradeoffs: ...; Variant N, ...."
>
> "Should runtime deps be baked into the Nix wrapper (hermetic, reproducible) or
> expected from PATH (lighter, user-managed)?"

Each option must be a real engineering alternative with specific tradeoffs.
The user's choice should directly inform the implementation.

**Structure questions as a decision tree:** highest-leverage boundaries first
(1-2 questions per AskUserQuestion call), then dependent decisions informed by
prior answers. Later questions should depend on earlier answers.

User should be prompted with multiSelect, because the user can choose multiple tradeoffs/design choices.

The user should NOT be prompted with all questions at once, about all components. The user MUST be shown snippets of the definition, the implementation, and a motivating example. Then they should be asked several critical questions about one component at a time.

See [UAT_TEMPLATE.md](UAT_TEMPLATE.md) for the structured output format and
[UAT_EXAMPLE.md](UAT_EXAMPLE.md) for a worked example of this question quality.

If user requests changes: Loop back to Phase 3 (architect revises as new PROPOSAL-N).
If user approves: Proceed to Phase 6 (Ratification).

See: [UAT_TEMPLATE.md](UAT_TEMPLATE.md) for the structured UAT output template.

---

## Phase 6: Ratification (`aura:p6-plan`)

### Consensus Requirement

**All 3 reviewers must vote ACCEPT AND user must approve via UAT.** No exceptions.

### Superseding Old Proposals

When a proposal is ratified, all previous proposals are marked as superseded:

```bash
# Mark old proposal as superseded
bd label add <old-proposal-id> aura:superseded
bd comments add <old-proposal-id> "Superseded by PROPOSAL-N (<new-proposal-id>)"
```

### Creating Ratified Version

```bash
# Add ratify label to the accepted proposal
bd label add <proposal-id> aura:p6-plan:s6-ratify
bd comments add <proposal-id> "RATIFIED: All 3 reviewers ACCEPT, UAT passed (<uat-task-id>)."

# Link to request:
bd dep add <request-id> --blocked-by <proposal-id>
```

**Next:** Proceed to Phase 7 (Handoff)

See: [../architect-ratify/SKILL.md](../architect-ratify/SKILL.md)

---

## Phase 7: Handoff (`aura:p7-plan`)

### Architect → Supervisor Handoff

The architect creates a handoff document with full inline provenance and transfers ownership to the supervisor.

**Storage:** `.git/.aura/handoff/{request-task-id}/architect-to-supervisor.md`

```bash
bd create --type=task --priority=2 \
  --title="HANDOFF: Architect → Supervisor for REQUEST" \
  --description="---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  proposal: <ratified-proposal-id>
---
Handoff from architect to supervisor. See handoff document at
.git/.aura/handoff/<request-task-id>/architect-to-supervisor.md" \
  --add-label "aura:p7-plan:s7-handoff"
```

### All 6 Handoff Transitions

| # | From | To | When | Content Level |
|---|------|----|------|---------------|
| 1 | Architect | Supervisor | Phase 7 | Full inline provenance |
| 2 | Supervisor | Worker | Phase 9 (slice assignment) | Summary + bd IDs |
| 3 | Supervisor | Reviewer | Phase 10 (code review) | Summary + bd IDs |
| 4 | Worker | Reviewer | Phase 10 (code review) | Summary + bd IDs |
| 5 | Reviewer | Followup | After Phase 10 | Summary + bd IDs |
| 6 | Supervisor | Architect | Follow-up lifecycle (FOLLOWUP_URE/URD → FOLLOWUP_PROPOSAL) | Summary + bd IDs |

**Same-actor transitions do NOT need handoff:** UAT → Ratify and Ratify → Handoff are performed by the same actor (architect).
In the follow-up lifecycle, the supervisor creating FOLLOWUP_URE and then FOLLOWUP_URD are also same-actor transitions (no handoff needed).

See: [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) for the standardized template.

---

## Phase 8: Implementation Plan (`aura:p8-impl`)

### Overview

Supervisor takes the ratified proposal and decomposes into **vertical slices** (production code paths).

**Key Principle:** Each worker owns a full vertical slice — types, tests, implementation, and wiring for one production code path.

**Supervisor startup sequence:**
1. Call `Skill(/aura:supervisor)` to load role instructions
2. Read RATIFIED_PLAN and URD via `bd show`
3. **Create 3 Cartographers** (the standing explore + review team) via TeamCreate before any codebase exploration — always exactly 3, regardless of complexity (see supervisor skill)
4. Decompose into vertical slices
5. **Identify horizontal Layer Integration Points** — contracts shared across slices (see Layer Integration Points below)
6. **Create leaf tasks (L1/L2/L3) for every slice** — a slice without leaf tasks is undecomposed
7. Spawn workers for leaf tasks

```
Layer 0: Shared infrastructure (common types, enums — optional, parallel)
   ↓
Vertical Slices (parallel, each worker owns one slice):
  Layer 1: Types for this slice
  Layer 2: Tests importing production code (will FAIL — expected!)
  Layer 3: Implementation + wiring (makes tests PASS)
   ↓
IMPLEMENTATION COMPLETE
```

### Cartographers (Standing Explore + Review Team)

The supervisor MUST create **exactly 3 Cartographers** via TeamCreate before any codebase exploration — always 3, regardless of feature complexity. Cartographers are dual-role agents that persist for the **full Ride the Wave cycle**:

- **Phase 8 role:** `/aura:explore` — map the codebase for workers, act as context caches. Once a Cartographer has explored an area, follow-up questions on that area cost minimal effort.
- **Phase 10 role:** `/aura:reviewer` — the same 3 agents switch to reviewer role for code review. No respawn needed.

**Cartographers MUST NEVER shut down between phases.** They persist from Phase 8 through Phase 10, maintaining their exploration context across the full implementation cycle. See `/aura:supervisor` skill for full setup guide.

### Layer Integration Points

When slices share types, interfaces, or data flows, the supervisor MUST identify **horizontal Layer Integration Points** in the IMPL_PLAN. These are contracts where one slice exports something another slice imports.

**Rule: merge sooner, not later.** Divergence grows with delay. If SLICE-1 defines a type that SLICE-2 and SLICE-3 consume, SLICE-1 must complete its L1 (types) layer before SLICE-2 and SLICE-3 begin their L1.

**Include an integration points table in the IMPL_PLAN design field:**

| ID | Contract | Owner (exports) | Consumer(s) (imports) | Merge Timing |
|----|----------|-----------------|----------------------|--------------|
| IP-1 | PhaseEnum type | SLICE-1 | SLICE-2, SLICE-3 | L1 (types) |
| IP-2 | EpochService interface | SLICE-2 | SLICE-3, SLICE-4 | L2 (tests) |

If no integration points exist, include an empty table with a note: "No cross-slice contracts identified."

### IMPL_PLAN Task

```bash
bd create --type=epic --priority=2 \
  --title="IMPL_PLAN: Vertical slice decomposition" \
  --description="---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  proposal: <ratified-proposal-id>
---
Supervisor's breakdown of ratified plan into slices" \
  --add-label "aura:p8-impl:s8-plan"
```

**Design field includes:**
- Vertical slice structure (which production code path per slice)
- Dependencies between slices (if any)
- Worker assignments
- Reference to ratified proposal in description frontmatter

---

## Phase 9: Worker Slices (`aura:p9-impl`)

### Creating SLICE-N Tasks

**One task per production code path.** Each worker owns the full vertical:

```bash
bd create --type=task --priority=2 \
  --title="SLICE-1: Implement logging infrastructure (full vertical)" \
  --description="---
references:
  impl_plan: <impl-plan-task-id>
  urd: <urd-task-id>
---
..." \
  --design="{validation_checklist: [...], acceptance_criteria: [...]}" \
  --add-label "aura:p9-impl:s9-slice"
```

Link dependency:
```bash
bd dep add <impl-plan-id> --blocked-by <slice-id>
```

### Creating Leaf Tasks Within Each Slice

**A slice without leaf tasks is undecomposed.** The supervisor MUST create Beads leaf tasks for each horizontal layer within the slice. Workers are assigned to leaf tasks, not slices directly.

```bash
# L1: Types for this slice
LEAF_L1=$(bd create --type=task --priority=2 \
  --title="SLICE-1-L1: Types — <slice name>" \
  --description="..." \
  --add-label "aura:p9-impl:s9-slice")
bd dep add <slice-id> --blocked-by $LEAF_L1

# L2: Tests (will fail until L3)
LEAF_L2=$(bd create --type=task --priority=2 \
  --title="SLICE-1-L2: Tests — <slice name>" \
  --description="..." \
  --add-label "aura:p9-impl:s9-slice")
bd dep add <slice-id> --blocked-by $LEAF_L2
bd dep add $LEAF_L2 --blocked-by $LEAF_L1   # L2 depends on L1

# L3: Implementation (makes tests pass)
LEAF_L3=$(bd create --type=task --priority=2 \
  --title="SLICE-1-L3: Impl — <slice name>" \
  --description="..." \
  --add-label "aura:p9-impl:s9-slice")
bd dep add <slice-id> --blocked-by $LEAF_L3
bd dep add $LEAF_L3 --blocked-by $LEAF_L2   # L3 depends on L2
```

The resulting tree per slice:

```
IMPL_PLAN
  └── blocked by SLICE-1
        ├── blocked by SLICE-1-L1: Types    (no deps)
        ├── blocked by SLICE-1-L2: Tests    (blocked by L1)
        └── blocked by SLICE-1-L3: Impl     (blocked by L2)
```

Workers are assigned to leaf tasks. The slice closes when all its leaf tasks close.

<!-- ADAPT: Replace quality gate commands with your project's equivalents -->

**Design field (canonical schema):**

```json
{
  "productionCodePath": "tool feature list",
  "validation_checklist": [
    "Type checking passes",
    "Tests pass",
    "Production code path implemented (not test-only export)",
    "Tests verify actual production code",
    "All TODO placeholders replaced with working code",
    "Production code verified via code inspection"
  ],
  "acceptance_criteria": [
    {
      "given": "user runs tool feature list",
      "when": "command executes",
      "then": "shows feature list from actual service",
      "should_not": "have dual-export (test vs production paths)"
    }
  ],
  "tradeoffs": [
    {
      "decision": "chosen approach",
      "rationale": "why this over alternatives"
    }
  ],
  "ratified_plan": "<task-id>"
}
```

### Layer 1: Types & Interfaces (Within Each Slice)

**Purpose:** Define public contracts (types, enums, interfaces, schemas) for this slice only.

**Quality Gate:** Type checking passes.

### Layer 2: Tests (Within Each Slice)

**CRITICAL:** Tests will FAIL in Layer 2. This is **correct and expected**.

**Tests must import production code paths:**

**Given** Layer 2 tests **when** writing **then** import actual production code (CLI/API/entry points) **should never** create test-only exports or dual code paths

Tests define what production code should do. When Layer 3 implements production code, these tests should pass.

**CORRECT — import actual production code:**
```
import the_actual_cli_command_or_api_handler
test that it does what end users expect
→ FAILS (expected, no implementation yet)
```

**WRONG — dual-export anti-pattern:**
```
import a test_only_export_of_internal_handler
mock out the system under test
→ PASSES but doesn't test what users actually run
```

### Layer 3: Implementation (Within Each Slice)

**Purpose:** Write code to make Layer 2 tests pass **using production code paths**.

**Given** Layer 3 implementation **when** implementing **then** wire production code together (service instantiation, CLI/API actions) **should never** leave TODO placeholders or create dual exports

**Critical:** Layer 3 is where you wire production code together:
- Create service instances with real dependencies
- Wire services into CLI commands / API handlers
- Ensure the code path users run is the code path tests verify

**Anti-pattern check:**

**Given** Layer 3 complete **when** tests pass but production code has TODOs **then** implementation is incomplete **should never** have dual-export (test vs production paths)

**Quality Gates:**
```bash
# Run your project's type checking and test commands
# Verify production code path via code inspection:
# - No TODO placeholders
# - Real dependencies wired (not mocks in production code)
# - Tests import production code (not test-only export)
```

### Ride the Wave — Worker Persistence

**Ride the Wave** is the execution model for Phases 8–10: workers implement slices, Cartographers review them, workers fix findings — all in a single continuous cycle without agent teardown between phases.

**Worker persistence rules:**

- Workers do **NOT** shut down after completing implementation
- When implementation is complete, workers signal via Beads comments (not `bd close`):
  ```bash
  bd comments add <slice-id> "Implementation complete, awaiting review"
  ```
- Workers stay alive for the review-fix cycle — Cartographers will review their work and may send findings back
- Workers wait for review feedback and fix any BLOCKERs or IMPORTANT findings assigned to them
- The supervisor receives completion notifications but does **NOT** close the slice

### Slice Closure Rules

- Slices **MUST NOT** be closed by workers immediately upon implementation completion
- A slice must be reviewed **at least once** by Cartographers before it can close
- **Only the supervisor closes slices**, after review passes (Phase 10) or after 3 review-fix cycles complete
- Workers who finish implementation stay alive and await review feedback before the session ends

---

## Phase 10: Code Review (`aura:p10-impl`)

### Overview

After all slices complete, the **Cartographers switch role** from `/aura:explore` (Phase 8) to `/aura:reviewer` (Phase 10). The same 3 agents, the same team — no respawn needed. They review all slices in parallel using the **full severity tree** with EAGER creation, then enter a review-fix cycle with workers.

### Review-Fix Cycle (Max 3)

Phase 10 runs up to **3 review-fix cycles**. Workers do not shut down — they await findings and fix them in-place.

**Cycle procedure:**

1. **Cartographers review all slices** — create severity groups (BLOCKER/IMPORTANT/MINOR) for each slice per the EAGER creation protocol
2. **Supervisor collects findings** — aggregates BLOCKERs and IMPORTANTs across all slices; sends findings to the relevant workers
3. **Workers fix BLOCKERs + IMPORTANTs** — workers address assigned findings and notify the supervisor when done
4. **Cartographers re-review fixed slices** — create new severity groups for the new round (round suffix increments: `-1`, `-2`, `-3`)
5. **Repeat** — max 3 cycles total

**Cycle exit conditions:**

| Condition | Action |
|-----------|--------|
| All slices ACCEPT, no open BLOCKERs | Proceed to Phase 11 (Implementation UAT) |
| BLOCKERs or IMPORTANT remain, cycles < 3 | Workers fix, Cartographers re-review (next cycle) |
| 3 cycles exhausted, IMPORTANT remain | Track in FOLLOWUP epic; proceed to Phase 11 |
| 3 cycles exhausted, only MINOR remain | Track in FOLLOWUP epic; proceed to Phase 11 |
| 3 cycles exhausted, BLOCKERs remain | **STOP** — escalate to user, do NOT proceed to UAT |

After cycle 3: UAT is **NOT blocked** on remaining IMPORTANT or MINOR findings. The supervisor creates the FOLLOWUP epic to track them, then proceeds to Phase 11.

### Severity Tree (EAGER Creation)

**ALWAYS create 3 severity group tasks per review round**, even if some groups have no findings:

```bash
# Create all 3 severity groups immediately
bd create --title "SLICE-1-REVIEW-A-1 BLOCKER" \
  --labels "aura:severity:blocker,aura:p10-impl:s10-review" ...
bd create --title "SLICE-1-REVIEW-A-1 IMPORTANT" \
  --labels "aura:severity:important,aura:p10-impl:s10-review" ...
bd create --title "SLICE-1-REVIEW-A-1 MINOR" \
  --labels "aura:severity:minor,aura:p10-impl:s10-review" ...

# Empty groups are closed immediately
bd close <empty-important-id>
bd close <empty-minor-id>
```

### Dual-Parent BLOCKER Relationship

BLOCKER findings have **two parents**:
1. The severity group task (`aura:severity:blocker`) — for categorization
2. The slice they block — for dependency tracking

```bash
# BLOCKER finding blocks both the severity group and the slice
bd dep add <blocker-group-id> --blocked-by <blocker-finding-id>
bd dep add <slice-id> --blocked-by <blocker-finding-id>
```

### Severity Group Dependency Routing (CRITICAL)

Each severity group is linked to exactly one parent based on its level:

| Severity | Blocks | Command |
|----------|--------|---------|
| BLOCKER | The **slice** it applies to | `bd dep add <slice-id> --blocked-by <blocker-group-id>` |
| IMPORTANT | The **FOLLOWUP epic** only | `bd dep add <followup-epic-id> --blocked-by <important-group-id>` |
| MINOR | The **FOLLOWUP epic** only | `bd dep add <followup-epic-id> --blocked-by <minor-group-id>` |

**NEVER link IMPORTANT or MINOR severity groups as blocking IMPL_PLAN or any slice.** Only BLOCKER findings block the implementation path. IMPORTANT and MINOR findings are non-blocking improvements tracked in the follow-up epic.

### Follow-up Epic

**Trigger:** Review completion + ANY IMPORTANT or MINOR findings exist.
**NOT gated on BLOCKER resolution.**
**Owner:** Supervisor creates it.

```bash
bd create --type=epic --priority=3 \
  --title="FOLLOWUP: Non-blocking improvements from code review" \
  --description="---
references:
  request: <request-task-id>
  review_round: <review-task-ids>
---
Aggregated IMPORTANT and MINOR findings from code review." \
  --add-label "aura:epic-followup"

# Route IMPORTANT and MINOR to FOLLOWUP (NOT to IMPL_PLAN or slices)
bd dep add <followup-epic-id> --blocked-by <important-group-id>
bd dep add <followup-epic-id> --blocked-by <minor-group-id>
```

The follow-up epic is created as soon as the review round completes, regardless of whether BLOCKERs are still being resolved. This ensures non-blocking improvements are tracked and not lost.

**After 3 review-fix cycles:** Any remaining IMPORTANT and MINOR findings both route to the FOLLOWUP epic. UAT proceeds immediately — it is NOT blocked on IMPORTANT or MINOR findings after cycle 3. The supervisor creates the FOLLOWUP epic and then advances to Phase 11.

### Follow-up Lifecycle (FOLLOWUP_* Phases)

The follow-up epic runs the same protocol phases with FOLLOWUP_* prefixed task types. This is NOT a flat task list — it is a full protocol re-run:

```
FOLLOWUP epic (aura:epic-followup)
  └── blocked-by: FOLLOWUP_URE         (Phase 2: scope which findings to address)
        └── blocked-by: FOLLOWUP_URD   (Phase 2: requirements for follow-up)
              └── blocked-by: FOLLOWUP_PROPOSAL-1  (Phase 3: proposal for follow-up)
                    └── blocked-by: FOLLOWUP_IMPL_PLAN  (Phase 8: decompose into slices)
                          ├── blocked-by: FOLLOWUP_SLICE-1  (Phase 9)
                          │     ├── blocked-by: important-leaf-task-...
                          │     └── blocked-by: minor-leaf-task-...
                          └── blocked-by: FOLLOWUP_SLICE-2
```

**Lifecycle steps:**
1. **Supervisor** creates FOLLOWUP_URE (same actor — scoping URE with user to determine which findings to address)
2. **Supervisor** creates FOLLOWUP_URD (same actor — requirements for follow-up scope)
3. **Supervisor → Architect (h6):** Hands off FOLLOWUP_URE + FOLLOWUP_URD to architect for FOLLOWUP_PROPOSAL creation
4. **Architect** creates FOLLOWUP_PROPOSAL-N (same review/ratify/UAT cycle applies)
5. **Architect → Supervisor (h1):** After FOLLOWUP_PROPOSAL ratified, hands off for FOLLOWUP_IMPL_PLAN
6. **Supervisor → Worker (h2):** FOLLOWUP_SLICE-N assignment with adopted leaf task IDs
7. **Supervisor → Reviewer (h3):** Code review of follow-up slices
8. **Worker → Reviewer (h4):** Follow-up slice completion, reports which original leaf tasks resolved

**Leaf task adoption (dual-parent):** When the supervisor creates FOLLOWUP_SLICE-N, the original IMPORTANT/MINOR leaf tasks gain a second parent — they are children of both the original severity group AND the follow-up slice.

**No followup-of-followup:** IMPORTANT/MINOR findings from follow-up code review are tracked on the existing follow-up epic. A nested follow-up epic is never created.

### Voting

Same binary voting as plan review: ACCEPT or REVISE.

All BLOCKERs must be resolved before proceeding. IMPORTANT and MINOR findings go to follow-up epic.

**Next (All BLOCKERs resolved, all reviewers ACCEPT):** Proceed to Phase 11 (Implementation UAT)

---

## Phase 11: Implementation UAT (`aura:p11-user`)

### User Approval

Present the completed implementation to the user for explicit approval, similar to Phase 5 but for code.

```bash
bd create --type=task --priority=2 \
  --title="UAT: Implementation acceptance for feature" \
  --description="---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  impl_plan: <impl-plan-task-id>
---
Implementation UAT" \
  --add-label "aura:p11-user:s11-uat"
```

If user approves: Proceed to Phase 12 (Landing).
If user requests changes: Loop back to appropriate phase.

---

## Phase 12: Landing (`aura:p12-impl`)

See [Session Completion](#session-completion-landing-the-plane) below.

---

## Worker Implementation Details

### Before Starting

Read your Beads task completely:
```bash
bd show <task-id>
```

Extract:
- `validation_checklist` - items you must verify
- `acceptance_criteria` - Given/When/Then specs you must satisfy
- `tradeoffs` - why certain decisions were made
- `ratified_plan` - link to larger context

### TDD Awareness

- **Layer 2 tests will fail** - this is normal until Layer 3 implementation exists
- **Layer 3 tests must pass** - if your implementation doesn't pass, it's not done
- **Don't fight TDD** - tests define the contract; implement to satisfy tests

### Implementation Checklist

- [ ] Read full Beads task with `bd show`
- [ ] Understand validation_checklist and acceptance_criteria
- [ ] Modify ONLY your assigned files (file-level ownership within your slice)
- [ ] Inject all dependencies (constructor DI, never hard-code)
- [ ] Validate external input at system boundaries
- [ ] Run type checking (must pass)
- [ ] Run tests (must pass)
- [ ] Mark task complete: `bd update <task-id> --status=done`

### Blockers

If you can't proceed:

```bash
bd update <task-id> --status=blocked
bd update <task-id> --notes="Blocked: Missing type definition. Waiting for: <dependency>"
```

Supervisor checks beads status and resolves or reassigns.

See: [../worker-blocked/SKILL.md](../worker-blocked/SKILL.md)

---

## Quality Assurance Throughout

### When to Run Tests

| Phase | What to Run | Must Pass? |
|-------|-------------|-----------|
| **L1: Types** | Type checking | **YES** |
| **L2: Tests** | Tests | NO (will fail) |
| **L3: Implementation** | Type checking + tests | **YES** |
| **Integration** | Integration tests | **YES** |
| **Before Commit** | All applicable | **YES** |

### Interpreting Failures

**Layer 2 Test Failures:**
- Expected! Tests import non-existent implementation.
- Proceed to Layer 3.
- Do NOT fix Layer 2 tests until Layer 3 exists.

**Layer 3 Test Failures After Implementation:**
- Your implementation is incomplete or wrong.
- Check `acceptance_criteria` - are all conditions met?
- Fix implementation to make tests pass.

**Failures in Unrelated Tests:**
- Example: You implemented feature X, but unrelated feature Y tests fail.
- This is NOT a blocker for your task (other workers own Y).
- Supervisor decides if layer continues or rollback.

### Rollback/Recovery

If a layer fails catastrophically:

```bash
# Revert commits:
git revert <commit-hash>

# Update beads:
bd update <all-tasks-in-layer> --status=blocked
bd update <layer-task> --notes="Layer rolled back due to X. Reassigning..."
```

Supervisor reassigns or revises approach.

---

## Monitoring & Status

### Check Progress Anytime

```bash
# Overall project health:
bd stats

# What's currently in progress:
bd list --labels="aura:p9-impl:s9-slice" --status=in_progress

# What's blocked:
bd list --labels="aura:p9-impl:s9-slice" --status=blocked
bd blocked

# What's ready (for supervisor):
bd ready

# Active proposals (not yet ratified):
bd list --labels="aura:p3-plan:s3-propose" --status=open

# Ratified plans awaiting implementation:
bd list --labels="aura:p6-plan:s6-ratify" --status=open
```

### Beads Query Reference

```bash
# Find all REQUEST tasks:
bd list --labels="aura:p1-user:s1_1-classify"

# Find all PROPOSAL-N in open status:
bd list --labels="aura:p3-plan:s3-propose" --status=open

# Find implementation slices:
bd list --labels="aura:p9-impl:s9-slice"

# Find tasks owned by you:
bd list --assignee=<your-name>

# Get detailed view:
bd show <task-id>

# Find severity groups for a review:
bd list --labels="aura:severity:blocker"
bd list --labels="aura:severity:important"
bd list --labels="aura:severity:minor"

# Find follow-up epics:
bd list --labels="aura:epic-followup"
```

See: [../status/SKILL.md](../status/SKILL.md)

---

## Coordination via Beads

All inter-agent coordination happens through beads task status and comments.

### Message Patterns

| Pattern | How | When |
|---------|-----|------|
| Task assignment | `bd update <task-id> --assignee=<worker>` | Supervisor assigns work |
| Task completion | `bd close <task-id>` + `bd comments add <task-id> "Done: ..."` | Worker finishes |
| Task blocked | `bd update <task-id> --status=blocked --notes="Reason"` | Worker is stuck |
| Review request | `bd comments add <task-id> "Review requested"` | Architect asks for review |
| Review vote | `bd comments add <task-id> "VOTE: ACCEPT - reason"` | Reviewer votes |
| State change | `bd comments add <task-id> "Phase 9 complete, proceeding to Phase 10"` | Supervisor announces |
| Supersede | `bd label add <id> aura:superseded` + comment | Architect supersedes old proposal |

### Supervisor Monitoring Loop

Supervisor continuously:

1. **Check beads for status updates:**
   ```bash
   bd list --labels="aura:p9-impl:s9-slice" --status=done
   bd list --labels="aura:p9-impl:s9-slice" --status=in_progress
   bd list --labels="aura:p9-impl:s9-slice" --status=blocked
   ```

2. **Review comments for progress:**
   ```bash
   bd comments <task-id>
   ```

3. **Decide next action:**
   - All slices done? → Proceed to Phase 10 (Code Review)
   - Some tasks blocked? → Resolve or reassign
   - Some tasks in progress? → Wait (don't block them)

4. **Repeat** until all slices complete

See: [../supervisor-track-progress/SKILL.md](../supervisor-track-progress/SKILL.md)

---

## Session Completion (Landing the Plane)

**Before you can say "done", you MUST complete this 7-step checklist:**

### 1. File Issues for Remaining Work

Create Beads tasks for anything discovered but not completed:

```bash
bd create --title="Follow-up: ..." --type=task --priority=3
```

### 2. Run Quality Gates

If code changed, run your project's quality gates. All must pass.

### 3. Update Issue Status

- Close completed tasks: `bd close <task-id>`
- Update in-progress: `bd update <task-id> --notes="..."`

### 4. Commit and Push (MANDATORY)

```bash
git add <changed-files>
bd sync
git agent-commit -m "feat(scope): Description of changes"
bd sync
git push
```

**Verify success:**
```bash
git status
# Must show: "Your branch is up to date with 'origin/...'"
```

### 5. Clean Up

```bash
# Clear stashes:
git stash clear

# Prune remote branches (optional):
git fetch --prune
```

### 6. Verify

```bash
git log --oneline -5  # Confirm commits are there
git push --dry-run     # Verify push would succeed
```

### 7. Hand Off

Create handoff document if actor transition occurs (see [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md)). Provide context for next session:
- Link to ratified plan (if applicable)
- Current phase (use phase number and label)
- Blockers or next steps
- Link to open issues

---

## Troubleshooting Decision Trees

### "My reviewer is stuck - keeps voting REVISE"

```
├─ Have you provided ACTIONABLE feedback?
│  └─ NO → Give specific suggestions, not just criticism
│  └─ YES → Continue
│
├─ Is feedback valid (aligns with acceptance_criteria)?
│  └─ NO → Explain why feedback is out of scope (respectfully)
│  └─ YES → Architect revises (creates PROPOSAL-N+1)
│
└─ > 3 revision rounds?
   └─ YES → Escalate to user: "Consensus not reachable. User decision needed."
   └─ NO → Continue revision loop
```

### "My worker reports TaskBlocked"

```
├─ Is the blocker valid?
│  └─ NO → Clarify why (update task); worker continues
│  └─ YES → Continue
│
├─ Can you resolve it?
│  ├─ YES → Create/unblock dependency task; notify worker
│  └─ NO → Reassign task to different worker; explain why
│
└─ Is blocker on critical path (blocks multiple workers)?
   └─ YES → Prioritize resolution
   └─ NO → Continue with other workers
```

### "Layer 2 tests are failing"

```
└─ Is this Layer 2 (test phase)?
   └─ YES → **EXPECTED!** Implementation doesn't exist yet.
   │        Proceed to Layer 3 immediately.
   │        Do NOT try to make tests pass in Layer 2.
   │
   └─ NO → Is this Layer 3+ (implementation phase)?
      └─ YES → This is a blocker. Implementation must make tests pass.
      └─ NO → Escalate; something is wrong with phase tracking
```

### "My layer has mixed success (some tasks done, some in progress)"

```
└─ Are all done tasks passing quality gates?
   └─ NO → Rerun failed tasks; don't proceed
   └─ YES → Continue
│
└─ Are blocked tasks on critical path (block other tasks)?
   └─ YES → Resolve blockers before proceeding to next layer
   └─ NO → Start next layer in parallel; return to blockers later
```

### "Tests are failing unrelated to my work"

```
└─ Is the failing test owned by another worker?
   └─ YES → Not your blocker. Notify supervisor; continue your work.
   │        Supervisor decides if layer continues or rollback.
   │
   └─ NO (owned by you) → Must resolve before marking task complete.
```

---

## Tools & Capabilities Matrix

### Architect Tools & Skills

| Tool | Purpose |
|------|---------|
| Explore | Map codebase, understand problem space |
| Read | Read existing code for context |
| Write, Edit | Document plan in Beads task |
| Bash | Git operations, running tests |
| Skill: aura:architect:propose-plan | Create PROPOSAL-N task |
| Skill: aura:architect:request-review | Spawn reviewers |
| Skill: aura:architect:ratify | Ratify proposal (Phase 6) |
| Skill: aura:architect:handoff | Handoff to supervisor (Phase 7) |

### Reviewer Tools & Skills

| Tool | Purpose |
|------|---------|
| Read, Glob, Grep | Read proposal, search code |
| Bash | Run tests to verify claims |
| Skill: aura:reviewer:review-plan | Evaluate proposal (Phase 4) |
| Skill: aura:reviewer:review-code | Evaluate implementation (Phase 10) |
| Skill: aura:reviewer:vote | Cast vote (ACCEPT/REVISE) |
| Skill: aura:reviewer:comment | Leave structured review comment (via Beads) |

### Supervisor Tools & Skills

| Tool | Purpose |
|------|---------|
| Bash | Git operations, run tests, launch agents |
| Read | Read ratified plan |
| Skill: aura:supervisor:plan-tasks | Create vertical slice decomposition (Phase 8) |
| Skill: aura:supervisor:spawn-worker | Launch workers (Phase 9) |
| Skill: aura:supervisor:track-progress | Monitor slice completion |
| Skill: aura:supervisor:commit | Atomic commit per layer (Phase 12) |

**Agent launching:**
```bash
# Launch supervisor/architect in-place (long-running, needs own tmux session)
aura-swarm start --swarm-mode intree --role supervisor -n 1 --prompt "..."

# Or use worktree mode for epic-based workflow
aura-swarm start --epic <id>

# For reviewers: use general-purpose subagents (Task tool) with /aura:reviewer skill — NOT aura-swarm start
```

### Worker Tools & Skills

| Tool | Purpose |
|------|---------|
| Read, Write, Edit | Implement assigned files |
| Glob, Grep | Understand dependencies |
| Bash | Run type checking, tests |
| Skill: aura:worker:implement | Write code for task |
| Skill: aura:worker:complete | Signal task done |
| Skill: aura:worker:blocked | Report blocker |

---

## Migration from v1

For migrating in-flight epics from v1 labels and conventions to v2, see [MIGRATION_v1_to_v2.md](MIGRATION_v1_to_v2.md).

---

## See Also

- [CONSTRAINTS.md](CONSTRAINTS.md) - Coding standards, checklists, naming conventions
- [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) - Standardized handoff document template
- [MIGRATION_v1_to_v2.md](MIGRATION_v1_to_v2.md) - Migration procedure from v1 to v2 labels
- `skills/` - Detailed agent role definitions
  - Architect: `aura:architect.md`
  - Reviewer: `aura:reviewer.md`
  - Supervisor: `aura:supervisor.md`
  - Worker: `aura:worker.md`
  - Cross-role: `aura:plan.md`, messaging, testing, status
