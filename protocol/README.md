# Aura Protocol

Multi-agent orchestration protocol for AI coding agents. Defines a 12-phase workflow from user request to landed code, with structured review gates, audit trail preservation, and inter-agent coordination via Beads.

## Quick Start

1. **Read [CLAUDE.md](CLAUDE.md)** — Core agent directive (philosophy, constraints, roles). Include this in your project's `CLAUDE.md`.
2. **Read [PROCESS.md](PROCESS.md)** — Single source of truth for the 12-phase workflow.
3. **Read [AGENTS.md](AGENTS.md)** — Which agent does what, in which phases.
4. **Read [SKILLS.md](SKILLS.md)** — All `/aura:*` slash commands and when to use them.

## File Map

| File | Purpose | When to Read |
|------|---------|--------------|
| [CLAUDE.md](CLAUDE.md) | Core agent directive: philosophy, constraints, label schema, roles | Always — include in every project |
| [CONSTRAINTS.md](CONSTRAINTS.md) | Coding standards, checklists, severity definitions, naming conventions | When writing code or reviewing |
| [PROCESS.md](PROCESS.md) | Step-by-step workflow execution for all 12 phases | When running or debugging a phase |
| [AGENTS.md](AGENTS.md) | Role taxonomy: phases owned, tools, handoff procedures | When spawning agents or assigning work |
| [SKILLS.md](SKILLS.md) | Command reference: every `/aura:*` skill mapped to phase and role | When invoking a skill or looking up usage |
| [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md) | Standardized template for 5 actor-change transitions | When creating handoff documents |
| [MIGRATION_v1_to_v2.md](MIGRATION_v1_to_v2.md) | Label and title migration from v1 to v2 | When updating old tasks |
| [UAT_TEMPLATE.md](UAT_TEMPLATE.md) | User Acceptance Test structured output template | When running UAT (Phase 5 or 11) |
| [UAT_EXAMPLE.md](UAT_EXAMPLE.md) | Worked UAT example | Reference for UAT format |

## 12-Phase Overview

```
Phase 1:  REQUEST        — Classify, research, explore (aura:p1-user)
Phase 2:  ELICIT + URD   — Requirements survey + living reference doc (aura:p2-user)
Phase 3:  PROPOSAL-N     — Architect proposes technical plan (aura:p3-plan)
Phase 4:  REVIEW         — 3 axis-specific reviewers: A/B/C (aura:p4-plan)
Phase 5:  Plan UAT       — User acceptance test on plan (aura:p5-user)
Phase 6:  Ratification   — Supersede old proposals (aura:p6-plan)
Phase 7:  Handoff        — Architect → Supervisor (aura:p7-plan)
Phase 8:  IMPL_PLAN      — Supervisor decomposes into slices (aura:p8-impl)
Phase 9:  SLICE-N        — Parallel workers, vertical slices (aura:p9-impl)
Phase 10: Code Review    — 3 reviewers, severity tree (aura:p10-impl)
Phase 11: Impl UAT       — User acceptance test on code (aura:p11-user)
Phase 12: Landing        — Commit, push, hand off (aura:p12-impl)
```

## Label Schema

```
Format: aura:p{phase}-{domain}:s{step}-{type}

Examples:
  aura:p1-user:s1_1-classify    — Phase 1, classify sub-step
  aura:p3-plan:s3-propose       — Phase 3, proposal
  aura:p9-impl:s9-slice         — Phase 9, implementation slice
  aura:p10-impl:s10-review      — Phase 10, code review

Special labels:
  aura:urd                      — User Requirements Document
  aura:superseded               — Superseded proposal
  aura:severity:blocker         — Blocker severity group
  aura:severity:important       — Important severity group
  aura:severity:minor           — Minor severity group
  aura:epic-followup            — Follow-up epic for non-blocking findings
```

## Key Principles

- **Audit trail preservation** — Never delete tasks, labels, or information
- **Dependency chaining** — `bd dep add <parent> --blocked-by <child>` (child finishes first)
- **Consensus required** — All 3 reviewers must ACCEPT before proceeding
- **Binary votes** — ACCEPT or REVISE only (no intermediate levels)
- **EAGER severity tree** — Always create 3 severity groups per code review round
- **Follow-up epic** — Triggered by review completion + ANY IMPORTANT/MINOR findings
- **Vertical slices** — Each worker owns one full production code path end-to-end

## References

- `commands/aura:*.md` — Slash command definitions (installed to `~/.claude/commands/`)
- `agents/tester.md` — BDD test writer agent definition
