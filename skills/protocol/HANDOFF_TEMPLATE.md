# Handoff Document Template

Standardized template for all 6 actor-change transitions in the Aura protocol.

**Storage:** `.git/.aura/handoff/{request-task-id}/{source}-to-{target}.md`

---

## Transitions Overview

| # | From | To | When | Content Level |
|---|------|-----|------|---------------|
| 1 | Architect | Supervisor | Phase 7 (Handoff) | Full inline provenance |
| 2 | Supervisor | Worker | Phase 9 (Slice assignment) | Summary + bd IDs |
| 3 | Supervisor | Reviewer | Phase 10 (Code review) | Summary + bd IDs |
| 4 | Worker | Reviewer | Phase 10 (Code review) | Summary + bd IDs |
| 5 | Reviewer | Followup | After Phase 10 (Follow-up epic) | Summary + bd IDs |
| 6 | Supervisor | Architect | Follow-up lifecycle (FOLLOWUP_URE/URD → FOLLOWUP_PROPOSAL) | Summary + bd IDs |

### Same-Actor Transitions (NO Handoff Needed)

These transitions are performed by the same actor and do not require a handoff document:
- **Plan UAT → Ratify** (Phase 5 → Phase 6): Architect performs both
- **Ratify → Handoff** (Phase 6 → Phase 7): Architect performs both

---

## Template Structure

```markdown
# Handoff: {{SOURCE_ROLE}} → {{TARGET_ROLE}}

## Metadata
- **Request:** {{REQUEST_TASK_ID}} — {{REQUEST_TITLE}}
- **Date:** {{YYYY-MM-DD}}
- **Source:** {{SOURCE_ROLE}} ({{SOURCE_AGENT_ID}})
- **Target:** {{TARGET_ROLE}}

## Task References
- **Request:** {{request-task-id}}
- **URD:** {{urd-task-id}}
- **Proposal:** {{proposal-task-id}}
- **Ratified Plan:** {{ratified-task-id}}  <!-- if applicable -->
- **Impl Plan:** {{impl-plan-task-id}}    <!-- if applicable -->
- **Slice:** {{slice-task-id}}            <!-- if applicable -->

## Context
{{BRIEF_DESCRIPTION_OF_WHAT_WAS_DONE_AND_WHY}}

## Key Decisions
{{LIST_OF_CRITICAL_DESIGN_DECISIONS_AND_THEIR_RATIONALE}}

## Open Items
{{ANYTHING_THE_TARGET_NEEDS_TO_BE_AWARE_OF}}

## Acceptance Criteria
{{WHAT_THE_TARGET_MUST_DELIVER}}
```

---

## Required Fields Per Transition

| Field | h1: Arch→Super | h2: Super→Worker | h3: Super→Reviewer | h4: Worker→Reviewer | h5: Reviewer→Followup | h6: Super→Architect |
|-------|----------------|-------------------|--------------------|--------------------|----------------------|---------------------|
| Request | Required | Required | Required | Required | Required | Required |
| URD | Required | Required | Required | Required | Required | Required |
| Proposal | Required | Required | Required | — | Required | — |
| Ratified Plan | Required | Required | Required | — | — | — |
| Impl Plan | — | Required | Required | Required | — | — |
| Slice | — | Required | — | Required | — | — |
| Followup Epic | — | — | — | — | Required | Required |
| Followup URE | — | — | — | — | — | Required |
| Followup URD | — | — | — | — | — | Required |
| Findings Summary | — | — | — | — | Required | Required |
| Context | Full provenance | Summary | Summary | Summary | Summary | Summary |
| Key Decisions | Full list | Slice-relevant | Review scope | Impl decisions | Findings summary | Scoping decisions |
| Open Items | Required | Required | — | Required | Required | Required |
| Acceptance Criteria | Required | Required | Required | — | Required | Required |

---

## Examples

### 1. Architect → Supervisor (Full Inline Provenance)

```markdown
# Handoff: Architect → Supervisor

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Date:** 2026-02-20
- **Source:** Architect (architect-agent-1)
- **Target:** Supervisor

## Task References
- **Request:** aura-scripts-abc
- **URD:** aura-scripts-def
- **Proposal:** aura-scripts-ghi (PROPOSAL-2, ratified)
- **Ratified Plan:** aura-scripts-jkl

## Context
User requested structured logging across all CLI commands. After URE survey,
user prioritized JSON output format and log-level filtering. PROPOSAL-1 was
superseded (used plain-text format); PROPOSAL-2 adopted JSON with slog and
was ratified after 1 revision round (3/3 ACCEPT).

## Key Decisions
1. **slog over zerolog:** User prefers stdlib compatibility; slog is Go stdlib.
2. **JSON output only (no plain-text):** User confirmed JSON-only in UAT.
3. **Log levels via env var:** LOG_LEVEL env var, not CLI flag, per user preference.
4. **No file output in MVP:** Console-only; file output deferred to follow-up epic.

## Open Items
- Reviewer suggested adding request-id correlation; deferred to follow-up.
- Performance benchmark not yet run; add to code review checklist.

## Acceptance Criteria
- All CLI commands emit structured JSON logs via slog
- LOG_LEVEL env var controls verbosity (debug, info, warn, error)
- No secrets appear in log output
- Tests verify log output format
```

### 2. Supervisor → Worker (Summary + bd IDs)

```markdown
# Handoff: Supervisor → Worker

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Date:** 2026-02-20
- **Source:** Supervisor (supervisor-agent-1)
- **Target:** Worker (SLICE-1 owner)

## Task References
- **Request:** aura-scripts-abc
- **URD:** aura-scripts-def
- **Proposal:** aura-scripts-ghi
- **Ratified Plan:** aura-scripts-jkl
- **Impl Plan:** aura-scripts-mno
- **Slice:** aura-scripts-pqr (SLICE-1)

## Context
SLICE-1 covers the core logging infrastructure: slog handler setup, JSON
formatter, and LOG_LEVEL env var parsing. Other slices depend on this.

## Key Decisions
1. Use slog.Handler interface for testability (inject mock handler in tests).
2. Parse LOG_LEVEL at startup, not per-call.

## Open Items
- SLICE-2 (CLI integration) depends on SLICE-1 completing first.

## Acceptance Criteria
- See bd task aura-scripts-pqr for full validation_checklist and acceptance_criteria.
```

### 3. Supervisor → Reviewer (Summary + bd IDs)

```markdown
# Handoff: Supervisor → Reviewer

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Date:** 2026-02-20
- **Source:** Supervisor (supervisor-agent-1)
- **Target:** Reviewer

## Task References
- **Request:** aura-scripts-abc
- **URD:** aura-scripts-def
- **Proposal:** aura-scripts-ghi
- **Ratified Plan:** aura-scripts-jkl
- **Impl Plan:** aura-scripts-mno

## Context
All 3 slices are complete. Code review covers the full implementation
against the ratified plan and URD requirements.

## Key Decisions
1. Review against URD priorities: JSON format, log-level filtering, no secrets in logs.
2. Check all 3 slices for consistency in slog handler usage.

## Acceptance Criteria
- Review all slices for end-user alignment (6 review criteria).
- Create severity groups (BLOCKER, IMPORTANT, MINOR) per EAGER creation rule.
- Vote ACCEPT or REVISE per slice.
```

### 4. Worker → Reviewer (Summary + bd IDs)

```markdown
# Handoff: Worker → Reviewer

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Date:** 2026-02-20
- **Source:** Worker (worker-slice-1)
- **Target:** Reviewer

## Task References
- **Request:** aura-scripts-abc
- **URD:** aura-scripts-def
- **Impl Plan:** aura-scripts-mno
- **Slice:** aura-scripts-pqr (SLICE-1)

## Context
SLICE-1 implements the core logging infrastructure. All quality gates pass
(type checking + tests). Production code path verified via code inspection.

## Key Decisions
1. Used slog.NewJSONHandler with os.Stderr as default output.
2. LOG_LEVEL parsed once at init() via env.MustGet("LOG_LEVEL").

## Open Items
- Consider adding log rotation in follow-up (not in scope for MVP).

## Acceptance Criteria
- See bd task aura-scripts-pqr for validation_checklist completion status.
```

### 5. Reviewer → Followup (Summary + bd IDs)

```markdown
# Handoff: Reviewer → Followup

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Date:** 2026-02-20
- **Source:** Reviewer (reviewer-A)
- **Target:** Followup (Supervisor creates follow-up epic)

## Task References
- **Request:** aura-scripts-abc
- **URD:** aura-scripts-def
- **Proposal:** aura-scripts-ghi

## Context
Code review complete. 0 BLOCKERs, 2 IMPORTANT, 1 MINOR findings.
Follow-up epic needed for non-blocking improvements.

## Key Decisions
1. IMPORTANT: Add request-id correlation to all log entries (cross-cutting).
2. IMPORTANT: Add performance benchmark for high-throughput logging paths.
3. MINOR: Rename LogConfig → LoggingConfig for consistency with project naming.

## Open Items
- All findings above should be tracked as tasks in the follow-up epic.

## Acceptance Criteria
- Follow-up epic created with label `aura:epic-followup`.
- All IMPORTANT and MINOR findings captured as individual tasks.
```

---

## Follow-up Lifecycle Handoffs

The follow-up epic runs the same protocol phases using 6 handoff types (h1-h5 reused from the main lifecycle, plus h6 unique to the follow-up lifecycle), scoped to the follow-up epic.

**Storage:** `.git/.aura/handoff/{followup-epic-id}/{source}-to-{target}.md`

### Handoff Chain Through Follow-up Lifecycle

| Order | Handoff | Description |
|-------|---------|-------------|
| 1 | **Reviewer → Followup (h5)** | Bridge from original review. Created by supervisor when IMPORTANT/MINOR findings exist. **Starts** the follow-up lifecycle. |
| 2 | *(same actor — no handoff)* | Supervisor creates FOLLOWUP_URE (scoping which findings to address). |
| 3 | *(same actor — no handoff)* | Supervisor creates FOLLOWUP_URD (synthesizes follow-up requirements). |
| 4 | **Supervisor → Architect (h6)** | Supervisor hands off completed FOLLOWUP_URE + FOLLOWUP_URD to architect for FOLLOWUP_PROPOSAL creation. Follow-up specific handoff. |
| 5 | **Architect → Supervisor (h1)** | After FOLLOWUP_PROPOSAL is ratified, architect hands off to supervisor for FOLLOWUP_IMPL_PLAN. References original URD + FOLLOWUP_URD + outstanding findings. |
| 6 | **Supervisor → Worker (h2)** | FOLLOWUP_SLICE-N assignment. Worker receives follow-up slice spec AND original leaf task IDs to resolve. |
| 7 | **Supervisor → Reviewer (h3)** | Code review of follow-up slices. Reviewer receives follow-up context + original findings being addressed. |
| 8 | **Worker → Reviewer (h4)** | Worker completes follow-up slice. Handoff includes which original leaf tasks were resolved. |

### 6. Supervisor → Architect (Follow-up Lifecycle — h6)

```markdown
# Handoff: Supervisor → Architect (Follow-up)

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Follow-up Epic:** aura-scripts-xyz — FOLLOWUP: Non-blocking improvements
- **Date:** 2026-02-25
- **Source:** Supervisor
- **Target:** Architect

## Task References
- **Original Request:** aura-scripts-abc
- **Original URD:** aura-scripts-def
- **Follow-up Epic:** aura-scripts-xyz
- **FOLLOWUP_URE:** aura-scripts-stu
- **FOLLOWUP_URD:** aura-scripts-uvw

## Context
Supervisor completed FOLLOWUP_URE with user (scoped 2 IMPORTANT findings
for this cycle) and synthesized FOLLOWUP_URD. Handing off to architect
for FOLLOWUP_PROPOSAL creation.

## Findings Summary
| Finding ID | Severity | Original Slice | Scoped? | Description |
|-----------|----------|----------------|---------|-------------|
| aura-scripts-111 | IMPORTANT | SLICE-1 | Yes | Request-id correlation |
| aura-scripts-222 | IMPORTANT | SLICE-2 | Yes | Performance benchmark |
| aura-scripts-333 | MINOR | SLICE-1 | No (deferred) | Rename LogConfig |

## Key Decisions
1. User scoped 2 of 3 findings for this follow-up cycle.
2. MINOR finding deferred — user considers it low-priority.

## Open Items
- MINOR finding aura-scripts-333 remains unscoped for future follow-up.

## Acceptance Criteria
- FOLLOWUP_PROPOSAL accounts for original URD + FOLLOWUP_URD.
- Proposal covers both scoped IMPORTANT findings.
- Standard review process (3 reviewers) applies.
```

### Key Differences from Original Handoffs

- **h5 is the entry point**: The Reviewer → Followup handoff bridges the original epic to the follow-up lifecycle. It provides the initial context.
- **Follow-up handoffs reference both epics**: Task References section includes both the original request/URD and the follow-up epic/FOLLOWUP_URD.
- **Worker handoff (h2) includes leaf task IDs**: The Supervisor → Worker handoff for FOLLOWUP_SLICE-N must list the specific IMPORTANT/MINOR leaf tasks the worker is adopting.
- **Worker completion (h4) reports resolution**: The Worker → Reviewer handoff for follow-up slices reports which original leaf tasks were resolved.

### Example: Supervisor → Worker for Follow-up Slice

```markdown
# Handoff: Supervisor → Worker (Follow-up)

## Metadata
- **Request:** aura-scripts-abc — REQUEST: Add structured logging
- **Follow-up Epic:** aura-scripts-xyz — FOLLOWUP: Non-blocking improvements
- **Date:** 2026-02-25
- **Source:** Supervisor
- **Target:** Worker (FOLLOWUP_SLICE-1 owner)

## Task References
- **Original Request:** aura-scripts-abc
- **Original URD:** aura-scripts-def
- **Follow-up Epic:** aura-scripts-xyz
- **FOLLOWUP_URD:** aura-scripts-uvw
- **FOLLOWUP_IMPL_PLAN:** aura-scripts-stu
- **Slice:** aura-scripts-pqr (FOLLOWUP_SLICE-1)

## Context
FOLLOWUP_SLICE-1 addresses 2 IMPORTANT findings from the original code review:
request-id correlation and performance benchmarking.

## Adopted Leaf Tasks
| Leaf Task ID | Severity | Original Slice | Description |
|-------------|----------|----------------|-------------|
| aura-scripts-111 | IMPORTANT | SLICE-1 | Add request-id correlation to log entries |
| aura-scripts-222 | IMPORTANT | SLICE-2 | Performance benchmark for high-throughput paths |

## Key Decisions
1. Correlation ID passed via context.Context (not global state).
2. Benchmark uses Go's testing.B framework.

## Open Items
- None

## Acceptance Criteria
- Both adopted leaf tasks resolved (tests pass, production code path verified).
- See bd task aura-scripts-pqr for full validation_checklist.
```
