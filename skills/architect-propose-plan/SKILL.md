# Architect: Propose Plan

Create PROPOSAL-N Beads task with full specification.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-3-proposal-n)**

## When to Use

Starting new feature design; creating formal plan for review.

## Given/When/Then/Should

**Given** feature request **when** proposing **then** use BDD Given/When/Then format with acceptance criteria **should never** write vague requirements

**Given** plan **when** creating task **then** include validation_checklist and tradeoffs in design field **should never** leave checklist empty

**Given** existing plan **when** revising **then** create PROPOSAL-N+1 task and mark old as `aura:superseded` **should never** lose history

## PROPOSAL-N Naming

Proposals are numbered incrementally: PROPOSAL-1, PROPOSAL-2, etc. Each revision increments N. Old proposals are marked `aura:superseded` with a comment explaining why.

## Beads Task Creation

```bash
bd create --type=feature \
  --labels="aura:p3-plan:s3-propose" \
  --title="PROPOSAL-1: <feature name>" \
  --description="$(cat <<'EOF'
---
references:
  request: <request-id>
  urd: <urd-id>
---

## Problem Space

**Axes of the problem:**
- Parallelism: ...
- Distribution: ...

**Has-a / Is-a:**
- X HAS-A Y
- Z IS-A W

## Engineering Tradeoffs

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| A | ... | ... | Selected |
| B | ... | ... | Rejected |

## MVP Milestone

<scope with tradeoff rationale>

## Public Interfaces

\`\`\`go
type Example interface { /* ... */ }
\`\`\`

## Types & Enums

\`\`\`go
type ExampleType int

const (
    ExampleTypeA ExampleType = iota
    ExampleTypeB
)
\`\`\`

## Validation Checklist

### Phase 1
- [ ] Item 1
- [ ] Item 2

### Phase 2
- [ ] Item 3

## BDD Acceptance Criteria

**Given** precondition
**When** action
**Then** outcome
**Should Not** negative case

## Files Affected
- pkg/path/file1.go (create)
- pkg/path/file2.go (modify)
EOF
)" \
  --design='{"validation_checklist":["Item 1","Item 2","Item 3"],"tradeoffs":[{"decision":"Use A","rationale":"Because..."}],"acceptance_criteria":[{"given":"X","when":"Y","then":"Z","should_not":"W"}]}'

# Link to request
bd dep add <request-id> --blocked-by <proposal-id>
```

## Before Creating the Proposal

Read the URD and Phase 1 outputs to understand full context before drafting:
```bash
bd show <urd-id>
bd show <request-id>   # includes classification, research findings, explore findings as comments
```

The URD contains the structured requirements, priorities, design choices, and MVP goals from the URE survey. The REQUEST task comments contain Phase 1 outputs: classification (4 axes), domain research findings (prior art, standards), and codebase exploration findings (entry points, related types, dependencies). Your proposal must:
- Trace back to URD requirements
- Incorporate research findings (prior art, domain standards) into engineering tradeoffs
- Reference explore findings (entry points, existing patterns) in the files affected section

## Plan Structure

- **Requirements Traceability: URD:** `<urd-id>`
- Problem Space (axes, has-a/is-a)
- Engineering Tradeoffs (table with decisions)
- MVP Milestone (scope with tradeoff rationale)
- Public Interfaces (Go)
- Types & Enums
- Validation Checklist (per phase)
- BDD Acceptance Criteria
- Files Affected

## Next Steps

After creating PROPOSAL-N task:
1. Run `/aura:architect-request-review` to spawn 3 reviewers
2. Wait for all 3 reviewers to vote ACCEPT
3. Run `/aura:architect-ratify` to add ratify label to PROPOSAL-N

## Follow-up Proposals (FOLLOWUP_PROPOSAL-N)

When creating proposals for a follow-up epic (received via h6 from supervisor):
- **Title prefix:** `FOLLOWUP_PROPOSAL-N:` (e.g., `FOLLOWUP_PROPOSAL-1: Add request-id correlation`)
- **References:** Include both `original_urd: <id>` and `followup_urd: <id>` in frontmatter
- **Content:** Address specific IMPORTANT/MINOR findings scoped in FOLLOWUP_URE/URD
- Same review/ratify/UAT lifecycle applies (3 reviewers, ACCEPT/REVISE, UAT, ratify, handoff)
