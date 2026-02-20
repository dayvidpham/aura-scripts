---
name: explore
description: Codebase exploration — find integration points, existing patterns, and related code
---

# Explore

General-purpose codebase exploration skill. Searches the codebase for integration points, existing patterns, data flow, dependencies, and potential conflicts relevant to a topic or feature.

See `CONSTRAINTS.md` for coding standards.

## When to Use

- **Phase 1 (s1_3-explore):** Spawned by `/aura:user-request` after user confirms research depth. Findings recorded as REQUEST task comment.
- **Standalone:** Any agent needing to understand codebase structure for a topic. Invoke directly with a topic and depth.

## Given/When/Then/Should

**Given** a topic or feature **when** exploring **then** follow the depth-scoped checklist and produce structured findings **should never** produce an unstructured list of file paths

**Given** depth is quick-scan **when** exploring **then** grep for keywords, check obvious entry points **should never** read entire modules or trace full dependency graphs

**Given** depth is standard-research **when** exploring **then** trace data flow, map dependencies, read related modules **should never** skip tracing how data flows through the relevant code paths

**Given** depth is deep-dive **when** exploring **then** build full dependency graph, perform architectural analysis, identify all touchpoints **should never** miss transitive dependencies or indirect consumers

**Given** code references **when** documenting **then** use `file:line` citation format **should never** reference files without line numbers for specific code

**Given** Phase 1 context **when** recording findings **then** add a structured comment on the REQUEST task via `bd comments add` **should never** only produce output without updating the REQUEST task

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `topic` | Yes | The feature or concept to explore (e.g., "session management", "CLI command registration") |
| `depth` | Yes | One of: `quick-scan`, `standard-research`, `deep-dive` |
| `request-task-id` | Phase 1 only | Beads task ID to record findings as comment |

## Exploration Checklist

### 1. Entry Points
Where would this feature plug in?
- CLI commands, subcommands, flag definitions
- API routes, handlers, middleware
- Event handlers, hooks, lifecycle callbacks
- Configuration loaders, init functions

### 2. Data Flow
What existing data structures, types, or schemas are relevant?
- Type definitions, interfaces, structs
- Database schemas, migration files
- Protobuf/OpenAPI/JSON schemas
- Configuration types

### 3. Dependencies
What modules/packages would this feature depend on or extend?
- Direct imports and consumers
- Shared utilities, helpers, constants
- External packages and their versions
- Build system integration (Nix flakes, package.json, go.mod)

### 4. Existing Patterns
How do similar features work in this codebase?
- Naming conventions (files, functions, types, tests)
- DI patterns (constructor injection, functional options, context)
- Error handling conventions (error types, wrapping, logging)
- Test structure (fixtures, mocks, test helpers, BDD style)

### 5. Conflicts
Are there existing implementations that would need modification or could conflict?
- Overlapping functionality that might be duplicated
- Shared state that could race or deadlock
- Configuration keys or CLI flags that could collide
- Import cycles or circular dependencies

## Depth Scoping

| Depth | Scope | Tools | Deliverable |
|-------|-------|-------|-------------|
| **quick-scan** | Grep for keywords, check obvious entry points, scan file tree | Glob, Grep | 1-paragraph summary per checklist item |
| **standard-research** | Trace data flow, map dependencies, read related modules, check test patterns | Glob, Grep, Read | Per-section structured findings with file:line citations |
| **deep-dive** | Full dependency graph, architectural analysis, identify all touchpoints, trace transitive consumers | Glob, Grep, Read, Bash (build/dep tools) | Complete architectural map with dependency diagram and risk assessment |

## Output Format

### Structured Findings

```markdown
## Explore Findings: <topic>

**Depth:** <quick-scan|standard-research|deep-dive>
**Date:** <YYYY-MM-DD>

### Entry Points

| File | Line | Type | Description |
|------|------|------|-------------|
| `src/cli/commands.ts` | 42 | CLI subcommand | `register` function adds command to CLI router |
| `src/api/routes.ts` | 118 | HTTP handler | `POST /sessions` endpoint |

### Data Flow

```
User input → CLI parser (src/cli/parse.ts:30)
  → Command handler (src/commands/session.ts:15)
    → Service layer (src/services/session.ts:42)
      → Repository (src/db/session-repo.ts:28)
        → Database
```

**Relevant types:**
- `SessionConfig` at `src/types/session.ts:12` — configuration schema
- `SessionState` at `src/types/session.ts:45` — runtime state enum

### Dependencies

**Direct:**
- `src/services/session.ts` imports `src/db/session-repo.ts`
- `src/commands/session.ts` imports `src/services/session.ts`

**Shared utilities:**
- `src/utils/logger.ts` — structured logging (used by all services)
- `src/utils/config.ts` — configuration loader

**External:**
- `better-sqlite3@11.0.0` — database driver
- `zod@3.23.0` — schema validation

### Existing Patterns

**Naming:** Commands use `<verb>-<noun>.ts` (e.g., `create-session.ts`)
**DI:** Constructor injection via factory functions (see `src/services/index.ts:20`)
**Tests:** Vitest with `describe/it` blocks, fixtures in `tests/fixtures/`
**Errors:** Custom error classes extending `AppError` at `src/errors/base.ts:5`

### Conflicts

- `src/services/auth.ts:88` — existing session cleanup logic may overlap
- `src/types/session.ts:45` — `SessionState` enum may need new values
- No import cycles detected
```

## Phase 1 Integration

When invoked as part of Phase 1 (s1_3-explore), record findings on the REQUEST task:

```bash
bd comments add {{request-task-id}} \
  "Explore findings ({{depth}}):
  - Entry points: {{list of files/functions with line numbers}}
  - Related types: {{existing types/schemas with locations}}
  - Dependencies: {{modules this would use}}
  - Patterns: {{how similar features work here}}
  - Conflicts: {{potential issues or 'none'}}"
```

## Example

### Invocation (Phase 1)

```
Topic: "backup event verbose logging"
Depth: standard-research
Request task: aura-scripts-82j
```

### Resulting Comment

```
Explore findings (standard-research):
  - Entry points: src/watch/handler.ts:42 (event dispatch), src/cli/watch.ts:15 (--verbose flag)
  - Related types: BackupEvent at src/types/events.ts:23, VerboseConfig at src/types/config.ts:88
  - Dependencies: src/services/backup.ts, src/utils/logger.ts, src/watch/debounce.ts
  - Patterns: Event handlers use observer pattern (src/watch/observer.ts:10), verbose fields added via spread operator on base event
  - Conflicts: none — verbose logging is additive, no existing verbose implementation
```

## Standalone Use

When used outside Phase 1, produce the structured findings directly as output. No beads comment is needed unless a task ID is provided.

```
/aura:explore
Topic: "Nix flake module system"
Depth: deep-dive
```

This produces the full architectural map without requiring a REQUEST task context.
