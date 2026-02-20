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

\`\`\`typescript
export interface IExample { ... }
\`\`\`

## Types & Enums

\`\`\`typescript
export enum ExampleType { ... }
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
- src/path/file1.ts (create)
- src/path/file2.ts (modify)
EOF
)" \
  --design='{"validation_checklist":["Item 1","Item 2","Item 3"],"tradeoffs":[{"decision":"Use A","rationale":"Because..."}],"acceptance_criteria":[{"given":"X","when":"Y","then":"Z","should_not":"W"}]}'

# Link to request
bd dep add <request-id> --blocked-by <proposal-id>
```

## Before Creating the Proposal

Read the URD to understand user requirements before drafting:
```bash
bd show <urd-id>
```

The URD contains the structured requirements, priorities, design choices, and MVP goals from the URE survey. Your proposal must trace back to these requirements.

## Plan Structure

- **Requirements Traceability: URD:** `<urd-id>`
- Problem Space (axes, has-a/is-a)
- Engineering Tradeoffs (table with decisions)
- MVP Milestone (scope with tradeoff rationale)
- Public Interfaces (TypeScript)
- Types & Enums
- Validation Checklist (per phase)
- BDD Acceptance Criteria
- Files Affected

## Next Steps

After creating PROPOSAL-N task:
1. Run `/aura:architect:request-review` to spawn 3 reviewers
2. Wait for all 3 reviewers to vote ACCEPT
3. Run `/aura:architect:ratify` to add ratify label to PROPOSAL-N
