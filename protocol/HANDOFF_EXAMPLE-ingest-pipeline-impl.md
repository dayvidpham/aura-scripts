# Handoff: `aura ingest` Data Ingestion Pipeline

> Request: unified-schema-t9d
> URE: unified-schema-m3l
> Proposal: unified-schema-hjy (RFC v0.2.0, RATIFIED)
> Impl Plan: unified-schema-fuf (10 vertical slices, all DONE)
> Plan UAT: llm/uat-plan-acceptance.md

## Summary

Implements a complete data ingestion pipeline for AI coding agent transcripts. The `aura ingest` CLI command discovers, normalizes, and stores session data from Claude Code and OpenCode into a filesystem-based staging area. The pipeline uses dependency injection throughout, strongly-typed newtypes with validated constructors, incremental diffing with TOCTOU mitigation, and atomic writes.

**~8,250 lines added across 30+ Go files** (3,600 implementation + 3,200 tests + 900 test infrastructure + config/docs/CLI).

---

## Design Principles Alignment

| Principle | Before | After |
|-----------|--------|-------|
| **Testability via DI** | No data abstraction | `FileSystem`, `GitResolver`, `SourceAdapter` interfaces enable `MemFS`/`StubGitResolver`/`StubAdapter` swap without touching pipeline |
| **Strongly-typed enums** | N/A | `Provider`, `Role`, `DiffStatus`, `SourceFormat`, `RedactionLevel` as typed enums; `SessionID`, `ModelID`, `ProjectHash`, `HostSlug`, `ResolvedPath` as validated newtypes |
| **Composition over inheritance** | N/A | Pipeline (orchestration) + Adapter (discovery) + Config (parsing) + Types (validation) — each replaceable |
| **Interface-first design** | No ingest layer | `FileSystem`, `GitResolver`, `SourceAdapter` defined before implementations; `MemFS`, `StubGitResolver`, `StubAdapter` satisfy same contracts |
| **Integration tests over unit tests** | N/A | Pipeline tests use real `Pipeline` with injected `MemFS`/`StubGitResolver`/`StubAdapter`; adapter tests run real adapters with `MemFS` fixtures |
| **ast-grep enforcement** | N/A | 4 custom rules: `no-bare-signal-literals`, `no-string-status-types`, `no-stringly-typed-args`, `no-untyped-string-const` |

---

## Architecture

### Pipeline Stages

```
aura ingest
    |
    v
DISCOVER ---- For each enabled provider, create adapter via factory, call Discover()
    |          Returns []DiscoveredSession with ModTime, SourcePath, SubagentPaths
    v
DIFF -------- Classify each session: New / Updated / Unchanged / Active
    |          Checks: metadata exists? schema version matches? source newer? staleness?
    v
FILTER ------ Skip Unchanged and Active (unless --force / --include-active)
    |
    v
EXTRACT+WRITE  Extract metadata via adapter, atomically write:
    |           1. Create .tmp-{sessionId}-{hex8} directory
    |           2. Copy transcript + debug files
    |           3. Write {sessionId}--metadata.json
    |           4. Rename temp dir to final location
    v
CLEANUP ----- Remove orphan .tmp-* directories from failed runs
    |
    v
REPORT ------ Return PipelineResult with summary counts + per-session status
```

### Output Layout

```
~/.local/share/aura/aura-sync/
└── {hostSlug}/                           # e.g. github.com--user--repo
    └── {sessionId}/
        ├── {unixMillis}--transcript.jsonl # Raw transcript (Claude: JSONL)
        ├── {sessionId}--metadata.json     # UnifiedMetadata JSON
        ├── debug/                         # Debug artifacts mirrored from source
        └── subagents/                     # Child sessions (if present)
            └── {childSessionId}/          # Same structure recursively
                ├── {unixMillis}--transcript.jsonl
                └── {childSessionId}--metadata.json
```

### Host Slug Derivation

```
git@github.com:dayvidpham/aura.git       -> github.com--dayvidpham--aura
https://gitlab.com/dayvidpham/project.git -> gitlab.com--dayvidpham--project
(no remote)                               -> __aura-untracked__--home--user--dev--project
```

### Dependency Injection

```
Pipeline
    ├── FileSystem ─── OSFileSystem (prod) / MemFS (test)
    ├── GitResolver ── ExecGitResolver (prod) / StubGitResolver (test)
    └── adapters map[Provider]AdapterFactory
            ├── claude ── ClaudeAdapter(fs, git)
            └── opencode ── OpenCodeAdapter(fs, git)
```

---

## New Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Strong Types | `internal/ingest/types.go` | 160 | `SessionID`, `ModelID`, `ProjectHash`, `HostSlug`, `ResolvedPath`, `Role` — validated newtypes with `New*` constructors |
| Path Validation | `internal/ingest/validate.go` | ~30 | `ValidatePathComponent`, `ValidatePathContainment` for traversal prevention |
| Schema Types | `internal/ingest/schema.go` | 60 | `Provider`, `SourceFormat`, `Session`, `Turn`, `ToolCall`, `SessionMetadata` enums and structs |
| Metadata | `internal/ingest/metadata.go` | 104 | `UnifiedMetadata` with `TimestampInfo`, `SourceInfo`, `GitInfo`, `ProjectInfo`, `StatsInfo`, `SubagentRef`, `DiagnosticsInfo` |
| FileSystem | `internal/ingest/fs.go` | 95 | `FileSystem` interface (11 methods) + `OSFileSystem` production impl |
| GitResolver | `internal/ingest/git.go` | 86 | `GitResolver` interface (5 methods) + `ExecGitResolver` via `exec.Command` |
| SourceAdapter | `internal/ingest/adapter.go` | 43 | `SourceAdapter` interface, `SourceConfig`, `DiscoveredSession`, `AdapterFactory` |
| Host Slug | `internal/ingest/hostslug.go` | ~80 | `DeriveHostSlug(remote, fallbackPath)` — SSH/HTTPS URL parsing + sanitized fallback |
| Claude Adapter | `internal/ingest/claude.go` | 418 | Walks `~/.claude/projects/` for JSONL transcripts, discovers subagents, extracts metadata from JSONL lines |
| OpenCode Adapter | `internal/ingest/opencode.go` | 484 | Reads `project/{hash}.json`, `session/{hash}/ses_{id}.json`, `message/ses_{id}/msg_{id}.json` hierarchy |
| Pipeline | `internal/ingest/pipeline.go` | 602 | 6-stage orchestrator: discover, diff, filter, extract+write, cleanup, report |
| Config | `internal/config/config.go` | 176 | `Config` struct, YAML parsing via `gopkg.in/yaml.v3`, defaults, git email auto-detect |
| Redaction Levels | `internal/redact/levels.go` | 26 | `RedactionLevel` enum: `minimal`, `standard`, `maximum` |
| Test Infrastructure | `internal/testutil/mocks.go` | 432 | `MemFS`, `StubGitResolver`, `StubAdapter`, shared test constants |
| CLI Wiring | `cmd/aura/main.go` | +260 | `buildIngestCmd()` with 9 cobra flags, DI setup, JSON/human output |
| Store (stub) | `internal/store/` | 22 | Placeholder `Store` struct and `Migration` for future SQLite |
| Metrics (stub) | `internal/metrics/` | 29 | Placeholder `BehavioralMetrics`, `PrecisionMetrics`, `EfficiencyMetrics`, `GitAnalyzer` |

### Test Files

| File | Lines | Tests | Coverage |
|------|-------|-------|----------|
| `internal/ingest/types_test.go` | 311 | 9 | SessionID, ModelID, ProjectHash, HostSlug, ResolvedPath, Role, Provider validation |
| `internal/ingest/validate_test.go` | ~60 | 2 | Path component + containment validation |
| `internal/ingest/fs_test.go` | ~200 | 11 | OSFileSystem integration: write, read, stat, rename, copy, remove, walk |
| `internal/ingest/git_test.go` | ~120 | 6 | ExecGitResolver integration: remote, branch, worktree, email |
| `internal/ingest/metadata_test.go` | ~180 | 10 | JSON round-trip, nullable fields, diagnostics, schema version |
| `internal/ingest/adapter_test.go` | ~30 | 2 | SourceConfig empty paths, DiscoveredSession zero value |
| `internal/ingest/hostslug_test.go` | ~80 | 1 (table) | SSH, HTTPS, SCP, fallback URL formats |
| `internal/ingest/claude_test.go` | ~400 | 14 | Discover (empty, multi-project, subagent linking, cancelled ctx), ExtractMetadata (tool counts, no git, corrupt JSONL, subagent ref) |
| `internal/ingest/opencode_test.go` | 556 | 9 | Discover (empty, subagent linking), ExtractMetadata (no git, message counts, missing model, dir naming) |
| `internal/ingest/pipeline_test.go` | 1,303 | 15 | End-to-end, incremental, dry-run, force, active session, include-active, error resilience, orphan cleanup, multi-provider, permissions, metadata contents |
| `internal/config/config_test.go` | 439 | 12 | YAML parsing, defaults, validation (redaction, version, staleness), Load with MemFS |
| `internal/redact/levels_test.go` | 27 | 1 (table) | RedactionLevel validation |
| `internal/testutil/mocks_test.go` | 467 | 15 | MemFS operations, StubGitResolver factories, StubAdapter behavior |
| `cmd/aura/main_test.go` | 259 | 8 | Flag parsing, invalid provider, dry-run, JSON output, verbose, source-path override/pairing |

---

## Key Design Decisions

### 1. FileSystem + GitResolver as Injected Interfaces

All file I/O and git operations go through interfaces, never direct `os.*` or `exec.Command` calls. This enables:
- **MemFS** for pipeline tests (no disk I/O, deterministic, fast)
- **StubGitResolver** with per-method error fields for simulating partial git failures
- Compile-time guards: `var _ FileSystem = (*OSFileSystem)(nil)` on all implementations

### 2. Validated Newtypes (Constructor Pattern)

Every string-based ID has a `New*(raw) (T, error)` constructor enforcing invariants:
- `SessionID`: regex-validated (UUID, agent-{hex}, ses_{id}, msg_{id}), rejects path separators and `..`
- `ProjectHash`: 64-character lowercase hex
- `HostSlug`: `[a-zA-Z0-9._-]+`, rejects `..`
- `ResolvedPath`: tilde-expanded, cleaned, absolute
- Raw `string` casts are never used outside constructors

### 3. Incremental Diffing with TOCTOU Mitigation

Sessions are classified as New/Updated/Unchanged/Active using a priority chain:
1. No existing metadata? → **New**
2. Schema version mismatch? → **Updated**
3. Source modified after metadata? → **Updated**
4. Source modified < staleness threshold ago? → **Active** (skip by default)
5. Otherwise → **Unchanged**

`--force` re-ingests Updated+Unchanged (still respects staleness). `--include-active` opts into active sessions separately.

### 4. Atomic Writes via Temp Directory + Rename

Each session writes to `.tmp-{sessionId}-{hex8}/` then renames to final path. This ensures:
- Partial writes never corrupt the output directory
- Orphan `.tmp-*` directories from crashed runs are cleaned up on next invocation
- `renameDir` handles cross-device moves portably (recursive copy + delete fallback)

### 5. Adapter Factory Pattern

Adapters are registered as `func(FileSystem, GitResolver) SourceAdapter` factories. The pipeline constructs adapters at runtime, injecting its own DI dependencies. This allows:
- Adding new providers (Gemini, Codex) without changing pipeline code
- Each adapter encapsulates its provider's quirks (JSONL vs JSON hierarchy, subagent discovery patterns)

### 6. Structured Diagnostics (UAT Change)

Adapter-level warnings use `DiagnosticEntry` objects (not plain strings):
```go
type DiagnosticEntry struct {
    ErrorType   string `json:"errorType"`   // e.g. "parse_error"
    Location    string `json:"location"`    // e.g. "line 47"
    Message     string `json:"message"`     // human-readable
    Remediation string `json:"remediation"` // actionable fix
}
```
This was upgraded from string-based warnings per UAT feedback.

---

## CLI Interface

```bash
$ aura ingest                                      # ingest with defaults (~/.config/aura/config.yaml)
$ aura ingest --config /path/to/config.yaml        # explicit config
$ aura ingest --source-provider claude \
              --source-path ~/.claude/projects/     # override source (REPLACES config, not additive)
$ aura ingest --output /tmp/aura-out               # override output directory
$ aura ingest --dry-run                             # show what would be ingested
$ aura ingest --force                               # re-ingest updated+unchanged (respects staleness)
$ aura ingest --include-active                      # also ingest sessions still being written
$ aura ingest --verbose                             # show per-session file-level detail
$ aura ingest --json                                # machine-readable JSON output
$ aura ingest --debug                               # (registered, not yet wired to logger)
```

Default output:
```
Output:  /home/user/.local/share/aura/aura-sync
Config:  /home/user/.config/aura/config.yaml
Sources: claude: /home/user/.claude/projects
aura ingest: 12 sessions (3 new, 2 updated, 5 unchanged), 2 active (skipped), 0 errors [1.2s]
```

With `--verbose`:
```
  NEW        claude     99d59925-36bc-424c-a789-8be54d9702ba  ->  /home/user/.local/share/aura/aura-sync/github.com--user--repo/99d59925.../
  UPDATED    opencode   ses_3cd91f52effeXd3QAJ54jOyzv5        ->  /home/user/.local/share/aura/aura-sync/github.com--user--repo/ses_3cd9.../
  UNCHANGED  claude     e4eb6fb5-5b87-4d6f-82da-0b5a5f917694
```

---

## Config Schema

```yaml
version: 1
user:
  email: ""  # auto-detected from git config --global user.email
redaction:
  level: minimal  # minimal | standard | maximum
sources:
  claude:
    enabled: true
    paths:
      - ~/.claude/projects
  opencode:
    enabled: false
    paths:
      - ~/.local/share/opencode
output:
  basePath: ~/.local/share/aura/aura-sync
  stalenessThresholdSec: 60
```

Missing config triggers a suggestion to run `aura kickstart` (FTUE, separate epic).

---

## Adapter Source Formats

### Claude Code (`~/.claude/projects/`)

```
~/.claude/projects/
└── {projectHash}/
    └── {sessionUUID}.jsonl           # One JSON object per line
        # First line: {"type":"summary","model":"claude-opus-4-6",...}
        # Subsequent: {"type":"human"|"assistant"|"tool_result",...}
    └── subagents/
        └── agent-{hex}.jsonl         # Same format, linked via parentUUID
```

### OpenCode (`~/.local/share/opencode/`)

```
~/.local/share/opencode/
├── project/{sha256}.json             # {"path":"/repo","name":"my-project"}
├── session/{sha256}/ses_{id}.json    # {"model":"claude-opus-4-6","parentID":"..."}
└── message/ses_{id}/msg_{id}.json    # Individual messages
```

---

## Implementation Slices

| Slice | Description | Commit | Group |
|-------|-------------|--------|-------|
| S1 | Strong types + validation | `705edcb` | Foundation |
| S2 | FileSystem + GitResolver interfaces | `e7fc426` | A (parallel) |
| S4 | UnifiedMetadata struct | `7e9d981` | A (parallel) |
| S5 | Host slug derivation | `faa18bd` | A (parallel) |
| S3 | Config package | `3f657cf` | B (after A) |
| S6 | SourceAdapter interface | `c9f398b` | B (after A) |
| S7 | Claude Code adapter | `b0f52af` | C (after S6) |
| S8 | OpenCode adapter | `f11ac30` | C (after S6) |
| S9 | Pipeline orchestrator | `0cac418` | D (sequential) |
| S10 | CLI wiring | `ed15717` | D (sequential) |

### Post-Implementation Fixes

| Commit | Fix |
|--------|-----|
| `978fe2b` | Add OutputPath to SessionResult, show paths in printSummary |
| `59861fe` | Add Tracking field to GitInfo from TrackingBranch() resolver |
| `ba818e7` | Worktree() uses `git worktree list --porcelain`, CWD fallback uses `filepath.Dir` |
| `94a4d83` | Copy debug files to `{sessionDir}/debug/` during processSession |
| `cd7b198` | Nest subagent sessions under `{parentID}/subagents/{childID}/` |
| `6d27147` | Two-pass Discover to fix empty SubagentPaths from walk order |
| `11a0332` | Change default base path from `~/.local/state/` to `~/.local/share/` |
| `0744377` | discover() returns partial results when one provider fails |
| `f629f2e` | Claude Discover walk callback returns ctx.Err() on cancellation |
| `3e2e11b` | Sanitize spaces and special chars in fallback HostSlug |
| `3f8d19b` | OpenCode adapter warns on empty model via diagnostics |
| `5db0071` | Error when --source-path and --source-provider are not paired |
| `81d3398` | Clean up dst directory on renameDir mid-walk failure |

---

## Quality Gates

```bash
make check    # fmt + vet + ast-grep + go test -race ./...
make fmt      # gofmt -l (fails if any file needs formatting)
make vet      # go vet ./...
```

4 ast-grep rules enforce type safety:
- `no-bare-signal-literals` (error) — no string literals for signal names
- `no-string-status-types` (warning) — no `type XStatus string` declarations
- `no-stringly-typed-args` (error) — no string literals in typed Status/Reason fields
- `no-untyped-string-const` (warning) — no untyped `const X = "..."` for status-like names

---

## Original User Request

> unified-schema-t9d (verbatim)

Take in the @initial-collaboration-protocol.md . We need the data ingestion pipeline to take in the Claude and OpenCode transcripts for our MVP. Right now, we just need to copy them to `~/.local/state/aura/aura-sync/{gitlab.com,github.com--{user}--{repo-name}}/{claude,opencode}/{uuid}/{uuid}--transcript.md`. Should occur in the `aura ingest` command. This should have a `~/.local/state/aura/aura-sync/{claude,opencode}/{uuid}/{uuid}--metadata.json` file that contains the path to repo on the user system, and the git branch, remote, or worktree. It will also contain the `modelHarness: "opencode"`, `model: claude-sonnet-<some year or ID>`. {user} is just their email, e.g. 'dayvidpham@gmail.com'

Each `{uuid}--transcript.md` should have a integer ISO timestamp for sortable usage. Also want the `debug/`, tool call outputs stored under the `{uuid}/`. Metadata on the subagents should be the same, just need a parentUuid that maps child to parent.

The `ingest` command will respect a yaml config that we create at `~/.config/aura/config.yaml`. The config will hold the user's chosen redaction level, their parsed git email from their config, which and the locations we scan for a given provider. Model harnesses have a HAS-A relationship with one-to-many set of transcript sources.

## User Requirements (URE)

> unified-schema-m3l

| Question | Answer |
|----------|--------|
| Claude Code location | `~/.claude/projects/` — default, per-project session dirs |
| OpenCode location | `~/.local/share/opencode/` — XDG data dir |
| Discovery strategy | Auto-scan configured directories (FTUE TUI is separate epic) |
| Host slug format | `github.com--user--repo`, fallback `__aura-untracked__--{sanitized-path}` |
| Timestamp precision | Unix milliseconds |
| Debug/tool output format | Raw transcripts; adapter layer driven by UnifiedMetadata |
| Scope | Ingest CLI + config ONLY (FTUE is separate epic) |
| Redaction levels | `minimal` / `standard` / `maximum` (matching `internal/redact/`) |

## Plan UAT

> llm/uat-plan-acceptance.md

5 components reviewed with user:

1. **Filesystem Layout** — ACCEPT (host slug format, permissions confirmed)
2. **UnifiedMetadata Schema** — ACCEPT_WITH_COMMENTS (token stats deferred; diagnostics upgraded to structured errors)
3. **Config Schema** — ACCEPT (missing config prompts `aura kickstart`; `--source-path` replaces config)
4. **Incremental Ingestion** — ACCEPT_WITH_COMMENTS (staleness configurable; separate `--include-active` flag)
5. **CLI Output** — ACCEPT_WITH_COMMENTS (dry-run collapses subagents; `--verbose` shows file-level detail)

---

## Open Items

- [ ] **Redaction not implemented** — `internal/redact/` has level definitions but no actual redaction logic (SecretDetector, PIIDetector, ASTAnonymizer are stubs)
- [ ] **Store not implemented** — `internal/store/` has placeholder Store struct; SQLite persistence is a future RFC
- [ ] **Metrics not implemented** — `internal/metrics/` has placeholder types; token efficiency and behavioral analysis deferred
- [ ] **No `{provider}/` segment in output path** — per URE, adapter layer uses UnifiedMetadata instead
- [ ] **Token stats are zero** — deferred to separate metrics pipeline per UAT
- [ ] **FTUE / kickstart** — first-time config setup is separate epic
- [ ] **Logging** — `--debug` flag registered but not wired to `slog` structured logging
- [ ] **Web dashboard integration** — `aura web` exists but does not consume ingest output yet (uses mock data)
