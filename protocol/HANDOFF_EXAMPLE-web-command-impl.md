# Handoff: WebSocket Connector + `aura web` Command Implementation

> Request: unified-schema-cgo
> URE: unified-schema-jdl
> Proposal: unified-schema-u5p (PROPOSAL-2, RFC v0.2.0)
> Plan UAT: unified-schema-z7n (UAT-1)
> Code Review: unified-schema-g42
> Impl UAT: unified-schema-gwz (UAT-2)

## Summary

Implements a full-stack real-time analytics dashboard for AI coding agent sessions. A Go WebSocket server streams mock session data to a Next.js frontend embedded in the binary via `go:embed`. The `aura web start/stop` CLI commands manage a background server process with health probing, auto-browser-open, and graceful shutdown (HTTP with SIGTERM fallback).

**5,132 lines added across 34 files** (1,444 Go backend + 933 TypeScript frontend + build/config/docs).

---

## Design Principles Alignment

| Principle | Before | After |
|-----------|--------|-------|
| **Testability via DI** | No data abstraction; TUI owned mock data | `DataProvider` interface enables mock/SQLite swap without touching Hub or server |
| **Strongly-typed enums** | N/A | `MessageType`, `ChannelName`, `Provider`, `Role` as Go string enums mirrored in TypeScript unions |
| **Composition over inheritance** | Monolithic TUI | Hub (concurrency) + Conn (I/O) + Server (HTTP) + Provider (data) — each replaceable |
| **Interface-first design** | No web layer | `DataProvider` interface defined before implementation; mock and future SQLite satisfy same contract |
| **Shared data model** | Mock data lived in `internal/tui/mock.go` | Extracted to `internal/mock/` — single source of truth for TUI and web |

---

## Architecture

### Data Flow

```
Browser (React)
    │
    ▼
useWebSocket Hook ◄── auto-reconnect, exponential backoff (1s→30s)
    │
    │  subscribe/unsubscribe JSON messages
    ▼
WebSocket /api/v1/ws
    │
    ▼
Hub (single goroutine, channel-based event loop)
    │
    ├── register/unregister ── Conn (per-connection read/write pumps)
    ├── subscribe ──────────── snapshot-on-subscribe + 5s ticker broadcast
    └── broadcast ──────────── non-blocking Send with backpressure (64-slot buffer)
    │
    ▼
DataProvider interface
    │
    ▼
mock.Provider (static) ──── future: SQLite Store
```

### Process Model

```
$ aura web start
    │
    ├── Re-exec self with --foreground (Setsid: true, detached)
    ├── Write PID to ~/.local/state/aura/web:{port}.pid
    ├── Poll GET /api/v1/health every 100ms (5s timeout)
    ├── Print startup banner with URL + stop hint + PID recovery info
    └── Open browser (xdg-open / open / start)

$ aura web stop
    │
    ├── POST /api/v1/shutdown (localhost-only, 2s timeout)
    └── Fallback: read PID file → SIGTERM
```

### WebSocket Protocol

```
Client → Server:
  {"type":"subscribe","channels":["dashboard","sessions"]}
  {"type":"subscribe","channels":["session_detail"],"id":"a1b2c3d4"}
  {"type":"unsubscribe","channels":["sessions"]}

Server → Client:
  {"type":"connected","version":"0.1.0-dev"}
  {"type":"dashboard","data":{...}}            ← snapshot + every 5s
  {"type":"sessions","data":{...}}             ← snapshot + every 5s
  {"type":"session_detail","data":{...}}       ← on-demand
  {"type":"error","message":"buffer full, re-subscribe for fresh snapshot"}
```

---

## New Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| CLI Commands | `cmd/aura/main.go` | 228+ | `aura web start/stop`, fork-to-background, readiness probe, browser open |
| Asset Embed | `embed.go` | 5+ | `//go:embed web/out/*` for single-binary distribution |
| DataProvider | `internal/api/provider.go` | 17 | DI boundary — interface for data source abstraction |
| Message Types | `internal/api/messages.go` | 126 | All WebSocket wire types, payload structs, channel/message enums |
| Hub | `internal/api/websocket.go` | 292+ | Single-goroutine event loop, channel mgmt, 5s ticker, snapshot-on-subscribe |
| Conn | `internal/api/conn.go` | 149 | Per-connection read/write pumps, backpressure handling (64-slot buffer) |
| Server | `internal/api/server.go` | 178 | HTTP server, SPA fallback, dev proxy, `/api/v1/shutdown` endpoint |
| MockProvider | `internal/mock/provider.go` | 118 | Implements `DataProvider` with aggregation (dashboard metrics, 7-day trends) |
| Mock Sessions | `internal/mock/sessions.go` | 191 | 7 deterministic sessions shared by TUI and web |
| TS Types | `web/src/types/messages.ts` | 113 | TypeScript mirrors of Go structs (compile-time contract) |
| WS Hook | `web/src/hooks/useWebSocket.ts` | 181 | React hook: connect, subscribe, reconnect, mount-aware state |
| Dashboard | `web/src/app/page.tsx` | 148 | 6 stat cards in 3x2 grid (sessions, tokens, duration, providers, turns, acceptance) |
| Sessions | `web/src/app/sessions/page.tsx` | 249 | Sortable table + click-to-expand detail with turn-by-turn view |
| Trends | `web/src/app/trends/page.tsx` | 156 | 7-day bar charts (tokens/day, sessions/day) via Recharts |
| NavSidebar | `web/src/components/NavSidebar.tsx` | 63 | Fixed sidebar with active-page highlighting |
| Layout | `web/src/app/layout.tsx` | 23 | Dark-mode root layout, sidebar + main content area |

---

## Key Design Decisions

### 1. Hub as Single Goroutine Owner

The Hub owns the `clients` map exclusively — no mutex needed. All mutations flow through buffered channels (`registerCh`, `unregisterCh`, `subscribeCh`, `broadcastCh`, size 16). This eliminates race conditions by design rather than by locking.

### 2. Snapshot-on-Subscribe + 5s Ticker

Clients receive current state immediately on subscribe (no stale-start). The 5s ticker re-pushes all channels so the UI feels live even with static mock data. When real ingest data arrives, the same mechanism delivers actual updates.

### 3. Provider Aggregates (not Hub)

`DashboardMetrics()` and `TrendsData()` return pre-aggregated payloads. The provider owns aggregation because: (a) SQLite can use SQL aggregates efficiently, (b) the Hub stays thin (just routing), (c) different providers may compute metrics differently.

### 4. Non-blocking Send with Client Error Notification

If a slow client's 64-slot write buffer is full, the message is dropped and an error message (`"buffer full, re-subscribe for fresh snapshot"`) is sent instead. This prevents one slow client from blocking the hub goroutine while giving the client a recovery path.

### 5. Embedded SPA with Dev Proxy

Production: `go:embed web/out/*` bundles the static export into the binary. Dev mode (`--dev`): reverse proxy to `localhost:3000` for hot-reload. SPA fallback handler serves `index.html` for any path not matching a real file.

### 6. HTTP Shutdown + SIGTERM Fallback

`aura web stop` sends `POST /api/v1/shutdown` (localhost-only). If the server is unresponsive after 2s, it reads the PID file and sends SIGTERM. This handles both the happy path (graceful HTTP) and the stuck-server case.

---

## CLI Interface

```bash
$ aura web                          # prints help (list of subcommands)
$ aura web start                    # fork to background, write PID, poll health, open browser
$ aura web start --foreground       # run in current terminal (Ctrl-C to stop)
$ aura web start --dev              # implies --foreground, proxy / to localhost:3000
$ aura web start --no-browser       # skip auto-open
$ aura web start --port 9999        # custom port
$ aura web stop                     # POST /api/v1/shutdown on localhost:8690
$ aura web stop --port 9999         # shutdown on custom port
```

Startup output:
```
Aura web dashboard running at http://localhost:8690
To stop the server, run:
  aura web stop

If the server becomes unresponsive, the process ID (12345)
is saved at /home/user/.local/state/aura/web:8690.pid
```

---

## Go ↔ TypeScript Contract

The WebSocket protocol relies on structural type parity between Go and TypeScript. Both sides define the same enums and payload shapes:

| Go (`internal/api/messages.go`) | TypeScript (`web/src/types/messages.ts`) | Notes |
|--------------------------------|------------------------------------------|-------|
| `MessageType` (string const) | `MessageType` (union literal) | 8 values: subscribe, unsubscribe, dashboard, sessions, session_detail, trends, connected, error |
| `ChannelName` (string const) | `ChannelName` (union literal) | 4 values: dashboard, sessions, session_detail, trends |
| `Provider` (ingest.Provider) | `Provider` (union literal) | claude, gemini, codex, opencode |
| `Role` (ingest.Role) | `Role` (union literal) | user, assistant, tool |
| `DashboardPayload` struct | `DashboardPayload` interface | 6 fields: totalSessions, totalTokens, avgDurationMins, providerBreakdown, avgTurnsPerSession, acceptanceRate |
| `SessionSummary` struct | `SessionSummary` interface | List row without turns |
| `SessionDetailPayload` struct | `SessionDetailPayload` interface | Full session with turns and tool calls |
| `TrendsPayload` struct | `TrendsPayload` interface | 7-day aggregates with per-day stats |

JSON marshalling ensures wire compatibility. `time.Time` marshals as ISO 8601; `time.Duration` stored as minutes (float64) in payloads.

---

## Blast Radius

| File | Changes |
|------|---------|
| **cmd/aura/main.go** | +228 lines: `web`, `web start`, `web stop` commands with flags, fork logic, readiness probe, browser open |
| **embed.go** | +5 lines: `//go:embed web/out/*` directive, `Version` string |
| **internal/api/provider.go** | New file: `DataProvider` interface (4 methods) |
| **internal/api/messages.go** | New file: All message types, payload structs, enum constants |
| **internal/api/websocket.go** | +292 lines: Hub event loop, broadcast, 5s ticker, HandleUpgrade |
| **internal/api/conn.go** | New file: Per-connection read/write pumps, backpressure |
| **internal/api/server.go** | New file: HTTP server, SPA handler, dev proxy, shutdown endpoint |
| **internal/api/handlers.go** | Deleted: Replaced by server.go |
| **internal/api/router.go** | Deleted: Replaced by server.go |
| **internal/mock/provider.go** | New file: MockProvider with aggregation logic |
| **internal/mock/sessions.go** | New file: 7 mock sessions, extracted from TUI |
| **internal/tui/mock.go** | -187 lines: Stripped to thin wrapper importing `internal/mock` |
| **internal/tui/session.go** | 1 line: Import path update |
| **internal/tui/trends.go** | 1 line: Import path update |
| **internal/ingest/schema.go** | +11 lines: `Role` enum (user/assistant/tool), `ToolCall` struct |
| **go.mod/go.sum** | +`github.com/coder/websocket` dependency |
| **.gitignore** | +4 lines: `bin/`, `web/out/`, `web/.next/` |
| **Makefile** | +11 lines: `web`, `build`, `run`, `clean` targets |
| **web/** (14 files) | New Next.js app: layout, 3 pages, sidebar, WS hook, types, config, styles |

---

## Original User Request

> unified-schema-cgo (verbatim)

Make me a websocket connector to link this Go application to a Next.js front-end. I want you to implement the `aura web` command, with start and stop as arguments, which should launch a website on the client's computer. I think that this websocket should pull the mock analytics data for now as this web portal will be used for displaying the analytics currently shown in the Bubble Tea TUI in a more rich manner.

## User Requirements Document (URD)

> unified-schema-jdl

### Q1: Embed Strategy
**Question:** Should the Next.js frontend be embedded into the Go binary (via go:embed after build), or should it run as a separate dev server during development and only be embedded for production builds?
**Answer:** Embedded + dev mode flag
**Detail:** Default embedded for users. `aura web start --dev` proxies to a separately-running Next.js dev server for development.

### Q2: Stop Mechanism
**Question:** What should `aura web stop` do exactly? The Go process serving the web UI needs a way to be signaled to stop.
**Answer:** Background + HTTP shutdown endpoint
**Detail:** `aura web start` backgrounds itself, `aura web stop` calls a local HTTP endpoint to trigger graceful shutdown.

### Q3: Data Flow Pattern
**Question:** Should the WebSocket push updates in real-time (simulating live data changes), or should the frontend fetch initial data via REST and use WebSocket only for future change notifications?
**Answer:** WebSocket only
**Detail:** All data flows through WebSocket. Frontend subscribes to channels and receives full data dumps. Simpler API surface but harder to cache/debug.

### Q4: Port
**Question:** Which port should `aura web` listen on by default?
**Answer:** 8690 (per proposal)
**Detail:** Consistent with existing documentation in aura_proposal.md.

### Consolidated Requirements

1. **Embed strategy:** go:embed for production, --dev flag proxies to Next.js dev server
2. **Process model:** `aura web start` backgrounds itself; `aura web stop` hits HTTP shutdown endpoint
3. **Data flow:** WebSocket-only for all data (no REST data endpoints)
4. **Port:** 8690 default, --port flag for override
5. **Data source:** Mock analytics data from internal/tui/mock.go (MockSessions)
6. **Frontend:** Next.js with static export for embedding
7. **Analytics parity:** Must display same data as Bubble Tea TUI (Dashboard, Sessions, Trends)

## UAT-1: Plan Acceptance

> unified-schema-z7n

**Question:** The revised proposal (RFC v0.2.0) addresses all reviewer feedback. Does this match your expectations?
**Answer (verbatim):** "Looks good, proceed"
**Result:** ACCEPTED — Ratified and moved to implementation.

## UAT-2: Implementation Acceptance

<uat>
  <metadata>
    <title>IMPL-UAT: WebSocket connector + aura web command</title>
    <beads-id>unified-schema-gwz</beads-id>
    <proposal-ref>unified-schema-u5p</proposal-ref>
    <phase>implementation</phase>
    <date>2026-02-19</date>
  </metadata>

  <components>

    <component id="1">
      <name>CLI Commands (aura web start/stop)</name>

      <definition>
        <code lang="go">
webStartCmd := &cobra.Command{
    Use:   "start",
    Short: "Start the web dashboard server",
}
webStartCmd.Flags().IntVar(&webPort, "port", 8690, "Port to listen on")
webStartCmd.Flags().BoolVar(&webDev, "dev", false, "Dev mode: proxy to Next.js dev server (implies --foreground)")
webStartCmd.Flags().BoolVar(&webFg, "foreground", false, "Run in foreground (no background fork)")
webStartCmd.Flags().BoolVar(&webNoBrowser, "no-browser", false, "Don't auto-open browser")

webStopCmd := &cobra.Command{
    Use:   "stop",
    Short: "Stop the web dashboard server",
}
webStopCmd.Flags().IntVar(&webPort, "port", 8690, "Port the server is listening on")
        </code>
      </definition>

      <motivating-example>
        Full CLI behavior:
        <code lang="bash">
$ aura web                          # prints help (list of subcommands)
$ aura web start                    # forks to background, writes PID, polls health, opens browser
$ aura web start --foreground       # runs in current terminal (Ctrl-C to stop)
$ aura web start --dev              # implies --foreground, proxies / to localhost:3000
$ aura web start --no-browser       # skip auto-open
$ aura web start --port 9999        # custom port
$ aura web stop                     # POST /api/v1/shutdown on localhost:8690
$ aura web stop --port 9999         # shutdown on custom port
        </code>
        Stop mechanism is HTTP-based (POST to /api/v1/shutdown, localhost-only).
        Background process is detached via Setsid: true with a PID file.
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>The `aura web start` command forks to background by re-executing itself with `--foreground`. It then polls the health endpoint every 100ms for up to 5 seconds before declaring ready. If the server doesn't respond in 5s, it prints a warning but doesn't kill the child. Is this readiness timeout behavior correct?</text>

          <options>
            <option id="A">
              <label>5s poll is fine</label>
              <description>5 seconds is enough for a local Go server to bind a port</description>
            </option>
            <option id="B">
              <label>Kill child on timeout</label>
              <description>If it can't bind in 5s, something is wrong — kill the child and report error</description>
            </option>
            <option id="C">
              <label>Longer timeout (10s)</label>
              <description>Be more patient, especially on slow machines or first launch (npm build)</description>
            </option>
          </options>

          <user-response>
            <selected>5s poll is fine</selected>
            <verbatim>5s poll is fine</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The stop mechanism uses HTTP POST to `/api/v1/shutdown` (localhost-only). This means `aura web stop` only works if the server is healthy enough to accept HTTP requests. If the server hangs, the user must manually `kill` the PID from `~/.config/aura/web.pid`. Should stop also try SIGTERM as a fallback?</text>

          <options>
            <option id="A">
              <label>HTTP-only (current)</label>
              <description>Simple. If server is hung, user can kill manually — rare case for a dev tool</description>
            </option>
            <option id="B">
              <label>HTTP then SIGTERM fallback</label>
              <description>Try HTTP first, if no response in 2s, read PID file and send SIGTERM</description>
            </option>
            <option id="C">
              <label>SIGTERM-only</label>
              <description>Skip HTTP, just read PID file and send SIGTERM directly — simpler, always works</description>
            </option>
          </options>

          <user-response>
            <selected>HTTP then SIGTERM fallback</selected>
            <verbatim>Should be (2), but the socket path should be at `~/.local/state/aura/web:{port}.pid` by default.</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (CLI commands) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>Proceed to next component</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>Two action items: (1) PID path moved to ~/.local/state/aura/web:{port}.pid, (2) stop adds SIGTERM fallback after HTTP timeout</decision-notes>
    </component>

    <component id="2">
      <name>WebSocket Protocol</name>

      <definition>
        <code lang="json">
Client -> Server:
  {"type":"subscribe","channels":["dashboard","sessions"]}
  {"type":"subscribe","channels":["session_detail"],"id":"a1b2c3d4"}
  {"type":"unsubscribe","channels":["sessions"]}

Server -> Client:
  {"type":"connected","version":"0.1.0-dev"}
  {"type":"dashboard","data":{...}}
  {"type":"sessions","data":{...}}
  {"type":"error","message":"unknown channel: foo"}
        </code>
      </definition>

      <motivating-example>
        Channel-based subscribe/unsubscribe with snapshot-on-subscribe.
        No periodic push at time of UAT — data pushed once on subscribe (snapshot).
        Mock data is static, so snapshot is the full picture.
        Per-connection channel map guarded by mutex; hub goroutine owns clients map (no mutex on hub).
        Non-blocking Send — if client write buffer (64 slots) is full, messages dropped with log warning.
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>Currently the server only pushes data once per subscribe (snapshot-on-subscribe). There is no periodic ticker. This means the dashboard is a static snapshot — if you leave the browser open, the numbers never change. For mock data this is fine, but should we add a periodic broadcast (e.g. every 5s) now so the UI feels "live", or defer that to when real ingest data exists?</text>

          <options>
            <option id="A">
              <label>Snapshot-only (current)</label>
              <description>Mock data is static anyway. Add periodic push when real ingest pipeline exists.</description>
            </option>
            <option id="B">
              <label>Add 5s ticker now</label>
              <description>Even with mock data, re-push every 5s so the WS feels alive and we can test reconnect behavior</description>
            </option>
            <option id="C">
              <label>Add ticker but configurable</label>
              <description>Add a --push-interval flag (default 5s) to control broadcast frequency</description>
            </option>
          </options>

          <user-response>
            <selected>Add 5s ticker now</selected>
            <verbatim>Add 5s ticker now</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The write buffer per connection is 64 messages. If a slow client falls behind, messages are silently dropped (logged server-side). Should the behavior be different?</text>

          <options>
            <option id="A">
              <label>Drop + log (current)</label>
              <description>Simple, prevents one slow client from blocking the hub goroutine</description>
            </option>
            <option id="B">
              <label>Drop + send error to client</label>
              <description>Client gets an error message saying it missed updates, can re-subscribe for fresh snapshot</description>
            </option>
            <option id="C">
              <label>Block briefly (100ms)</label>
              <description>Try to deliver with a short timeout before dropping</description>
            </option>
          </options>

          <user-response>
            <selected>Drop + send error to client</selected>
            <verbatim>Drop + send error to client</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (WebSocket protocol) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>Proceed to next component</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>Two action items: (1) Add 5s broadcast ticker to Hub.Run(), (2) On buffer full send error message to client before dropping</decision-notes>
    </component>

    <component id="3">
      <name>Dashboard Page</name>

      <definition>
        <code lang="tsx">
// 6 stat cards in a 3x2 grid:
// Row 1: Total Sessions | Total Tokens | Avg Duration
// Row 2: Provider Breakdown | Avg Turns/Session | Acceptance Rate
<StatCard label="Total Sessions" value={dashboard.totalSessions} />
<StatCard label="Total Tokens" value={dashboard.totalTokens.toLocaleString()} />
<StatCard label="Avg Duration" value={formatDuration(dashboard.avgDurationMins)} />
<ProviderCard breakdown={dashboard.providerBreakdown} />
<StatCard label="Avg Turns / Session" value={dashboard.avgTurnsPerSession.toFixed(1)} />
<StatCard label="Acceptance Rate" value={`${dashboard.acceptanceRate.toFixed(1)}%`} />
        </code>
      </definition>

      <motivating-example>
        Dashboard screenshot verified in browser showing:
        Total Sessions: 7, Total Tokens: 61,600, Avg Duration: 41m,
        Provider Breakdown (Claude 43%, Codex 29%, Gemini 29%) with color-coded dots,
        Avg Turns/Session: 9.0, Acceptance Rate: 78.3%.
        AcceptanceRate hardcoded at 78.3 in mock provider — no real acceptance tracking yet.
        Provider colors: violet=Claude, blue=Gemini, emerald=Codex, amber=OpenCode.
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>The Acceptance Rate is hardcoded to 78.3% in the mock provider since there's no real acceptance tracking. Should this metric be kept as a placeholder to show the eventual capability, or removed from the dashboard until real data backs it?</text>

          <options>
            <option id="A">
              <label>Keep placeholder (current)</label>
              <description>Shows the UI layout intent. Value is obviously fake but demonstrates the card.</description>
            </option>
            <option id="B">
              <label>Remove until real</label>
              <description>Don't show metrics that can't be backed by data yet — misleading even as a demo</description>
            </option>
            <option id="C">
              <label>Show as N/A</label>
              <description>Keep the card but display 'N/A' or '--' instead of a fake number</description>
            </option>
          </options>

          <user-response>
            <selected>Keep placeholder (current)</selected>
            <verbatim>Keep placeholder (current)</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The dashboard is a flat grid of stat cards. There's no hierarchy or grouping — all 6 cards have equal visual weight. The TUI has a similar flat layout. Is this the right structure, or should some metrics be visually prioritized (e.g., Total Tokens larger, provider breakdown in a sidebar)?</text>

          <options>
            <option id="A">
              <label>Flat grid (current)</label>
              <description>Simple, consistent. All metrics equally visible at a glance.</description>
            </option>
            <option id="B">
              <label>Hero card + smaller cards</label>
              <description>Make Total Tokens or Total Sessions a large hero stat at top, rest smaller below</description>
            </option>
            <option id="C">
              <label>Two groups</label>
              <description>Group into 'Usage' (sessions, tokens, duration) and 'Quality' (turns, acceptance, provider) sections</description>
            </option>
          </options>

          <user-response>
            <selected>Flat grid (current)</selected>
            <verbatim>Flat grid (current)</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (Dashboard page) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>Proceed to next component</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>No changes required.</decision-notes>
    </component>

    <component id="4">
      <name>Sessions Page</name>

      <definition>
        <code lang="tsx">
// Sortable table columns:
// ID | Provider | Date (default sort desc) | Duration | Tokens | Turns
// Click-to-expand detail view with turn-by-turn conversation,
// role badges (color-coded user/assistant/tool), tool call details.
// No pagination — all sessions rendered in one table.
        </code>
      </definition>

      <motivating-example>
        Sessions screenshot verified in browser showing 7 mock sessions.
        Table with columns: ID (a1b2c3d4), Provider (Claude), Date (Feb 18, 01:00 AM),
        Duration (15m / 2h 0m), Tokens (4,600), Turns (5).
        Tool call count exists in data model but not shown as column (appears in expanded detail).
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>The sessions table has no pagination — all sessions render in one list. With mock data (7 rows) this is fine. When real data arrives, there could be hundreds of sessions. Should we add pagination/virtual scrolling now, or defer until real data exists?</text>

          <options>
            <option id="A">
              <label>Defer (current)</label>
              <description>7 rows is fine. Add pagination when we have real data and know the typical volume.</description>
            </option>
            <option id="B">
              <label>Add basic pagination now</label>
              <description>25 rows per page with prev/next. Establishes the pattern early.</description>
            </option>
            <option id="C">
              <label>Add infinite scroll</label>
              <description>Load more as user scrolls down. More modern UX but more complex WS protocol change.</description>
            </option>
          </options>

          <user-response>
            <selected>Defer (current)</selected>
            <verbatim>(1) Defer, but should create follow-up task for (2) Add basic pagination.</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The session IDs shown are short hex strings (a1b2c3d4). These are mock IDs. Real Claude session IDs are UUIDs (e.g., `e4eb6fb5-5b87-4d6f-82da-0b5a5f917694`). Should the ID column show truncated IDs (first 8 chars) or full UUIDs?</text>

          <options>
            <option id="A">
              <label>Truncated (8 chars)</label>
              <description>Keeps the table compact. Full ID visible in detail view on click.</description>
            </option>
            <option id="B">
              <label>Full UUID</label>
              <description>No ambiguity, but makes the table wide. Could use monospace font.</description>
            </option>
            <option id="C">
              <label>Truncated + tooltip</label>
              <description>Show 8 chars, hover to see full ID. Best of both worlds.</description>
            </option>
          </options>

          <user-response>
            <selected>Truncated (8 chars)</selected>
            <verbatim>Truncated (8 chars)</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (Sessions page) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>Proceed to next component</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>Follow-up task created: unified-schema-3am — basic pagination for sessions table (25 rows/page)</decision-notes>
    </component>

    <component id="5">
      <name>Trends Page</name>

      <definition>
        <code lang="tsx">
// Summary cards: 7-Day Total Tokens, 7-Day Total Sessions
// Tokens Per Day: Purple bar chart (recharts BarChart) over 7 days
// Sessions Per Day: Blue bar chart, same 7-day window
// Rolling window computed from time.Now().UTC() in mock provider
        </code>
      </definition>

      <motivating-example>
        Trends screenshot verified in browser showing:
        7-Day Total Tokens: 54,300, 7-Day Total Sessions: 6.
        Two stacked bar charts: Tokens/day (purple, Thu Feb 12 - Wed Feb 18),
        Sessions/day (blue, same window).
        No date range picker — fixed 7-day window.
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>The trends page uses a fixed 7-day rolling window. There's no way to change the time range. Should we add a time range selector now, or defer?</text>

          <options>
            <option id="A">
              <label>Defer (current)</label>
              <description>Fixed 7-day is fine for mock data. Add range picker when real data exists.</description>
            </option>
            <option id="B">
              <label>Add preset buttons</label>
              <description>7d / 14d / 30d toggle buttons. Simple to implement, useful immediately.</description>
            </option>
            <option id="C">
              <label>Add date picker</label>
              <description>Full date range selector. More complex but more flexible.</description>
            </option>
          </options>

          <user-response>
            <selected>Defer (current)</selected>
            <verbatim>Defer (current)</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The trends page shows two separate bar charts stacked vertically (tokens/day, sessions/day). An alternative is a single dual-axis chart with both metrics overlaid. Which layout do you prefer?</text>

          <options>
            <option id="A">
              <label>Separate charts (current)</label>
              <description>Clear, no visual confusion between metrics. Takes more vertical space.</description>
            </option>
            <option id="B">
              <label>Dual-axis overlay</label>
              <description>Compact, shows correlation between tokens and sessions. But dual-axis charts can be misleading.</description>
            </option>
            <option id="C">
              <label>Side by side</label>
              <description>Two charts horizontally instead of vertically. Uses screen width better on wide monitors.</description>
            </option>
          </options>

          <user-response>
            <selected>Separate charts (current)</selected>
            <verbatim>Separate charts (current)</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (Trends page) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>Proceed to next component</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>No changes required.</decision-notes>
    </component>

    <component id="6">
      <name>Server Architecture (DataProvider + Embed)</name>

      <definition>
        <code lang="go">
type DataProvider interface {
    Sessions(ctx context.Context) ([]ingest.Session, error)
    SessionByID(ctx context.Context, id string) (*ingest.Session, error)
    DashboardMetrics(ctx context.Context) (*DashboardPayload, error)
    TrendsData(ctx context.Context) (*TrendsPayload, error)
}
        </code>
      </definition>

      <motivating-example>
        go:embed bundles web/out/* into the binary. `make build` runs
        `cd web && npm run build` first, then `go build`. Single binary distribution.
        SPA fallback handler serves index.html for any path not matching a real file.
        Dev mode (--dev): proxies / to localhost:3000, serves /api/v1/* from Go.
        Mock data in internal/mock/ shared between TUI and web.
        internal/tui/mock.go is thin wrapper: func MockSessions() []ingest.Session { return mock.Sessions() }
      </motivating-example>

      <questions>

        <question id="Q1">
          <text>The DataProvider interface has 4 methods. `DashboardMetrics` and `TrendsData` return pre-aggregated payloads — the provider does the aggregation, not the hub. This means swapping MockProvider for a SQLite Store requires the Store to compute aggregates (AVG, SUM, COUNT). An alternative is a thinner interface where the provider only returns raw sessions and the hub/server layer aggregates. Which approach?</text>

          <options>
            <option id="A">
              <label>Provider aggregates (current)</label>
              <description>Clean separation. SQLite can use SQL aggregates (fast). Hub stays thin.</description>
            </option>
            <option id="B">
              <label>Hub aggregates</label>
              <description>Provider only returns raw sessions. Hub computes metrics. Simpler provider interface but hub does more work.</description>
            </option>
            <option id="C">
              <label>Separate interfaces</label>
              <description>Split into SessionStore (raw CRUD) and MetricsService (aggregation). More interfaces but clear responsibility.</description>
            </option>
          </options>

          <user-response>
            <selected>Provider aggregates (current)</selected>
            <verbatim>Provider aggregates (current)</verbatim>
          </user-response>
        </question>

        <question id="Q2">
          <text>The mock data was extracted from `internal/tui/mock.go` into `internal/mock/sessions.go`. The TUI now imports from `internal/mock`. This creates a shared dependency between TUI and web. Is this the right factoring, or should mock data stay closer to its consumers?</text>

          <options>
            <option id="A">
              <label>Shared mock package (current)</label>
              <description>Single source of truth. Both TUI and web use the same mock data.</description>
            </option>
            <option id="B">
              <label>Each consumer owns its mocks</label>
              <description>TUI has its own mock data, web has its own. No shared dependency but potential drift.</description>
            </option>
            <option id="C">
              <label>Top-level testdata/</label>
              <description>Move mock data to testdata/ directory following Go convention. Both consumers import from there.</description>
            </option>
          </options>

          <user-response>
            <selected>Shared mock package (current)</selected>
            <verbatim>Shared mock package (current)</verbatim>
          </user-response>
        </question>

        <question id="Q3">
          <text>Do you ACCEPT this component (Server architecture) to proceed?</text>
          <options>
            <option id="A"><label>ACCEPT</label><description>All components reviewed — finalize UAT</description></option>
            <option id="B"><label>REVISE</label><description>Needs changes before proceeding</description></option>
          </options>
          <user-response>
            <selected>ACCEPT</selected>
            <verbatim>ACCEPT</verbatim>
          </user-response>
        </question>

      </questions>

      <decision>ACCEPT</decision>
      <decision-notes>No changes required.</decision-notes>
    </component>

  </components>

  <addenda>

    <addendum>
      <verbatim>the `web start` command should output location of the socket too, to inform the user.</verbatim>
      <design-implication>Start output should include PID file path so user knows where process info is stored.</design-implication>
    </addendum>

    <addendum>
      <verbatim>Shouldn't just say "PID file:", need to be more descriptive about what it is. Pretend that somebody doesn't know what a PID file is.</verbatim>
      <design-implication>Avoid jargon in CLI output. Describe the file's purpose, not its technical name.</design-implication>
    </addendum>

    <addendum>
      <verbatim>Isn't this a socket that has power to control the server? [...] Let's design a more informative error message. What kind of socket is it? And what messages does it expect? Why might a user care about this socket? when is it going to be relevant? what's the most common case?</verbatim>
      <design-implication>User pushed for deeper design thinking about the output message. Analysis revealed: (1) it's a PID file not a socket, (2) the real control channel is HTTP /api/v1/shutdown, (3) PID file is a fallback for when HTTP fails, (4) most common case is happy path where user never thinks about the file. Led to redesigned output with context-appropriate framing: URL + stop command prominently, PID file path only as recovery info.</design-implication>
    </addendum>

    <addendum>
      <verbatim>Great, almost perfect. Should have `aura web stop` on a newline, and indented. In the second sentence, want to say `the process ID ({the actual pid})`.</verbatim>
      <design-implication>Final output format:
```
Aura web dashboard running at http://localhost:8690
To stop the server, run:
  aura web stop

If the server becomes unresponsive, the process ID (12345)
is saved at /home/user/.local/state/aura/web:8690.pid
```</design-implication>
    </addendum>

  </addenda>

  <final-decision>
    <verdict>ACCEPT</verdict>
    <summary>
      <change id="1">PID file path moved from ~/.config/aura/web.pid to ~/.local/state/aura/web:{port}.pid (XDG state dir, port-scoped)</change>
      <change id="2">aura web stop falls back to SIGTERM via PID file if HTTP shutdown fails (2s timeout)</change>
      <change id="3">Hub broadcasts all channels every 5s (periodic ticker) so dashboard feels live</change>
      <change id="4">Buffer-full drops now send error message to client suggesting re-subscribe</change>
      <change id="5">aura web start output redesigned: URL + stop command + recovery info with PID file context</change>
    </summary>
    <open-questions>
      <question>Follow-up: basic pagination for sessions table (25 rows/page) — unified-schema-3am</question>
      <question>Deferred: time range selector for trends page</question>
      <question>Deferred: session_detail not re-subscribed on WebSocket reconnect in frontend (M2 from code review)</question>
      <question>Low priority: mock dates will show zeros after Feb 25 (L2 from code review)</question>
    </open-questions>
  </final-decision>

</uat>

## Test Results

All UAT fixes verified by automated test agent (Sonnet):

| Test | Result | Notes |
|------|--------|-------|
| PID file path | PASS | `~/.local/state/aura/web:8690.pid` with valid PID |
| Health endpoint | PASS | `{"status":"ok"}` |
| WebSocket 5s ticker | PASS | 3 dashboard messages in 8s (1 snapshot + 2 ticks) |
| HTTP graceful stop | PASS | Server stops, PID file cleaned |
| SIGTERM fallback | PASS | Process terminates on SIGTERM |
| Dashboard HTML | PASS | Full SPA served with "Dashboard" content |

**Test coverage gap:** No unit or integration test files exist for either Go (`internal/api/`) or TypeScript (`web/src/`). All verification was manual/agent-driven.

## Commits

```
8f3b99f feat(web/gitignore): adds create-next-app default gitignore
d087dd9 docs: add structured IMPL-UAT handoff document
cc7d01c fix: improve aura web start output with stop hint and control socket path
4942dd1 fix: apply IMPL-UAT feedback — PID path, SIGTERM fallback, ticker, backpressure
2adcbdd feat: add aura web dashboard with WebSocket connector
```

Implementation slices (feature branch, squashed into 2adcbdd on main):
```
3f6160e feat(api): add WebSocket message types, DataProvider interface, and shared mock package (S1)
477861d feat(web): implement WebSocket Hub, HTTP server, CLI commands, and Next.js scaffold (S2+S3+S4)
953a572 feat(web): implement dashboard pages, embed integration, and build pipeline (S5+S6)
2bde166 fix(api): resolve blocking review findings — session detail, wire format, Hub shutdown safety
```

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `cmd/aura/main.go` | 308 | CLI: `aura web start/stop` with flags, fork-to-background, readiness probe, browser open |
| `embed.go` | 9 | `//go:embed web/out/*` directive + Version string |
| `internal/api/provider.go` | 17 | `DataProvider` interface (DI boundary) |
| `internal/api/messages.go` | 126 | All WebSocket message types and payload structs |
| `internal/api/websocket.go` | 289 | Hub: single-goroutine event loop, channel mgmt, 5s ticker, snapshot-on-subscribe |
| `internal/api/conn.go` | 149 | Per-connection read/write pumps, backpressure handling (64-slot buffer) |
| `internal/api/server.go` | 178 | HTTP server, SPA fallback handler, dev proxy, shutdown endpoint |
| `internal/mock/provider.go` | 118 | MockProvider implementing DataProvider with aggregation |
| `internal/mock/sessions.go` | 191 | Shared mock session data (7 sessions, used by TUI and web) |
| `internal/ingest/schema.go` | 59 | Core types: Session, Turn, ToolCall, Provider/Role enums |
| `web/src/hooks/useWebSocket.ts` | 181 | WebSocket hook: connect, subscribe, reconnect with exponential backoff |
| `web/src/types/messages.ts` | 113 | TypeScript types mirroring Go structs |
| `web/src/app/page.tsx` | 148 | Dashboard page (6 stat cards in 3x2 grid) |
| `web/src/app/sessions/page.tsx` | 249 | Sessions page (sortable table, click-to-expand detail with turns) |
| `web/src/app/trends/page.tsx` | 156 | Trends page (recharts bar charts, 7-day rolling window) |
| `web/src/components/NavSidebar.tsx` | 63 | Navigation sidebar with active page highlighting |
| `Makefile` | 13 | Build targets: `web`, `build`, `run`, `clean` |

## Open Items

- [ ] **No test coverage** — Go API layer and TypeScript frontend have zero test files
- [ ] **Follow-up: basic pagination** for sessions table (25 rows/page) — unified-schema-3am
- [ ] **Deferred: time range selector** for trends page
- [ ] **Deferred: session_detail re-subscribe** on WebSocket reconnect (M2 from code review)
- [ ] **Low priority: mock date decay** — mock dates hardcoded to Feb 12-18, will show zeros in trends after Feb 25
- [ ] **Unmerged fix:** commit `2bde166` (session detail, wire format, Hub shutdown safety) sits on feature branch, not yet on `main`
