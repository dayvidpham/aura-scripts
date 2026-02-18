---
name: impl:review
description: Code review across all implementation slices (Phase 10)
tools: Bash, Task, Read, Glob, Grep
---

# Implementation Code Review (Phase 10)

Conduct code review across ALL implementation slices. Each of 3 reviewers reviews every slice.

## Given/When/Then/Should

**Given** all slices complete **when** starting review **then** spawn 3 reviewers for ALL slices **should never** assign reviewers to single slices

**Given** reviewer assigned **when** reviewing **then** check each slice against criteria **should never** skip any slice

**Given** review complete **when** voting **then** create review task per slice **should never** give single vote for all

**Given** any REVISE vote **when** deciding **then** return to implementation **should never** proceed to UAT

## Review Structure

Each reviewer (1, 2, 3) reviews EVERY slice (A, B, C, ...):

```
Reviewer 1: Reviews A, B, C → Creates review-A-1, review-B-1, review-C-1
Reviewer 2: Reviews A, B, C → Creates review-A-2, review-B-2, review-C-2
Reviewer 3: Reviews A, B, C → Creates review-A-3, review-B-3, review-C-3
```

## Spawning Reviewers

Supervisor spawns 3 parallel reviewers:

```bash
# Use launch-parallel.py to spawn reviewers
~/codebases/dayvidpham/aura-scripts/launch-parallel.py \
  --role reviewer -n 3 \
  --skill aura:reviewer:review-code \
  --prompt "You are Reviewer {{N}}.
Review ALL slices: {{slice-A-id}}, {{slice-B-id}}, {{slice-C-id}}
For each slice, run: bd show {{slice-id}}
Create a review task for each slice you review."
```

## Review Criteria

Each reviewer checks each slice for:

1. **Requirements Alignment**
   - Does implementation match ratified plan?
   - Are all acceptance criteria met?

2. **User Vision**
   - Does it fulfill the user's original request?
   - Does it match UAT expectations?

3. **MVP Scope**
   - Is scope appropriate (not over/under engineered)?

4. **Codebase Quality**
   - Follows project style/constraints?
   - No TODO placeholders?
   - Tests import production code?

5. **Validation Checklist**
   - All items from slice checklist verified?

## Creating Review Tasks

Each reviewer creates a task per slice:

```bash
# Reviewer 1 reviewing Slice A
bd create --labels aura:impl:review,slice-A:review-1 \
  --title "CODE-REVIEW-1: slice-A" \
  --description "## Review of Slice A by Reviewer 1

### Requirements Alignment
{{findings}}

### User Vision
{{findings}}

### MVP Scope
{{findings}}

### Codebase Quality
{{findings}}

### Validation Checklist
{{findings}}

## VOTE: {{ACCEPT or REVISE}}
Reason: {{justification}}"

bd dep add {{review-task-id}} {{slice-A-id}}
```

## Consensus Check

All 9 reviews (3 reviewers × 3 slices) must be ACCEPT:

```bash
# Check for any REVISE votes
bd list --labels aura:impl:review --desc-contains "VOTE: REVISE"

# If any REVISE, return to implementation
# If all ACCEPT, proceed to impl-uat
```

## Review Comments on Slice Tasks

In addition to creating review tasks, reviewers add comments to slice tasks:

```bash
bd comments add {{slice-A-id}} "REVIEW-1: ACCEPT - Implementation matches plan, tests comprehensive"
bd comments add {{slice-A-id}} "REVIEW-2: ACCEPT - Code quality good, no TODOs"
bd comments add {{slice-A-id}} "REVIEW-3: REVISE - Missing error handling in auth flow"
```

## Handling REVISE

If any reviewer votes REVISE on any slice:

1. **Document issues** in the review task description
2. **Return slice to worker** for fixes
3. **Re-review** after fixes complete

```bash
# Mark slice as needing revision
bd label add {{slice-id}} needs-revision
bd comments add {{slice-id}} "REVISION NEEDED: {{specific issues}}"

# After worker fixes
bd label remove {{slice-id}} needs-revision
# Re-run review cycle
```

## Proceeding to UAT

Only when ALL reviews are ACCEPT:

```bash
# Verify consensus
bd list --labels aura:impl:review | grep -c "VOTE: ACCEPT"
# Should equal total reviews (e.g., 9 for 3 reviewers × 3 slices)

# Proceed to impl-uat (Phase 11)
Skill(/aura:user:uat)
```
