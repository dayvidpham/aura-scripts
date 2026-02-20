---
name: user-request
description: Capture user's feature request verbatim as Phase 1 of epoch
---

# User Request (Phase 1)

Capture the user's feature request **verbatim** in a beads task, then classify, research, and explore. This is the immutable record that all subsequent phases reference.

See `CONSTRAINTS.md` for coding standards.

**-> [Full workflow in PROCESS.md](../protocol/PROCESS.md#phase-1-request-aurap1-user)**

## Given/When/Then/Should

**Given** user provides request **when** capturing **then** store verbatim without paraphrasing **should never** summarize or interpret

**Given** request captured **when** classifying **then** use `aura:p1-user:s1_1-classify` label **should never** use other labels for the initial capture

**Given** classification complete **when** user confirms research depth **then** run s1_2-research and s1_3-explore in parallel **should never** skip research depth confirmation

**Given** Phase 1 complete **when** proceeding **then** invoke `/aura:user-elicit` for Phase 2 **should never** skip to proposal

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

## Step 3: Record Depth + Spawn Parallel Agents (s1_2 || s1_3)

Record the user's depth choice, then spawn two parallel agents:

```bash
bd comments add {{request-task-id}} \
  "Research depth: {{depth}} (user confirmed)"
```

Spawn both agents in parallel (via Task tool with `run_in_background: true`). Each agent invokes its dedicated skill:

### s1_2-research: Domain Research

Invoke `/aura:research` with:
- **topic:** derived from the user's request
- **depth:** the user-confirmed research depth
- **request-task-id:** the REQUEST beads task ID

The `/aura:research` skill handles the full research workflow: depth-scoped checklist, structured report written to `docs/research/<topic>.md`, and summary comment on the REQUEST task.

See [skills/research/SKILL.md](../research/SKILL.md) for full procedure, output format, and examples.

**Depth determines scope:**

| Depth | Local | Web | Deliverable |
|-------|-------|-----|-------------|
| **Quick scan** | Grep project for related patterns, check README/docs | None | 1-paragraph summary of local findings |
| **Standard research** | Local scan + check project dependencies, related repos | Search for domain standards, established patterns | List of prior art with relevance notes |
| **Deep dive** | Full local analysis + dependency tree | Search for competing solutions, RFCs, academic papers, well-regarded projects | Structured report: standards found, competing approaches, recommended direction |

**Research checklist:**
1. What domain standards exist? (RFCs, specs, community conventions)
2. What well-regarded projects solve similar problems? (prior art)
3. What patterns are established in this domain? (idioms, best practices)
4. Are there existing solutions that could be reused or adapted?

**Record findings** as a comment on the REQUEST task:
```bash
bd comments add {{request-task-id}} \
  "Research findings ({{depth}}):
  - Standards: {{list or 'none found'}}
  - Prior art: {{list of projects/solutions}}
  - Patterns: {{established approaches}}
  - Recommendation: {{brief direction}}
  - Full report: docs/research/{{topic}}.md"
```

### s1_3-explore: Codebase Exploration

Invoke `/aura:explore` with:
- **topic:** derived from the user's request
- **depth:** the user-confirmed research depth (same depth applies)
- **request-task-id:** the REQUEST beads task ID

The `/aura:explore` skill handles the full exploration workflow: depth-scoped checklist, structured findings, and summary comment on the REQUEST task.

See [skills/explore/SKILL.md](../explore/SKILL.md) for full procedure, output format, and examples.

**Exploration checklist:**
1. **Entry points:** Where would this feature plug in? (CLI commands, API routes, event handlers)
2. **Data flow:** What existing data structures, types, or schemas are relevant?
3. **Dependencies:** What modules/packages would this feature depend on or extend?
4. **Existing patterns:** How do similar features work in this codebase? (conventions, DI patterns, test structure)
5. **Conflicts:** Are there existing implementations that would need modification or could conflict?

**Depth determines thoroughness:**

| Depth | Scope | Tools |
|-------|-------|-------|
| **Quick scan** | Grep for keywords, check obvious entry points | Glob, Grep |
| **Standard research** | Trace data flow, map dependencies, read related modules | Glob, Grep, Read |
| **Deep dive** | Full dependency graph, architectural analysis, identify all touchpoints | Glob, Grep, Read, Bash (for build/dep tools) |

**Record findings** as a comment on the REQUEST task:
```bash
bd comments add {{request-task-id}} \
  "Explore findings ({{depth}}):
  - Entry points: {{list of files/functions}}
  - Related types: {{existing types/schemas}}
  - Dependencies: {{modules this would use}}
  - Patterns: {{how similar features work here}}
  - Conflicts: {{potential issues or 'none'}}"
```

### Completion

Both agents must complete before proceeding to Phase 2. Their findings are recorded as comments on the REQUEST task, available for the elicitation survey and proposal phases.

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

After Phase 1 completes, invoke `/aura:user-elicit` to begin requirements elicitation (Phase 2).

The elicit task will block this request task:
```bash
bd dep add {{request-task-id}} --blocked-by {{elicit-task-id}}
```
