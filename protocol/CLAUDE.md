# Aura Protocol - Agent Directive

This is the reusable core agent directive for projects using the Aura protocol.
Copy or include this file in your project's CLAUDE.md alongside project-specific instructions.

## System Philosophy

- What does the end-user need, and how will this tradeoff impact them?
- One of the primary design goals of each behaviour, interface, and API, is that they should be easily testable. This is usually done through creation of interfaces with a public API that you KNOW you will need in the end.
- Integration tests are of the most important value, though we want public behaviours to be unit testable.
- If things can be statically defined, then prefer this over runtime definitions and checking.
- Prefer using strongly-typed enums instead of stringly-typed API, return values, or arguments.
- Think about mapping the engineering design space of the specific problem along its axes:
    - how much parallelism do we have in this problem?
    - is it a distributed problem, or a sequential one?
    - do we need many of something, or one?
    - what are the has-a relationships in the problem, and what are the is-a relationships?
    - how often will this problem occur, and how much will it cost each time?

## Constraints

### Universal Code Quality

**Given** shared resources **when** modifying **then** use atomic operations with timeouts **should never** check-then-act

**Given** external input **when** parsing **then** validate at system boundaries with the project's schema/validation tooling **should never** trust raw input or cast types unsafely

**Given** parallel work **when** assigning files **then** ensure each file has exactly one owner with atomic commits **should never** have multiple workers on same file

**Given** a feature request **when** writing requirements **then** use Given/When/Then/Should,Should Not format **should never** write vague criteria

**Given** a class or struct with dependencies **when** designing **then** inject all deps (including clocks, loggers) **should never** hard-code

**Given** runtime events **when** logging **then** use structured logging with context **should never** log secrets or use unstructured print statements

**Given** status/type fields **when** defining **then** use strongly-typed enums **should never** use bare strings at API boundaries

**Given** code changes **when** committing **then** type checking and tests must pass **should never** allow optional CI

### Git & Beads

**Given** task is implemented **when** you are about to commit **then** you **should** use `git agent-commit -m ...`, **should never** use `git commit -m ...`

**Given** you want to execute Beads **when** you are about to call `bd <command> ...` **then** you **should never** `cd <repo_root> && bd <command> ...`, instead you **should** always just call `bd <command> ...`

**Given** you are adding a Beads dependency **when** determining the direction **then** the **parent** (plan, request, epic) is blocked by the **child** (implementation, proposal, task). The parent stays open until the child resolves it. **MUST** use `bd dep add <parent-id> --blocked-by <child-id>`. **SHOULD NEVER** make the child blocked by the parent — that inverts the relationship and means the child can't start until the parent closes, which is backwards.

**The rule:** Ask "which one stays open until the other finishes?" That one is the parent. `bd dep add <stays-open> --blocked-by <must-finish-first>`.

### Correct: `--blocked-by` points at what must finish first

```bash
# "REQUEST is blocked by URE" — URE must complete before REQUEST can close
bd dep add request-id --blocked-by ure-id

# "PROPOSAL is blocked by IMPL PLAN"
bd dep add proposal-id --blocked-by impl-plan-id

# "IMPL PLAN is blocked by each slice"
bd dep add impl-plan-id --blocked-by slice-1-id
bd dep add impl-plan-id --blocked-by slice-2-id

# "slice is blocked by its leaf tasks"
bd dep add slice-1-id --blocked-by leaf-task-a-id
bd dep add slice-1-id --blocked-by leaf-task-b-id
```

Produces the correct tree (leaf work at the bottom, user request at the top):

```
REQUEST
  └── blocked by URE
        └── blocked by PROPOSAL
              └── blocked by IMPL PLAN
                    ├── blocked by slice-1
                    │     ├── blocked by leaf-task-a
                    │     └── blocked by leaf-task-b
                    └── blocked by slice-2
                          ├── blocked by leaf-task-c
                          └── blocked by leaf-task-d
```

### Wrong: reversed direction

```bash
# WRONG — this says "URE is blocked by REQUEST", meaning the request
# must finish before requirements gathering can start (backwards)
bd dep add ure-id --blocked-by request-id
```

**Rule of thumb:** The `--blocked-by` target is always the thing you do *first*. Work flows bottom-up; closure flows top-down.

### User Requirements Document (URD)

**Given** Phase 2 (URE) completes **when** requirements are captured **then** create a URD task (label `aura:urd`) as the single source of truth for user requirements **should never** scatter requirements across multiple unlinked tasks

**Given** a URD exists **when** any phase creates or updates requirements **then** update the URD via `bd comments add <urd-id> "..."` **should never** leave the URD stale when scope changes

**Given** a URD exists **when** architects, reviewers, or supervisors need to understand user intent **then** read the URD with `bd show <urd-id>` **should never** rely solely on the original REQUEST task for requirements

**Given** a URD is created **when** linking to other tasks **then** use `bd dep relate <urd-id> <other-task-id>` (peer reference, NOT `--blocked-by`) **should never** make the URD a blocking dependency — it is a living reference document

### Agent Orchestration

**Given** you need to launch parallel agents for an epic **then** use `aura-swarm start --epic <id>` to create worktree-based agent sessions. Use `aura-swarm status` to monitor. **SHOULD NOT** launch long-running supervisors or workers as Task tool subagents.

**Given** you need a separate supervisor or architect to plan a new epic **then** use `launch-parallel.py --role <role> -n 1 --prompt "..."` to launch in a tmux session. **SHOULD** only use `launch-parallel.py` for long-running supervisor/architect agents that need persistent context. **SHOULD NOT** use `launch-parallel.py` for reviewer rounds.

**Given** you need reviewer rounds (plan review or code review) **then** spawn reviewers as subagents (via the Task tool) or coordinate via TeamCreate. Reviewers are short-lived and should stay in-session for direct result collection. **SHOULD NOT** use `launch-parallel.py` for reviewers.

**Given** inter-agent communication is needed **then** use beads for coordination (`bd comments add`, `bd update --notes`, `bd show`). **SHOULD NOT** reference `aura agent send/broadcast/inbox` — that CLI does not exist.

### Tests & Fixtures

**Given** you are writing a test **when** you need any value (email, path, UUID, timestamp, etc.) **then**:
1. **MUST** first check for an existing fixture/constant in the project's test fixtures
2. **MUST** use centralized constants when they exist
3. **MUST** use factory functions for complex objects when they exist
4. **MUST** use mock factories for dependencies when they exist
5. **SHOULD NOT** write inline string or numeric literals for values that have fixture equivalents
6. **OTHERWISE** if no fixture exists, **MUST** add the value to the appropriate fixture file **before** using it in any test
7. **MUST NOT** mock the system under test — mock dependencies only

### User Interviews (URE/UAT)

**Given** a user interview (requirements elicitation or UAT) **when** capturing the Q&A in a Beads task **then** you **MUST** record the full question, ALL options presented with their descriptions, AND the user's verbatim response. **SHOULD NEVER** summarize options as "(1)", "(2)", "(3)" without the option text — the user's answer referencing option numbers is meaningless without the full options.

### Worker Completion

**Given** a worker finishes implementation **when** signaling completion **then** the worker **MUST**:
1. Run all quality gates (type checking + tests must pass)
2. Verify production code path via code inspection (no TODOs, real deps wired)
3. Update beads task status (`bd close <task-id>`)
4. Add completion comment (`bd comments add <task-id> "Implementation complete."`)

**SHOULD NEVER** close a bead with only "tests pass" as the completion gate — must also verify production code path.

### Slice Reviews

**Given** a slice implementation is complete (tests + typecheck pass) **when** considering closing the bead **then** you **MUST** launch a code review before closing the bead, **MUST** resolve all blocking findings before closing, **SHOULD NEVER** close a slice bead with only "tests pass" as the completion gate.

## Behavior

**When uncertain, ask.** If requirements are ambiguous, scope is unclear, or multiple valid approaches exist — stop and ask before proceeding. Wrong assumptions compound.

**Always think about how your work will affect the end-user**, and if the code will handle changes in the future.

**Design the interface you know you will need:** if it will be required in the end, then include it. But don't make it more complicated than it needs to be, and don't make it simpler than it is.

**Work backwards from the final API/result to define architecture** — but you do NOT need to implement it all upfront. Define all public interfaces and structure first; implementations can be mocked or stubbed until needed.

### Self-Validation Model

Before claiming completion:

1. **Plan backwards:** *"What does success look like, and what does it require?"*
   - Define the end state, then identify each prerequisite working backwards
   - Missing prerequisites reveal missing work
   - Define all public interfaces first; use mocks/stubs until full implementation is needed

2. **Invert the problem:** *"What would make this fail?"*
   - List failure modes (edge cases, race conditions, unhandled errors)
   - Verify each is addressed or explicitly out of scope
   - If you can't falsify your own work, it's not ready

## Agent Roles

| Role | Responsibility |
|------|----------------|
| Architect | Specs, tradeoffs, validation checklist, BDD criteria |
| Reviewer | End-user alignment, implementation gaps, MVP impact |
| Supervisor | Vertical-slice task decomposition, worker allocation, merge order, commits |
| Worker | Vertical slice implementation (full production code path) |

**Consensus:** All 3 reviewers must ACCEPT. Revisions loop until consensus.

## Beads-Unified Workflow

All work flows through Beads tasks:

```
REQUEST_PLAN (user prompt)
    |
ELICIT (URE survey) → creates URD (single source of truth)
    |                      ↕ bd dep relate (peer reference)
PROPOSE_PLAN (architect drafts full plan)
    |
REVIEW_1, REVIEW_2, REVIEW_3 (parallel, vote ACCEPT/REVISE)
    | (loop if any REVISE)
REVISION_N (architect addresses feedback)
    | (back to reviews)
RATIFIED_PLAN (consensus reached, all sign off)
    |
USER_ACCEPTANCE_TEST (plan UAT)
    |
IMPLEMENTATION_PLAN (supervisor decomposes into slices)
    |
VERTICAL SLICES (parallel, each worker owns one production code path)
    |
IMPLEMENTATION_DONE
    |
REVIEW_IMPLEMENTATION (3x reviewers, same end-user alignment criteria)
    |
USER_ACCEPTANCE_TEST (implementation UAT)
    |
ACCEPT
```

### When Reviewing

Check **end-user alignment**, not technical specializations:

- Who are the end-users?
- What would end-users want?
- How would this affect them?
- Are there implementation gaps?
- Does MVP scope make sense?
- Is validation checklist complete?

### When Working

**Supervisor** creates vertical slice tasks with:
- One production code path per slice
- Key details from ratified plan
- Tradeoffs relevant to each slice
- Link back to RATIFIED_PLAN task
- Validation checklist items per task
- BDD acceptance criteria (Given/When/Then/Should Not)
- Explicit file ownership boundaries within each slice
- NEVER implements code themselves — ALWAYS spawns workers

**Worker** implements by:
- Owning a full vertical slice (types → tests → implementation → wiring)
- Following interface contracts from ratified plan
- Satisfying validation checklist items
- Meeting BDD acceptance criteria
- Running quality gates (type checking + tests)
- Signaling completion via beads

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **COMMIT AND PUSH** - This is MANDATORY:
   ```bash
   git add <files>
   git agent-commit -m "feat(scope): description"
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Use `git agent-commit` (not `git commit`) for signed commits
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing — that leaves work stranded locally
- NEVER say "ready to push when you are" — YOU must push
- If push fails, resolve and retry until it succeeds

## References

- [PROCESS.md](PROCESS.md) - Step-by-step workflow execution (single source of truth)
- [CONSTRAINTS.md](CONSTRAINTS.md) - Coding standards, checklists, naming conventions
- `.claude/commands/aura:*.md` - Agent role definitions
