# Architect: Propose Plan

Create PROPOSE_PLAN Beads task with full specification.

## When to Use

Starting new feature design; creating formal plan for review.

## Given/When/Then/Should

**Given** feature request **when** proposing **then** use BDD Given/When/Then format with acceptance criteria **should never** write vague requirements

**Given** plan **when** creating task **then** include validation_checklist and tradeoffs in design field **should never** leave checklist empty

**Given** existing plan **when** revising **then** create REVISION task linking to original **should never** lose history

## Beads Task Creation

```bash
bd create --type=feature \
  --labels="aura:propose-plan" \
  --title="Plan: <feature name>" \
  --description="$(cat <<'EOF'
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

After creating PROPOSE_PLAN task:
1. Run `/aura:architect:request-review` to spawn 3 reviewers
2. Wait for all 3 reviewers to vote ACCEPT
3. Run `/aura:architect:ratify` to create RATIFIED_PLAN
