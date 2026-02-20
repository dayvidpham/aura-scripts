# Aura Protocol Constraints

Common constraints referenced by all agent and skill files.

## Coding Standards

**Given** shared resources **when** modifying **then** use atomic operations with timeouts **should never** check-then-act

**Given** external input **when** parsing **then** validate at system boundaries with the project's schema/validation tooling **should never** trust raw input or cast types unsafely

**Given** parallel work **when** assigning files **then** ensure each file has exactly one owner with atomic commits **should never** have multiple workers on same file

**Given** a feature request **when** writing requirements **then** use Given/When/Then/Should,Should Not format **should never** write vague criteria

**Given** a class or struct with dependencies **when** designing **then** inject all deps (including clocks, loggers) **should never** hard-code

**Given** runtime events **when** logging **then** use structured logging with context **should never** log secrets or use unstructured print statements

**Given** status/type fields **when** defining **then** use strongly-typed enums **should never** use bare strings at API boundaries

**Given** code changes **when** committing **then** type checking and tests must pass **should never** allow optional CI

**Given** task is implemented **when** you are about to commit **then** you **should** use `git agent-commit -m ...`, **should never** use `git commit -m ...`

**Given** you want to execute Beads **when** you are about to call `bd <command> ...` **then** you **should never** `cd <repo_root> && bd <command> ...`, instead you **should** always just call `bd <command> ...`

## Checklists

### Security
- No secrets in code or logs
- Input validated at all boundaries
- No SQL/command injection vectors
- File permissions 0o600 for sensitive data

### Scalability
- No N+1 queries or unbounded loops
- All collections have bounded sizes
- Resource cleanup (timeouts, `defer`/`finally`, `.Close()`)

### Correctness
- Tests cover happy path AND error cases
- Types strict (no `any`, proper discriminated unions or typed enums)
- BDD acceptance criteria met
- Production code path verified via code inspection

## Vote Levels

| Vote | Meaning |
|------|---------|
| ACCEPT | No BLOCKER issues; all review criteria satisfied |
| REVISE | BLOCKER issues found; must provide actionable feedback |

Binary only. No intermediate levels.

## Issue Severity

| Severity | When to Use | Blocks |
|----------|-------------|--------|
| BLOCKER | Security, type errors, test failures, broken production code paths | Yes |
| IMPORTANT | Performance, missing validation, architectural concerns | No (tracked in follow-up epic) |
| MINOR | Style, optional optimizations, naming improvements | No (tracked in follow-up epic) |

**EAGER severity group creation:** For every code review round (Phase 10), ALWAYS create 3 severity group tasks (BLOCKER, IMPORTANT, MINOR) immediately. Empty groups have no children and are closed immediately. This is NOT lazy creation.

**Follow-up epic:** When a review round completes and ANY IMPORTANT or MINOR findings exist, the Supervisor creates a follow-up epic (label `aura:epic-followup`). This is NOT gated on BLOCKER resolution — it triggers as soon as the review round completes.

**Follow-up lifecycle:** The follow-up epic runs the same protocol phases with FOLLOWUP_* prefixed task types: FOLLOWUP_URE → FOLLOWUP_URD → FOLLOWUP_PROPOSAL → FOLLOWUP_IMPL_PLAN → FOLLOWUP_SLICE-N. The supervisor creates FOLLOWUP_URE and FOLLOWUP_URD, then hands off to architect via h6 for FOLLOWUP_PROPOSAL. Original IMPORTANT/MINOR leaf tasks are adopted by FOLLOWUP_SLICE-N (dual-parent: original severity group + follow-up slice).

**No followup-of-followup:** IMPORTANT/MINOR findings from FOLLOWUP_SLICE code review are tracked on the existing follow-up epic as tasks. A nested follow-up-of-followup epic is never created.

## Beads Task Naming & Tagging Standards

All work flows through Beads with standardized titles and the v2 label schema:

### Label Schema

```
Format: aura:p{phase}-{domain}:s{step}-{type}

Phase-domain pairs (12 phases):
  aura:p1-user     — Request + classify + research + explore
  aura:p2-user     — Elicit + URD
  aura:p3-plan     — Propose
  aura:p4-plan     — Plan review
  aura:p5-user     — Plan UAT
  aura:p6-plan     — Ratify
  aura:p7-plan     — Handoff
  aura:p8-impl     — Impl plan
  aura:p9-impl     — Worker slices
  aura:p10-impl    — Code review
  aura:p11-user    — Impl UAT
  aura:p12-impl    — Landing

Special labels:
  aura:urd                  — User Requirements Document
  aura:superseded           — Superseded proposal/plan
  aura:severity:blocker     — Blocker severity group
  aura:severity:important   — Important severity group
  aura:severity:minor       — Minor severity group
  aura:epic-followup        — Follow-up epic
```

### Planning Phase Tasks

| Title Format | Label | Purpose | Created By |
|---|---|---|---|
| `REQUEST: Description` | `aura:p1-user:s1_1-classify` | Capture user's problem statement | User or Coordinator |
| `PROPOSAL-N: Description` | `aura:p3-plan:s3-propose` | Architect's full technical proposal (N increments per revision) | Architect |
| `PROPOSAL-N-REVIEW-{axis}-{round}: Description` | `aura:p4-plan:s4-review` | Reviewer assessment of proposal N (axis=A/B/C, round=1,2,...) | Reviewers (spawned by architect) |
| `URD: Description` | `aura:urd` | Single source of truth for user requirements | Architect (after Phase 2 URE) |

### Implementation Phase Tasks

| Title Format | Label | Ownership |
|---|---|---|
| `IMPL_PLAN: Description` | `aura:p8-impl:s8-plan` | Supervisor |
| `SLICE-N: Description` | `aura:p9-impl:s9-slice` | One worker per slice |

**Vertical Slice Ownership Model:**
- Each **production code path** is owned by exactly ONE worker
- A worker owns the full vertical (types → tests → implementation → wiring)
- Never assign the same production code path to multiple workers
- Workers CAN share Layer 0 infrastructure (common types/enums)

### Naming Conventions

- **PROPOSAL-N:** N starts at 1 and increments with each revision. Old proposals are marked `aura:superseded`.
- **PROPOSAL-N-REVIEW-{axis}-{round}:** Axis identifies the reviewer's criteria focus (A=Correctness, B=Test quality, C=Elegance). Round increments per re-review cycle.
- **SLICE-N:** N identifies the slice number within the implementation plan.

### Follow-up Lifecycle Tasks

| Title Format | Label | Purpose | Created By |
|---|---|---|---|
| `FOLLOWUP: Description` | `aura:epic-followup` | Follow-up epic for non-blocking improvements | Supervisor |
| `FOLLOWUP_URE: Description` | `aura:p2-user:s2_1-elicit` | Scoping URE: which IMPORTANT/MINOR findings to address | Supervisor |
| `FOLLOWUP_URD: Description` | `aura:p2-user:s2_2-urd,aura:urd` | Requirements document for follow-up scope | Supervisor |
| `FOLLOWUP_PROPOSAL-N: Description` | `aura:p3-plan:s3-propose` | Architect's follow-up proposal (accounts for original URD + FOLLOWUP_URD) | Architect (after h6) |
| `FOLLOWUP_IMPL_PLAN: Description` | `aura:p8-impl:s8-plan` | Follow-up implementation plan | Supervisor (after follow-up h1) |
| `FOLLOWUP_SLICE-N: Description` | `aura:p9-impl:s9-slice` | Follow-up slice (adopts original leaf tasks as dual-parent children) | Supervisor |

### Frontmatter References

Instead of peer-reference commands, include task IDs in the description frontmatter:

```bash
bd create --title "URD: Feature name" \
  --description "---
references:
  request: <request-task-id>
  elicit: <elicit-task-id>
---
## Requirements
..."
```

This replaces the old peer-reference command for linking related tasks. The URD is a living reference document — not a blocking dependency.

### Design Field Schema (Canonical)

All implementation tasks use this structure in the `design` field:

```json
{
  "productionCodePath": "tool feature list",
  "validation_checklist": [
    "Type checking passes",
    "Tests pass",
    "Production code path implemented (not test-only export)",
    "Tests verify actual production code (CLI/API users will run)",
    "All TODO placeholders replaced with working code",
    "Production code verified (via code inspection: no TODOs, real deps wired)"
  ],
  "acceptance_criteria": [
    {
      "given": "implementation complete",
      "when": "user runs production code",
      "then": "it works (not just tests passing)",
      "should_not": "have separate test-only code paths or dual-export anti-pattern"
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

---

## User Requirements Document (URD)

**Given** Phase 2 (URE) completes **when** creating the URD **then** use label `aura:urd` and include structured requirements (priorities, design choices, MVP goals, end-vision goals) **should never** leave requirements scattered across REQUEST and ELICIT tasks without a URD

**Given** a URD exists **when** linking to other tasks **then** include the URD task ID in the description frontmatter of referencing tasks (e.g., `urd: <urd-id>`) **should never** use `--blocked-by` for URD links — it is a reference document, not a blocking dependency

**Given** scope changes at any phase **when** updating requirements **then** add a comment to the URD via `bd comments add <urd-id> "..."` **should never** leave the URD out of date when UAT results, ratification, or user feedback modify requirements

## Documentation Standards

All documentation must follow these patterns:

### Command File Headers

Every `skills/*/SKILL.md` file must start with:

```yaml
---
name: agent-name
description: Brief role/purpose
tools: Tool1, Tool2, Tool3
---

# Agent Name

Brief description of role. See `CONSTRAINTS.md` for coding standards.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-x)** <- Link to relevant phase
```

### Section Organization

Use consistent structure:
- **Given/When/Then/Should** constraints (borrowed from BDD)
- **Tools & Skills** table (what this agent can do)
- **Common Patterns** with correct/wrong examples
- **See Also** section linking to PROCESS.md

### Code Examples

Always show both:
1. **CORRECT pattern** (preferred approach)
2. **WRONG pattern** (anti-pattern to avoid)

With explanatory comments.

### Linking Convention

**PROCESS.md links:**
```markdown
-> [Full workflow in PROCESS.md](PROCESS.md#phase-1-request)
```

**CONSTRAINTS.md links:**
```markdown
See `CONSTRAINTS.md` for [section name]
```

**Cross-file references in commands:**
```markdown
See: [../agent/SKILL.md](../agent/SKILL.md)
```

---

## References

See also:
- [PROCESS.md](PROCESS.md) - Step-by-step workflow execution (single source of truth)
- [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) - Standardized handoff document template
- [MIGRATION_v1_to_v2.md](MIGRATION_v1_to_v2.md) - Migration procedure from v1 to v2 labels
- `skills/` - Detailed agent role definitions
