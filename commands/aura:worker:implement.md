# Worker: Implement Vertical Slice

Implement your vertical slice (full production code path from CLI/API → service → types).

**-> [Full workflow in PROCESS.md](PROCESS.md#phase-9-worker-slices)** <- Phase 9

## When to Use

You have a Beads task ID for a vertical slice and are ready to implement end-to-end.

## Given/When/Then/Should

**Given** vertical slice task **when** implementing **then** plan backwards from production code path **should never** start with types without knowing the end

**Given** production code path **when** implementing **then** own full vertical (types → tests → impl → wiring) **should never** implement only horizontal layer

**Given** tests **when** writing **then** import actual production code **should never** create test-only export or dual code paths

**Given** implementation complete **when** verifying **then** confirm production code path is wired (via code inspection or safe testing) **should never** rely only on unit tests passing

**Given** dependencies **when** designing **then** inject all deps for testability **should never** hard-code `new`

**Given** external input **when** processing **then** validate with schema/validation tooling **should never** trust raw input

See the project's `AGENTS.md` and `~/.claude/CLAUDE.md` for coding standards.

## Steps

0. **Plan backwards from production code path (before implementing):**

   **Given** Beads task **when** starting **then** identify production code path first

   ```bash
   bd show <task-id>
   # Look for: "productionCodePath": "cli-command subcommand" or "api-endpoint"
   ```

   **Trace backwards through call stack:**
   ```
   End: User runs production command
     ↓ Entry: CLI command.action(...) or API endpoint handler
     ↓ Service: createXService({ deps }).method(...)
     ↓ Types: InputType → OutputType
   ```

   **Identify what you own in each layer:**
   - **L1 Types:** Which types does YOUR slice need? (not other slices)
   - **L2 Tests:** Import actual production code (CLI/API), not test-only export
   - **L3 Implementation:** Service method + wiring with real dependencies (not TODO)

1. Read Beads task for full context:
   ```bash
   bd show <task-id>
   ```

2. Update status:
   ```bash
   bd update <task-id> --status=in_progress
   ```

3. Implement your vertical slice in layers:

   **Layer 1: Types (your slice only)**
   - Create only types YOUR slice needs
   - Don't add types for other slices

   **Layer 2: Tests (import production code)**
   - Import actual CLI/API: `import { commandCli } from '...'`
   - NOT test-only export: ~~`import { handleCommand } from '...'`~~
   - Tests will FAIL - expected (no impl yet)

   **Layer 3: Implementation + Wiring**
   - Service method for your slice
   - CLI/API wiring with real dependencies: `createService({ fs, logger, ... })`
   - NOT TODO placeholders: ~~`// TODO: Wire service`~~

   Follow:
   - validation_checklist items
   - acceptance_criteria (BDD Given/When/Then)
   - tradeoffs from ratified plan

4. Verify quality gates:
   - Type checking passes
   - Tests pass

## Checklist

- [ ] Planned backwards from production code path
- [ ] Read Beads task for validation_checklist
- [ ] Each validation_checklist item satisfied
- [ ] BDD acceptance_criteria met
- [ ] Tests import actual production code (not test-only export)
- [ ] No dual-export anti-pattern (one code path for tests and production)
- [ ] No TODO placeholders in production code
- [ ] Service wired with real dependencies (not mocks in production)
- [ ] Quality gates pass (type checking + tests)
- [ ] Production code path verified (via code inspection: no TODOs, real deps wired, tests import production code)

## Next

- Complete: `/aura:worker:complete`
- Blocked: `/aura:worker:blocked`
