# Aura Plan

Orchestrate the full Beads/RFC planning workflow. Replaces EnterPlanMode.

See the project's `AGENTS.md` for full workflow context.

## When to Use

Starting any non-trivial implementation task.

## Given/When/Then/Should

**Given** user request **when** planning **then** create REQUEST_PLAN and invoke architect **should never** skip Beads tracking

**Given** proposal ready **when** reviewing **then** spawn 3 reviewers in parallel **should never** spawn sequentially

**Given** any REVISE vote **when** handling **then** architect revises, reviewers re-review **should never** ratify with REVISE outstanding

**Given** all 3 ACCEPT **when** presenting **then** show plan to user via AskUserQuestion **should never** auto-ratify without user

**Given** user approves **when** ratifying **then** create RATIFIED_PLAN and handoff **should never** skip supervisor handoff

## Steps

### 1. Create REQUEST_PLAN

Capture the user's request as a Beads task:

```bash
bd create --type=task \
  --labels="aura:request-plan" \
  --title="Request: <summary of user request>" \
  --description="<full user prompt verbatim>"
```

Store the returned task ID for subsequent steps.

### 2. Architect Proposes

Invoke architect to explore codebase and create PROPOSE_PLAN. Pass the URD ID so the architect references the single source of truth:

```
Task(
  description: "Architect: propose plan",
  prompt: "Create PROPOSE_PLAN for REQUEST_PLAN <request-plan-id>.
    URD: <urd-id> (read with bd show <urd-id> for requirements context)
    Include: problem space (axes, has-a/is-a), engineering tradeoffs table,
    MVP milestone, public interfaces, types/enums, validation checklist,
    BDD acceptance criteria, files affected.
    Run /aura:architect:propose-plan when ready.",
  subagent_type: "architect"
)
```

Retrieve the PROPOSE_PLAN task ID from the architect's output.

### 3. Request Review

Spawn 3 reviewers in parallel (single message, multiple Task calls):

```
Task(description: "Reviewer 1: review plan",
     prompt: "Review PROPOSE_PLAN task <propose-plan-id>. Apply end-user alignment criteria. Run /aura:reviewer:review-plan",
     subagent_type: "reviewer")
Task(description: "Reviewer 2: review plan",
     prompt: "Review PROPOSE_PLAN task <propose-plan-id>. Apply end-user alignment criteria. Run /aura:reviewer:review-plan",
     subagent_type: "reviewer")
Task(description: "Reviewer 3: review plan",
     prompt: "Review PROPOSE_PLAN task <propose-plan-id>. Apply end-user alignment criteria. Run /aura:reviewer:review-plan",
     subagent_type: "reviewer")
```

### 4. Handle Votes

Check comments on PROPOSE_PLAN:

```bash
bd comments <propose-plan-id>
```

Parse votes from comments (look for "VOTE: ACCEPT" or "VOTE: REVISE"):

- **All 3 ACCEPT**: Proceed to step 5
- **Any REVISE**:
  1. Architect creates REVISION task addressing feedback
  2. Re-spawn reviewers to review updated plan
  3. Repeat until all 3 ACCEPT

### 5. User Approval

After all 3 reviewers vote ACCEPT, present plan summary to user:

```
AskUserQuestion(
  questions: [{
    question: "Plan has consensus (3 ACCEPT votes). Ready to ratify and begin implementation?",
    header: "Ratify Plan",
    options: [
      {label: "Approve & Implement", description: "Create RATIFIED_PLAN and handoff to supervisor for implementation"},
      {label: "Request Changes", description: "Provide feedback for architect to revise before ratifying"}
    ],
    multiSelect: false
  }]
)
```

- **Approve & Implement**: Proceed to step 6
- **Request Changes**: Capture user feedback, architect revises, re-review

### 6. Ratify and Handoff

On user approval:

1. Run `/aura:architect:ratify` to create RATIFIED_PLAN:
   ```
   Skill(skill: "aura:architect:ratify", args: "<propose-plan-id>")
   ```

2. Run `/aura:architect:handoff` to create IMPLEMENTATION_PLAN and spawn supervisor:
   ```
   Skill(skill: "aura:architect:handoff", args: "<ratified-plan-id>")
   ```

## Verification Checklist

- [ ] REQUEST_PLAN task exists with user prompt
- [ ] URD task exists with structured requirements from URE
- [ ] PROPOSE_PLAN has problem space, tradeoffs, interfaces, checklist, BDD criteria
- [ ] 3 reviewer comments with ACCEPT votes
- [ ] User approved via AskUserQuestion
- [ ] RATIFIED_PLAN links to PROPOSE_PLAN
- [ ] IMPLEMENTATION_PLAN links to RATIFIED_PLAN
- [ ] Supervisor spawned with correct task IDs

## Quick Reference

```bash
# Check current state
bd list --labels="aura:request-plan" --status=open
bd list --labels="aura:propose-plan" --status=open
bd comments <task-id>

# Get project overview
bd stats
```

## State Machine

```
IDLE
  │ user request
  ↓
REQUEST_PLAN created
  │ URE survey (Phase 2)
  ↓
URD created (single source of truth)
  │ architect explores
  ↓
PROPOSE_PLAN created
  │ reviewers spawned
  ↓
REVIEW (loop)
  │ all 3 ACCEPT
  ↓
USER_APPROVAL
  │ user approves
  ↓
RATIFIED_PLAN created
  │ handoff
  ↓
IMPLEMENTATION_PLAN + supervisor
```

### State Transitions

**Given** IDLE state **when** user submits request **then** create REQUEST_PLAN task and transition to REQUEST_PLAN state **should never** proceed without capturing user prompt in Beads

**Given** REQUEST_PLAN state **when** task created **then** spawn architect agent to explore and propose **should never** skip codebase exploration

**Given** REQUEST_PLAN state **when** architect completes exploration **then** create PROPOSE_PLAN task and transition to PROPOSE_PLAN state **should never** create proposal without problem space, tradeoffs, interfaces, checklist, BDD criteria

**Given** PROPOSE_PLAN state **when** proposal ready **then** spawn 3 reviewer agents in parallel and transition to REVIEW state **should never** spawn reviewers sequentially or spawn fewer than 3

**Given** REVIEW state **when** any reviewer votes REVISE **then** architect creates REVISION task addressing feedback, re-spawn reviewers **should never** ignore REVISE feedback or proceed to ratification

**Given** REVIEW state **when** all 3 reviewers vote ACCEPT **then** transition to USER_APPROVAL state **should never** proceed with fewer than 3 ACCEPT votes

**Given** USER_APPROVAL state **when** user selects "Request Changes" **then** capture feedback, architect revises, return to REVIEW state **should never** ignore user feedback

**Given** USER_APPROVAL state **when** user selects "Approve & Implement" **then** create RATIFIED_PLAN task and transition to RATIFIED_PLAN state **should never** auto-ratify without explicit user approval

**Given** RATIFIED_PLAN state **when** ratification complete **then** create IMPLEMENTATION_PLAN task, spawn supervisor, transition to IMPLEMENTATION state **should never** skip supervisor handoff or lose link to ratified plan
