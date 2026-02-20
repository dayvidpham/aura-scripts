# Supervisor: Plan Tasks

Break RATIFIED_PLAN into vertical slice Implementation tasks for workers.

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-8-implementation-plan)** <- Phase 8

## When to Use

Received handoff from architect with RATIFIED_PLAN task ID and placeholder IMPL_PLAN task.

## Given/When/Then/Should

**Given** IMPL_PLAN placeholder **when** planning **then** decompose into vertical slices (production code paths) **should never** decompose into horizontal layers (files)

**Given** RATIFIED_PLAN features/commands **when** creating tasks **then** assign one vertical slice per worker (full end-to-end) **should never** assign horizontal layers (types worker, tests worker, impl worker)

**Given** vertical slice **when** defining **then** specify production code path and backward planning approach **should never** leave workers guessing what end users will run

**Given** validation_checklist **when** distributing **then** include production code verification **should never** allow test-only validation

## Critical: Vertical Slices, Not Horizontal Layers

**ANTI-PATTERN (causes dual-export problem):**
```
Task A: Layer 1 - types.go (all types)
Task B: Layer 2 - service_test.go (all tests)
Task C: Layer 3 - service.go (all implementation)
Task D: Layer 4 - CLI wiring
```

**Problem:** No worker owns full production code path → dual-export anti-pattern

**CORRECT PATTERN:**
```
SLICE-1: "feature list command" (Worker A owns full vertical)
  - ListOptions, ListEntry types (L1)
  - Tests importing `cli-tool feature list` CLI (L2)
  - service.ListItems() implementation (L3)
  - listCmd (cobra) RunE handler wiring (L3)

SLICE-2: "feature detail command" (Worker B owns full vertical)
  - DetailView types (L1)
  - Tests importing `cli-tool feature detail` CLI (L2)
  - service.GetItemDetail() implementation (L3)
  - detailCmd (cobra) RunE handler wiring (L3)
```

## Steps

1. **Read RATIFIED_PLAN and URD tasks:**
   ```bash
   bd show <ratified-plan-id>
   bd show <urd-id>
   ```

2. **Identify production code paths** (what end users will actually run):
   - CLI commands: `cli-tool feature`, `cli-tool feature list`, `cli-tool feature detail`
   - API endpoints: `POST /api/items`, `GET /api/items/:id`
   - Background jobs: `sync-daemon`, `backup-daemon`

3. **Decompose into vertical slices** (one per production code path):
   - Each slice = one command/endpoint/job
   - Each slice owned by ONE worker
   - Each slice goes from types → tests → implementation → wiring

4. **Identify shared infrastructure** (optional Layer 0):
   - Common types used across ALL slices (e.g., base error enums)
   - Shared utilities (not specific to one slice)
   - If significant, create Layer 0 tasks (parallel, no deps)

5. **Create vertical slice tasks:**
   ```bash
   bd create --type=task \
     --labels="aura:p9-impl:s9-slice" \
     --title="SLICE-1: Implement 'cli-tool feature list' command (full vertical)" \
     --description="$(cat <<'EOF'
   ---
   references:
     impl_plan: <impl-plan-task-id>
     urd: <urd-task-id>
   ---
   ## Production Code Path

   **End user runs:** `./bin/cli-tool feature list`

   ## Worker Owns (Full Vertical Slice)

   Plan backwards from production code path:
   1. End: CLI entry point `listCmd (cobra.Command) RunE handler`
   2. Back: Service call `feature.NewService(deps).ListItems(opts)`
   3. Back: Service method `ListItems(opts ListOptions) ([]ListEntry, error)`
   4. Back: Types `ListOptions`, `ListEntry`

   ## Files You Own (Within These Files)

   - pkg/feature/types.go (ListOptions, ListEntry ONLY)
   - cmd/feature/list_test.go (import actual CLI)
   - pkg/feature/service.go (ListItems method ONLY)
   - cmd/feature/list.go (list subcommand wiring ONLY)

   ## Implementation Order (Layers Within Your Slice)

   **Layer 1: Types** (your slice only)
   - Create ListOptions, ListEntry
   - Do NOT add types for other slices (e.g., DetailView)

   **Layer 2: Tests** (importing production code)
   - Import actual CLI: `import "myproject/cmd/feature"`
   - Test the actual command users will run
   - Tests will FAIL - expected, no implementation yet

   **Layer 3: Implementation + Wiring**
   - Implement service.ListItems() method
   - Wire cobra command with feature.NewService(realDeps)
   - No TODO placeholders
   - Tests should now PASS

   ## Validation

   Before marking complete:
   - [ ] Production code verified via code inspection (no TODOs, real deps wired)
   - [ ] Tests import actual CLI (not test-only export)
   - [ ] No dual-export anti-pattern
   - [ ] No TODO placeholders
   - [ ] Service wired with real dependencies
   EOF
   )" \
     --design='{
       "productionCodePath": "cli-tool feature list",
       "validation_checklist": [
         "Type checking passes",
         "Tests pass",
         "Production code verified via code inspection",
         "Tests import production CLI package",
         "No TODO placeholders in CLI action",
         "Service wired with real dependencies"
       ],
       "acceptance_criteria": [{
         "given": "user runs cli-tool feature list",
         "when": "command executes",
         "then": "shows list from actual service",
         "should_not": "have dual-export (test vs production paths)"
       }],
       "ratified_plan": "<ratified-plan-id>"
     }'

   bd dep add <impl-plan-id> --blocked-by <slice-task-id>
   ```

6. **Update IMPL_PLAN with vertical slice breakdown:**
   ```bash
   bd update <impl-plan-id> --description="$(cat <<'EOF'
   ---
   references:
     request: <request-task-id>
     urd: <urd-task-id>
     proposal: <ratified-proposal-id>
   ---
   ## Vertical Slice Decomposition

   Each worker owns ONE production code path (full vertical slice from CLI → service → types).

   ### Shared Infrastructure (Layer 0 - optional)
   - Common types: SortOrder, OutputFormat, ErrorCode enums
   - Implemented first, parallel

   ### Vertical Slices (parallel, after Layer 0)

   **SLICE-1: "cli-tool feature" (default command)**
   - Worker: A
   - Production path: `./bin/cli-tool feature`
   - Owns: default action, recent items logic
   - Task: aura-xxx

   **SLICE-2: "cli-tool feature list"**
   - Worker: B
   - Production path: `./bin/cli-tool feature list`
   - Owns: ListOptions types, list tests, listItems() method, list CLI wiring
   - Task: aura-yyy

   **SLICE-3: "cli-tool feature detail"**
   - Worker: C
   - Production path: `./bin/cli-tool feature detail <id>`
   - Owns: DetailView types, detail tests, getItemDetail() method, detail CLI wiring
   - Task: aura-zzz

   **SLICE-4: "cli-tool feature search"**
   - Worker: D
   - Production path: `./bin/cli-tool feature search`
   - Owns: SearchQuery types, search tests, searchItems() method, search CLI wiring
   - Task: aura-www

   ## Execution Order

   1. Layer 0 (if needed): Shared infrastructure (parallel)
   2. SLICE-1 through SLICE-4: Each worker implements their vertical slice (parallel)
      - Within each slice: Types (L1) → Tests (L2) → Impl+Wiring (L3)

   ## Validation

   All production code paths verified via code inspection:
   - ./bin/cli-tool feature
   - ./bin/cli-tool feature list
   - ./bin/cli-tool feature detail <id>
   - ./bin/cli-tool feature search
   EOF
   )"
   ```

## Vertical Slice Task Structure

```json
{
  "slice": "feature-list",
  "productionCodePath": "cli-tool feature list",
  "taskId": "aura-xxx",
  "workerOwns": {
    "endPoint": "listCmd (cobra.Command) RunE handler",
    "types": ["ListOptions", "ListEntry"],
    "tests": ["cmd/feature/list_test.go"],
    "implementation": [
      "(*FeatureService).ListItems() method",
      "listCmd wired with feature.NewService(realDeps)"
    ]
  },
  "planningApproach": "Backwards from production code path",
  "validation_checklist": [
    "Type checking passes",
    "Tests pass",
    "Production code works: ./bin/aura sessions list",
    "Tests import production CLI (not test-only export)",
    "No TODO placeholders",
    "Service wired with real dependencies"
  ],
  "acceptance_criteria": [{
    "given": "user runs aura sessions list",
    "when": "command executes",
    "then": "shows session list from actual service",
    "should_not": "have dual-export or TODO placeholders"
  }],
  "ratified_plan": "<ratified-plan-id>",
  "urd": "<urd-id>"
}
```

## Layer Cake Within Each Vertical Slice

Each worker implements their slice in layers (TDD approach):

```
Worker A's Slice: "aura sessions list"
  Layer 1: Types (ListOptions, SessionListEntry only)
  Layer 2: Tests (import sessions package, test list action)
           → Tests will FAIL (expected - no impl yet)
  Layer 3: Implementation + Wiring
           - (*SessionsService).ListSessions() method
           - listCmd wired with sessions.NewService(deps)
           - Wire action to call service
           → Tests should now PASS
```

**Important:** Layer 2 tests failing is expected. Worker knows tests define the contract, implementation comes in Layer 3.

## Red Flags vs Green Flags

**Red flags (horizontal layer decomposition):**
- Tasks organized by layer: "Layer 1 all types", "Layer 2 all tests"
- Worker assigned "all types" or "all tests" instead of feature slice
- No production code path specified per task
- Tasks describe "file to modify" not "production code path to deliver"

**Green flags (vertical slice decomposition):**
- Each task specifies production code path (e.g., "aura sessions list")
- Worker owns full vertical (types → tests → impl → wiring)
- Task description says "plan backwards from end point"
- Validation checklist includes "production code works: ./bin/aura <command>"
- Workers can execute independently (parallel slices)

## Shared Infrastructure (Layer 0)

If multiple slices share common infrastructure:

```
Layer 0 Tasks (parallel, implemented first):
- Common enums: SortOrder, OutputFormat, SessionsErrorCode
- Common types: ParseHealth (used by all slices)
- Shared utilities: isSidechainSession(), getGitBranch()
```

Then vertical slices proceed in parallel, depending on Layer 0.

**Key insight:** Shared infrastructure is the exception, not the rule. Most types/logic belong to specific slices.

## Follow-up Implementation Plan (FOLLOWUP_IMPL_PLAN)

When planning for a follow-up epic (after receiving h1 from architect post-FOLLOWUP_PROPOSAL ratification), the same vertical slice decomposition applies:

```bash
# Create FOLLOWUP_IMPL_PLAN
bd create --type=epic --priority=2 \
  --labels="aura:p8-impl:s8-plan" \
  --title="FOLLOWUP_IMPL_PLAN: <follow-up feature>" \
  --description="---
references:
  followup_epic: <followup-epic-id>
  original_request: <request-task-id>
  original_urd: <urd-task-id>
  followup_urd: <followup-urd-id>
  followup_proposal: <followup-proposal-id>
---
Vertical slice decomposition for follow-up epic."

# Create FOLLOWUP_SLICE-N with adopted leaf tasks
bd create --type=task \
  --labels="aura:p9-impl:s9-slice" \
  --title="FOLLOWUP_SLICE-1: <description>" \
  --description="---
references:
  followup_impl_plan: <followup-impl-plan-id>
  followup_urd: <followup-urd-id>
---
## Adopted Leaf Tasks
| Leaf Task ID | Severity | Original Slice | Description |
|---|---|---|---|
| <leaf-id-1> | IMPORTANT | SLICE-1 | <description> |
| <leaf-id-2> | MINOR | SLICE-2 | <description> |

## Specification
<detailed spec>

## Validation Checklist
- [ ] All adopted leaf tasks resolved
- [ ] Tests pass
- [ ] Production code path verified"

# Wire dual-parent for adopted leaf tasks
bd dep add <followup-slice-id> --blocked-by <leaf-task-id-1>
bd dep add <followup-slice-id> --blocked-by <leaf-task-id-2>
```
