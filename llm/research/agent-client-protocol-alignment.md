---
title: "Agent Client Protocol (ACP) Alignment — Domain Research"
date: "2026-02-25"
depth: "standard-research"
request: "unified-schema-4z7n"
---

## Executive Summary

This document assesses Aura's alignment with **Coder's Agent Client Protocol (ACP)** — the protocol standardizing communication between code editors and AI coding agents (Claude Code, Gemini CLI, Copilot, etc.). ACP defines a JSON-RPC streaming protocol with 72 types covering sessions, messages, tool calls, and content blocks.

**Key finding:** ACP and Aura occupy different layers but are converging. ACP is a **real-time streaming protocol** (editor ↔ agent wire format). Aura is an **analytics/storage layer** that ingests, indexes, and queries the artifacts those agents produce. The two share core enums (`StopReason`, `ToolCallKind`, `Role`) where alignment is already high. More importantly, the SDK's `ContentBlock` discriminated union and `SessionUpdate` types directly address the most brittle ~40% of Aura's transcript indexer code — the hand-rolled content block parsing and tool call extraction.

**Ecosystem status:** ACP adoption is broad and accelerating. OpenCode is native ACP. Claude Code is accessible via Zed's `claude-agent-acp` adapter (not native). Gemini CLI, GitHub Copilot, Codex CLI, Cline, Goose, and 20+ other agents support ACP. Cursor does not. On the client side, Zed, JetBrains, Neovim, VS Code, and Emacs all have ACP support.

**Protocol identity correction:** Our earlier research document (`v2-protocol-research.md`) covers IBM's `i-am-bee/acp` (Agent Communication Protocol) and mislabels it "Agent Context Protocol." That protocol is now archived and merged into Google's A2A. It is **not** the ACP discussed here. Coder's Agent Client Protocol (`coder/acp-go-sdk`) is a separate, active protocol.

**Recommended direction:** Import `acp-go-sdk` as a dependency (zero transitive deps, Apache 2.0). Use its `ContentBlock`, `SessionUpdate`, and `ToolCallUpdate` types as the shared indexer input — replacing ~320 lines of brittle content block parsing across both Claude and OpenCode indexers. This also establishes the foundation for live ACP client mode, where Aura connects directly to running agents and receives `SessionUpdate` notifications in real-time.

---

## Protocol Identity

### Naming Confusion: Three Different "ACP" Protocols

During research, we discovered three protocols that share the "ACP" abbreviation or similar names. This section disambiguates them to prevent future confusion.

| Name | Organization | Repository | Status | Domain |
|------|-------------|------------|--------|--------|
| **Agent Client Protocol** | Coder | `coder/acp-go-sdk` | Active | Editor ↔ AI agent communication |
| Agent Communication Protocol | IBM | `i-am-bee/acp` | Archived (merged into A2A) | Agent orchestration REST API |
| "Agent Context Protocol" | Mislabel | Same as IBM's | Same | Same — incorrect name in our docs |

**The protocol assessed in this document is Coder's Agent Client Protocol.** References:

- Official docs: https://agentclientprotocol.com/protocol/schema
- JSON schema: https://raw.githubusercontent.com/coder/acp-go-sdk/refs/heads/main/schema/schema.json
- Go SDK: https://github.com/coder/acp-go-sdk

### Our Earlier Research (`v2-protocol-research.md`)

Lines 162-300 of `v2-protocol-research.md` cover IBM's protocol under the heading "Agent Context Protocol (ACP)." This is wrong twice: (1) IBM calls it "Agent Communication Protocol," not "Agent Context Protocol"; (2) it is not the ACP the user wants. The findings in that document remain valid for IBM's protocol but should not be confused with Coder's ACP.

### Assessment

| Aspect | Coder ACP | IBM ACP |
|--------|-----------|---------|
| Status | Active, maintained | Archived, merged into A2A |
| Domain | Editor ↔ agent streaming | Agent orchestration REST API |
| Relevance to Aura | High (we ingest what these agents produce) | Low (orchestration layer we don't participate in) |
| JSON convention | camelCase properties, snake_case enum values | snake_case throughout |

**Adoption recommendation:** Focus exclusively on Coder's ACP for type alignment. Ignore IBM's archived protocol.

---

## Ecosystem Support

### Agent ACP Support (as of 2026-02-25)

Source: https://agentclientprotocol.com/get-started/agents.md

| Agent | ACP Support | Mechanism | Notes |
|-------|------------|-----------|-------|
| **OpenCode** | Native | Built-in | Direct ACP implementation. Cleanest path for live ingest. |
| **Claude Code** | Via adapter | `zed-industries/claude-agent-acp` (TypeScript) | Wraps Claude Agent SDK → ACP. Not built into Claude Code itself. Claude Code's own transcript format is Anthropic Messages API JSONL. |
| **Gemini CLI** | Native | Built-in | The `acp-go-sdk` example directory has a Gemini bridge. |
| **GitHub Copilot** | Public preview | Built-in | Announced Jan 2026. |
| **Codex CLI** | Via adapter | `zed-industries/codex-acp` | Similar pattern to Claude adapter. |
| **Cline** | Native | Built-in | |
| **Goose** | Native | Built-in | |
| **Junie (JetBrains)** | Native | Built-in | |
| **Kiro CLI** | Native | Built-in | |
| **OpenHands** | Native | Built-in | |
| **Augment Code** | Native | Built-in | |
| **Cursor** | **Not supported** | N/A | Proprietary fork of VS Code. No ACP, no public protocol. |

Full list includes 28+ agents. Only notable absences: Cursor, Windsurf.

### Client ACP Support (editors/IDEs)

Source: https://agentclientprotocol.com/get-started/clients.md

| Client | ACP Support | Mechanism |
|--------|------------|-----------|
| **Zed** | Native | Driving force behind ACP |
| **JetBrains** | Native | Built-in AI Assistant ACP support |
| **Neovim** | Via plugins | CodeCompanion, avante.nvim, agentic.nvim |
| **VS Code** | Via extension | `vscode-acp` extension |
| **Emacs** | Via package | `agent-shell.el` |
| **Cursor** | Not supported | Proprietary integration |

### Implications for Aura

**For file-based ingest (current):**
- Claude Code will continue producing its own JSONL format — the Claude adapter stays
- OpenCode produces its own directory structure — the OpenCode adapter stays
- Both adapters would convert their native formats into ACP `SessionUpdate` types before feeding the shared indexer

**For live ACP client mode (future):**
- OpenCode: direct connection, no adapter, `SessionUpdate` notifications arrive natively
- Claude Code: requires running `claude-agent-acp` adapter process alongside
- Gemini CLI, Copilot, Cline, etc.: direct connection for any native ACP agent
- Cursor: not possible without reverse engineering

**Strategic assessment:** ACP is the de facto standard. 28+ agents, 15+ clients. The holdouts (Cursor, Windsurf) are proprietary editor forks that resist open protocols. Investing in ACP alignment is a bet on the open ecosystem winning — which is where the agent diversity is.

---

## JSON Wire Format Conventions

### ACP Convention

ACP uses **camelCase** for all JSON property names and **snake_case** for enum string values. This was confirmed by direct inspection of the JSON schema (72 type definitions).

**Properties** (camelCase):
- `sessionId`, `toolCallId`, `stopReason`, `mimeType`, `rawInput`, `rawOutput`

**Enum values** (snake_case):
- `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`
- `bash`, `computer`, `text_editor`, `mcp`, `code_edit`, `file_read`, `file_write`, `notebook_edit`, `switch_mode`

### Aura Convention

`pkg/schema` already uses camelCase JSON tags:

```go
// pkg/schema/content.go:8-32
type SessionEntry struct {
    Index       int           `json:"index"`
    EntryType   EntryType     `json:"entryType"`
    Role        Role          `json:"role"`
    Content     string        `json:"content"`
    ToolUseID   string        `json:"toolUseId"`
    ToolName    string        `json:"toolName"`
    ToolInput   string        `json:"toolInput"`
    ToolOutput  string        `json:"toolOutput"`
    // ...
}
```

`internal/ingest/types.go:152-176` has a duplicate `SessionEntry` with snake_case JSON tags (`tool_use_id`, `tool_name`, etc.), but these tags are never used — the store layer uses manual positional column binding via `zombiezen.com/go/sqlite`, not JSON marshaling.

### Wire Name Mismatches

| Field | Aura (`pkg/schema`) | ACP | Notes |
|-------|---------------------|-----|-------|
| Tool call ID | `toolUseId` | `toolCallId` | ACP uses "call" consistently |
| Tool input | `toolInput` | `rawInput` | ACP prefixes with "raw" |
| Tool output | `toolOutput` | `rawOutput` | ACP prefixes with "raw" |
| Tool kind | `toolKind` (on `SessionEntry`) | `kind` (on `ToolCallUpdate`) | ACP uses bare `kind` within tool context |

### Assessment

| Aspect | Aura | ACP |
|--------|------|-----|
| Property casing | camelCase (aligned) | camelCase |
| Enum value casing | snake_case (aligned) | snake_case |
| Naming convention | "toolUse" prefix | "toolCall" prefix |

**Adoption recommendation:** Adapt — rename `toolUseId` → `toolCallId` to match ACP. The `toolInput`/`toolOutput` vs `rawInput`/`rawOutput` difference is semantic (ACP means "raw" as in unprocessed streaming bytes) and may not warrant renaming. Evaluate during the type unification work (task `unified-schema-4z7n`).

---

## Enum Alignment

### StopReason

ACP defines `StopReason` with 5 values. Aura's `pkg/schema` defines the same 5 values:

```go
// pkg/schema/types.go:358-393
const (
    StopReasonEndTurn         StopReason = "end_turn"
    StopReasonMaxTokens       StopReason = "max_tokens"
    StopReasonMaxTurnRequests StopReason = "max_turn_requests"
    StopReasonRefusal         StopReason = "refusal"
    StopReasonCancelled       StopReason = "cancelled"
)
```

ACP schema (from `schema.json`):
```json
"StopReason": {
  "type": "string",
  "enum": ["end_turn", "max_tokens", "max_turn_requests", "refusal", "cancelled"]
}
```

**Exact match.** All 5 values are identical in both name and meaning.

### ToolCallKind (ToolKind)

ACP defines 10 values for `ToolCallKind`. Aura's `pkg/schema` defines 9 as `ToolCallKind`:

| Value | ACP | Aura | Notes |
|-------|-----|------|-------|
| `bash` | Yes | Yes | |
| `computer` | Yes | Yes | |
| `text_editor` | Yes | Yes | |
| `mcp` | Yes | Yes | |
| `code_edit` | Yes | Yes | |
| `file_read` | Yes | Yes | |
| `file_write` | Yes | Yes | |
| `notebook_edit` | Yes | Yes | |
| `glob` | No | Yes | Aura-specific (from Claude Code transcripts) |
| `switch_mode` | Yes | No | ACP-specific (agent mode switching) |

**Near-exact match.** 8 values are shared. Aura has `glob` (observed in transcripts but not in ACP). ACP has `switch_mode` (agent mode switching, not relevant to transcript analytics).

```go
// pkg/schema/types.go:312-351
const (
    ToolCallKindBash         ToolCallKind = "bash"
    ToolCallKindComputer     ToolCallKind = "computer"
    ToolCallKindTextEditor   ToolCallKind = "text_editor"
    ToolCallKindMCP          ToolCallKind = "mcp"
    ToolCallKindCodeEdit     ToolCallKind = "code_edit"
    ToolCallKindFileRead     ToolCallKind = "file_read"
    ToolCallKindFileWrite    ToolCallKind = "file_write"
    ToolCallKindNotebookEdit ToolCallKind = "notebook_edit"
    ToolCallKindGlob         ToolCallKind = "glob"
)
```

### Role

ACP defines 2 roles: `user`, `assistant`. Aura defines 4:

| Value | ACP | Aura | Notes |
|-------|-----|------|-------|
| `user` | Yes | Yes | |
| `assistant` | Yes | Yes | |
| `tool` | No | Yes | Tool result entries (ACP models these as `ToolResult` type, not a role) |
| `system` | No | Yes | System prompt entries (ACP has no system prompt concept) |

**Aura is a superset.** ACP's 2 roles are insufficient for transcript analytics — we need `tool` and `system` to distinguish entry types. This is expected: ACP models tool results as typed messages, not as a role.

### Assessment

| Enum | Alignment | Action Needed |
|------|-----------|---------------|
| `StopReason` | Exact match (5/5) | None — already aligned |
| `ToolCallKind` | Near match (8/10) | Add `switch_mode` if observed in transcripts; keep `glob` as Aura extension |
| `Role` | Superset (2/4 overlap) | Keep Aura's 4 roles — `tool` and `system` are analytics-domain needs |

**Adoption recommendation:** Adopt `StopReason` directly (could even import from `acp-go-sdk`). Adapt `ToolCallKind` by adding `switch_mode` when needed. Keep `Role` as-is — Aura's superset is correct for the analytics domain.

---

## Type System Boundaries

### What ACP Defines (Streaming Protocol)

ACP defines 72 types for real-time editor ↔ agent communication:

- **Session lifecycle:** `SessionNewRequest`, `SessionNewResponse`, `SessionPromptRequest`, `SessionPromptResponse`, `SessionResumeRequest`
- **Message streaming:** `MessageUpdate`, `ToolCallUpdate`, `ToolResult`, `ContentBlock`
- **Content types:** `TextContent`, `ImageContent`, `ThinkingContent`, `RedactedThinkingContent`, `ServerTurnContent`, `McpToolResultContent`, `LocalToolResultContent`
- **Metadata:** `StopReason`, `Role`, `ToolCallKind`, `_meta` (extensibility object on every type)

### What ACP Does NOT Define (Aura's Domain)

ACP is a streaming protocol — it has **no concept of**:

| Aura Concept | ACP Equivalent | Notes |
|-------------|----------------|-------|
| `SessionEntry` (indexed transcript row) | None | ACP streams messages; Aura materializes them into indexed rows |
| `EntryType` (text, tool_use, tool_result, ...) | Partial — `ContentBlock` discriminator | ACP uses `kind` on content blocks, but not as a storage-layer enum |
| Token counts per entry | None | ACP doesn't track tokens at the message level |
| Timestamps per entry | None | ACP has session-level timestamps only |
| `SessionOutcome` (success, failure, ...) | None | ACP has `StopReason` but no outcome assessment |
| `QualityMetrics` (signal density, retry loops, ...) | None | Entirely Aura's analytics domain |
| `Provider` (claude, opencode, gemini, ...) | None | ACP is provider-agnostic |
| `UnifiedMetadata` (project, model, cost, ...) | Partial — `_meta` extensibility | Could carry metadata in `_meta`, but no defined schema |
| Transcript retrieval API | None | ACP is push-based streaming, not query-based |

### Assessment

| Domain | ACP Coverage | Aura Coverage | Overlap |
|--------|-------------|---------------|---------|
| Wire protocol (editor ↔ agent) | Complete | None (Aura is not a protocol participant) | None |
| Shared enums (stop reasons, tool kinds, roles) | Defines them | Uses compatible values | High |
| Storage schema (entries, metrics, outcomes) | None | Complete | None |
| Query/retrieval API | None | Complete (REST + WebSocket) | None |

**Adoption recommendation:** Do not attempt to replace Aura's storage-layer types with ACP types. The domains are complementary, not overlapping. Align at the enum level only.

---

## SDK Import: Arguments For and Against

The question is not "should we align with ACP" (yes) but "should we `go get github.com/coder/acp-go-sdk`?"

### SDK Structure (what you actually import)

The SDK has **zero external dependencies** (`go.mod` contains only `go 1.21`). It provides 6 layers:

| Layer | Files | What it provides |
|-------|-------|-----------------|
| Generated types | `types_gen.go` | 72 ACP types with full JSON marshal/unmarshal, discriminated union handling, `Validate()` methods, `_meta` extensibility |
| Generated constants | `constants_gen.go` | Method name constants for 12 agent methods + 9 client methods |
| JSON-RPC connection | `connection.go` | Production-grade JSON-RPC 2.0 transport over stdio: request/response correlation, notification ordering, cancellation, graceful shutdown |
| Agent/Client interfaces | `agent.go`, `client.go` | `Agent` interface (6 methods), `Client` interface (9 methods), `AgentLoader`, `AgentExperimental` |
| Generated dispatchers | `agent_gen.go`, `client_gen.go` | Route JSON-RPC methods to interface methods with automatic param validation |
| Helpers | `helpers.go`, `helpers_gen.go` | Content block constructors (`TextBlock`, `ImageBlock`), tool call builders (`StartToolCall`, `UpdateToolCall` with functional options) |
| Extensions | `extensions.go` | `CallExtension`/`NotifyExtension` for custom `_`-prefixed methods |

### Arguments For Importing

**1. ContentBlock discriminated union replaces ~160 lines of brittle parsing.**

The SDK's `ContentBlock` is a proper Go discriminated union with typed variants (`Text`, `Image`, `Audio`, `ResourceLink`, `Resource`). Its `UnmarshalJSON` dispatches on the `"type"` field automatically. Today, both indexers implement this dispatch by hand — the Claude indexer does it twice (depth=0 and depth=1 with separate structs), and the OpenCode indexer uses `map[string]any`.

```go
// Current: 4 separate switch chains across 2 indexers, 2 parallel structs
switch block.Type {
case "tool_use": ...   // claude_indexer.go:164 AND :275 (duplicated)
case "tool_result": ... // repeated in opencode_indexer.go:289 via map[string]any
}

// With SDK: single typed unmarshal
var block acp.ContentBlock
json.Unmarshal(data, &block)
if tc := block.ToolCall; tc != nil {
    // tc.Kind, tc.RawInput, tc.ToolCallId — all typed
}
```

**2. SessionUpdate as universal indexer input type.**

`SessionUpdate` is the ACP discriminated union for streaming events: `UserMessageChunk`, `AgentMessageChunk`, `AgentThoughtChunk`, `ToolCall`, `ToolCallUpdate`, `Plan`, `StopReason`, etc. This is the natural intermediate representation for Aura's indexer:

```
Provider adapter              Shared indexer              Storage
──────────────               ──────────────              ───────
Claude JSONL  → parse → []acp.SessionUpdate → convert → []schema.SessionEntry
OpenCode JSON → parse → []acp.SessionUpdate → convert →     (same)
Live ACP conn →  (direct)  → []acp.SessionUpdate → convert →     (same)
```

Each provider adapter handles its native format quirks (Claude's polymorphic `content` field, OpenCode's directory structure). The shared indexer only needs to understand ACP types.

**3. ToolCallUpdate populates fields we define but never set.**

`ToolCallKind` is defined in `pkg/schema/types.go:312-351` and `StopReason` in `pkg/schema/types.go:358-393`. Both are fields on `schema.SessionEntry`. Neither indexer currently populates them. The ACP `ToolCallUpdate` and `PromptResponse` types carry these values — adopting SDK types means these fields get populated automatically.

**4. Zero transitive dependency cost.**

`go.mod` is literally two lines: `module github.com/coder/acp-go-sdk` and `go 1.21`. No transitive deps. The concern about "adding deps to `pkg/schema`" is moot — the SDK adds nothing to the dependency tree.

**5. The JSON-RPC connection layer is needed for live ACP client mode.**

`connection.go` provides a production-grade JSON-RPC 2.0 transport with request/response correlation, notification ordering, cancellation via `$/cancel_request`, and graceful shutdown. Building this from scratch would be significant effort. The SDK gives it for free.

**6. The `Client` interface is the exact starting point for live ingest.**

```go
type Client interface {
    ReadTextFile(ctx, ReadTextFileRequest) (ReadTextFileResponse, error)
    WriteTextFile(ctx, WriteTextFileRequest) (WriteTextFileResponse, error)
    RequestPermission(ctx, RequestPermissionRequest) (RequestPermissionResponse, error)
    SessionUpdate(ctx, SessionNotification) error  // ← this is the live ingest entry point
    CreateTerminal(ctx, CreateTerminalRequest) (CreateTerminalResponse, error)
    // ...
}
```

Aura's live ingest adapter implements `Client`, primarily `SessionUpdate()`. The SDK dispatches incoming JSON-RPC notifications to this method automatically. Aura receives typed `SessionNotification` objects containing `SessionUpdate` variants.

**7. Active maintenance, broad adoption.**

85 stars, 5 contributors, 16 commits, Apache 2.0. Coder (the company behind Coder/coder) maintains it. Zed, JetBrains, Gemini CLI, and 28+ agents depend on this protocol. It's not going away.

### Arguments Against Importing

**1. `pkg/schema` gains an external dependency.**

`pkg/schema` currently has zero external deps in its `go.mod`. It's a shared contract module consumed by the marketplace backend. Adding `acp-go-sdk` means marketplace also transitively imports it. However, since `acp-go-sdk` has zero transitive deps itself, the actual cost is minimal.

**2. Not all 72 types are useful.**

Aura needs `ContentBlock`, `SessionUpdate`, `ToolCallUpdate`, `StopReason`, `ToolKind`, `Role`, and the `Client` interface + connection layer. The remaining ~60 types (auth methods, terminal management, MCP capabilities, session forking, etc.) are unused. They don't cause runtime cost — they're just dead code in the binary.

**3. Coupling to Coder's release cadence.**

If ACP introduces a breaking change, we must update. However: (a) ACP is designed for stability (like LSP); (b) `Unstable*` types are clearly marked; (c) we can pin to a specific version.

**4. The SDK's `ContentBlock` variants don't map 1:1 to Anthropic's format.**

Claude Code's JSONL uses Anthropic's Messages API content blocks (`tool_use`, `tool_result`, `thinking`, `text`). ACP's `ContentBlock` has `Text`, `Image`, `Audio`, `ResourceLink`, `Resource` — but `tool_use` and `tool_result` are modeled as separate `ToolCallUpdate` / `ToolResult` types, not as content block variants. The Claude adapter would still need to map Anthropic blocks → ACP types. This is a translation, not a free lunch.

**5. The import doesn't go in `pkg/schema` — it goes in `internal/ingest`.**

The SDK types are intermediate representations used during indexing. `pkg/schema.SessionEntry` remains the storage/API contract. The SDK import belongs in `internal/ingest` (the indexer layer), not in `pkg/schema` (the public contract). This means `pkg/schema` keeps zero external deps.

### Where the Import Goes

| Package | What it imports from SDK | Why |
|---------|------------------------|-----|
| `internal/ingest` | `ContentBlock`, `SessionUpdate`, `ToolCallUpdate`, `ToolKind`, `StopReason`, `Role` | Indexer input types — replace hand-rolled content block parsing |
| `internal/api` (future) | `Client` interface, `ClientSideConnection`, `Connection` | Live ACP client mode — connect to running agents |
| `pkg/schema` | **Nothing** | Keeps zero external deps. `SessionEntry` stays as-is. |

### Assessment

| Aspect | Import SDK | Manual Alignment |
|--------|-----------|-----------------|
| Dependency cost | Zero transitive deps | Zero |
| Content block parsing | Eliminated (~160 lines) | 4 hand-rolled switches |
| ToolCallKind/StopReason population | Automatic from parsed types | Must add manual extraction |
| Live ACP client | Connection layer + Client interface free | Must build JSON-RPC from scratch |
| `pkg/schema` impact | None (import is in `internal/ingest`) | None |
| Risk | Coupled to ACP spec evolution | Coupled to each provider's format evolution |

**Adoption recommendation:** Import `acp-go-sdk` into `internal/ingest` and (future) `internal/api`. Do NOT import it into `pkg/schema`. Use SDK types as the intermediate representation between provider adapters and the shared indexer. This gives concrete value today (replace brittle parsing) and strategic value tomorrow (live ACP client foundation).

---

## Concrete Pipeline Impact

### Current Indexer Architecture (before SDK)

```
Claude JSONL ──→ ClaudeIndexer ──→ []ingest.SessionEntry ──→ store
                 (claude_indexer.go)
                 - claudeContentBlock struct (depth=0)
                 - claudeFullBlock struct (depth=1)
                 - 2 duplicated switch chains
                 - polymorphic content (string vs array)
                 - 4-branch timestamp parser

OpenCode JSON ──→ OpenCodeIndexer ──→ []ingest.SessionEntry ──→ store
                  (opencode_indexer.go)
                  - openCodeIndexMsg struct
                  - map[string]any for parts (depth=1)
                  - type assertions for field access
                  - marshalPartInput/marshalPartOutput round-trips
```

### Target Indexer Architecture (with SDK)

```
Claude JSONL  ──→ ClaudeAdapter  ──→ []acp.SessionUpdate ──→ SharedIndexer ──→ []schema.SessionEntry ──→ store
OpenCode JSON ──→ OpenCodeAdapter ──→ []acp.SessionUpdate ──→   (same)      ──→      (same)
Live ACP conn ──→    (direct)     ──→ []acp.SessionUpdate ──→   (same)      ──→      (same)
```

Each provider adapter handles only its native format quirks. The shared indexer converts ACP types to storage entries.

### Files and Lines Affected

| File | Current lines | What changes | Estimated reduction |
|------|--------------|-------------|-------------------|
| `internal/ingest/claude_indexer.go` | ~370 | `claudeContentBlock` + `claudeFullBlock` structs eliminated. Both depth=0 and depth=1 switch chains replaced by `acp.ContentBlock` unmarshal. Polymorphic content handling simplified. | ~160 lines |
| `internal/ingest/opencode_indexer.go` | ~415 | `map[string]any` part parsing eliminated. `marshalPartInput`/`marshalPartOutput` eliminated. Type assertion chains replaced by typed field access. | ~95 lines |
| `internal/ingest/types.go` | ~176 | `ingest.SessionEntry` removed entirely (already planned in `unified-schema-4z7n`). Indexer intermediate types replaced by SDK types. | ~25 lines |
| `internal/ingest/shared_indexer.go` | (new) | Shared `[]acp.SessionUpdate → []schema.SessionEntry` converter. Single place for entry type mapping, token extraction, preview generation. | +~150 lines |
| `internal/api/acp_client.go` | (new, future) | Implements `acp.Client` interface for live ingest. `SessionUpdate()` feeds the shared indexer. | +~100 lines (future) |

**Net line change (immediate):** Remove ~280, add ~150 = **~130 lines net reduction** with significantly less brittleness.

### Specific SDK Types Used

| SDK Type | Used where | Replaces |
|----------|-----------|----------|
| `acp.ContentBlock` | Shared indexer | `claudeContentBlock`, `claudeFullBlock`, `map[string]any` part parsing |
| `acp.ContentBlockText` | Shared indexer (text entries) | `block.Text` string extraction in both indexers |
| `acp.SessionUpdate` | Adapter output / indexer input | `claudeIndexLine`, `openCodeIndexMsg` — becomes the universal intermediate type |
| `acp.SessionUpdateToolCall` | Shared indexer (tool_use entries) | `case "tool_use":` switch branches in both indexers |
| `acp.SessionToolCallUpdate` | Shared indexer (tool_call_update entries) | Tool metadata extraction (`RawInput`, `RawOutput`, `Kind`, `ToolCallId`) |
| `acp.ToolKind` | Shared indexer → `schema.SessionEntry.ToolKind` | Field exists on `schema.SessionEntry` but is **never populated** today |
| `acp.StopReason` | Shared indexer → `schema.SessionEntry.StopReason` | Field exists on `schema.SessionEntry` but is **never populated** today |
| `acp.Role` | Shared indexer → `schema.SessionEntry.Role` | Manual string matching (`"user"`, `"assistant"`, `"tool"`) |
| `acp.Client` (interface) | Future live ingest adapter | Nothing (new capability) |
| `acp.ClientSideConnection` | Future live ingest adapter | Nothing (new capability) |
| `acp.Connection` | Future live ingest adapter | Nothing (would need to build JSON-RPC 2.0 from scratch) |

### Fields Currently Defined But Never Populated

These `schema.SessionEntry` fields exist in `pkg/schema/content.go` but no indexer sets them:

| Field | Type | Why unpopulated | SDK type that provides it |
|-------|------|----------------|--------------------------|
| `ToolKind` | `schema.ToolCallKind` | Indexers don't classify tool calls by kind | `acp.SessionUpdateToolCall.Kind` (`acp.ToolKind`) |
| `StopReason` | `schema.StopReason` | Indexers don't extract stop reason from transcripts | `acp.PromptResponse.StopReason` |

With SDK types in the indexer, these fields get populated as a side effect of using the correctly-typed intermediate representation.

---

## Marketplace Data Flow and Push Gap

### Current Push Pipeline

`aura push` sends session metadata + raw transcript blob to the marketplace. The transcript index (`session_entries`) is **not included** — it exists only in the local SQLite database.

```
LOCAL (Aura CLI)                           REMOTE (Marketplace)
────────────────                           ────────────────────
SQLite: sessions                           PostgreSQL: transcripts (wide table)
SQLite: session_entries  ← NOT PUSHED      (no session_entries table)
SQLite: session_metrics  ← nil TODO        (quality columns exist, never populated)
Filesystem: transcript   ─────────────→    S3: transcript blob (opaque)
Filesystem: metadata     ─────────────→    PostgreSQL: transcripts columns
```

**Wire format:** `POST /api/v1/transcripts/publish` as `multipart/form-data`:
- Part 1: `metadata` — `schema.PublishRequest` JSON (identity, model, timestamps, git, project, stats, quality)
- Part 2: `transcript_file` — raw transcript binary (stored as opaque blob in S3)

**`schema.PublishRequest`** (`pkg/schema/publish.go:13-24`) contains metadata and quality metrics but **no session entries**. Comment on `SessionEntry` (`content.go:4`): _"Defined for v2 content-layer use; NOT used in v1 PublishRequest wire format."_

**Known gaps:**
- Quality metrics are plumbed in the mapper (`internal/push/mapper.go:102-149`) but pipeline passes `nil` (TODO at `pipeline.go:303`)
- No `session_entries` equivalent in marketplace PostgreSQL
- No push-to-entry mapping table

### What the Marketplace Needs

When session entries are eventually pushed, the marketplace PostgreSQL will need:

**1. A `session_entries` table** — the server-side equivalent of Aura's local SQLite `session_entries`. Schema must match `pkg/schema.SessionEntry` since that's the shared contract type.

```sql
-- Projected marketplace table
CREATE TABLE session_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id   UUID REFERENCES transcripts(id) NOT NULL,
    index           INTEGER NOT NULL,
    entry_type      VARCHAR(30) NOT NULL,    -- schema.EntryType
    role            VARCHAR(20) NOT NULL,    -- schema.Role
    content         TEXT,
    tool_use_id     VARCHAR(100),            -- matches schema.SessionEntry.ToolUseID
    tool_name       VARCHAR(200),
    tool_kind       VARCHAR(30),             -- schema.ToolCallKind
    tool_input      TEXT,
    tool_output     TEXT,
    stop_reason     VARCHAR(30),             -- schema.StopReason
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    timestamp_ms    BIGINT,
    extra           JSONB,                   -- schema.SessionEntry.Extra
    UNIQUE (transcript_id, index)
);
CREATE INDEX idx_session_entries_transcript ON session_entries(transcript_id);
CREATE INDEX idx_session_entries_type ON session_entries(entry_type);
CREATE INDEX idx_session_entries_tool_kind ON session_entries(tool_kind);
```

**2. A push index / mapping** — links pushed transcripts to their indexed entries. Three approaches:

**Option A: Entries embedded in push payload.** Extend `schema.PublishRequest` to include `Entries []SessionEntry`. Marketplace handler inserts them alongside the transcript row. Simple, keeps indexing on the local side where the provider-specific adapters live. Increases payload size.

**Option B: Server-side indexing.** Marketplace downloads the transcript blob from S3 and runs its own indexer. Avoids large payloads but requires duplicating the indexer logic on the server or sharing it as a library. The local indexer lives in `internal/ingest` which is not importable by external modules.

**Option C: Hybrid.** Push sends entry count and summary (for the `transcripts` table). Full entry index is built server-side on first query (lazy indexing).

**Recommended: Option A** — simplest, keeps all provider-specific parsing local, marketplace receives pre-indexed entries and just stores them. The indexer already produces `[]schema.SessionEntry`; the push pipeline just needs to include them in the payload.

### Relationship to `pkg/schema.SessionEntry`

`pkg/schema.SessionEntry` is the **contract type** that must work on both sides:
- Locally: written to SQLite by the indexer, read by the web dashboard and TUI
- Remotely: will be stored in PostgreSQL, read by the marketplace API

The same JSON serialization works for:
1. Local SQLite → web dashboard WebSocket
2. `aura push` payload (future v2)
3. Marketplace PostgreSQL → marketplace API

Column and field names should be settled before entries enter the push wire format. Once the marketplace starts storing entries under a field name, changing it requires a migration on both sides. This is independent of whether or not the ACP SDK is ever imported — it's a naming decision for the shared contract.

**Note on ACP alignment:** The ACP refactor (importing `acp-go-sdk`, shared indexer, `ContentBlock` type replacement) is a separate concern. It changes how entries are *produced* internally by the indexer, not how they are *transmitted* or *stored*. The push migration does not depend on the ACP refactor, and the ACP refactor does not depend on the push migration. They share a prerequisite (the `ingest.SessionEntry` → `schema.SessionEntry` unification in task `unified-schema-4z7n`) but are otherwise independent work streams.

### Assessment

| Aspect | Current State | Target State | Depends on ACP? |
|--------|--------------|-------------|-----------------|
| Session entries in push | Not included | Included in v2 `PublishRequest` | No |
| Marketplace entry table | Does not exist | `session_entries` in PostgreSQL | No |
| Quality metrics in push | Mapper exists, pipeline passes nil | Plumbed and populated | No |
| `ingest.SessionEntry` → `schema.SessionEntry` unification | Planned (`unified-schema-4z7n`) | Single type in `pkg/schema` | No (shared prereq) |
| Field naming (`toolUseId` vs `toolCallId`) | Current: `toolUseId` | Decision needed before push v2 | No (naming decision) |
| Push tracking | Local `push_log` + `pushed_at` | Extend with entry-level tracking if needed | No |

**Adoption recommendation:** Complete the `ingest.SessionEntry` → `schema.SessionEntry` unification (task `unified-schema-4z7n`), settle field naming, then extend `PublishRequest` to include `Entries []SessionEntry`. This is independent of the ACP SDK import — do whichever is needed first.

---

## `_meta` Extensibility Pattern

ACP defines `_meta` on every object type:

```json
"_meta": {
  "type": ["object", "null"],
  "additionalProperties": true
}
```

This is ACP's extensibility mechanism — vendors can attach arbitrary metadata to any message, tool call, or content block without breaking schema validation.

Aura's `SessionEntry` has an analogous field:

```go
// pkg/schema/content.go:30
Extra map[string]any `json:"extra,omitempty"`
```

If Aura ever becomes an ACP participant (e.g., receiving streaming data from an ACP-compatible agent), the `extra` field could be renamed to `_meta` for alignment. This is a low-cost rename with no semantic change.

**Adoption recommendation:** Defer. Renaming `extra` → `_meta` is trivial but unnecessary until Aura participates in ACP. The fields serve the same purpose.

---

## Summary

| Topic Area | Recommendation | Rationale |
|------------|---------------|-----------|
| Protocol identity | Clarify | Correct naming confusion in `v2-protocol-research.md`; document that Coder's ACP is the relevant protocol |
| Ecosystem alignment | Adopt | 28+ agents, 15+ clients. ACP is the de facto standard for editor ↔ agent communication. |
| SDK import (`acp-go-sdk`) | **Adopt** | Zero transitive deps. Replaces ~280 lines of brittle content block parsing. Provides JSON-RPC connection layer for live ACP client. Import into `internal/ingest`, NOT `pkg/schema`. |
| StopReason enum | Adopt | Exact 5/5 match; already aligned. SDK import means it gets populated automatically. |
| ToolCallKind enum | Adopt | 8/10 match; add `switch_mode` when observed. SDK import means ToolKind gets populated (currently defined but never set). |
| Role enum | Skip (keep ours) | Aura's 4-role superset is correct for analytics domain |
| Wire name alignment | Adapt | Rename `toolUseId` → `toolCallId`; evaluate `toolInput`/`toolOutput` renaming during type unification |
| Shared indexer | Adopt | New `shared_indexer.go` converts `[]acp.SessionUpdate → []schema.SessionEntry`. Replaces duplicated logic across Claude and OpenCode indexers. |
| Live ACP client | Adopt (future) | SDK's `Client` interface + `ClientSideConnection` + `Connection` = complete foundation for live session streaming. |
| SessionEntry replacement | Skip | ACP has no equivalent — different domain layers. `schema.SessionEntry` stays. |
| Marketplace `session_entries` table | Adopt (plan now) | Marketplace PostgreSQL needs an entries table mirroring `schema.SessionEntry`. Settle field naming before entries enter the push wire format. Independent of ACP SDK import. |
| Push payload v2 (entries) | Adopt (design now, implement later) | Extend `schema.PublishRequest` with `Entries []SessionEntry`. Simplest approach — keeps all provider-specific parsing local. Independent of ACP SDK import. |
| `_meta` / `extra` alignment | Defer | Trivial rename, unnecessary until ACP participation |

## Key Takeaways

### Adopt
- **Import `acp-go-sdk`** into `internal/ingest` — zero transitive deps, replaces ~280 lines of brittle parsing
- `StopReason` values are already ACP-aligned (exact match) — SDK import means automatic population
- `ToolCallKind` values are ACP-aligned (8/10 match) — SDK import means ToolKind field gets populated
- Shared indexer pattern: `[]acp.SessionUpdate → []schema.SessionEntry` — single conversion point for all providers

### Adapt
- Settle `toolUseId` vs `toolCallId` naming in `pkg/schema/content.go` during type unification (task `unified-schema-4z7n`) — **must happen before entries enter the push wire format**, since the marketplace PostgreSQL table will use these column names. This is a naming decision independent of the ACP SDK import.
- Add ACP-referencing comments to shared enum definitions in `pkg/schema/types.go`
- Claude adapter: map Anthropic Messages API content blocks → `acp.SessionUpdate` (translation layer, part of ACP refactor)
- OpenCode adapter: map directory-based parts → `acp.SessionUpdate` (translation layer, part of ACP refactor)
- Design marketplace `session_entries` PostgreSQL table mirroring `schema.SessionEntry` (independent of ACP)
- Extend `PublishRequest` with `Entries []SessionEntry` for push v2 (independent of ACP)

### Defer
- Renaming `extra` → `_meta` — trivial but unnecessary now
- Live ACP client mode — build after shared indexer is proven with file-based ingest

### Skip
- Replacing `SessionEntry`, `QualityMetrics`, `SessionOutcome`, or `Provider` with ACP types — no ACP equivalents exist
- Importing SDK into `pkg/schema` — keep it in `internal/ingest` to preserve zero-dep contract module
- Aligning with IBM's archived "Agent Communication Protocol" — different protocol, archived, irrelevant
- Cursor support via ACP — not possible, proprietary protocol
