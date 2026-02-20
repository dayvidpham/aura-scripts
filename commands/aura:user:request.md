---
name: user:request
description: Capture user's feature request verbatim as Phase 1 of epoch
tools: Bash, AskUserQuestion
---

# User Request (Phase 1)

Capture the user's feature request **verbatim** in a beads task, then classify, research, and explore. This is the immutable record that all subsequent phases reference.

See `CONSTRAINTS.md` for coding standards.

**-> [Full workflow in PROCESS.md](../../protocol/PROCESS.md#phase-1-request-aurap1-user)**

## Given/When/Then/Should

**Given** user provides request **when** capturing **then** store verbatim without paraphrasing **should never** summarize or interpret

**Given** request captured **when** classifying **then** use `aura:p1-user:s1_1-classify` label **should never** use other labels for the initial capture

**Given** classification complete **when** user confirms research depth **then** run s1_2-research and s1_3-explore in parallel **should never** skip research depth confirmation

**Given** Phase 1 complete **when** proceeding **then** invoke `/aura:user:elicit` for Phase 2 **should never** skip to proposal

## Phase 1 Sub-steps

| Sub-step | Label | Description | Parallel? |
|----------|-------|-------------|-----------|
| s1_1-classify | `aura:p1-user:s1_1-classify` | Capture verbatim + classify along 4 axes | Sequential (first) |
| s1_2-research | `aura:p1-user:s1_2-research` | Find domain standards, prior art | Parallel with s1_3 |
| s1_3-explore | `aura:p1-user:s1_3-explore` | Codebase exploration for integration points | Parallel with s1_2 |

## Step 1: Capture and Classify (s1_1)

1. **Get the user's request verbatim:**
   ```
   AskUserQuestion: "What feature or change would you like to request?"
   ```

2. **Create the request task:**
   ```bash
   bd create --labels "aura:p1-user:s1_1-classify" \
     --title "REQUEST: {{short summary}}" \
     --description "{{VERBATIM user request - do not edit}}" \
     --assignee architect
   ```

3. **Classify along 4 axes:**
   - **Scope:** Single file, module, cross-cutting
   - **Complexity:** Low, medium, high
   - **Risk:** Breaking changes, new API, internal-only
   - **Domain novelty:** Familiar patterns vs new territory

4. **Record classification** via comment on the request task:
   ```bash
   bd comments add {{request-task-id}} \
     "Classification: scope={{scope}}, complexity={{complexity}}, risk={{risk}}, novelty={{novelty}}"
   ```

## Step 2: Research Depth Confirmation

After classification, confirm research depth with the user:

```
AskUserQuestion:
  question: "Based on classification ({{scope}}, {{complexity}}, {{risk}}, {{novelty}}), how deep should research go?"
  header: "Research Depth"
  options:
    - label: "Quick scan"
      description: "Familiar domain, low complexity — brief prior art check"
    - label: "Standard research"
      description: "Moderate complexity or some novelty — find existing patterns and standards"
    - label: "Deep dive"
      description: "High complexity, new territory, or high risk — thorough domain analysis"
```

## Step 3: Research + Explore (s1_2 || s1_3)

Run in parallel after user confirms depth:

**s1_2-research:** Find domain standards, prior art, existing solutions relevant to the request.

**s1_3-explore:** Search the codebase for integration points, existing patterns, and related code.

## Example

User says: "I want to add a logout button to the header that clears the session and redirects to the login page"

```bash
bd create --labels "aura:p1-user:s1_1-classify" \
  --title "REQUEST: Add logout button to header" \
  --description "I want to add a logout button to the header that clears the session and redirects to the login page" \
  --assignee architect
# Returns: bd-abc123

bd comments add bd-abc123 \
  "Classification: scope=module, complexity=low, risk=internal-only, novelty=familiar"
```

## Next Phase

After Phase 1 completes, invoke `/aura:user:elicit` to begin requirements elicitation (Phase 2).

The elicit task will block this request task:
```bash
bd dep add {{request-task-id}} --blocked-by {{elicit-task-id}}
```
