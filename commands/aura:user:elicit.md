---
name: user:elicit
description: User Requirements Elicitation (URE) survey - Phase 2 of epoch
tools: Bash, AskUserQuestion
---

# User Requirements Elicitation (Phase 2)

Conduct a structured URE survey to gather comprehensive requirements before proposal creation.

## Given/When/Then/Should

**Given** user request captured **when** eliciting **then** plan backwards from end vision to MVP **should never** start proposal without elicitation

**Given** elicitation questions **when** asking **then** use multiSelect: true for flexibility **should never** force single-choice answers

**Given** responses captured **when** storing **then** record questions AND answers verbatim **should never** summarize user responses

**Given** elicitation complete **when** creating task **then** chain dependency to request task **should never** skip dependency

## Elicitation Strategy

### 1. End Vision (Plan Backwards)
Ask about the user's ultimate goal and what interfaces they envision:
- What does the final feature look like?
- How will users interact with it?
- What other systems need to integrate?

### 2. MVP Scope (Plan Forward)
Jump to the starting point:
- What's the minimum viable version?
- What can be deferred to later iterations?
- What are the must-have vs nice-to-have features?

### 3. Engineering Dimensions
Ask targeted questions to map the problem space:
- Parallelism: Can operations run concurrently?
- Distribution: Single process or distributed?
- Scale: How many users/requests/items?
- Has-a / Is-a relationships in the domain

### 4. Boundaries and Constraints
- Performance requirements?
- Security considerations?
- Compatibility constraints?
- Error handling expectations?

### 5. Catch-All
Final question to capture anything missed.

## Example Survey

```
AskUserQuestion(questions: [
  {
    question: "What is your end vision for this feature? How will users interact with it when complete?",
    header: "End Vision",
    multiSelect: true,
    options: [
      { label: "Simple UI control", description: "Button/link users click" },
      { label: "Automated process", description: "Happens without user action" },
      { label: "API endpoint", description: "Programmatic access" },
      { label: "Background service", description: "Runs continuously" }
    ]
  },
  {
    question: "What is the minimum viable version (MVP) that would be useful?",
    header: "MVP Scope",
    multiSelect: true,
    options: [
      { label: "Core functionality only", description: "Just the basic action" },
      { label: "With confirmation", description: "User confirms before action" },
      { label: "With feedback", description: "Show success/error state" },
      { label: "Full featured", description: "All bells and whistles" }
    ]
  },
  {
    question: "Are there any specific constraints or requirements?",
    header: "Constraints",
    multiSelect: true,
    options: [
      { label: "Performance critical", description: "Must be fast" },
      { label: "Security sensitive", description: "Handles sensitive data" },
      { label: "Backwards compatible", description: "Can't break existing" },
      { label: "No constraints", description: "Flexible implementation" }
    ]
  },
  {
    question: "Is there anything else we should know about this feature?",
    header: "Other",
    multiSelect: true,
    options: [
      { label: "Related to existing feature", description: "Connects to something" },
      { label: "Inspired by another product", description: "Has a reference" },
      { label: "Urgent timeline", description: "Needed soon" },
      { label: "Nothing else", description: "Covered everything" }
    ]
  }
])
```

## Creating the Elicit Task

After survey completion:

```bash
bd create --labels aura:user:elicit \
  --title "ELICIT: {{feature name}}" \
  --description "## Questions and Responses

### End Vision
Q: What is your end vision...
A: {{user's verbatim selections and any custom input}}

### MVP Scope
Q: What is the minimum viable...
A: {{user's verbatim selections}}

### Constraints
Q: Are there any specific...
A: {{user's verbatim selections}}

### Other
Q: Is there anything else...
A: {{user's verbatim input}}" \
  --assignee architect

# Chain dependency
bd dep add {{elicit-task-id}} {{request-task-id}}
```

## Next Phase

After elicitation, invoke `/aura:architect` to begin proposal creation (Phase 3).
