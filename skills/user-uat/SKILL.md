---
name: user-uat
description: User Acceptance Testing with demonstrative examples
---

# User Acceptance Test (UAT)

Conduct UAT at key checkpoints (after plan review, after implementation) to verify alignment with user's vision and MVP requirements.

**-> [Full workflow in PROCESS.md](../protocol/PROCESS.md#phase-5-plan-uat)** <- Phase 5 (Plan UAT) and Phase 11 (Impl UAT)

See `../protocol/CONSTRAINTS.md` for coding standards.

## Given/When/Then/Should

**Given** reviewers reach consensus **when** conducting UAT **then** show demonstrative examples **should never** ask abstract questions

**Given** UAT questions **when** asking **then** present one component at a time with definition + implementation + example BEFORE asking **should never** dump all questions at once about all components simultaneously

**Given** UAT questions **when** forming options **then** describe specific tradeoffs and design choices made **should never** use generic approval options like "exactly matches", "mostly matches", "requires revisions"

**Given** user feedback **when** storing **then** record verbatim with context **should never** paraphrase concerns

**Given** user rejects **when** plan UAT **then** return to proposal phase **should never** proceed to implementation

**Given** user rejects **when** impl UAT **then** return to relevant slice **should never** proceed to landing

**Given** component questions **when** presenting **then** ALWAYS include an open-ended feedback question alongside the ACCEPT/REVISE decision so the user can raise related concerns **should never** present only the ACCEPT/REVISE decision without a free-text feedback opportunity

**Given** UAT completes **when** results are captured **then** update the URD with UAT results via `bd comments add <urd-id> "UAT: <summary>"` **should never** leave the URD out of date after UAT

## UAT Phases

### Plan UAT (Phase 5 — `aura:p5-user:s5-uat`)
After 3 reviewers ACCEPT the proposal, present each major design decision to the user one at a time. For each component:
1. Show the proposed interface definition (code snippet)
2. Show a motivating example (how a user would use it)
3. Ask about the specific design choices made (tradeoffs, alternatives considered)

### Implementation UAT (Phase 11 — `aura:p11-user:s11-uat`)
After code review consensus, demonstrate what was actually built component by component. For each component:
1. Run the actual command / show real output
2. Compare against the original proposal
3. Ask about the specific behavioral decisions made in the implementation

## How to Structure UAT Questions

**Critical:** Questions must split the engineering design space on its ambiguous
boundaries to extract maximum information — like a decision tree, where each
question bisects the remaining uncertainty.

The user needs to see the actual thing — definition, behavior, example — and
then evaluate the specific engineering tradeoffs at the boundaries where the
design could go either way.

### Question Design Principles

1. **Each question targets one ambiguous boundary.** Identify where in the design
   space two or more viable alternatives exist, and ask the user to choose.
2. **Options describe competing tradeoffs, not approval levels.** Each option is
   a real engineering alternative with its own pros/cons.
3. **Later questions depend on earlier answers.** Structure the survey as a
   decision tree — Round 1 settles the highest-leverage boundaries, Round 2
   addresses dependent decisions informed by Round 1 answers, etc.
4. **Show context before asking.** The user MUST see a code snippet, interface
   definition, or motivating before/after example before being asked to evaluate.
5. **One component per AskUserQuestion call.** Never batch all components into
   one survey.

### WRONG — generic approval (DO NOT USE):
```
"Does this match your vision?"
options: ["Yes exactly", "Mostly yes", "Partially", "No"]

"Is the MVP scope appropriate?"
options: ["Right scope", "Too minimal", "Too much", "Wrong focus"]
```

These fail because:
- The options don't represent engineering alternatives
- Multiple options lack clear tradeoffs
- The answer doesn't help the architect make better decisions

### RIGHT — boundary-splitting design decisions:
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

"Should runtime deps be baked into the Nix wrapper (hermetic, reproducible) or
expected from PATH (lighter, user-managed)?"
options based on packaging tradeoffs:
  - "Bake all in (hermetic) — writeShellApplication with all runtimeInputs. Fully reproducible."
  - "Bake tmux+python, expect claude+bd from PATH — Wrap what Nix can provide."
  - "Expect all from PATH — Only patch the shebang. User manages all deps."
```

These work because each option is a real engineering alternative with clear
tradeoffs, and the user's choice directly informs the implementation.

See [UAT_EXAMPLE.md](../protocol/UAT_EXAMPLE.md) for a complete worked example
of this question quality in practice.

### Pre-requisite: Cross-reference URE Against the Proposal

UAT is the **second time** the user evaluates this feature. The first time was
during URE (see [/aura:user-elicit](../user-elicit/SKILL.md)), where the user
stated their requirements, priorities, and design preferences. The proposal was
then written to satisfy those requirements.

Before designing UAT questions, cross-reference the URE responses and URD
against the proposal to identify what to surface:

```bash
bd show <elicit-id>     # Re-read the user's original URE responses
bd show <urd-id>        # The structured requirements document
bd show <proposal-id>   # The architect's proposal and tradeoffs
```

Look for:
- **Faithful translations:** Where the proposal directly implements a URE
  choice — show the user how their requirement became a concrete design and
  confirm it matches their intent
- **Tradeoffs the architect resolved:** Where the URE left ambiguity and the
  architect chose one direction — surface the choice and its rationale so the
  user can validate or redirect
- **New dimensions the proposal introduced:** Engineering concerns that weren't
  in the URE (emerged during research/exploration or review) — present these
  with context so the user understands why they matter
- **Gaps or drift:** Where the proposal may have diverged from, reinterpreted,
  or dropped a URE requirement — flag these explicitly

### Question Sequence (Decision Tree)

Structure questions to progressively validate the proposal against the user's
original requirements. Each round narrows the remaining uncertainty.

**Round 1: Highest-leverage tradeoffs** (1-2 questions per AskUserQuestion call)

Start with the 2-3 architectural decisions where the proposal made the biggest
choices. These are the axes where a different decision would lead to a
fundamentally different implementation.

For each, show the user:
1. What they originally said in URE (their stated requirement/preference)
2. What the proposal chose (the concrete interface, type, or approach)
3. The alternatives that were considered and why this one was picked

**Round 2: Dependent and derivative decisions** (informed by Round 1)

With the major tradeoffs validated, surface the second-order decisions that
flow from them — implementation details the user should be aware of.

**Round 3: New dimensions not in URE** (if any)

Present engineering concerns that emerged after URE (from research, codebase
exploration, or reviewer feedback). The user hasn't seen these before, so
provide enough context for an informed decision.

**Final: Catch-all**

One open-ended question — "Is there anything from your original requirements
that you don't see reflected in this proposal?"

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

```
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
      question: "Any related feedback, concerns, or gaps not covered above?",
      header: "Feedback",
      multiSelect: false,
      options: [
        { label: "No additional feedback", description: "All concerns addressed by the questions above" },
        { label: "Related concern", description: "I have feedback on something adjacent or related to this component" },
        { label: "Missing coverage", description: "There's a requirement or design decision from the URD/URE that wasn't addressed" }
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
bd create --labels "aura:p5-user:s5-uat" \
  --title "UAT: Plan acceptance for <feature>" \
  --description "---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  proposal: <proposal-N-id>
---
## Components Reviewed

### Component: <component-name>
**Definition shown:**
\`\`\`
<interface/type/signature shown to user>
\`\`\`

**Motivating example shown:**
\`\`\`
<before/after or input/output example>
\`\`\`

**Question asked:** <exact question text>
**Options presented:** <exact option labels and descriptions>
**User response:** <verbatim selection(s)>

---

### Component: <next-component>
...

## Final Decision
<ACCEPT or REVISE with verbatim reason>"

bd dep add <proposal-id> --blocked-by <uat-task-id>

# Update URD with plan UAT results
bd comments add <urd-id> "Plan UAT: <ACCEPT or REVISE> - <summary of key decisions>"
```

```bash
# For Implementation UAT (Phase 11)
bd create --labels "aura:p11-user:s11-uat" \
  --title "UAT: Implementation acceptance for <feature>" \
  --description "---
references:
  request: <request-task-id>
  urd: <urd-task-id>
  impl_plan: <impl-plan-task-id>
---
## Components Demonstrated

### Component: <component-name>
**Command run / output shown:**
\`\`\`
<actual terminal output shown to user>
\`\`\`

**Question asked:** <exact question>
**User response:** <verbatim response>

## Final Decision
<ACCEPT or REVISE>"

bd dep add <impl-plan-id> --blocked-by <impl-uat-task-id>

# Update URD with implementation UAT results
bd comments add <urd-id> "Impl UAT: <ACCEPT or REVISE> - <summary of findings>"
```

## Handling REVISE

If user selects REVISE:
- **Plan UAT:** Return to architect for proposal revision on the specific component
- **Impl UAT:** Return to relevant slice for implementation fixes

Document the specific component and the user's verbatim feedback in the task description. Do not generalize.
