---
name: user:request
description: Capture user's feature request verbatim as Phase 1 of epoch
tools: Bash, AskUserQuestion
---

# User Request (Phase 1)

Capture the user's feature request **verbatim** in a beads task. This is the immutable record that all subsequent phases reference.

## Given/When/Then/Should

**Given** user provides request **when** capturing **then** store verbatim without paraphrasing **should never** summarize or interpret

**Given** request captured **when** creating task **then** use `aura:user:request` label **should never** use other labels for this phase

**Given** task created **when** proceeding **then** invoke `/aura:user:elicit` for Phase 2 **should never** skip to proposal

## Capture Process

1. **Get the user's request verbatim:**
   ```
   AskUserQuestion: "What feature or change would you like to request?"
   ```

2. **Create the request task:**
   ```bash
   bd create --labels aura:user:request \
     --title "REQUEST: {{short summary}}" \
     --description "{{VERBATIM user request - do not edit}}" \
     --assignee architect
   ```

3. **Record the task ID** for dependency chaining in Phase 2.

## Example

User says: "I want to add a logout button to the header that clears the session and redirects to the login page"

```bash
bd create --labels aura:user:request \
  --title "REQUEST: Add logout button to header" \
  --description "I want to add a logout button to the header that clears the session and redirects to the login page" \
  --assignee architect
# Returns: bd-abc123
```

## Next Phase

After capturing the request, invoke `/aura:user:elicit` to begin requirements elicitation (Phase 2).

The elicit task will block this request task:
```bash
bd dep add {{request-task-id}} --blocked-by {{elicit-task-id}}
```
