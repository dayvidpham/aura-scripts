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
| APPROVE | No blocking issues |
| APPROVE_WITH_COMMENTS | Minor issues noted |
| REQUEST_CHANGES | Blocking issues found |
| REJECT | Fundamental design problems |

## Issue Severity

| Severity | When to Use | Blocks |
|----------|-------------|--------|
| BLOCKING | Security, type errors, test failures | Yes |
| MAJOR | Performance, missing validation | Maybe |
| MINOR | Style, optional optimizations | No |

## Beads Task Naming & Tagging Standards

All work flows through Beads with standardized ALL_CAPS titles and hierarchical tags:

### Planning Phase Tasks

| Title | Tag | Purpose | Created By |
|-------|-----|---------|-----------|
| REQUEST_PLAN: Description | `aura:plan:request` | Capture user's problem statement | User or Coordinator |
| PROPOSE_PLAN: Description | `aura:plan:propose` | Architect's full technical proposal | Architect |
| REVISION_1/2/N: Description | `aura:plan:revision` | Architect revises after reviewer feedback | Architect (loop if needed) |
| REVIEW_1/2/3: Description | `aura:review` | Reviewer assessment | Reviewers (spawned by architect) |
| URD: Description | `aura:urd` | Single source of truth for user requirements, priorities, design choices, MVP goals | Architect (after Phase 2 URE) |
| RATIFIED_PLAN: Description | `aura:plan:ratified` | Consensus reached; ready for implementation | Architect (after all 3 reviewers ACCEPT) |

### Implementation Phase Tasks

| Title Format | Tags | Ownership |
|--------------|------|-----------|
| [SLICE] Implement 'command name' (full vertical) | `aura:impl`, `slice:<name>` | One worker per slice |
| [L0] Shared infrastructure: description | `aura:impl`, `layer-0` | Parallel, no deps |

**Vertical Slice Ownership Model:**
- Each **production code path** is owned by exactly ONE worker
- A worker owns the full vertical (types → tests → implementation → wiring)
- Never assign the same production code path to multiple workers
- Workers CAN share Layer 0 infrastructure (common types/enums)

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

**Given** a URD exists **when** linking to other tasks **then** use `bd dep relate` (peer reference) to connect URD ↔ REQUEST, ELICIT, PROPOSAL, IMPL_PLAN, and UAT tasks **should never** use `--blocked-by` for URD links — it is a reference document, not a blocking dependency

**Given** scope changes at any phase **when** updating requirements **then** add a comment to the URD via `bd comments add <urd-id> "..."` **should never** leave the URD out of date when UAT results, ratification, or user feedback modify requirements

## Documentation Standards

All documentation must follow these patterns:

### Command File Headers

Every `.claude/commands/*.md` file must start with:

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
-> [Full workflow in PROCESS.md](PROCESS.md#phase-1-request_plan--propose_plan)
```

**CONSTRAINTS.md links:**
```markdown
See `CONSTRAINTS.md` for [section name]
```

**Cross-file references in commands:**
```markdown
See: [.claude/commands/aura:agent.md](.claude/commands/aura:agent.md)
```

---

## References

See also:
- [PROCESS.md](PROCESS.md) - Step-by-step workflow execution (single source of truth)
- `.claude/commands/` - Detailed agent role definitions
