# Review Code Implementation

Review code implementation with full severity tree procedure (Phase 10).

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-10-code-review)**

## When to Use

Assigned to review code implementation after worker slices complete.

## Given/When/Then/Should

**Given** code assignment **when** reviewing **then** apply end-user alignment criteria and verify production code paths **should never** approve without running quality gates

**Given** implementation **when** verifying **then** run the project's quality gates **should never** approve without passing checks

**Given** issues found **when** categorizing **then** use BLOCKER/IMPORTANT/MINOR severity with EAGER group creation **should never** skip creating empty severity groups

**Given** BLOCKER finding **when** wiring dependencies **then** add dual-parent relationship (severity group + slice) **should never** wire BLOCKER to only one parent

## Severity Tree: EAGER Creation

**ALWAYS create 3 severity group tasks per review round**, even if some groups have no findings:

```bash
# Step 1: Create all 3 severity groups immediately (EAGER, not lazy)
bd create --labels "aura:severity:blocker,aura:p10-impl:s10-review" \
  --title "SLICE-1-REVIEW-reviewer1-1 BLOCKER" \
  --description "---
references:
  slice: <slice-id>
  review: <review-id>
---
BLOCKER findings for this review round"
# Result: <blocker-group-id>

bd create --labels "aura:severity:important,aura:p10-impl:s10-review" \
  --title "SLICE-1-REVIEW-reviewer1-1 IMPORTANT" \
  --description "---
references:
  slice: <slice-id>
  review: <review-id>
---
IMPORTANT findings for this review round"
# Result: <important-group-id>

bd create --labels "aura:severity:minor,aura:p10-impl:s10-review" \
  --title "SLICE-1-REVIEW-reviewer1-1 MINOR" \
  --description "---
references:
  slice: <slice-id>
  review: <review-id>
---
MINOR findings for this review round"
# Result: <minor-group-id>

# Step 2: Wire severity groups to review task
bd dep add <review-id> --blocked-by <blocker-group-id>
bd dep add <review-id> --blocked-by <important-group-id>
bd dep add <review-id> --blocked-by <minor-group-id>
```

### Adding Findings to Severity Groups

```bash
# BLOCKER finding — dual-parent relationship
bd create --title "BLOCKER: <finding title>" \
  --description "<finding details with file:line references>"
bd dep add <blocker-group-id> --blocked-by <blocker-finding-id>
bd dep add <slice-id> --blocked-by <blocker-finding-id>

# IMPORTANT finding — single parent (severity group only)
bd create --title "IMPORTANT: <finding title>" \
  --description "<finding details>"
bd dep add <important-group-id> --blocked-by <important-finding-id>

# MINOR finding — single parent (severity group only)
bd create --title "MINOR: <finding title>" \
  --description "<finding details>"
bd dep add <minor-group-id> --blocked-by <minor-finding-id>
```

### Closing Empty Groups

Empty severity groups (no findings) are closed immediately:

```bash
# If no IMPORTANT findings were found:
bd close <important-group-id>

# If no MINOR findings were found:
bd close <minor-group-id>
```

### Dual-Parent BLOCKER Relationship

BLOCKER findings have **two parents**:
1. The severity group task (`aura:severity:blocker`) — for categorization
2. The slice they block — for dependency tracking

This ensures BLOCKERs both categorize under the severity tree AND block the slice they apply to.

IMPORTANT and MINOR findings do **NOT** block the slice — they are tracked in the follow-up epic.

## Steps

1. Read code changes and the URD:
   ```bash
   bd show <slice-id>
   bd show <urd-id>   # Read URD for requirements context
   ```

2. Run quality gates:
   ```bash
   # Run your project's type checking and test commands
   ```

3. Apply review criteria (see End-User Alignment in `aura:reviewer.md`)

4. **Verify production code paths** (see below)

5. Create review task:
   ```bash
   bd create --labels "aura:p10-impl:s10-review" \
     --title "SLICE-1-REVIEW-reviewer1-1: <feature>" \
     --description "---
   references:
     slice: <slice-id>
     urd: <urd-id>
   ---
   VOTE: <ACCEPT|REVISE> - <justification>"
   bd dep add <slice-id> --blocked-by <review-id>
   ```

6. Create severity tree (EAGER — all 3 groups immediately)

7. Add findings to appropriate severity groups

8. Close empty severity groups

9. Cast vote via `bd comments add`

## Verify Production Code Paths

**Given** code implementation **when** reviewing **then** verify production code paths wired **should never** approve dual-export anti-pattern

1. **Check for dual-export anti-pattern:**

   **Anti-pattern example:**
   ```typescript
   // WRONG: Test-only export
   export const handleCommand = (argv, service) => { /* tested */ };

   // WRONG: Production-only export (not tested)
   export const commandCli = new Command()
     .action(async () => {
       // TODO: wire up service
     });
   ```

   **Correct example:**
   ```typescript
   // CORRECT: Single export, both tested and used in production
   export const commandCli = new Command()
     .action(async (options) => {
       const service = createService({ /* real deps */ });
       const result = await service.doThing(options);
       console.log(result);
     });

   // Tests import commandCli directly
   import { commandCli } from './commands/thing.js';
   ```

2. **Verify no TODO placeholders:**
   ```bash
   grep -r "TODO" src/  # Should not find any in delivered code
   ```

3. **Check tests import production code:**
   - Test file should import the actual CLI command or API endpoint
   - Not a separate test harness function

4. **Production code verified via code inspection:**
   - No TODOs in CLI/API actions
   - Real dependencies wired (not mocks in production code)
   - Tests import production code

## Follow-up Epic

**Trigger:** Review completion + ANY IMPORTANT or MINOR findings exist.
**NOT gated on BLOCKER resolution.**
**Owner:** Supervisor creates the follow-up epic (label `aura:epic-followup`).

## Report Results

```bash
# Add vote comment to the review task
bd comments add <review-id> "VOTE: ACCEPT - Implementation matches plan, tests comprehensive"

# Or
bd comments add <review-id> "VOTE: REVISE - BLOCKERs found, see severity tree for details"
```
