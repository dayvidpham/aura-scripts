# Aura Plan

Orchestrate the full Beads planning workflow. Replaces EnterPlanMode.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-3-proposal-n)**

## When to Use

Starting any non-trivial implementation task.

## Given/When/Then/Should

**Given** user request **when** planning **then** create REQUEST task and invoke architect **should never** skip Beads tracking

**Given** proposal ready **when** reviewing **then** spawn 3 reviewers in parallel **should never** spawn sequentially

**Given** any REVISE vote **when** handling **then** architect revises as PROPOSAL-N+1, reviewers re-review **should never** ratify with REVISE outstanding

**Given** all 3 ACCEPT **when** presenting **then** show plan to user via AskUserQuestion **should never** auto-ratify without user

**Given** user approves **when** ratifying **then** add `aura:p6-plan:s6-ratify` label and handoff **should never** skip supervisor handoff

## Steps

### 1. Create REQUEST

Capture the user's request as a Beads task:

```bash
bd create --type=task \
  --labels="aura:p1-user:s1_1-classify" \
  --title="REQUEST: <summary of user request>" \
  --description="<full user prompt verbatim>"
```

Store the returned task ID for subsequent steps.

### 2. Architect Proposes

Invoke architect to explore codebase and create PROPOSAL-N. Pass the URD ID so the architect references the single source of truth:

```
Task(
  description: "Architect: propose plan",
  prompt: "Create PROPOSAL-1 for REQUEST <request-id>.
    URD: <urd-id> (read with bd show <urd-id> for requirements context)
    Include: problem space (axes, has-a/is-a), engineering tradeoffs table,
    MVP milestone, public interfaces, types/enums, validation checklist,
    BDD acceptance criteria, files affected.
    Run /aura:architect-propose-plan when ready.",
  subagent_type: "architect"
)
```

Retrieve the PROPOSAL-N task ID from the architect's output.

### 3. Request Review

Spawn 3 reviewers in parallel (single message, multiple Task calls):

```
Task(description: "Reviewer A: correctness",
     prompt: "Review PROPOSAL-1 task <proposal-id>. You are Reviewer A (Correctness). Run /aura:reviewer-review-plan",
     subagent_type: "reviewer")
Task(description: "Reviewer B: test quality",
     prompt: "Review PROPOSAL-1 task <proposal-id>. You are Reviewer B (Test quality). Run /aura:reviewer-review-plan",
     subagent_type: "reviewer")
Task(description: "Reviewer C: elegance",
     prompt: "Review PROPOSAL-1 task <proposal-id>. You are Reviewer C (Elegance). Run /aura:reviewer-review-plan",
     subagent_type: "reviewer")
```

### 4. Handle Votes

Check comments on PROPOSAL-N:

```bash
bd comments <proposal-id>
```

Parse votes from comments (look for "VOTE: ACCEPT" or "VOTE: REVISE"):

- **All 3 ACCEPT**: Proceed to step 5
- **Any REVISE**:
  1. Architect creates PROPOSAL-N+1 addressing feedback
  2. Old proposal marked `aura:superseded`
  3. Re-spawn reviewers to review new proposal
  4. Repeat until all 3 ACCEPT

### 5. User Approval

After all 3 reviewers vote ACCEPT, present plan summary to user:

```
AskUserQuestion(
  questions: [{
    question: "Plan has consensus (3 ACCEPT votes). Ready to ratify and begin implementation?",
    header: "Ratify Plan",
    options: [
      {label: "Approve & Implement", description: "Add ratify label to PROPOSAL-N and handoff to supervisor for implementation"},
      {label: "Request Changes", description: "Provide feedback for architect to revise before ratifying"}
    ],
    multiSelect: false
  }]
)
```

- **Approve & Implement**: Proceed to step 6
- **Request Changes**: Capture user feedback, architect revises as PROPOSAL-N+1, re-review

### 6. Ratify and Handoff

On user approval:

1. Run `/aura:architect-ratify` to add ratify label to PROPOSAL-N:
   ```
   Skill(skill: "aura:architect:ratify", args: "<proposal-id>")
   ```

2. Run `/aura:architect-handoff` to create handoff document and spawn supervisor:
   ```
   Skill(skill: "aura:architect:handoff", args: "<ratified-proposal-id>")
   ```

## Follow-up Proposals (FOLLOWUP_PROPOSAL-N)

This same planning cycle (Phases 3-7) applies for follow-up proposals. The entry point differs:
- **Standard:** Starts from user request (Phase 1)
- **Follow-up:** Starts from h6 handoff (Supervisor → Architect with FOLLOWUP_URE + FOLLOWUP_URD)
- **Task naming:** `FOLLOWUP_PROPOSAL-N` prefix
- **References:** Frontmatter includes both original URD and FOLLOWUP_URD

## Verification Checklist

- [ ] REQUEST task exists with user prompt
- [ ] URD task exists with structured requirements from URE
- [ ] PROPOSAL-N has problem space, tradeoffs, interfaces, checklist, BDD criteria
- [ ] 3 reviewer comments with ACCEPT votes
- [ ] User approved via AskUserQuestion
- [ ] PROPOSAL-N has `aura:p6-plan:s6-ratify` label
- [ ] Handoff document at `.git/.aura/handoff/{request-id}/architect-to-supervisor.md`
- [ ] Supervisor spawned with correct task IDs

## Quick Reference

```bash
# Check current state
bd list --labels="aura:p1-user:s1_1-classify" --status=open
bd list --labels="aura:p3-plan:s3-propose" --status=open
bd comments <task-id>

# Get project overview
bd stats
```

## State Machine

```
IDLE
  | user request
  v
REQUEST created
  | URE survey (Phase 2)
  v
URD created (single source of truth)
  | architect explores
  v
PROPOSAL-N created
  | reviewers spawned
  v
REVIEW (loop)
  | all 3 ACCEPT
  v
USER_APPROVAL
  | user approves
  v
PROPOSAL-N ratified (label added)
  | handoff
  v
Supervisor launched
```

### State Transitions

**Given** IDLE state **when** user submits request **then** create REQUEST task and transition to REQUEST state **should never** proceed without capturing user prompt in Beads

**Given** REQUEST state **when** task created **then** spawn architect agent to explore and propose **should never** skip codebase exploration

**Given** REQUEST state **when** architect completes exploration **then** create PROPOSAL-N task and transition to PROPOSAL state **should never** create proposal without problem space, tradeoffs, interfaces, checklist, BDD criteria

**Given** PROPOSAL state **when** proposal ready **then** spawn 3 reviewer agents in parallel and transition to REVIEW state **should never** spawn reviewers sequentially or spawn fewer than 3

**Given** REVIEW state **when** any reviewer votes REVISE **then** architect creates PROPOSAL-N+1 addressing feedback, marks old as `aura:superseded`, re-spawn reviewers **should never** ignore REVISE feedback or proceed to ratification

**Given** REVIEW state **when** all 3 reviewers vote ACCEPT **then** transition to USER_APPROVAL state **should never** proceed with fewer than 3 ACCEPT votes

**Given** USER_APPROVAL state **when** user selects "Request Changes" **then** capture feedback, architect revises as PROPOSAL-N+1, return to REVIEW state **should never** ignore user feedback

**Given** USER_APPROVAL state **when** user selects "Approve & Implement" **then** add `aura:p6-plan:s6-ratify` label to PROPOSAL-N **should never** auto-ratify without explicit user approval

**Given** RATIFIED state **when** ratification complete **then** create handoff document, spawn supervisor, transition to IMPLEMENTATION state **should never** skip supervisor handoff or lose link to ratified plan
