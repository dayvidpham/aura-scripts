---
name: research
description: Domain research — find standards, prior art, and competing approaches for a topic
---

# Research

General-purpose domain research skill. Finds standards, prior art, existing solutions, and established patterns for a given topic. Writes structured findings to `docs/research/<topic>.md`.

See `CONSTRAINTS.md` for coding standards.

## When to Use

- **Phase 1 (s1_2-research):** Spawned by `/aura:user-request` after user confirms research depth. Findings recorded as REQUEST task comment AND written to `docs/research/`.
- **Standalone:** Any agent needing domain research outside the 12-phase workflow. Invoke directly with a topic and depth.

## Given/When/Then/Should

**Given** a research topic **when** investigating **then** follow the depth-scoped checklist and write findings to `docs/research/<topic>.md` **should never** skip writing the deliverable file

**Given** depth is quick-scan **when** researching **then** search local project only (Grep, Glob, Read) **should never** make web requests

**Given** depth is standard-research **when** researching **then** search local project AND web for domain standards and established patterns **should never** skip local analysis

**Given** depth is deep-dive **when** researching **then** perform full local analysis, web search for competing solutions, RFCs, academic papers, and well-regarded projects **should never** produce an unstructured dump

**Given** findings exist **when** writing deliverable **then** use the structured report format with per-topic sections, code citations (file:line), assessment tables, and adoption recommendations **should never** write a flat bullet list for standard-research or deep-dive depths

**Given** Phase 1 context **when** recording findings **then** ALSO add a summary comment on the REQUEST task via `bd comments add` **should never** only write the file without updating the REQUEST task

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `topic` | Yes | The research subject (e.g., "CEL policy engines", "HTTP proxy patterns") |
| `depth` | Yes | One of: `quick-scan`, `standard-research`, `deep-dive` |
| `request-task-id` | Phase 1 only | Beads task ID to record findings as comment |

## Research Checklist

Apply all items appropriate to the depth level:

### 1. Domain Standards
- What RFCs, specs, or community conventions exist?
- Are there formal standards bodies or working groups?

### 2. Prior Art
- What well-regarded projects solve similar problems?
- What is the maturity, adoption, and maintenance status of each?
- Which approaches have been tried and abandoned (and why)?

### 3. Established Patterns
- What idioms and best practices are established in this domain?
- Are there canonical implementations or reference architectures?
- What do experienced practitioners recommend?

### 4. Reusable Solutions
- Are there existing libraries, frameworks, or tools that could be reused or adapted?
- What are the tradeoffs of build-vs-buy for this domain?

## Depth Scoping

| Depth | Local | Web | Deliverable |
|-------|-------|-----|-------------|
| **quick-scan** | Grep project for related patterns, check README/docs, scan dependency manifests | None | 1-paragraph summary per checklist item (4 paragraphs total) |
| **standard-research** | Local scan + check project dependencies, related repos, read key source files | Search for domain standards, established patterns, well-regarded projects | Per-topic sections with relevance notes and brief assessment |
| **deep-dive** | Full local analysis + dependency tree, architectural trace | Search for competing solutions, RFCs, academic papers, canonical implementations | Full structured report (see format below) |

## Output Format

Write findings to `docs/research/<topic>.md` using the structured report format.

### File Structure

```markdown
---
title: "<Topic> — Domain Research"
date: "<YYYY-MM-DD>"
depth: "<quick-scan|standard-research|deep-dive>"
request: "<request-task-id or 'standalone'>"
---

## Executive Summary

<1-3 paragraphs: key finding, scope of research, recommended direction>

---

## <Topic Area 1>

### <Subject A>: <Approach/Pattern Name>

<Description of how this subject implements/addresses the topic area.
Include code snippets with file:line citations where applicable.>

```<language>
// source-file.go:150-152
code snippet here
```

### <Subject B>: <Alternative Approach>

<Description of alternative.>

### Assessment

| Aspect | Subject A | Subject B |
|--------|-----------|-----------|
| <dimension 1> | ... | ... |
| <dimension 2> | ... | ... |

**Adoption recommendation:** <adopt/adapt/defer/skip with rationale>

---

## <Topic Area 2>

<Same structure: subjects → code citations → assessment table → recommendation>

---

## Summary

| Topic Area | Recommendation | Rationale |
|------------|---------------|-----------|
| Area 1 | Adopt/Adapt/Defer/Skip | Brief reason |
| Area 2 | ... | ... |

## Key Takeaways

### Adopt
- <Pattern or solution to adopt immediately>

### Adapt
- <Pattern to adapt with modifications>

### Defer
- <Interesting but not needed for MVP>

### Skip
- <Evaluated and rejected, with reason>
```

### Adoption Categories

| Category | Meaning |
|----------|---------|
| **Adopt** | Use directly or with minimal modification |
| **Adapt** | Useful pattern but needs significant modification for our context |
| **Defer** | Valuable but not needed for current scope; track for later |
| **Skip** | Evaluated and rejected; document why to prevent re-evaluation |

## Phase 1 Integration

When invoked as part of Phase 1 (s1_2-research), record a summary on the REQUEST task in addition to writing the full report:

```bash
bd comments add {{request-task-id}} \
  "Research findings ({{depth}}):
  - Standards: {{list or 'none found'}}
  - Prior art: {{list of projects/solutions}}
  - Patterns: {{established approaches}}
  - Recommendation: {{brief direction}}
  - Full report: docs/research/{{topic}}.md"
```

## Example

### Invocation (Phase 1)

```
Topic: "HTTP proxy credential injection"
Depth: standard-research
Request task: aura-scripts-82j
```

### Resulting file: `docs/research/http-proxy-credential-injection.md`

```markdown
---
title: "HTTP Proxy Credential Injection — Domain Research"
date: "2026-02-20"
depth: "standard-research"
request: "aura-scripts-82j"
---

## Executive Summary

HTTP proxy credential injection is the pattern of intercepting outbound HTTP requests
and injecting authentication credentials (API keys, OAuth tokens, mTLS certificates)
before forwarding to the upstream service. Three well-regarded projects implement this
pattern: Octelium (zero-trust gateway), CyberArk Secretless Broker (sidecar proxy),
and goproxy (MITM library). The recommended approach for our use case is...

---

## Token Rotation

### Octelium: Explicit Rotation API

Octelium manages credential rotation through a dedicated API server endpoint at
`cluster/apiserver/apiserver/admin/credential.go:137-300`...

```go
// credential.go:150-152
cred.Status.TokenID = vutils.UUIDv4()
cred.Status.LastRotationAt = pbutils.Now()
```

### Secretless Broker: Provider-Delegated Refresh

...

### Assessment

| Aspect | Octelium | Secretless Broker |
|--------|----------|-------------------|
| Rotation trigger | Explicit API call | Provider-managed |
| State tracking | Counter + timestamp | None |

**Adoption recommendation:** Adapt Octelium's rotation counter pattern...

---

## Summary

| Topic Area | Recommendation | Rationale |
|------------|---------------|-----------|
| Token Rotation | Adapt | Counter useful, but delegate to vault |
| Injector Interface | Adopt | Clean DI pattern maps directly |

## Key Takeaways

### Adopt
- Injector interface pattern from Secretless Broker

### Defer
- Multi-protocol support (not needed for MVP)
```
