# Aura Protocol - Process Guide

**This is the single source of truth for Aura workflow execution.**

For agent role definitions and detailed tool references, see `.claude/commands/`.

---

## Quick Start (60 seconds)

**The Aura Protocol runs through 4 phases:**

```
REQUEST_PLAN → PROPOSE_PLAN → REVIEW_N → RATIFIED_PLAN → IMPLEMENTATION
   (1 phase)      (1 phase)   (parallel)    (1 phase)     (parallel layers)
```

**Check current progress:**
```bash
bd stats                                      # Project overview
bd list --labels="aura:plan:propose"          # Active proposals
bd list --labels="aura:impl" --status=in_progress  # Implementation progress
```

**Full sections below.** For detailed steps, see agent files in `.claude/commands/`.

---

## Phase 1: REQUEST_PLAN & PROPOSE_PLAN

### When to Trigger Planning

Start planning when:
- User submits a new feature request
- A blocker requires architectural decision
- Multi-phase work needs coordination

### REQUEST_PLAN Task

**What:** Capture user's problem statement as a Beads task.

```bash
bd create --type=feature --priority=2 \
  --title="REQUEST_PLAN: Brief description of need" \
  --description="Full user request with context, acceptance criteria"
```

Add label: `aura:plan:request`

**Who:** Usually user or coordinator creates this.

**Next:** Architect runs `/aura:user:elicit` for URE survey (Phase 2), then creates the URD.

### User Requirements Document (URD)

**What:** A single Beads task (label `aura:urd`) that serves as the single source of truth for user requirements, priorities, design choices, MVP goals, and end-vision goals.

**Lifecycle:**
- **Created** in Phase 2 (`aura:user:elicit`) with structured requirements from the URE survey
- **Linked** via `bd dep relate` (NOT `--blocked-by`) to REQUEST, ELICIT, PROPOSAL, IMPL_PLAN, and UAT tasks
- **Updated** via `bd comments add` whenever requirements/scope change (UAT results, ratification, user feedback)
- **Consulted** by architects, reviewers, and supervisors as the single source of truth for "what does the user want?"

**Why `relate` not `blocked-by`:** The URD is a peer reference document, not a blocking dependency. No phase waits on it; it accumulates information as phases progress.

```bash
# Create URD after elicitation
bd create --labels aura:urd \
  --title "URD: {{feature name}}" \
  --description "## Requirements
{{structured requirements from URE survey}}

## Priorities
{{user-stated priorities}}

## Design Choices
{{design decisions from elicitation}}

## MVP Goals
{{minimum viable scope}}

## End-Vision Goals
{{user's ultimate vision}}"

# Link URD to related tasks (peer reference, not blocking)
bd dep relate <urd-id> <request-id>
bd dep relate <urd-id> <elicit-id>
```

**Don't Forget About the URD!** Every agent should consult the URD before making decisions. When in doubt about requirements, `bd show <urd-id>` is your first stop.

### Dependencies

The canonical dependency chain flows top-down (parents blocked by children):

```
REQUEST
  └── blocked by ELICIT
        └── blocked by PROPOSAL
              └── blocked by RATIFIED_PLAN
                    └── blocked by IMPL_PLAN
                          ├── blocked by slice-1
                          │     ├── blocked by leaf-task-a
                          │     └── blocked by leaf-task-b
                          └── blocked by slice-2

URD ←──── bd dep relate ────→ (REQUEST, ELICIT, PROPOSAL, IMPL_PLAN, UAT)
```

**Rule:** `bd dep add <stays-open> --blocked-by <must-finish-first>`. The `--blocked-by` target is always the thing you do first. Work flows bottom-up; closure flows top-down.

**Next:** Architect spawns `/aura:architect:propose-plan` skill to explore and propose.

### PROPOSE_PLAN Task

**What:** Architect's full technical proposal including tradeoffs, interfaces, validation checklist, and BDD criteria.

**PROPOSE_PLAN must include:**

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
  --title="PROPOSE_PLAN: Technical proposal for RequestPlan" \
  --description="..." \
  --design="validation_checklist: [...], acceptance_criteria: [...]" \
  --add-label "aura:plan:propose"
```

Link dependency:
```bash
bd dep add <request-plan-id> --blocked-by <propose-plan-id>
```

**Next:** Architect runs `/aura:architect:request-review` to spawn 3 reviewers in **PARALLEL**.

See: [.claude/commands/aura:architect:propose-plan.md](.claude/commands/aura:architect:propose-plan.md)

---

## Phase 2: REVIEW_N (Parallel, Consensus Required)

### Spawning Reviewers

Architect spawns **3 independent reviewers** in parallel (not sequentially).

Spawn reviewers as **subagents** (via the Task tool) or coordinate via **TeamCreate**. Reviewers are short-lived — keep them in-session for direct result collection. Do NOT use `launch-parallel.py` for reviewer rounds.

> **CRITICAL: No Fake Reviews**
>
> The architect **MUST** spawn actual independent reviewer subagents. The architect **CANNOT**:
> - Write review comments pretending to be reviewers
> - Simulate votes by adding comments from the same actor
> - Skip the review phase by self-approving
>
> If the architect lacks permission to spawn subagents, it **MUST** ask the user for help rather than faking reviews. Reviews from the same actor do not count as independent consensus.

**Reviewer Selection:**
- **Plan Review:** Use generic end-user alignment perspective (NOT technical specialization)
- **Code Review (post-implementation):** Optional specialized reviewers (security, performance, etc.)

### Review Criteria (6 Questions)

Each reviewer assesses **end-user alignment**, not technical taste:

1. **Who are the end-users?** Can you name them?
2. **What do end-users want?** What problem does this solve for them?
3. **How will this affect them?** Positively? Any downsides?
4. **Are there implementation gaps?** Will the code actually deliver what's promised?
5. **Does MVP scope make sense?** Is it achievable without taking on too much?
6. **Is validation checklist complete?** Can each item be tested independently?

### Voting: ACCEPT vs REVISE

| Vote | Requirement |
|------|-------------|
| **ACCEPT** | All 6 criteria satisfied; no action items |
| **REVISE** | Issues found; must provide actionable feedback (not just criticism) |

**Documentation (via Beads comments):**
```bash
bd comments add <task-id> "VOTE: ACCEPT - [reason]"
# OR
bd comments add <task-id> "VOTE: REVISE - [specific issue]. Suggest: [fix]"
```

### Revision Loop

If any reviewer votes REVISE:

1. Architect reads feedback in task comments
2. Creates REVISION_N task with fixes
3. Re-spawns all 3 reviewers to re-assess
4. Loop until all 3 vote ACCEPT

**Max Revision Rounds:** No hard limit; use common sense. If > 3 rounds, escalate to user for decision.

**Next (All 3 ACCEPT):** Proceed to Phase 3 (Ratification)

See: [.claude/commands/aura:reviewer.md](.claude/commands/aura:reviewer.md)

---

## Phase 3: RATIFIED_PLAN & Handoff

### Consensus Requirement

**All 3 reviewers must vote ACCEPT.** No exceptions.

### Creating RATIFIED_PLAN

```bash
bd create --type=feature --priority=2 \
  --title="RATIFIED_PLAN: Consensus reached" \
  --description="Final version with all reviewer sign-offs" \
  --design="[copied from PROPOSE_PLAN with any revisions]" \
  --add-label "aura:plan:ratified"

# Link to propose plan:
bd dep add <propose-plan-id> --blocked-by <ratified-plan-id>

# Close propose plan:
bd close <propose-plan-id> --reason="Ratified as aura-xxxx"
```

### User Approval (Required!)

**DO NOT auto-proceed.** Present RATIFIED_PLAN to user for explicit approval.

The idea here is: the plan and the implementation MUST match with the user's end vision for the project.
The architect should also plan out several MVP milestones, in order to reach the user's vision.

The questions should not be general.

**BAD example:**
> "exactly matches feedback, mostly matches feedback, requires revisions, ..." . Questions should be about examples of how the requirements were met using various abstractions.

**GOOD example:**
> "Should this be statically-allocated, allocated at runtime, ...?"
> "Which of these variants we chose are appropriate, and why? Variant 1, main tradeoffs: ...; Variant N, ...."

The questions should address critical decisions in the software engineering design space.
User should be prompted with multiSelect, because the user can choose multiple tradeoffs/design choices.

The user should NOT be prompted with all questions at once, about all components. The user MUST be shown snippets of the definition, the implementation, and a motivating example. Then they should be asked several critical questions about one component at a time.

If user requests changes: Loop back to architect to revise.
If user approves: Proceed to IMPLEMENTATION_PLAN.

See: [.claude/commands/aura:architect:ratify.md](.claude/commands/aura:architect:ratify.md)

---

## Phase 4: IMPLEMENTATION (Layer Cake with TDD)

### Overview

Supervisor takes RATIFIED_PLAN and decomposes into **vertical slices** (production code paths).

**Key Principle:** Each worker owns a full vertical slice — types, tests, implementation, and wiring for one production code path.

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

### IMPLEMENTATION_PLAN Task

```bash
bd create --type=epic --priority=2 \
  --title="IMPLEMENTATION_PLAN: Vertical slice decomposition" \
  --description="Supervisor's breakdown of ratified plan into slices"
```

**Design field includes:**
- Vertical slice structure (which production code path per slice)
- Dependencies between slices (if any)
- Worker assignments
- Link to ratified plan

### Creating Vertical Slice Tasks

**One task per production code path.** Each worker owns the full vertical:

```bash
bd create --type=task --priority=2 \
  --title="[SLICE] Implement 'tool feature list' command (full vertical)" \
  --description="..." \
  --design="{validation_checklist: [...], acceptance_criteria: [...]}" \
  --add-label "aura:impl" \
  --add-label "slice:feature-list"
```

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

See: [.claude/commands/aura:worker:blocked.md](.claude/commands/aura:worker:blocked.md)

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
bd list --labels="aura:impl" --status=in_progress

# What's blocked:
bd list --labels="aura:impl" --status=blocked
bd blocked

# What's ready (for supervisor):
bd ready

# Active plans (not yet implemented):
bd list --labels="aura:plan:propose" --status=open
bd list --labels="aura:plan:ratified" --status=open
```

### Beads Query Reference

```bash
# Find all REQUEST_PLAN tasks:
bd list --labels="aura:plan:request"

# Find all PROPOSE_PLAN in open status:
bd list --labels="aura:plan:propose" --status=open

# Find implementation tasks by slice:
bd list --labels="aura:impl,slice:feature-list"

# Find tasks owned by you:
bd list --assignee=<your-name>

# Get detailed view:
bd show <task-id>
```

See: [.claude/commands/aura:status.md](.claude/commands/aura:status.md)

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
| State change | `bd comments add <task-id> "Layer 1 complete, proceeding to Layer 2"` | Supervisor announces |

### Supervisor Monitoring Loop

Supervisor continuously:

1. **Check beads for status updates:**
   ```bash
   bd list --labels="aura:impl" --status=done
   bd list --labels="aura:impl" --status=in_progress
   bd list --labels="aura:impl" --status=blocked
   ```

2. **Review comments for progress:**
   ```bash
   bd comments <task-id>
   ```

3. **Decide next action:**
   - All tasks in layer done? → Commit and move to next layer
   - Some tasks blocked? → Resolve or reassign
   - Some tasks in progress? → Wait (don't block them)

4. **Repeat** until all layers complete

See: [.claude/commands/aura:supervisor:track-progress.md](.claude/commands/aura:supervisor:track-progress.md)

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

Provide context for next session:
- Link to ratified plan (if applicable)
- Current phase (REQUEST/PROPOSE/REVIEW/RATIFIED/IMPL)
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
│  └─ YES → Architect revises
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
| Skill: aura:architect:propose-plan | Create PROPOSE_PLAN task |
| Skill: aura:architect:request-review | Spawn reviewers |
| Skill: aura:architect:ratify | Create RATIFIED_PLAN |
| Skill: aura:architect:handoff | Handoff to supervisor |

### Reviewer Tools & Skills

| Tool | Purpose |
|------|---------|
| Read, Glob, Grep | Read proposal, search code |
| Bash | Run tests to verify claims |
| Skill: aura:reviewer:review-plan | Evaluate proposal |
| Skill: aura:reviewer:vote | Cast vote |
| Skill: aura:reviewer:comment | Leave structured review comment (via Beads) |

### Supervisor Tools & Skills

| Tool | Purpose |
|------|---------|
| Bash | Git operations, run tests, launch agents |
| Read | Read ratified plan |
| Skill: aura:supervisor:plan-tasks | Create vertical slice decomposition |
| Skill: aura:supervisor:spawn-worker | Launch workers |
| Skill: aura:supervisor:track-progress | Monitor layer completion |
| Skill: aura:supervisor:commit | Atomic commit per layer |

**Agent launching:**
```bash
# Launch supervisor/architect via launch-parallel.py (long-running, needs own tmux session)
~/codebases/dayvidpham/aura-scripts/launch-parallel.py --role supervisor -n 1 --prompt "..."

# Or use aura-swarm for epic-based worktree workflow
~/codebases/dayvidpham/aura-scripts/aura-swarm start --epic <id>

# For reviewers: use subagents (Task tool) or TeamCreate — NOT launch-parallel.py
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

## See Also

- [CONSTRAINTS.md](CONSTRAINTS.md) - Coding standards, checklists, naming conventions
- `.claude/commands/` - Detailed agent role definitions
  - Architect: `aura:architect.md`
  - Reviewer: `aura:reviewer.md`
  - Supervisor: `aura:supervisor.md`
  - Worker: `aura:worker.md`
  - Cross-role: `aura:plan.md`, messaging, testing, status
