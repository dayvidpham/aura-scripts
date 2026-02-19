# Review Code Implementation

Review code from your specialization's perspective.

## When to Use

Assigned to review code implementation.

## Given/When/Then/Should

**Given** code assignment **when** reviewing **then** apply the project's review criteria (see `AGENTS.md`) **should never** review outside your perspective

**Given** implementation **when** verifying **then** run the project's quality gates (e.g., `go test -race ./...` or `npm run test`) **should never** approve without passing checks

**Given** issues found **when** categorizing **then** use BLOCKING/MAJOR/MINOR severity **should never** block on style

## Steps

1. Read code changes and the URD (`bd show <urd-id>`) for requirements context
2. Run `npm run typecheck` and `npm run test:unit`
3. Apply specialization checklist
4. **Verify production code paths work** (see below)
5. Categorize issues by severity
6. Create RFC comment with findings
7. Cast vote

## Verify Production Code Paths Work

**Given** code implementation **when** reviewing **then** verify production code paths wired **should never** approve dual-export anti-pattern

When reviewing implementation:

1. **Check for dual-export anti-pattern:**

   **Anti-pattern example:**
   ```typescript
   // ❌ ANTI-PATTERN: Test-only export
   export const handleCommand = (argv, service) => { /* tested */ };

   // ❌ ANTI-PATTERN: Production-only export (not tested)
   export const commandCli = new Command()
     .action(async () => {
       // TODO: wire up service
     });
   ```

   **Correct example:**
   ```typescript
   // ✅ CORRECT: Single export, both tested and used in production
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

## RFC Comment

File: `docs/{version}/rfc/comments/{NNN}__{perspective}-review-code__{YYYY-MM-DD}.Rmd`

Get next ID: `npx tsx src/cli/aura.ts rfc next-id`

## Report Results

```bash
# Add review comment to the task
bd comments add <task-id> "CODE-REVIEW: ACCEPT - Implementation matches plan, tests comprehensive"

# Or create a review task
bd create --labels aura:impl:review --title "CODE-REVIEW: <slice-name>" --description "VOTE: ACCEPT - ..."
bd dep add <review-task-id> --blocked-by <slice-task-id>
```
