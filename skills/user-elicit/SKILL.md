---
name: user-elicit
description: User Requirements Elicitation (URE) survey - Phase 2 of epoch
---

# User Requirements Elicitation (Phase 2)

Conduct a structured URE survey to gather comprehensive requirements, then create the URD as the single source of truth.

See `../protocol/CONSTRAINTS.md` for coding standards.

**-> [Full workflow in PROCESS.md](../protocol/PROCESS.md#phase-2-elicit--urd-aurap2-user)**

## Given/When/Then/Should

**Given** user request captured **when** eliciting **then** plan backwards from end vision to MVP **should never** start proposal without elicitation

**Given** Phase 1 complete **when** starting elicitation **then** read Phase 1 outputs (classification, research findings, explore findings) from REQUEST task comments to scope URE questions **should never** ignore prior art discoveries or codebase exploration results

**Given** elicitation questions **when** asking **then** use multiSelect: true for flexibility **should never** force single-choice answers

**Given** responses captured **when** storing **then** record questions AND answers verbatim (including all options presented) **should never** summarize user responses or omit option text

**Given** elicitation complete **when** creating task **then** chain dependency to request task **should never** skip dependency

**Given** URD created **when** linking to other tasks **then** include URD ID in description frontmatter of referencing tasks **should never** use `bd dep add --blocked-by` for URD links (URD is a reference document, not a blocking dependency)

## Sub-steps

| Sub-step | Label | Description |
|----------|-------|-------------|
| s2_1-elicit | `aura:p2-user:s2_1-elicit` | URE survey — structured requirements elicitation |
| s2_2-urd | `aura:p2-user:s2_2-urd` (also `aura:urd`) | Create URD — single source of truth for requirements |

## Elicitation Strategy (s2_1)

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

### Pre-requisite: Read Phase 1 Outputs

Before designing URE questions, **read all Phase 1 outputs** (classification,
research findings, codebase exploration) from the REQUEST task and its comments.
These narrow the design space and reveal which boundaries are already clear vs
which need user input.

```bash
bd show <request-task-id>   # Read classification + research + explore findings
```

Use the Phase 1 findings to identify:
- Which engineering dimensions are **already decided** (don't ask about these)
- Which dimensions have **multiple viable alternatives** (ask about these)
- Which dimensions the user **may not have considered** (surface these)

### Question Sequence (Decision Tree)

Structure questions as a decision tree that progressively narrows the design
space. Each question should depend on the answers to previous questions.

**Round 1: Highest-leverage boundaries** (1-2 questions per AskUserQuestion call)

Identify the 2-3 dimensions that most constrain the design. These are the axes
where different choices lead to fundamentally different architectures.

Ask one component at a time. Show the user:
1. The concrete thing being decided (code snippet, interface, diagram)
2. A motivating example of how each option plays out
3. The tradeoffs between options

**Round 2: Dependent decisions** (informed by Round 1 answers)

With the high-level architecture settled, ask about the next layer of decisions
that were ambiguous.

**Round 3: Edge cases and constraints** (if needed)

Remaining questions about error handling, performance targets, compatibility
requirements — but only where the answer isn't obvious from prior context.

**Final: Catch-all**

One open-ended question to capture anything the decision tree missed.

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

## Creating the Elicit Task (s2_1)

After survey completion, capture the full Q&A record using the same structured
format as [UAT_TEMPLATE.md](../protocol/UAT_TEMPLATE.md). Each question must
include the exact question text, ALL options with their descriptions, and the
user's verbatim response.

```bash
bd create --labels "aura:p2-user:s2_1-elicit" \
  --title "ELICIT: {{feature name}}" \
  --description "---
references:
  request: {{request-task-id}}
---
## Questions and Responses

### End Vision
Q: What is your end vision for this feature? How will users interact with it when complete?
Options: Simple UI control (Button/link users click), Automated process (Happens without user action), API endpoint (Programmatic access), Background service (Runs continuously)
A: {{user's verbatim selections and any custom input}}

### MVP Scope
Q: What is the minimum viable version (MVP) that would be useful?
Options: Core functionality only (Just the basic action), With confirmation (User confirms before action), With feedback (Show success/error state), Full featured (All bells and whistles)
A: {{user's verbatim selections}}

### Constraints
Q: Are there any specific constraints or requirements?
Options: Performance critical (Must be fast), Security sensitive (Handles sensitive data), Backwards compatible (Can't break existing), No constraints (Flexible implementation)
A: {{user's verbatim selections}}

### Other
Q: Is there anything else we should know about this feature?
Options: Related to existing feature (Connects to something), Inspired by another product (Has a reference), Urgent timeline (Needed soon), Nothing else (Covered everything)
A: {{user's verbatim input}}" \
  --assignee architect

# Chain dependency: REQUEST blocked by ELICIT
bd dep add {{request-task-id}} --blocked-by {{elicit-task-id}}
```

## Creating the URD (s2_2)

After the elicit task is created, create the URD as the single source of truth for user requirements:

```bash
bd create --labels "aura:urd,aura:p2-user:s2_2-urd" \
  --title "URD: {{feature name}}" \
  --description "---
references:
  request: {{request-task-id}}
  elicit: {{elicit-task-id}}
---
## Requirements
{{structured requirements extracted from URE survey}}

## Priorities
{{user-stated priorities from survey responses}}

## Design Choices
{{design decisions surfaced during elicitation}}

## MVP Goals
{{minimum viable scope identified}}

## End-Vision Goals
{{user's ultimate vision for the feature}}"
```

The URD is a **reference document**, not a blocking dependency. Other tasks reference it via description frontmatter (`urd: <urd-task-id>`), not via blocking dependency commands.

Record the URD task ID — pass it to the architect for Phase 3.

## Next Phase

After elicitation and URD creation, invoke `/aura:architect` to begin proposal creation (Phase 3). Pass the URD ID so the architect can reference it.

The proposal task will block the elicit task:
```bash
bd dep add {{elicit-task-id}} --blocked-by {{proposal-task-id}}
```
