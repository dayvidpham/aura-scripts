# Agent Roles and Phase Ownership

This document maps each agent role to its owned phases, available tools/skills, and handoff procedures.

See [PROCESS.md](PROCESS.md) for the full step-by-step workflow. See [SKILLS.md](SKILLS.md) for the complete command reference.

---

## Role Summary

| Role | Phases Owned | Primary Responsibility |
|------|-------------|----------------------|
| **Epoch** | 1-12 (orchestrator) | Master orchestrator; delegates to other roles per phase |
| **Architect** | 1-7 | Specs, tradeoffs, proposals, review coordination, ratification, handoff |
| **Reviewer** | 4, 10 | End-user alignment review for plans (P4) and code (P10) |
| **Supervisor** | 7-12 | Task decomposition, worker allocation, review coordination, landing |
| **Worker** | 9 | Vertical slice implementation (full production code path) |

---

## Epoch (Orchestrator)

**Command:** `/aura:epoch`

**Phases:** All 12 (delegates to specialists)

**Responsibility:** Coordinates the full 12-phase workflow. Creates the initial REQUEST task, invokes the appropriate role skill for each phase, and ensures dependency chaining and audit trail preservation throughout.

**Skills invoked:**
- Phase 1: `/aura:user:request`
- Phase 2: `/aura:user:elicit`
- Phases 3-7: `/aura:architect`
- Phases 5, 11: `/aura:user:uat`
- Phases 7-10: `/aura:supervisor`
- Phase 12: Manual git commit and push

---

## Architect

**Command:** `/aura:architect`

**Phases owned:** 1-7

| Phase | Label | Skill | What Happens |
|-------|-------|-------|-------------|
| 1 | `aura:p1-user:s1_1-classify` | `/aura:user:request` | Classify request along 4 axes |
| 1 | `aura:p1-user:s1_2-research` | (parallel agent) | Domain research |
| 1 | `aura:p1-user:s1_3-explore` | (parallel agent) | Codebase exploration |
| 2 | `aura:p2-user:s2_1-elicit` | `/aura:user:elicit` | URE survey with user |
| 2 | `aura:p2-user:s2_2-urd` | (within elicit) | Create URD task |
| 3 | `aura:p3-plan:s3-propose` | `/aura:architect:propose-plan` | Create PROPOSAL-N |
| 4 | `aura:p4-plan:s4-review` | `/aura:architect:request-review` | Spawn 3 axis-specific reviewers |
| 5 | `aura:p5-user:s5-uat` | `/aura:user:uat` | Plan UAT with user |
| 6 | `aura:p6-plan:s6-ratify` | `/aura:architect:ratify` | Ratify proposal, mark old as superseded |
| 7 | `aura:p7-plan:s7-handoff` | `/aura:architect:handoff` | Create handoff document, hand off to supervisor |

**Receives from:** User (Phase 1 request)
**Hands off to:** Supervisor (Phase 7 handoff document at `.git/.aura/handoff/`)

**Handoff document:** Full inline provenance — includes all task references (REQUEST, URD, PROPOSAL, ratified plan), key decisions with rationale, open items, and acceptance criteria.

---

## Reviewer

**Command:** `/aura:reviewer`

**Phases owned:** 4 (plan review), 10 (code review)

### Plan Review (Phase 4)

| Axis | Label | Focus |
|------|-------|-------|
| A — Correctness | `aura:p4-plan:s4-review` | Does the plan faithfully serve the user's request? Technical consistency? |
| B — Test quality | `aura:p4-plan:s4-review` | Are test strategies adequate? Integration > unit? Mock deps not SUT? |
| C — Elegance | `aura:p4-plan:s4-review` | Is complexity proportional to the problem? No over/under-engineering? |

**Task title:** `PROPOSAL-N-REVIEW-{axis}-{round}` (e.g., `PROPOSAL-2-REVIEW-A-1`)

**Votes:** Binary — ACCEPT or REVISE. No intermediate levels. All 3 must ACCEPT.

**No severity tree** for plan reviews — binary vote only.

### Code Review (Phase 10)

Same 3 axes, applied to implementation slices.

**Task title:** `SLICE-N-REVIEW-{axis}-{round}` (e.g., `SLICE-1-REVIEW-A-1`)

**Severity tree (EAGER creation):** Always create 3 severity groups per review round:
- `aura:severity:blocker` — Blocks the slice
- `aura:severity:important` — Tracked in follow-up epic
- `aura:severity:minor` — Tracked in follow-up epic

Empty groups are closed immediately.

**Skills:** `/aura:reviewer:review-plan`, `/aura:reviewer:review-code`, `/aura:reviewer:comment`, `/aura:reviewer:vote`

**Receives from:** Architect (Phase 4) or Supervisor (Phase 10)
**Hands off to:** Architect (Phase 4 results) or Supervisor/Followup (Phase 10 findings)

---

## Supervisor

**Command:** `/aura:supervisor`

**Phases owned:** 7-12

| Phase | Label | Skill | What Happens |
|-------|-------|-------|-------------|
| 7 | `aura:p7-plan:s7-handoff` | (receives handoff) | Read architect handoff document |
| 8 | `aura:p8-impl:s8-plan` | `/aura:supervisor:plan-tasks` | Decompose ratified plan into vertical slices |
| 9 | `aura:p9-impl:s9-slice` | `/aura:supervisor:spawn-worker` | Spawn workers, assign slices |
| 9-10 | — | `/aura:supervisor:track-progress` | Monitor worker status |
| 10 | `aura:p10-impl:s10-review` | `/aura:impl:review` | Spawn 3 code reviewers per slice |
| 11 | `aura:p11-user:s11-uat` | `/aura:user:uat` | Implementation UAT with user |
| 12 | `aura:p12-impl:s12-landing` | `/aura:supervisor:commit` | Atomic commit, push, hand off |

**Receives from:** Architect (Phase 7 handoff document)
**Hands off to:** Workers (Phase 9 slice assignments), Reviewers (Phase 10), User (Phase 11 UAT)

**Key constraints:**
- Never implements code — always spawns workers
- Each production code path owned by exactly ONE worker
- Creates follow-up epic (`aura:epic-followup`) when code review has IMPORTANT/MINOR findings

---

## Worker

**Command:** `/aura:worker`

**Phases owned:** 9

| Phase | Label | Skill | What Happens |
|-------|-------|-------|-------------|
| 9 | `aura:p9-impl:s9-slice` | `/aura:worker:implement` | Implement assigned vertical slice |
| 9 | — | `/aura:worker:complete` | Signal completion after quality gates |
| 9 | — | `/aura:worker:blocked` | Report blockers to supervisor |

**Receives from:** Supervisor (Phase 9 slice assignment with handoff document)
**Hands off to:** Reviewer (Phase 10 via supervisor)

**Vertical slice ownership:** Worker owns the full vertical — types, tests, implementation, and wiring. Within the slice, follows TDD layers:
1. Layer 1: Types and schemas
2. Layer 2: Tests (import production code — will fail initially)
3. Layer 3: Implementation + wiring (make tests pass)

**Completion gates:**
1. Type checking passes
2. Tests pass
3. Production code path verified via code inspection (no TODOs, real deps wired)
4. Update Beads task with completion comment

---

## Handoff Matrix

| # | From | To | Phase | Document Location | Content Level |
|---|------|----|-------|-------------------|--------------|
| 1 | Architect | Supervisor | 7 | `.git/.aura/handoff/{request-id}/architect-to-supervisor.md` | Full inline provenance |
| 2 | Supervisor | Worker | 9 | `.git/.aura/handoff/{request-id}/supervisor-to-worker.md` | Summary + bd IDs |
| 3 | Supervisor | Reviewer | 10 | `.git/.aura/handoff/{request-id}/supervisor-to-reviewer.md` | Summary + bd IDs |
| 4 | Worker | Reviewer | 10 | `.git/.aura/handoff/{request-id}/worker-to-reviewer.md` | Summary + bd IDs |
| 5 | Reviewer | Followup | post-10 | `.git/.aura/handoff/{request-id}/reviewer-to-followup.md` | Summary + bd IDs |

**Same-actor transitions** (no handoff needed): Plan UAT → Ratify (Phase 5→6), Ratify → Handoff (Phase 6→7) — both performed by the architect.

See [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) for the standardized template.

---

## References

- [PROCESS.md](PROCESS.md) — Step-by-step workflow execution (single source of truth)
- [SKILLS.md](SKILLS.md) — Complete command reference
- [CONSTRAINTS.md](CONSTRAINTS.md) — Coding standards and naming conventions
- [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) — Handoff document template
