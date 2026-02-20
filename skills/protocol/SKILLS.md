# Command Reference

All `/aura:*` skills, organized by role and phase. Each skill is a `SKILL.md` file in its own directory under `skills/`.

See [AGENTS.md](AGENTS.md) for role definitions and phase ownership.

---

## Orchestration

| Command | Phase | Description |
|---------|-------|-------------|
| `/aura:epoch` | 1-12 | Master orchestrator for the full 12-phase workflow. Delegates to role-specific skills per phase. |
| `/aura:plan` | 1-6 | Plan coordination across roles (phases 1-6 subset). |
| `/aura:status` | any | Project status and monitoring via Beads queries. |

---

## User Interaction

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:user-request` | 1 | `aura:p1-user:s1_1-classify` | Capture user's feature request verbatim. Classify along 4 axes (scope, complexity, risk, domain novelty). Triggers parallel research and explore sub-steps. |
| `/aura:user-elicit` | 2 | `aura:p2-user:s2_1-elicit`, `aura:p2-user:s2_2-urd` | User Requirements Elicitation (URE) survey. Creates ELICIT task with full Q&A transcript and URD task as single source of truth. |
| `/aura:user-uat` | 5, 11 | `aura:p5-user:s5-uat`, `aura:p11-user:s11-uat` | User Acceptance Testing. Phase 5 tests the plan; Phase 11 tests the implementation. Uses structured demonstrative examples. |

---

## Architect

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:architect` | 1-7 | (multiple) | Main architect role. Coordinates specification, proposals, reviews, ratification, and handoff. |
| `/aura:architect-propose-plan` | 3 | `aura:p3-plan:s3-propose` | Create a PROPOSAL-N task with full technical plan. Includes public interfaces, implementation approach, validation checklist, and BDD acceptance criteria. |
| `/aura:architect-request-review` | 4 | `aura:p4-plan:s4-review` | Spawn 3 parallel reviewers with axis-specific focus. Creates PROPOSAL-N-REVIEW-{axis}-{round} tasks (A=Correctness, B=Test quality, C=Elegance). |
| `/aura:architect-ratify` | 6 | `aura:p6-plan:s6-ratify` | Ratify proposal after all 3 reviewers ACCEPT. Marks old proposals as `aura:superseded`. Creates placeholder IMPL_PLAN task for supervisor. |
| `/aura:architect-handoff` | 7 | `aura:p7-plan:s7-handoff` | Create handoff document (full inline provenance) and store at `.git/.aura/handoff/`. Transfers ownership to supervisor. |

---

## Supervisor

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:supervisor` | 7-12 | (multiple) | Main supervisor role. Receives handoff, decomposes plan, spawns workers, coordinates reviews, and lands code. |
| `/aura:supervisor-plan-tasks` | 8 | `aura:p8-impl:s8-plan` | Decompose ratified plan into vertical slices (SLICE-N tasks). Each slice = one production code path owned by one worker. |
| `/aura:supervisor-spawn-worker` | 9 | `aura:p9-impl:s9-slice` | Launch a worker agent for an assigned slice. Creates handoff document (summary + bd IDs). Worker must call `/aura:worker` at start. |
| `/aura:supervisor-track-progress` | 9-10 | `aura:p9-impl:s9-slice` | Monitor worker status via Beads. Check for blocked/complete/in-progress slices. |
| `/aura:supervisor-commit` | 12 | `aura:p12-impl:s12-landing` | Atomic commit per completed layer/slice. Uses `git agent-commit`. Syncs Beads and pushes. |

---

## Worker

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:worker` | 9 | `aura:p9-impl:s9-slice` | Main worker role. Reads slice assignment, implements full vertical (types → tests → impl → wiring). |
| `/aura:worker-implement` | 9 | `aura:p9-impl:s9-slice` | Implement the assigned vertical slice following TDD layers (L1 types, L2 tests, L3 implementation). |
| `/aura:worker-complete` | 9 | `aura:p9-impl:s9-slice` | Signal slice completion after all quality gates pass (typecheck + tests + production code path verified). |
| `/aura:worker-blocked` | 9 | `aura:p9-impl:s9-slice` | Report a blocker to the supervisor via Beads comment. |

---

## Reviewer

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:reviewer` | 4, 10 | `aura:p4-plan:s4-review`, `aura:p10-impl:s10-review` | Main reviewer role. Reviews plans (Phase 4) and code (Phase 10) against 3 axes. |
| `/aura:reviewer-review-plan` | 4 | `aura:p4-plan:s4-review` | Review a PROPOSAL-N against one axis (A/B/C). Binary vote: ACCEPT or REVISE. No severity tree for plan reviews. |
| `/aura:reviewer-review-code` | 10 | `aura:p10-impl:s10-review`, `aura:severity:*` | Review implementation slices against one axis. EAGER severity tree creation (BLOCKER/IMPORTANT/MINOR). |
| `/aura:reviewer-comment` | 4, 10 | — | Leave structured feedback on a Beads task. Utility command (no task creation). |
| `/aura:reviewer-vote` | 4, 10 | — | Cast ACCEPT or REVISE vote. Binary only. |

### Review Axes

| Axis | Letter | Focus | Key Questions |
|------|--------|-------|---------------|
| Correctness | A | Spirit and technicality | Does it faithfully serve the user's request? Technical consistency? |
| Test quality | B | Test strategy adequacy | Integration > unit? Mock deps not SUT? Shared fixtures? |
| Elegance | C | Complexity matching | Proportional to problem? No over/under-engineering? |

---

## Implementation Coordination

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:impl-slice` | 9 | `aura:p9-impl:s9-slice` | Vertical slice assignment and tracking. Manages slice creation, worker assignment, and progress aggregation. |
| `/aura:impl-review` | 10 | `aura:p10-impl:s10-review` | Code review coordination across all slices. Spawns 3 reviewers (A/B/C) who each review ALL slices. Creates severity tree per review round. |

---

## Messaging (Beads-based IPC)

| Command | Description |
|---------|-------------|
| `/aura:msg-send` | Send a message to another agent via Beads comment. |
| `/aura:msg-receive` | Check inbox for messages from other agents. |
| `/aura:msg-broadcast` | Broadcast a message to multiple agents. |
| `/aura:msg-ack` | Acknowledge received messages. |

---

## Research & Exploration

| Command | Phase | Label | Description |
|---------|-------|-------|-------------|
| `/aura:research` | 1 (s1_2), any | `aura:p1-user:s1_2-research` | Domain research — find standards, prior art, competing approaches. Writes structured findings to `docs/research/<topic>.md`. Depth-scoped: quick-scan, standard-research, deep-dive. |
| `/aura:explore` | 1 (s1_3), any | `aura:p1-user:s1_3-explore` | Codebase exploration — find integration points, existing patterns, dependencies, conflicts. Depth-scoped: quick-scan, standard-research, deep-dive. |

---

## Utilities

| Command | Description |
|---------|-------------|
| `/aura:test` | Run tests using BDD patterns. |
| `/aura:feedback` | Leave structured feedback on any Beads task. |

---

## Phase → Command Quick Reference

| Phase | Commands Used |
|-------|-------------|
| 1 — REQUEST | `/aura:user-request`, `/aura:research` (s1_2), `/aura:explore` (s1_3) |
| 2 — ELICIT + URD | `/aura:user-elicit` |
| 3 — PROPOSAL-N | `/aura:architect-propose-plan` |
| 4 — REVIEW | `/aura:architect-request-review`, `/aura:reviewer-review-plan`, `/aura:reviewer-vote` |
| 5 — Plan UAT | `/aura:user-uat` |
| 6 — Ratification | `/aura:architect-ratify` |
| 7 — Handoff | `/aura:architect-handoff` |
| 8 — IMPL_PLAN | `/aura:supervisor-plan-tasks` |
| 9 — SLICE-N | `/aura:supervisor-spawn-worker`, `/aura:worker-implement`, `/aura:worker-complete`, `/aura:impl-slice` |
| 10 — Code Review | `/aura:impl-review`, `/aura:reviewer-review-code`, `/aura:reviewer-vote` |
| 11 — Impl UAT | `/aura:user-uat` |
| 12 — Landing | `/aura:supervisor-commit` |
| Follow-up (post-10) | `/aura:supervisor` (create FOLLOWUP_URE/URD), `/aura:architect` (FOLLOWUP_PROPOSAL via h6), `/aura:supervisor-plan-tasks` (FOLLOWUP_IMPL_PLAN), `/aura:supervisor-spawn-worker` (FOLLOWUP_SLICE-N), `/aura:impl-review` (follow-up code review) |

---

## References

- [AGENTS.md](AGENTS.md) — Role taxonomy and handoff procedures
- [PROCESS.md](PROCESS.md) — Step-by-step workflow execution (single source of truth)
- [CONSTRAINTS.md](CONSTRAINTS.md) — Coding standards and naming conventions
