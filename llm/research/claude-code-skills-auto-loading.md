---
title: "Claude Code Skills Auto-Loading & Cross-References — Domain Research"
date: "2026-02-20"
depth: "standard-research"
request: "standalone"
---

## Executive Summary

Claude Code skills (SKILL.md) **cannot auto-load other skills**. Only agent definitions (`.claude/agents/`) can preload skills via the `skills` frontmatter field, which injects full skill content into the subagent's context at startup. Skills have no dependency or prerequisite mechanism — markdown links in SKILL.md are informational only and do not trigger file reads.

This has implications for the Aura protocol: protocol docs (PROCESS.md, CLAUDE.md, CONSTRAINTS.md) are not guaranteed to be in context when a skill is invoked unless the agent independently decides to follow a link.

---

## Skill Auto-Loading Mechanism

### How Skills Load

When a skill is invoked (via `/skill-name` or by Claude automatically), only the SKILL.md content is injected into context. Supporting files in the skill directory are **not** auto-loaded — they must be explicitly referenced from SKILL.md so Claude knows to read them when needed.

> "Skills can include multiple files in their directory. This keeps SKILL.md focused on the essentials while letting Claude access detailed reference material only when needed."

Skill descriptions are always in context (so Claude knows what's available), but full skill content only loads when invoked.

### SKILL.md Frontmatter Fields (Complete List)

| Field | Description |
|-------|-------------|
| `name` | Display name / slash-command name |
| `description` | What the skill does; Claude uses this to decide when to auto-load |
| `argument-hint` | Hint shown during autocomplete |
| `disable-model-invocation` | Prevent Claude from auto-loading (manual `/name` only) |
| `user-invocable` | Set `false` to hide from `/` menu (Claude-only) |
| `allowed-tools` | Tools Claude can use without permission when skill is active |
| `model` | Model to use when skill is active |
| `context` | Set to `fork` to run in isolated subagent context |
| `agent` | Subagent type when `context: fork` (e.g., `Explore`, `Plan`, `general-purpose`) |
| `hooks` | Hooks scoped to skill lifecycle |

**No `skills` field exists.** Skills cannot declare dependencies on other skills.

---

## Agent Definitions: The Only Preload Mechanism

### How Agents Preload Skills

Agent definitions (`.claude/agents/*.md`) support a `skills` frontmatter field that injects full skill content at startup:

```yaml
---
name: api-developer
description: Implement API endpoints following team conventions
skills:
  - api-conventions
  - error-handling-patterns
---
```

> "The full content of each skill is injected into the subagent's context, not just made available for invocation. Subagents don't inherit skills from the parent conversation; you must list them explicitly."

### Agent Frontmatter Fields (Complete List)

| Field | Description |
|-------|-------------|
| `name` | Unique identifier (required) |
| `description` | When Claude should delegate (required) |
| `tools` | Tools the subagent can use |
| `disallowedTools` | Tools to deny |
| `model` | `sonnet`, `opus`, `haiku`, or `inherit` |
| `permissionMode` | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | Max agentic turns |
| **`skills`** | **Skills to preload into context at startup** |
| `mcpServers` | MCP servers available to subagent |
| `hooks` | Lifecycle hooks scoped to subagent |
| `memory` | Persistent memory scope: `user`, `project`, `local` |
| `background` | Run as background task |
| `isolation` | Set to `worktree` for git worktree isolation |

### Key Constraint: Subagents Cannot Spawn Subagents

> "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."

This means an agent with preloaded skills cannot further delegate to sub-subagents.

---

## Skill ↔ Agent Interaction (Two Directions)

| Approach | System prompt | Task | Also loads |
|----------|--------------|------|------------|
| Skill with `context: fork` | From agent type (`Explore`, `Plan`, etc.) | SKILL.md content | CLAUDE.md |
| Agent with `skills` field | Agent's markdown body | Claude's delegation message | Preloaded skills + CLAUDE.md |

With `context: fork`, the skill content becomes the task and you pick an agent type to execute it. With `skills` in an agent, the agent controls the system prompt and loads skill content as reference material.

---

## Implications for Aura Protocol

### Current State

Our SKILL.md files contain markdown links like:
```
**-> [Full workflow in PROCESS.md](../protocol/PROCESS.md#phase-8)**
See `../protocol/CONSTRAINTS.md` for coding standards.
```

These are informational — the agent may or may not follow them.

### The protocol CLAUDE.md loading path

The protocol `CLAUDE.md` is only loaded if:
1. A project copies it into their project's `CLAUDE.md` (auto-loaded by Claude Code)
2. An agent definition preloads the `protocol` skill
3. An agent explicitly invokes `/aura:protocol`

### Options for Guaranteed Protocol Loading

| Approach | Mechanism | Tradeoffs |
|----------|-----------|-----------|
| Agent definitions with `skills` preload | `skills: [protocol]` in agent frontmatter | Only works for agents, not direct `/aura:*` invocation |
| Explicit read instruction in SKILL.md | "Read `../protocol/PROCESS.md` before proceeding" | Adds a tool call; may be large; slightly repetitive |
| `context: fork` + custom agent | Skill runs in agent that has protocol preloaded | Loses main conversation context |
| Inline critical constraints | Copy key rules into each SKILL.md | Duplication; drift risk |
| Current approach (links) | Hope agent follows markdown links | No guarantee |

### Recommended Approach

Create agent definitions for each Aura role that preload the protocol skill:

```yaml
# .claude/agents/aura-supervisor.md
---
name: aura-supervisor
description: Task coordinator for Aura protocol Phase 8-12
skills:
  - aura:protocol
  - aura:supervisor
model: inherit
---
```

This ensures protocol docs are in context when the agent starts. For direct `/aura:supervisor` invocation (without the agent wrapper), the SKILL.md link serves as a fallback hint.

---

## Other Findings

### Skill Description Budget

> "If you have many skills, they may exceed the character budget. The budget scales dynamically at 2% of the context window, with a fallback of 16,000 characters."

With 35+ Aura skills, descriptions may be truncated. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var if needed.

### Live Reload

Skills from `--add-dir` directories support live change detection — edits during a session take effect without restart.

### CLAUDE.md from --add-dir

> "CLAUDE.md files from --add-dir directories are not loaded by default. To load them, set CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1."

---

## Summary

| Topic | Finding | Action |
|-------|---------|--------|
| Skills auto-loading skills | Not supported | No `skills` field in SKILL.md frontmatter |
| Agent preloading skills | Supported | `skills` field injects full content at startup |
| Protocol doc loading | Not guaranteed via links | Create agent definitions that preload protocol skill |
| Skill description budget | 2% of context window | Monitor with 35+ skills; set env var if truncated |

## Key Takeaways

### Adopt
- Agent definitions with `skills` preload for guaranteed protocol context injection

### Adapt
- Current SKILL.md link pattern — keep as fallback, but don't rely on it as primary loading mechanism

### Defer
- `context: fork` approach — useful but loses main conversation context; evaluate when isolation is needed

### Skip
- Inlining protocol constraints into every SKILL.md — too much duplication and drift risk
