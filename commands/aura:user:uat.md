---
name: user:uat
description: User Acceptance Testing with demonstrative examples
tools: Bash, AskUserQuestion
---

# User Acceptance Test (UAT)

Conduct UAT at key checkpoints (after plan review, after implementation) to verify alignment with user's vision and MVP requirements.

## Given/When/Then/Should

**Given** reviewers reach consensus **when** conducting UAT **then** show demonstrative examples **should never** ask abstract questions

**Given** UAT questions **when** asking **then** present one component at a time with definition + implementation + example BEFORE asking **should never** dump all questions at once about all components simultaneously

**Given** UAT questions **when** forming options **then** describe specific tradeoffs and design choices made **should never** use generic approval options like "exactly matches", "mostly matches", "requires revisions"

**Given** user feedback **when** storing **then** record verbatim with context **should never** paraphrase concerns

**Given** user rejects **when** plan UAT **then** return to proposal phase **should never** proceed to implementation

**Given** user rejects **when** impl UAT **then** return to relevant slice **should never** proceed to landing

**Given** UAT completes **when** results are captured **then** update the URD with UAT results via `bd comments add <urd-id> "UAT: <summary>"` and `bd dep relate <urd-id> <uat-id>` **should never** leave the URD out of date after UAT

## UAT Phases

### Plan UAT (Phase 5)
After 3 reviewers ACCEPT the proposal, present each major design decision to the user one at a time. For each component:
1. Show the proposed interface definition (code snippet)
2. Show a motivating example (how a user would use it)
3. Ask about the specific design choices made (tradeoffs, alternatives considered)

### Implementation UAT (Phase 11)
After code review consensus, demonstrate what was actually built component by component. For each component:
1. Run the actual command / show real output
2. Compare against the original proposal
3. Ask about the specific behavioral decisions made in the implementation

## How to Structure UAT Questions

**Critical:** Questions must be about specific design decisions, not general approval. The user needs to see the actual thing — definition, behavior, example — and then evaluate specific choices you made.

### WRONG — generic approval (DO NOT USE):
```
"Does this match your vision?"
options: ["Yes exactly", "Mostly yes", "Partially", "No"]

"Is the MVP scope appropriate?"
options: ["Right scope", "Too minimal", "Too much", "Wrong focus"]
```

### RIGHT — component-specific design decisions:
```
"The verbose flag adds the following fields to each log entry. Which fields are most useful?"
options based on actual fields implemented, e.g.:
  - "session ID on every transcript event — adds noise but enables correlation"
  - "backupDir on backup events — confirms where files land"
  - "repo path + hash on sync events — confirms which repo was detected"
  - "full key=value dump for unknown events — good for debugging"

"We sanitize emails in file paths by replacing @ with _ and non-alphanumeric chars with _. Which sanitization behavior is correct?"
options based on real alternatives:
  - "@ → _AT_ (reversible, unambiguous)"
  - "@ → _ (current behavior, ambiguous if username contains _)"
  - "keep @ (valid on most filesystems except Windows)"
  - "base64-encode the email (fully reversible, opaque)"
```

## Component-at-a-Time Pattern

For each major component being UAT'd:

### Step 1: Show the definition and motivating example
```
Present the interface/type definition (e.g., the TypeScript type or function signature)
Then show a concrete before/after or input/output example:

  BEFORE this change:  $ aura watch --follow
  [23:24:20] Updated: session-abc123
  → Backed up 3 files

  AFTER this change: $ aura watch --follow --verbose
  [23:24:20] Updated: -home-minttea-dev.../session-abc123
    path: /home/minttea/.claude/projects/...
    session: abc123
    → Repo sync: enqueued (debounced)
    repo: /home/minttea/dev/project, hash: -home-minttea-dev-project
    → State backup: 6 files staged → git-repos/.../epic__branch/user_gmail.com
    targetDir: git-repos/-home-minttea-.../epic__branch/user_gmail.com
```

### Step 2: Ask about specific decisions
Design-space questions to ask per component type:

**For output/display decisions:**
- Which fields are useful vs. noise at the default verbosity level?
- Which fields belong only in verbose mode?
- Is the path truncation appropriate, or should the full path always show?

**For data model / type decisions:**
- Should this be statically defined (enum) or dynamic (string)?
- Should the schema be strict (reject unknown fields) or loose (allow extra)?
- Is runtime validation needed, or is this internal-only?

**For behavioral/algorithm decisions:**
- Should this fail fast or recover silently?
- Should side effects be eager (immediate) or lazy (deferred/debounced)?
- Is the current retry/fallback behavior appropriate?

**For API/interface decisions:**
- Is the flag name/command name intuitive?
- Does the default behavior match expectations?
- Should the opt-in/opt-out be reversed?

## UAT Survey Template

Use one AskUserQuestion call per component — do NOT batch all components into one survey.

```typescript
// Example for a specific component (not generic)
AskUserQuestion({
  questions: [
    {
      question: `The verbose flag shows the following extra lines for backup events:
  backupDir: /home/user/.aura/aura-sync/repo/project/provider/claude/session/abc123
  session: abc123
Which of these verbose fields are useful?`,
      header: "Verbose fields",
      multiSelect: true,
      options: [
        { label: "backupDir (full path)", description: "Shows where the backup actually landed" },
        { label: "session ID", description: "Enables log correlation across events" },
        { label: "repo path + hash", description: "Confirms which git repo was detected" },
        { label: "targetDir (state backup)", description: "Shows git-repos/ classified path" },
      ]
    },
    {
      question: `We sanitize emails for use in directory names:
  dayvidpham@gmail.com → dayvidpham_gmail.com
  (@ replaced with _, other non-alphanumeric chars → _)
Is this the right sanitization strategy?`,
      header: "Email sanitize",
      multiSelect: false,
      options: [
        { label: "@ → _AT_ (unambiguous)", description: "Reversible, no collision with usernames containing _" },
        { label: "@ → _ (current)", description: "Simpler but ambiguous: a_gmail.com could come from two different emails" },
        { label: "Keep @ in path", description: "Most filesystems support it; Windows is exception" },
        { label: "URL-encode (@ → %40)", description: "Fully reversible but ugly" },
      ]
    },
    {
      question: "Do you ACCEPT this component to proceed?",
      header: "Decision",
      multiSelect: false,
      options: [
        { label: "ACCEPT", description: "Proceed to next component" },
        { label: "REVISE", description: "Needs changes before proceeding" }
      ]
    }
  ]
})
```

## Creating UAT Task

Capture the questions shown AND the user's verbatim responses. Do not paraphrase.

```bash
# For Plan UAT (Phase 5)
bd create --labels aura:user:uat,proposal-{{N}}:uat-{{M}} \
  --title "UAT-{{M}}: Plan acceptance for {{feature}}" \
  --description "## Components Reviewed

### Component: {{component-name}}
**Definition shown:**
\`\`\`
{{interface/type/signature shown to user}}
\`\`\`

**Motivating example shown:**
\`\`\`
{{before/after or input/output example}}
\`\`\`

**Question asked:** {{exact question text}}
**Options presented:** {{exact option labels and descriptions}}
**User response:** {{verbatim selection(s)}}

---

### Component: {{next-component}}
...

## Final Decision
{{ACCEPT or REVISE with verbatim reason}}"

bd dep add {{last-review-task-id}} --blocked-by {{uat-task-id}}

# Update URD with plan UAT results
bd comments add {{urd-id}} "Plan UAT: {{ACCEPT or REVISE}} - {{summary of key decisions}}"
bd dep relate {{urd-id}} {{uat-task-id}}
```

```bash
# For Implementation UAT (Phase 11)
bd create --labels aura:impl:uat \
  --title "IMPL-UAT: {{feature}}" \
  --description "## Components Demonstrated

### Component: {{component-name}}
**Command run / output shown:**
\`\`\`
{{actual terminal output shown to user}}
\`\`\`

**Question asked:** {{exact question}}
**User response:** {{verbatim response}}

## Final Decision
{{ACCEPT or REVISE}}"

bd dep add {{last-code-review-task-id}} --blocked-by {{impl-uat-task-id}}

# Update URD with implementation UAT results
bd comments add {{urd-id}} "Impl UAT: {{ACCEPT or REVISE}} - {{summary of findings}}"
bd dep relate {{urd-id}} {{impl-uat-task-id}}
```

## Handling REVISE

If user selects REVISE:
- **Plan UAT:** Return to architect for proposal revision on the specific component
- **Impl UAT:** Return to relevant slice for implementation fixes

Document the specific component and the user's verbatim feedback in the task description. Do not generalize.
