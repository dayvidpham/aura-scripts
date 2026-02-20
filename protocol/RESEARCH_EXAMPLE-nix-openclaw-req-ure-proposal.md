dayvidpham/nix-openclaw-vm [main]
 I  -> pwd 
/home/minttea/codebases/dayvidpham/nix-openclaw-vm

===========

dayvidpham/nix-openclaw-vm [main]
 I  -> bd show nix-openclaw-vm-et5
○ nix-openclaw-vm-et5 · REQUEST: Credential proxy security layer for openclaw-vm   [● P1 · OPEN]
Owner: David Huu Pham · Type: task
Created: 2026-02-17 · Updated: 2026-02-17

DESCRIPTION
Verbatim User Request: Implement a credential proxy security layer for the openclaw microVM where the agent inside the VM has zero external network access, all auth-required requests are delegated to a trusted proxy service on the host via VSOCK, credentials are stored in OpenBao with domain binding enforcement, the proxy injects auth headers (agent never sees API keys), and full audit trail of all credential access. User Clarifications: Does NOT want Rust. Prefers Zig, Gleam/Elixir, or Golang. Does NOT want to re-implement secret-to-domain mapping or the proxy itself if avoidable. Interested in Temporal for backend orchestration (audit trail, event sourcing, event-driven architecture). Wants to evaluate existing solutions before building from scratch. Source Document: ~/dotfiles/docs/agent-sandbox.md

NOTES
Reopened: REQUEST must remain open until user performs UAT. Depends on URE (whp) which is now open.

LABELS: aura:user:request

DEPENDS ON
  → ○ nix-openclaw-vm-coe: IMPL-UAT: Credential proxy end-to-end acceptance test ● P1
  → ○ nix-openclaw-vm-whp: URE: Credential proxy scope and MVP ● P1

============

dayvidpham/nix-openclaw-vm [main]
 I  -> bd show nix-openclaw-vm-whp
○ nix-openclaw-vm-whp · URE: Credential proxy scope and MVP   [● P1 · OPEN]
Owner: David Huu Pham · Type: task
Created: 2026-02-17 · Updated: 2026-02-17

DESCRIPTION
## User Requirements Elicitation — Credential Proxy Security Layer

### Session 1: Initial Requirements Interview

#### URE Q1: MVP Scope
**Q:** "What is the MVP scope? Should Phase 1 focus on just the proxy + OpenBao domain binding, or do you also want Temporal orchestration in the MVP?"
- (1) Proxy + domain binding only — MVP: VSOCK listener, OpenBao credential fetch, domain binding check, header injection, JSONL audit. Add Temporal later.
- (2) Include Temporal from start — Build on Temporal from day 1: each proxy request = workflow execution, audit trail via workflow history, event replay built-in.
- (3) Temporal for audit only — Simple proxy handles requests directly, but logs events to Temporal for audit trail and replay. Hybrid approach.

**A:** "Include Temporal from start"

#### URE Q2: Deployment Model
**Q:** "For deployment: should the credential proxy run as a standalone systemd service on the host, or inside a container (Podman) like OpenBao?"
- (1) Systemd service (Recommended) — Native binary, systemd hardening (like the existing gateway). Simpler, less overhead, direct VSOCK access.
- (2) Podman container — Containerized like OpenBao. More isolation but adds complexity for VSOCK passthrough.
- (3) Decide later — Design the NixOS module to support both, decide during implementation.

**A:** "Systemd service (Recommended)"

#### URE Q3: Response Templating
**Q:** "How important is response templating (agent requests specific fields, proxy strips the rest) for MVP? The agent-sandbox.md spec includes it but it adds complexity."
- (1) Essential for MVP — Agent should never see fields it didn't request (PII protection, minimizing attack surface).
- (2) Defer to Phase 2 — MVP passes full response through. Add field filtering later. Domain binding is the critical security layer.

**A:** "Essential for MVP — Agent should never see fields it didn't request (PII protection, minimizing attack surface). But also, the response should NOT contain any auth / secrets. It should just contain that placeholder string. I imagine something similar to vaultwarden, where the secret has a templated form `agent-vault-<uuid>`, and the proxy searches for this, ingests it, replaces it on the proxy-side, and responses all replace the auth with this string when returned to the agent."

#### URE Q4: Guest-Side Client
**Q:** "Should the guest-side client be a proper CLI tool, or is a simple shell wrapper (e.g., around socat/curl) sufficient for MVP?"
- (1) Shell wrapper (socat+curl) — Minimal: shell script that sends JSON over VSOCK via socat. Quick to build, easy to debug.
- (2) Proper CLI tool — Compiled binary with arg parsing, error handling, structured output. More robust but more work.
- (3) Library/SDK — Import-able library the agent's code calls directly. Most ergonomic but heaviest to build.

**A:** "Shell wrapper (socat+curl)"

#### URE Q5: Language Preference (Free-form)
**Q:** (Prompted by initial plan proposing Rust)

**A:** "Whoa. I don't know about using Rust. Why would that be the case? I think using Zig, Gleam/Elixir, or Golang would be better. Let's consider. Which language has decent support for Keycloak and OpenBao? I also don't want to re-implement this 'secret-to-domain' allowable mapping, or even the proxy itself if I can avoid it. Let's see what exists already. I'm particularly interested in trying to use Temporal on the backend, as this will help with building the audit trail, the event sourcing, and the event-driven system for the proxy."

#### URE Q6: Language Confirmation (after research)
**Q:** "Given the research, Go is the only language with production-grade support for all three key dependencies (Temporal, OpenBao, OIDC). Are you okay with Go, or do you want to explore a polyglot approach (e.g., Go for the proxy, Gleam/Elixir for something else)?"
- (1) Go (Recommended) — Monolingual. First-party Vault client, tier 1 Temporal SDK, excellent OIDC + VSOCK + Nix support.
- (2) Polyglot approach — Go for the proxy core, but use another language for some component (e.g., Gleam for a future API layer).
- (3) Need more info — I want to dig deeper into one of the alternatives before deciding.

**A:** "Go (Recommended)"

#### URE Q7: Placeholder Pattern
**Q:** "For the credential placeholder pattern: should placeholders be per-credential-ref (e.g., `{{vault:openclaw/api/key}}`) or opaque UUIDs (e.g., `agent-vault-a1b2c3d4`) that map to credentials via a separate config?"
- (1) Opaque UUIDs — Agent sees `agent-vault-<uuid>`. Mapping from UUID to credential ref + domain is stored in proxy config. Agent can't infer what the credential is.
- (2) Structured refs — Agent sees `{{vault:path/to/secret}}`. More readable, agent knows what credential it's using, but leaks the secret path.
- (3) Agent-chosen aliases — Agent uses human-readable aliases like `my-api-key`. Proxy maps alias to credential ref + domain. Flexible but requires alias management.

**A:** "Opaque UUIDs"

#### URE Q8: Temporal Deployment
**Q:** "For Temporal deployment on NixOS: `temporal-cli` is in nixpkgs and includes a dev server with SQLite. For production, you'd want PostgreSQL-backed. Which path for the MVP?"
- (1) temporal-cli dev server — Single binary, SQLite, includes web UI. Simplest. Good enough for single-host with a few VMs. Can migrate to PostgreSQL later.
- (2) Podman container — Use official temporalio/auto-setup Docker image in Podman. More production-like but adds container dependency.
- (3) Full PostgreSQL setup — Build a proper NixOS module for Temporal with PostgreSQL backend. Most work upfront but most production-ready.

**A:** "temporal-cli dev server"

#### URE Q9: Credential Provisioning
**Q:** "How should placeholder-to-credential mappings be provisioned to the agent inside the VM? The agent needs to know which placeholder string to use for which service."
- (1) Environment variables — Inject placeholders as env vars (e.g., ANTHROPIC_API_KEY=agent-vault-abc123). Agent code uses them naturally.
- (2) Config file via fw_cfg — JSON config file passed through QEMU fw_cfg (like existing openclaw-config). Lists all available placeholders and their target services.
- (3) Query proxy at boot — Agent asks the proxy 'what credentials do I have?' over VSOCK and gets back a list of placeholder aliases and their allowed domains.

**A:** "Can do (1) and (2)."

#### URE Q10: Transport Protocol
**Q:** "For the VSOCK transport, should the proxy act as an HTTP forward proxy (agent sets HTTP_PROXY env var, needs MITM TLS for HTTPS) or use a simple JSON RPC (agent sends {url, method, headers, body} and proxy makes the actual request)?"
- (1) JSON RPC (Recommended) — Simple POST to proxy with request details as JSON. No TLS MITM needed. Clean placeholder substitution. Matches your shell wrapper preference.
- (2) HTTP forward proxy — Standard HTTP proxy (CONNECT tunneling). More transparent but requires MITM CA cert for HTTPS inspection. Complex.
- (3) Both modes — JSON RPC for MVP, add forward proxy mode later for agents that want transparent proxying.

**A:** "JSON RPC (Recommended)"

#### URE Q11: User Directive on Solution Research (Free-form)

**A:** "Agent-native and agentic software / MCP open-source projects are generally terrible. Look for pre-existing and established solutions that were well-accepted by the security community for our problem in a NON-agentic scenario. This is inherently a non-agentic problem."

#### URE Q12: Build vs Wrap (Octelium)
**Q:** "Given the research, Octelium (Go, 3.4k stars, AGPLv3) is the closest existing solution with 'secretless access' and Go implementation. Should we evaluate integrating/wrapping Octelium, or build custom since our requirements (VSOCK, Temporal, placeholder pattern) diverge enough?"
- (1) Build custom (Recommended) — Our requirements (VSOCK, Temporal, placeholder pattern, domain binding) are sufficiently unique. Borrow design patterns from Octelium/Peta/Vultrino but build our own ~500 lines of Go core logic.
- (2) Evaluate Octelium first — Clone Octelium, read its credential injection code, and assess if we can wrap/extend it. Risk: AGPLv3 license, may not be worth the effort if VSOCK+Temporal don't fit.
- (3) Evaluate Peta Core first — Clone Peta, read its vault/injection code. Risk: TypeScript (not Go), ELv2 license, may not fit our architecture.
- (4) Hybrid approach — Use Octelium as the access gateway layer and bolt Temporal + custom VSOCK listener on top. Most integration work but most reuse.

**A:** "Evaluate Octelium first"

#### URE Q13: Additional Research
**Q:** "Is there anything else you'd like me to research before finalizing the plan? The research confirmed no existing solution covers our needs, and Go + custom proxy is the path."
- (1) Research is sufficient — You've seen enough. Let's finalize the plan and move to implementation.
- (2) Dig into Vultrino source — Clone zachyking/vultrino and study its architecture in detail — borrow design patterns for our Go implementation.
- (3) Explore goproxy more — Investigate whether elazarl/goproxy could serve as the proxy foundation (forward proxy mode instead of JSON RPC).
- (4) Something else — I want to research a specific topic before we proceed.

**A:** "Explore goproxy more"

#### URE Q14: Proxy Mode (after goproxy research)
**Q:** "Given goproxy's capabilities, should we use it as a transparent forward proxy (agent just sets HTTP_PROXY and makes normal requests) or stick with JSON RPC? The forward proxy approach means zero agent code changes but requires MITM TLS with a custom CA cert installed in the VM."
- (1) Forward proxy (goproxy) — Agent sets HTTP_PROXY env var, makes normal requests. goproxy does MITM TLS, placeholder substitution, domain enforcement. Requires installing custom CA cert in VM.
- (2) JSON RPC (current plan) — Agent uses credproxy wrapper to send structured JSON. No TLS MITM needed. More explicit but requires agent to use the wrapper.
- (3) Both modes — Build on goproxy as foundation. Support both forward proxy mode AND a /proxy JSON RPC endpoint. Agent can use whichever suits its needs.
- (4) Need more info — I want to understand the tradeoffs better before deciding.

**A:** "Forward proxy (goproxy)"

#### URE Q15: Credential Pattern + Implementation (Rejected)
**Q:** "Secretless Broker uses a 'transparent proxy' pattern where the agent doesn't know about credentials AT ALL (just sets http_proxy). Your placeholder pattern (agent-vault-uuid) gives the agent explicit control over where credentials go. Which approach do you prefer?" / "For the proxy implementation: should we wrap/extend Secretless Broker (reuse its Vault provider, connector system, HTTP proxy), or build a custom thin proxy using the Go vault/api client directly (~500 lines)?"

**A:** (REJECTED — user wanted clarification first)

#### URE Q16: Clarification Request
**Q:** "What would you like to clarify about the credential pattern choice (transparent proxy vs placeholder) or the implementation approach (Secretless Broker vs custom)?"
- (1) Explain transparent proxy more
- (2) Explain placeholder pattern more
- (3) Explain Secretless limitations
- (4) I have a different idea
(Multi-select)

**A:** "Explain transparent proxy more, Explain Secretless limitations, Can I self-host Secretless Broker? This all needs to be self-hostable"

#### URE Q17: Transport (VSOCK vs TAP)
**Q:** "Should the proxy listen on VSOCK (direct hypervisor channel, no IP networking) or on the TAP bridge IP (10.88.0.1:18790, reuse existing network, simpler)? The VM already has a TAP interface for host communication."
- (1) TAP bridge (simpler) — Proxy listens on 10.88.0.1:18790. VM sets HTTP_PROXY=http://10.88.0.1:18790. Reuses existing TAP network. nftables restricts VM to only reach the proxy. No socat needed.
- (2) VSOCK (more isolated) — Proxy listens on VSOCK CID:4 port:18790. Adds socat bridge in VM. Physically impossible for traffic to escape. But adds the socat bridge complexity.
- (3) Both (belt and suspenders) — Proxy listens on both. TAP for the forward proxy (HTTP_PROXY). VSOCK as a fallback/admin channel. Maximum flexibility.

**A:** "VSOCK (more isolated)"

#### URE Q18: Secretless Broker Approach (Premature)
**Q:** "Given Secretless Broker's gaps (no response sanitization, no Temporal, weak domain binding, no rate limiting), which approach do you prefer?"

**A:** "So far have been given no details on Secretless Broker, what it is"

#### URE Q19: Build vs Wrap (after Secretless explanation)
**Q:** "Now that you understand Secretless Broker: should we use it as the credential injection layer and build our custom features on top, or build our own proxy that borrows its patterns?"
- (1) Use Secretless + add layers — Run Secretless as the credential injection proxy. Build a Go middleware service in front that adds: VSOCK listener, domain binding enforcement, Temporal audit, response sanitization, rate limiting. Two processes, most code reuse.
- (2) Custom proxy, inspired by SB — Build our own single Go binary (~500 lines core). Use vault/api directly for OpenBao. Borrow Secretless design (connector configs, provider abstraction) but own the full stack. One process, full control.
- (3) Fork Secretless Broker — Fork the repo, add our features (VSOCK, domain binding, Temporal, response sanitization) directly into the codebase. Most reuse but we maintain a fork.
- (4) Clone and evaluate first — Before deciding, clone the Secretless Broker repo to ~/codebases/ and read the actual Go code. Understand the architecture hands-on before committing to an approach.

**A:** "Use Secretless + add layers"

#### URE Q20: Response Sanitization Conflict
**Q:** "Given the response sanitization conflict with Secretless Broker, which tradeoff do you prefer?"
- (1) Single Go binary (current plan) — Our proxy fetches creds from OpenBao, injects into requests, AND scrubs from responses. One process, full control. Uses goproxy for HTTP proxy + mdlayher/vsock for transport. This is what the current plan file already describes.
- (2) Secretless + skip sanitization — Use Secretless for injection. Accept that API responses may leak credentials. Rely on domain binding to limit exposure. Simpler (Secretless handles Vault), but weaker security.
- (3) Secretless + parallel fetch — Use Secretless for injection AND separately fetch creds from OpenBao in our middleware for sanitization. Two Vault lookups per request (one by Secretless, one by us). Redundant but keeps separation.
- (4) Clone Secretless, evaluate — Before deciding, clone the Secretless Broker repo and read how its credential provider works. Maybe we can extract the provider interface as a library.

**A:** "Single Go binary (current plan)"

### Session 2: Deeper Research and Architecture Refinement

#### ExitPlanMode Rejection 1: Existing Solutions Research
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "Still need to do research about what exists, and how we can avoid re-implementing this. For example, vaultwarden exists. How is it different from OpenBao? Any other auth proxies exist that do NOT expose ANY secrets AT ALL to the clients?"

#### ExitPlanMode Rejection 2: Online Research Needed
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "Still need to do research. Still have not looked online and seen what exists."

#### ExitPlanMode Rejection 3: VSOCK Purpose
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "Why do we even need VSOCK? What's the purpose or point of VSOCK?"

#### ExitPlanMode Rejection 4: Secretless vs goproxy
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "If we use Secretless Broker, do we need goproxy?"

#### ExitPlanMode Rejection 5: Envoy Inquiry
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "So, what about Envoy + ext_authz? What is that? What does that do? why was it deemed too heavyweight?"

### Session 3: Continued Deep Research

#### ExitPlanMode Rejection 6: OpenBao vs Vaultwarden
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "This is looking very good indeed. However, does OpenBao not handle the 'secret-to-domain' mapping already? or does Vaultwarden? Why do we use OpenBao instead of Vaultwarden?"

#### ExitPlanMode Rejection 7: OpenBao Extensions
**Q:** (ExitPlanMode — attempt to finalize plan)

**A (Rejection):** "In some sense, the agent is a human, and it essentially needs a secretless broker-style password manager for use in the CLI and developing applications. OpenBao has nice attributes though. Has there been no attempts at extending OpenBao with this application-level logic?"

#### URE Q21: Riptides + Boundary Investigation
**Q:** "Riptides is the closest existing solution to what you described. Want me to dig deeper into it before we finalize, or are you satisfied that the custom goproxy approach is the right path given our specific requirements (VSOCK, response sanitization, Temporal audit, NixOS)?"
- (1) Finalize with goproxy — The research is thorough. Custom Go proxy with goproxy + OpenBao + Temporal is the right call — nothing existing covers all our requirements.
- (2) Investigate Riptides — Dig deeper into Riptides — licensing, source availability, how kernel-level injection works, whether it could work inside a microVM with VSOCK.
- (3) Investigate Boundary — Dig deeper into HashiCorp Boundary's credential injection — it's the 'official' Vault ecosystem approach even if HTTP API support is pending.

**A:** "Investigate deeper into both Riptides and Boundary. Is there an open-source alternative to Boundary? Must be self-hostable. Surprised the security and privacy communities haven't developed anything here yet."

#### URE Q22: Ready to Finalize?
**Q:** "The research is thorough across 17 solutions. The gap is real — no OSS tool provides outbound HTTPS credential injection + response sanitization + VSOCK + audit. Ready to finalize the custom Go proxy plan, or is there another direction you want explored?"
- (1) Finalize plan — Research is complete. The custom Go proxy (goproxy + OpenBao + Temporal over VSOCK) fills a genuine gap. Ready to approve and move to implementation.
- (2) Explore more — There's another solution category or specific tool I want investigated before committing.

**A:** "Explore more"

#### URE Q23: What to Explore
**Q:** "What area or tool would you like me to investigate further?"
- (1) Riptides deeper — Check if the kernel module could work in our microVM, or if their tokenex/SPIFFE approach is worth adopting without the kernel module.
- (2) eBPF-based approach — Could we use eBPF (like Cilium, Falco, or custom) for transparent credential injection instead of a userspace proxy? Kernel-level but open source.
- (3) Secretless Broker fork — Could we fork Secretless Broker and add HTTPS MITM + response sanitization + VSOCK rather than building from scratch?
- (4) WASM/plugin proxy — Investigate proxy architectures with plugin systems (WASM, Go plugins) for extensibility — e.g., could we build something others could extend?
(Multi-select)

**A:** "eBPF-based approach, Well, I think that we don't need a SINGLE tool that does both inbound and outbound secrets management and scrubbing. Couldn't we just have a gateway that delegates its inbound requests to the best-fitting inbound tool, and then outbound requests to the best-fitting outbound tool"

#### URE Q24: Architecture Decision
**Q:** "The composable gateway pattern is a better architecture than the original monolithic proxy. Do you want me to update the plan with this architecture, or dig into anything else?"
- (1) Update plan — Adopt composable gateway architecture. Single Go binary with CONNECT-based routing: outbound (goproxy + credential injection) and inbound (pluggable auth handler). Finalize plan.
- (2) eBPF defense-in-depth — Also add an eBPF enforcement layer spec to the plan — guest-side eBPF program that blocks all outbound traffic except to proxy port.
- (3) More research — There's something else I want explored before updating the plan.
(Multi-select)

**A:** "Update plan, How is Pomerium versus Oathkeeper versus the other tools we've explored? It seems like our application will have 5 components: (1) the secret vault whose access MUST require authentication via (2) Keycloak auth from an OIDC JWT that then MUST be checked for (3) authorization application protocol that determines what secrets the authenticated identity can access and for what domain/protocol/purpose, who receives requests from a (4) inbound handler, and then sends out to a (5) outbound handler?"

#### URE Q25: Agent Authentication
**Q:** "For agent-to-proxy authentication, VSOCK CID gives implicit identity (the hypervisor assigns it, can't be spoofed from inside the VM). Is CID-based identity sufficient for MVP, or do you want full Keycloak OIDC JWT authentication from the agent through the proxy?"
- (1) VSOCK CID for MVP (Recommended) — CID is hypervisor-enforced, can't be spoofed. Each VM has a unique CID. Sufficient for single-agent or known-agent scenarios. Add OIDC later if multi-agent with different trust levels.
- (2) Full OIDC from start — Agent authenticates to Keycloak, gets JWT, presents it in proxy-auth header. More complex but supports multi-agent with fine-grained identity from day 1.
- (3) Both — CID + OIDC — Use CID for transport-level identity (which VM), OIDC for application-level identity (which agent/role). Defense in depth.

**A:** "Both — CID + OIDC"

#### URE Q26: OIDC Revision (Free-form)
**Q:** (Unprompted user correction following Q25)

**A:** "Wait actually nevermind, we should only require the Keycloak OIDC JWT"

---

### Derived Requirements Summary

| Requirement | Decision | Source |
|------------|----------|--------|
| Language | Go | Q5, Q6 |
| Orchestration | Temporal from day 1 (temporal-cli dev server) | Q1, Q8 |
| Credential pattern | Placeholder substitution (opaque UUIDs: `agent-vault-<uuid>`) | Q3, Q7 |
| Proxy mode | HTTP forward proxy (goproxy + MITM TLS) | Q14 |
| Transport | VSOCK (physically isolated) | Q17 |
| Provisioning | Env vars + fw_cfg config | Q9 |
| Deployment | Systemd service on host | Q2 |
| Guest client | Shell wrapper (socat+curl) | Q4 |
| Domain binding | Fail-closed enforcement | Q3 |
| Response sanitization | Essential — scrub credentials from responses | Q3, Q20 |
| Authentication | Keycloak OIDC JWT only (not CID) | Q25, Q26 |
| Authorization | OPA embedded (Rego policies) | Q24 |
| Architecture | 5-component composable gateway (single Go binary) | Q23, Q24 |
| Build vs buy | Custom proxy (no existing solution fits) | Q11, Q12, Q19, Q20, Q21, Q22, Q23 |
| Self-hostable | Required | Q16, Q21 |
| Existing solutions | "Agent-native / MCP projects are generally terrible. Look for pre-existing and established solutions." | Q11 |

NOTES
Reopened: URD must remain open until user performs UAT. Was closed without user review.

LABELS: aura:user:elicit

DEPENDS ON
  → ○ nix-openclaw-vm-35e: PROPOSAL: Credential proxy implementation plan ● P1

BLOCKS
  ← ○ nix-openclaw-vm-et5: REQUEST: Credential proxy security layer for openclaw-vm ● P1

==============

dayvidpham/nix-openclaw-vm [main]
 I  -> bd show nix-openclaw-vm-35e
○ nix-openclaw-vm-35e · PROPOSAL: Credential proxy implementation plan   [● P1 · OPEN]
Owner: David Huu Pham · Type: task
Created: 2026-02-17 · Updated: 2026-02-17

DESCRIPTION
# Credential Proxy Security Layer — Implementation Plan

**Beads**: `nix-openclaw-vm-7xk` (epic), `nix-openclaw-vm-et5` (request), `nix-openclaw-vm-whp` (URE)

---

## Research Findings

### Existing Solutions Evaluated

| Solution | What It Does | Domain Binding | VSOCK | Verdict |
|----------|-------------|----------------|-------|---------|
| [Vultrino](https://github.com/zachyking/vultrino) | Rust credential proxy for AI agents. Alias-based refs, MCP server, WASM plugins. 6 stars, Jan 2026. | No (glob scoping only) | No | **Design reference only**. Too immature, Rust (rejected), no domain binding. |
| [Agent Gateway](https://github.com/agentgateway/agentgateway) | Rust MCP/A2A gateway. Linux Foundation. RBAC, JWT, header manipulation. | No | No | **Wrong purpose**. Inbound agent-to-tool routing, NOT outbound credential injection. |
| [elazarl/goproxy](https://github.com/elazarl/goproxy) | Go HTTP proxy library. MITM HTTPS, per-host handlers, request/response modification. 6.6k stars, BSD-3, 10+ years. | N/A (library) | Yes (custom `net.Listener`) | **Foundation library**. Implements `http.Handler` — serves on any listener including VSOCK. |
| Envoy + ext_authz | C++ L7 proxy (CNCF). ext_authz calls external service for auth + header injection. In nixpkgs. | Header-only (ext_authz can't modify bodies) | No (TCP/Unix only) | **Wrong tool.** ext_authz injects headers but cannot modify request/response bodies. MITM HTTPS is experimental (no cert generation). No VSOCK. Would still need custom Go for body substitution, response scrubbing, Temporal, OpenBao — making Envoy pure overhead (3 moving parts instead of 1). |
| Vault/OpenBao Agent | Proxies requests TO vault, not outbound. | N/A | No | **Backend only**. Use OpenBao for secret storage. |
| [Secretless Broker](https://github.com/cyberark/secretless-broker) | Go HTTP forward proxy by CyberArk. Injects credentials from Vault/Conjur into outbound HTTP. Plugin arch (Providers + Connectors). Apache 2.0, 366 stars, v1.7.32 Feb 2026, maintained since 2018. 25+ pre-built API configs. | URL regex matching, per-connector-port | No (tcp/unix only) | **Closest existing solution but 3 blockers**: (1) Rejects CONNECT with 405 — cannot MITM HTTPS; (2) No response sanitization — "app never sees secrets" model conflicts with our need to scrub credentials from API responses; (3) No VSOCK or Temporal. |
| [Octelium](https://github.com/octelium/octelium) | Go zero-trust access platform. L7-aware "secretless access" — injects API keys, Bearer, OAuth2, Sigv4 per-upstream. CEL/OPA policy-as-code. 3.4k stars, AGPLv3. | Per-service routing + CEL policies | No | **Too heavyweight + AGPLv3**. Full platform (VPN, ZTNA, PaaS, MCP gateway). No response sanitization documented. No VSOCK. |
| [Envoy credential_injector](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/credential_injector_filter) | Native Envoy filter. Injects credentials from SDS into outbound requests. First-class in Envoy Gateway v1.4+. | Via routing rules / HTTPRouteFilter | No | **Kubernetes-centric, heavyweight**. Requires full Envoy. No response sanitization. |
| [Ory Oathkeeper](https://www.ory.com/docs/oathkeeper) | Go zero-trust proxy. Per-domain access rules, header/JWT injection, CNCF ecosystem. | Per-rule domain matching | No | **Inbound-focused**. Designed for authenticating users TO your services, not injecting creds into outbound API calls. |
| [Peta Core](https://github.com/dunialabs/peta-core) | TypeScript MCP gateway. Server-side vault with JIT decryption (30s TTL), short-lived agent tokens, HITL approvals. 28 stars, ELv2. | No | No | **TypeScript (not Go), ELv2 license**. Custom vault (not OpenBao). No domain binding. Design reference for JIT decryption + audit patterns. |
| [Riptides](https://riptides.io/) | **Proprietary** kernel module for on-the-wire credential injection. kTLS + SPIFFE identity. Go userspace agent for OPA policy evaluation. Intercepts outbound IP sockets before TLS. | Per-process SPIFFE scoping | No (IP sockets only, not AF_VSOCK) | **Proprietary, no VSOCK, no response sanitization.** Core kernel module is closed-source. Plans to open-source "the core" but hasn't. Uses Lima VMs (TAP networking) — likely incompatible with VSOCK-only microVMs. No response scrubbing. No Temporal. Design reference for on-the-wire injection timing + SPIFFE identity. |
| [Boundary](https://developer.hashicorp.com/boundary) (HashiCorp) | Credential brokering + injection for SSH, RDP, databases. Controller+Worker model. BSL 1.1. | Per-target | No | **3 blockers**: (1) BSL license (not truly OSS since 2023); (2) Credential injection is **Enterprise/HCP-only** — community edition only has brokering; (3) HTTP API injection is [not implemented](https://github.com/hashicorp/boundary/issues/5273) — only SSH, RDP, DB targets supported. |
| [Pomerium](https://www.pomerium.com/) | Zero-trust access proxy. JWT injection + Vault integration. Apache 2.0. | Per-route | No | **Inbound-focused + JWT only.** Authenticates users TO apps. Can inject JWTs but not arbitrary API keys/headers into outbound requests. |
| [Teleport](https://goteleport.com/) | Secure access platform. REST API access with JWT injection. Elastic v2/AGPL. | Per-app | No | **Restrictive license + JWT only.** Elastic v2 is not OSS. Same JWT-only limitation as Pomerium. |

**Conclusion**: No existing solution provides our required combination (VSOCK + MITM HTTPS + placeholder substitution + response sanitization + domain binding + Temporal audit). CyberArk Secretless Broker was closest but has fundamental conflicts with response sanitization (its "app never sees secrets" model means it can't scrub credentials from API responses). Build custom Go proxy using [goproxy](https://github.com/elazarl/goproxy) as the HTTP proxy foundation and [mdlayher/vsock](https://github.com/mdlayher/vsock) as the transport. Borrow design patterns from Secretless (Vault provider, connector configs) and Peta (JIT decryption, audit trail) without taking the dependencies.

### Go Libraries

| Library | Component | Purpose | Status |
|---------|-----------|---------|--------|
| [`elazarl/goproxy`](https://github.com/elazarl/goproxy) | (4)(5) Gateway | HTTP/HTTPS forward proxy with MITM | 6.6k stars, BSD-3, 10+ years |
| [`mdlayher/vsock`](https://github.com/mdlayher/vsock) | (4) Transport | AF_VSOCK `net.Listener` | v1 stable, updated Jan 2025 |
| [`coreos/go-oidc/v3`](https://github.com/coreos/go-oidc) | (2) Authentication | Keycloak JWT validation via JWKS | Industry standard |
| [`open-policy-agent/opa/rego`](https://pkg.go.dev/github.com/open-policy-agent/opa/rego) | (3) Authorization | Rego policy evaluation (embedded) | CNCF graduated, <10ms P99 |
| [`openbao/openbao/api/v2`](https://pkg.go.dev/github.com/openbao/openbao/api) | (1) Secret vault | OpenBao client (Vault API compat) | Official, maintained |
| [`temporalio/sdk-go`](https://go.temporal.io/sdk) | Full lifecycle orchestration | Workflows, activities, signals, search attributes | Tier 1, v1.29+, production-grade |
| `temporal-cli` | Infrastructure | Temporal dev server | [In nixpkgs](https://www.nixhub.io/packages/temporal-cli) |

### Auth/Authz Tool Evaluation

Pomerium, Ory Oathkeeper, and OPA were evaluated for components (2) and (3):

| Tool | Keycloak OIDC | Embeddable | Forward proxy (CONNECT) | Authz model | Verdict |
|------|--------------|------------|------------------------|-------------|---------|
| **Pomerium** | Native (redirect flow) | **No** — standalone only | Partial (needs pomerium-cli) | PPL (YAML) + Rego | **Too heavy**. Can't embed, requires separate process. |
| **Oathkeeper** | JWT validation | **Yes** (gRPC middleware) | **No** | Rules + remote authorizer | **No CONNECT**. Good mutators but wrong proxy mode. |
| **OPA (embedded)** | JWT decode in Rego | **Yes** (library) | N/A (policy engine) | Rego (very flexible) | **Winner for (3).** <10ms, embeddable, expressive. |
| **coreos/go-oidc** | JWKS validation | **Yes** (library) | N/A | N/A | **Winner for (2).** Simple, 5 lines of code. |

**Decision:** Use `coreos/go-oidc` for JWT validation + `OPA embedded` for authorization policy. Skip Pomerium and Oathkeeper — they don't handle CONNECT, and their auth can be done more simply with direct libraries.

### Language Elimination

| Language | Temporal SDK | Vault Client | OIDC | VSOCK | Verdict |
|----------|-------------|-------------|------|-------|---------|
| **Go** | Tier 1 | First-party | Excellent | `mdlayher/vsock` | **Winner** |
| Rust | Alpha | Community | Good | Available | User rejected; Temporal experimental |
| Gleam/Elixir | **None** | Poor | Fair | **None** | Eliminated |
| Zig | **None** | **None** | **None** | Syscall | Eliminated |

---

## Context

The openclaw-vm gives an AI agent a sandboxed microVM with VSOCK-only host communication. Currently, the agent needs API credentials passed in directly (via fw_cfg), meaning a compromised agent could exfiltrate secrets. This plan builds a **transparent forward proxy** on the host that:

- Listens on **VSOCK** (hypervisor-level socket — physically cannot reach the internet, no IP routing)
- Acts as a standard HTTP forward proxy — agent just sets `HTTP_PROXY` / `HTTPS_PROXY` env vars
- **Intercepts HTTPS** via MITM TLS with a custom CA cert installed in the VM
- Detects **opaque placeholder strings** (`agent-vault-<uuid>`) in request headers/body
- **Replaces placeholders with real credentials** fetched from OpenBao
- Enforces **domain binding** (credential X only works for domain Y, fail-closed)
- **Scrubs credentials from responses** (replaces real values back with placeholders)
- Records every credential access as a **Temporal workflow** for audit/replay

**Why VSOCK?** Unlike TAP networking (which relies on nftables rules that could be misconfigured), VSOCK is a direct guest↔host channel provided by the hypervisor. Traffic on VSOCK physically cannot be routed to the internet — it's not an IP socket. This provides defense-in-depth: even if firewall rules are wrong, credentials can only flow through the proxy.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | **Go** | First-party Vault client, tier-1 Temporal SDK, goproxy library, VSOCK support |
| Architecture | **Composable 5-component gateway** | Separation of concerns: auth, authz, vault, inbound, outbound. Single Go binary. |
| Proxy foundation | **goproxy, not Secretless Broker** | Secretless rejects CONNECT (405) — no MITM HTTPS. goproxy handles MITM natively. |
| Authentication | **Keycloak OIDC JWT via `coreos/go-oidc`** | Agent presents JWT in `Proxy-Authorization` header. Proxy validates against Keycloak JWKS. Pomerium/Oathkeeper evaluated but too heavy (can't embed, wrong proxy mode). |
| Authorization | **OPA embedded (Rego policies)** | Evaluates "identity X with role Y can use credential Z for domain D". <10ms P99, embeddable library. |
| Proxy mode | **Transparent forward proxy** (goproxy) | Agent sets `HTTP_PROXY` env var. Zero agent code changes. |
| HTTPS handling | **MITM with custom CA** | goproxy's `ConnectMitm` action. CA cert installed in VM at build time. |
| Credential pattern | **Placeholder substitution** | `agent-vault-<uuid>` strings in headers/body. Proxy replaces outbound, scrubs inbound. |
| Orchestration | **Temporal as access decision orchestrator** | Every proxy access attempt = `ProxyAccessDecision` workflow. Authn → authz → credential path resolution are activities. goproxy owns HTTP lifecycle; Temporal owns the decision pipeline. Audit trail, replay, retries, rate limiting. See [temporal-agent-orchestration.Rmd](docs/research/temporal-agent-orchestration.Rmd). |
| Provisioning | **Env vars + fw_cfg** | `ANTHROPIC_API_KEY=agent-vault-abc123` + JSON config listing all placeholders. |
| Deployment | **Systemd service** on host | Direct VSOCK access, systemd hardening. |
| Temporal hosting | **temporal-cli dev server** | In nixpkgs. SQLite-backed. Upgrade to PostgreSQL later. |
| Domain enforcement | **OPA policy + goproxy `DstHostIs()`** | OPA for fine-grained authz, goproxy for fail-closed domain allowlist. |

---

## Architecture (Temporal-Orchestrated Access Decision Gateway)

goproxy owns the HTTP lifecycle (CONNECT, MITM TLS, request/response forwarding).
Temporal owns the access decision pipeline (authn, authz, credential path resolution).
Secret values never enter Temporal event history — only credential *paths* flow through workflows.

```
Guest VM (zero external network)                Host (NixOS)
┌──────────────────────────────┐    VSOCK     ┌──────────────────────────────────────────────┐
│ Agent                        │  CID:4       │ credproxy (Single Go Binary)                  │
│  HTTP_PROXY=localhost:18790  │  port:18790  │                                               │
│  HTTPS_PROXY=localhost:18790 │ ──────────▶  │  GOPROXY (HTTP lifecycle)    TEMPORAL WORKER   │
│                              │              │  ┌───────────────────┐  ┌──────────────────┐  │
│ Keycloak JWT in              │              │  │ HandleConnect:    │  │ ProxyRequest WF: │  │
│  Proxy-Authorization header  │              │  │  domain allowlist │  │  1.ValidateIdent │  │
│                              │              │  │  + JWT extraction │  │  2.EvaluatePolicy│  │
│ Makes normal HTTP(S) calls:  │              │  │                   │  │  3.FetchAndInject│  │
│  curl -H "x-api-key:         │              │  │ OnRequest:        │  │    (local act,   │  │
│   agent-vault-abc123"        │              │  │  register in      │  │    vault fetch,  │  │
│   https://api.anthropic.com  │              │  │  RequestRegistry ─┼──▶   modify req)   │  │
│                              │              │  │  start workflow   │  │  4.Wait signal   │  │
│                              │              │  │  block on ch ◀────┼──┤  "response_done" │  │
│                              │              │  │  forward request  │  │  5.Finalize audit│  │
│                              │  ◀────────── │  │                   │  └──────────────────┘  │
│ socat VSOCK↔localhost bridge │   response   │  │ OnResponse:       │                        │
│ CA cert: /etc/ssl/credproxy  │  (sanitized) │  │  scrub creds      │     RequestRegistry    │
└──────────────────────────────┘              │  │  signal workflow ──▶    (sync.Map:          │
                                              │  └───────────────────┘     reqID→*http.Req    │
                                              │                            + ScrubMap)         │
                                              └──────┬──────┬──────────┬───────────────────────┘
                                                     │      │          │
                                                ┌────▼──┐┌──▼───┐┌───▼──────────┐
                                                │OpenBao││Keyclk││ Temporal     │
                                                └───────┘└──────┘└──────────────┘
```

---

## Request Flow (Temporal Full-Lifecycle Orchestration)

```
1. Agent authenticates to Keycloak, receives JWT.
   Agent makes normal HTTPS request with JWT:
     curl -H "x-api-key: agent-vault-abc123" \
          -H "Proxy-Authorization: Bearer <jwt>" \
          https://api.anthropic.com/v1/messages

2. curl respects HTTP_PROXY=http://localhost:18790
   → Sends CONNECT api.anthropic.com:443 to proxy (with Proxy-Authorization header)

3. socat in VM bridges localhost:18790 → VSOCK CID:4 port:18790 → Host

4. GOPROXY HandleConnect:
   a. Extract Proxy-Authorization JWT, store in connTokens
   b. Is api.anthropic.com in domain allowlist?
      NO  → ConnectReject
      YES → ConnectMitm (MITM intercept with custom CA)

5. goproxy decrypts the HTTPS request via MITM TLS.

6. GOPROXY OnRequest handler:
   a. Retrieve JWT from connTokens
   b. Extract placeholders from headers + body (regex: agent-vault-[a-f0-9-]{36})
   c. If no placeholders → pass through (no workflow needed)
   d. Register RequestContext in RequestRegistry (request ID → *http.Request + chan)
   e. Start Temporal workflow: ProxyRequestWorkflow

7. TEMPORAL WORKFLOW: ProxyRequestWorkflow
   Input: { requestID, rawJWT, placeholders[], targetDomain }
   Search attributes set immediately: TargetDomain, Status=in_progress

   7a. Activity: ValidateIdentity (regular — JWKS needs network)
       - Verify JWT signature, issuer, audience, expiry via Keycloak JWKS
       - Extract claims: { sub, roles, groups }
       - Returns: IdentityClaims (safe for event history)
       INVALID → workflow finalizes as denied, sends denial on DecisionCh

   7b. Local Activity: EvaluatePolicy (OPA is in-process)
       - Input: { identity claims, placeholders, target_domain }
       - Resolves credential bindings from config
       - Evaluates Rego policy: identity.roles → credential → domain
       DENIED → workflow finalizes as denied, sends denial on DecisionCh

   7c. Local Activity: FetchAndInject (vault fetch + request modification)
       - Looks up RequestContext from RequestRegistry by requestID
       - Resolves vault paths from config
       - Fetches real credentials from OpenBao
       - Replaces placeholders in *http.Request headers/body (in-place)
       - Populates RequestContext.ScrubMap (realValue → placeholder)
       - Sends "allowed" decision on DecisionCh (unblocks goproxy)
       - Returns: InjectResult { credentialCount } (no secrets in output)

   7d. Workflow waits for "response_complete" signal (up to 60s timeout)

8. GOPROXY (unblocked by DecisionCh):
   a. Request was already modified in-place by FetchAndInject
   b. Forward modified request to api.anthropic.com
   c. Receive response

9. GOPROXY OnResponse handler:
   a. Scan response body for real credential values (using ScrubMap from registry)
   b. Replace any found values with their placeholder strings
   c. Clean up connTokens entry
   d. Signal workflow: "response_complete" with { statusCode, scrubCount, bytes }
   e. Return sanitized response through MITM TLS → VSOCK → Agent

10. TEMPORAL WORKFLOW receives signal, updates search attributes, completes.
    Full audit trail: agentID, targetDomain, credentialCount, scrubCount,
    statusCode, latencyMs, allowed/denied status — all queryable via
    Temporal's search attribute API.
```

---

## goproxy Integration Details

### Responsibility Split: goproxy vs Temporal

| Concern | Owner | Rationale |
|---------|-------|-----------|
| CONNECT handling, domain allowlist | goproxy | Must happen before MITM; no benefit from durability |
| JWT extraction from headers | goproxy | Parsing only — deterministic, no I/O |
| Placeholder extraction from body/headers | goproxy | Parsing only — deterministic, no I/O |
| JWT verification (JWKS) | Temporal activity | Network I/O (JWKS fetch), benefits from retry |
| OPA policy evaluation | Temporal activity | May timeout, benefits from retry + audit |
| Credential path resolution | Temporal activity | Config lookup with audit trail |
| Vault secret fetch | Temporal local activity (`FetchAndInject`) | In-process via RequestRegistry; secrets never serialized |
| Placeholder→credential substitution | Temporal local activity (`FetchAndInject`) | Modifies `*http.Request` in-place via RequestRegistry |
| HTTP forwarding | goproxy | Owns the HTTP lifecycle |
| Response credential scrubbing | goproxy + Temporal signal | goproxy scrubs; signals workflow with outcome metadata |
| Audit recording | Temporal (workflow lifecycle + search attributes) | Full lifecycle: authn, authz, inject, forward, scrub |

### Handler Registration

```go
// HandleConnect: domain allowlist + JWT extraction (no Temporal yet)
proxy.OnRequest().HandleConnect(goproxy.FuncHttpsHandler(
    func(host string, ctx *goproxy.ProxyCtx) (*goproxy.ConnectAction, string) {
        domain := stripPort(host)
        if !gw.cfg.IsAllowedDomain(domain) {
            return goproxy.RejectConnect, host
        }
        gw.connTokens.Store(ctx.Req.RemoteAddr, extractBearerToken(
            ctx.Req.Header.Get("Proxy-Authorization")))
        return goproxy.MitmConnect, host
    }))

// OnRequest: register context → start Temporal workflow → block on decision
proxy.OnRequest().DoFunc(func(req *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
    rawToken := gw.resolveToken(req)
    if rawToken == "" {
        return req, errorResponse(req, 407, "missing authentication token")
    }
    req.Header.Del("Proxy-Authorization")

    placeholders, _ := Extract(req)
    if len(placeholders) == 0 {
        return req, nil // No credentials needed — pass through
    }

    // Register request in shared registry for local activities
    requestID := generateRequestID()
    decisionCh := make(chan *WorkflowDecision, 1)
    reqCtx := &RequestContext{Request: req, DecisionCh: decisionCh}
    gw.registry.Store(requestID, reqCtx)
    defer gw.registry.Delete(requestID)

    // Start Temporal workflow (stays alive until response_complete signal)
    targetDomain := stripPort(req.Host)
    run, err := gw.temporal.ExecuteWorkflow(bgCtx, client.StartWorkflowOptions{
        ID:        fmt.Sprintf("proxy-%s-%s", targetDomain, requestID),
        TaskQueue: gw.cfg.Temporal.TaskQueue,
    }, workflows.ProxyRequestWorkflow, workflows.ProxyInput{
        RequestID:    requestID,
        RawJWT:       rawToken,
        Placeholders: placeholders,
        TargetDomain: targetDomain,
    })

    // Block until FetchAndInject activity signals decision (NOT run.Get())
    decision := <-decisionCh
    if decision.Status != StatusAllowed {
        return req, errorResponse(req, 403, decision.Reason)
    }

    // Request was modified in-place by FetchAndInject. ScrubMap populated.
    ctx.UserData = &requestState{
        scrubMap:   reqCtx.ScrubMap,
        workflowID: run.GetID(),
        runID:      run.GetRunID(),
    }
    return req, nil
})

// OnResponse: scrub credentials, then signal workflow completion
proxy.OnResponse().DoFunc(func(resp *http.Response, ctx *goproxy.ProxyCtx) *http.Response {
    state := ctx.UserData.(*requestState)
    scrubCount := ScrubCredentials(resp, state.scrubMap)

    // Signal workflow that response is handled — completes the audit trail
    gw.temporal.SignalWorkflow(bgCtx, state.workflowID, state.runID,
        "response_complete", ResponseOutcome{
            StatusCode:       resp.StatusCode,
            ScrubCount:       scrubCount,
            BytesTransferred: resp.ContentLength,
        })

    return resp
})
```

### Custom CA Certificate

Generated at NixOS build time:
```nix
# In modules/credential-proxy/default.nix
pkgs.runCommand "credproxy-ca" { buildInputs = [ pkgs.openssl ]; } ''
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout $out/ca.key -out $out/ca.crt -days 3650 -nodes \
    -subj '/CN=Credential Proxy CA/O=openclaw-vm'
''
```

Installed in guest VM:
```nix
# In guest.nix
security.pki.certificateFiles = [ "${credproxyCa}/ca.crt" ];
```

---

## File Structure

### Go Service: `credential-proxy/`

```
credential-proxy/
├── go.mod
├── go.sum
├── main.go                        # Entry: VSOCK listener, goproxy setup, Temporal worker
├── config/
│   └── config.go                  # Config types, YAML loading, domain allowlist
├── auth/
│   └── oidc.go                    # (2) Keycloak JWT validation (coreos/go-oidc wrapper)
├── authz/
│   ├── engine.go                  # (3) OPA embedded policy evaluator
│   └── policies/
│       └── credential_access.rego # Rego policy: identity → credential → domain
├── proxy/
│   ├── gateway.go                 # Composable gateway router (CONNECT → outbound)
│   ├── handlers.go                # goproxy OnRequest/OnResponse + signal workflow
│   ├── registry.go                # RequestRegistry: shared state between goproxy and Temporal
│   ├── placeholder.go             # Placeholder extraction + substitution (regex)
│   └── sanitizer.go               # Response credential scrubbing
├── vault/
│   └── client.go                  # (1) OpenBao client wrapper (DI-friendly interface)
├── workflows/
│   ├── proxy_workflow.go          # ProxyAccessDecision workflow (authn→authz→resolve)
│   └── activities.go              # ValidateIdentity, EvaluatePolicy, ResolveCredentialPaths
└── audit/
    └── search_attributes.go       # Temporal search attribute definitions
```

### NixOS Modules: `modules/credential-proxy/`

```
modules/credential-proxy/
├── default.nix                    # Host: proxy service + Temporal + CA generation
├── guest.nix                      # Guest: VSOCK bridge, CA cert, HTTP_PROXY env
└── openbao-policy.nix             # OpenBao read-only policy for proxy
```

### Modifications to Existing Files

| File | Change |
|------|--------|
| `flake.nix` | Add `credential-proxy` Go package (`buildGoModule`), module imports, test-vm config |
| `modules/openclaw-vm/default.nix` | Add `credentialProxy` option group, VSOCK port 18790, CA cert fw_cfg |
| `modules/openclaw-vm/guest.nix` | VSOCK bridge for port 18790, `HTTP_PROXY`/`HTTPS_PROXY` env vars, CA cert install |

---

## Temporal Workflow Design

### ProxyRequest Workflow — Full Lifecycle Orchestration

The workflow orchestrates the **entire proxy request lifecycle** — authentication,
authorization, credential injection, and response scrubbing audit. It stays alive for
the full HTTP request duration, receiving a completion signal from goproxy when the
response has been scrubbed.

**Key constraint**: goproxy owns the live `*http.Request` and `*http.Response` objects
(they cannot be serialized into Temporal). Solution: a `RequestRegistry` (`sync.Map`)
shared between goproxy and Temporal local activities. Activities reference requests by
ID; secrets flow through in-process memory, never through Temporal event history.

```
Input:  { requestID, rawJWT, placeholders[], targetDomain }
Output: { status, statusCode, credentialCount, scrubCount, latencyMs }

Search attributes: AgentID, TargetDomain, CredentialRefHash, Status

Signals:
  "response_complete" → { statusCode, scrubCount, bytesTransferred }
```

```go
func ProxyRequestWorkflow(ctx workflow.Context, input ProxyInput) (*ProxyOutput, error) {
    start := workflow.Now(ctx)
    upsertSearchAttributes(ctx, "", input.TargetDomain, input.Placeholders, StatusInProgress)

    // Phase 1: Validate identity (regular activity — JWKS may need network)
    var identity IdentityClaims
    err := workflow.ExecuteActivity(authnCtx, ValidateIdentity, input.RawJWT).Get(ctx, &identity)
    if err != nil {
        return finalize(ctx, start, StatusDenied, "authentication_failed")
    }
    upsertSearchAttributes(ctx, identity.Subject, "", nil, "")

    // Phase 2: Evaluate authorization policy (local activity — OPA is in-process)
    var decision AuthzDecision
    err = workflow.ExecuteLocalActivity(authzCtx, EvaluatePolicy, AuthzInput{
        Identity: identity, Placeholders: input.Placeholders, TargetDomain: input.TargetDomain,
    }).Get(ctx, &decision)
    if err != nil || !decision.Allowed {
        return finalize(ctx, start, StatusDenied, decision.Reason)
    }

    // Phase 3: Fetch credentials from vault and inject into request (local activity)
    // Accesses *http.Request via RequestRegistry[input.RequestID].
    // Secrets stay in-process — only metadata in event history.
    var injectResult InjectResult
    err = workflow.ExecuteLocalActivity(injectCtx, FetchAndInject, FetchAndInjectInput{
        RequestID:    input.RequestID,
        Placeholders: input.Placeholders,
    }).Get(ctx, &injectResult)
    if err != nil {
        return finalize(ctx, start, StatusError, "credential_injection_failed")
    }

    // Phase 4: Wait for goproxy to forward + scrub response.
    // goproxy signals us when response scrubbing is complete.
    var outcome ResponseOutcome
    timerCtx, _ := workflow.WithDeadline(ctx, workflow.Now(ctx).Add(60*time.Second))
    signalCh := workflow.GetSignalChannel(timerCtx, "response_complete")
    signalCh.Receive(timerCtx, &outcome)

    return &ProxyOutput{
        Status:          StatusSuccess,
        StatusCode:      outcome.StatusCode,
        CredentialCount: injectResult.CredentialCount,
        ScrubCount:      outcome.ScrubCount,
        LatencyMs:       workflow.Now(ctx).Sub(start).Milliseconds(),
    }, nil
}
```

### Request Registry (Shared In-Process State)

goproxy and Temporal local activities run in the same process. The `RequestRegistry`
bridges them without serializing secrets through Temporal:

```go
// In proxy/registry.go
type RequestRegistry struct {
    entries sync.Map // requestID → *RequestContext
}

type RequestContext struct {
    Request    *http.Request            // live HTTP request (goproxy owns this)
    ScrubMap   map[string]string        // realValue → placeholder (populated by FetchAndInject)
    DecisionCh chan<- *WorkflowDecision // unblocks goproxy when injection is complete
}
```

Flow:
1. goproxy creates `RequestContext`, stores in registry, starts workflow
2. goproxy blocks on `DecisionCh` (NOT `run.Get()` — workflow stays alive)
3. Workflow activities access the `RequestContext` by ID
4. `FetchAndInject` activity: fetches secrets from vault, modifies `*http.Request`,
   populates scrub map, sends decision on `DecisionCh`
5. goproxy unblocks, forwards request, scrubs response using `ScrubMap`
6. goproxy signals workflow with `response_complete` (status, scrub count, bytes)
7. Workflow records final audit metadata and completes

### Activities

1. **ValidateIdentity** (regular activity — authn via coreos/go-oidc)
   - Input: raw JWT string
   - Verifies JWT signature against Keycloak JWKS (cached, but may need network)
   - Extracts claims: sub, realm_access.roles, groups
   - Returns: `IdentityClaims` (safe for event history)
   - Retry: 2 attempts (JWKS endpoint may be temporarily unreachable)
   - Timeout: 10s start-to-close

2. **EvaluatePolicy** (local activity — authz via OPA embedded)
   - Input: identity claims + placeholders + target domain
   - Resolves placeholder→credential bindings from config
   - Evaluates Rego policy: "identity.roles → credential → domain"
   - Returns: `AuthzDecision { allowed, reason }`
   - Local activity: OPA evaluation is in-process, no network
   - Timeout: 5s start-to-close

3. **FetchAndInject** (local activity — vault fetch + credential injection)
   - Input: `{ requestID, placeholders }` (no secrets in input)
   - Looks up `RequestContext` from `RequestRegistry` by requestID
   - Resolves credential vault paths from config
   - Fetches real credentials from OpenBao (network call to vault)
   - Replaces placeholders in request headers/body (modifies `*http.Request` in-place)
   - Populates `RequestContext.ScrubMap` for response scrubbing
   - Sends decision on `RequestContext.DecisionCh` (unblocks goproxy)
   - Returns: `InjectResult { credentialCount }` (no secrets in output)
   - Timeout: 30s start-to-close

### Secrets Safety

Secret values NEVER appear in Temporal event history:

| Data | In Temporal history? | Where it lives |
|------|---------------------|----------------|
| Raw JWT | Yes (activity input) | Short-lived, already on VSOCK |
| Identity claims | Yes (activity output) | Public metadata from JWT |
| Credential paths | No (local activity) | In-process config lookup |
| Real secret values | **No** | In-process memory via RequestRegistry |
| Scrub map | **No** | In-process memory via RequestRegistry |
| HTTP request/response | **No** | goproxy memory via RequestRegistry |
| Scrub count / status code | Yes (signal payload) | Metadata, not secrets |

### What This Replaces

The previous implementation had:
- `ProxyRequestWorkflow` — dead code that tried to own the HTTP lifecycle inside a
  `FetchAndForward` activity, rebuilding requests from scratch (discarding headers/body).
- `AuditWorkflow` — fire-and-forget metadata logger, only recorded successes.
- All authn/authz/vault/scrub logic was inline in goproxy `handleRequest`.

The new `ProxyRequestWorkflow` orchestrates the full lifecycle:
- **Authn, authz, credential injection** are Temporal activities
- **Response scrubbing** is tracked via signal from goproxy to the workflow
- Every access attempt (allowed AND denied) is a complete workflow with search attributes
- The workflow is the single source of truth for "what happened with this request"

---

## OpenBao Credential Schema

```
Path: secret/data/openclaw/credentials/<alias>
Data: {
  "type": "api_key" | "bearer" | "basic_auth" | "header",
  "key": "sk-ant-...",
  "domain": "api.anthropic.com",
  "header_name": "x-api-key",
  "header_prefix": "",
  "placeholder": "agent-vault-<uuid>"
}
```

---

## Guest VM Configuration

### What changes in the VM:

1. **socat VSOCK bridge** (new systemd service):
   ```
   socat TCP-LISTEN:18790,fork,reuseaddr VSOCK-CONNECT:2:18790
   ```

2. **HTTP proxy env vars** (for all users + services):
   ```
   HTTP_PROXY=http://localhost:18790
   HTTPS_PROXY=http://localhost:18790
   NO_PROXY=localhost,127.0.0.1,10.88.0.1
   ```

3. **CA certificate** installed system-wide:
   ```nix
   security.pki.certificateFiles = [ credproxyCaCert ];
   ```

4. **Placeholder env vars** (per credential):
   ```
   ANTHROPIC_API_KEY=agent-vault-a1b2c3d4-...
   GITHUB_TOKEN=agent-vault-e5f6a7b8-...
   ```

5. **Placeholder config** via fw_cfg (JSON listing available credentials with aliases + domains)

---

## Implementation Phases

### Phase 1: Types, Config, Auth, Authz (no external service deps)
- `credential-proxy/config/config.go` — Config types, YAML loading, domain allowlist
- `credential-proxy/authn/oidc.go` — Keycloak JWT validation wrapper (coreos/go-oidc)
- `credential-proxy/authz/engine.go` — OPA embedded policy evaluator
- `credential-proxy/authz/policies/credential_access.rego` — Authorization policy
- `credential-proxy/proxy/placeholder.go` — Placeholder regex extraction + substitution
- `credential-proxy/proxy/sanitizer.go` — Response credential scrubbing
- `credential-proxy/proxy/registry.go` — RequestRegistry (sync.Map bridging goproxy ↔ Temporal)

### Phase 2: Tests (import production code paths)
- `credential-proxy/authn/oidc_test.go` — JWT validation (valid, expired, wrong issuer)
- `credential-proxy/authz/engine_test.go` — OPA policy (allow, deny, domain mismatch)
- `credential-proxy/proxy/placeholder_test.go` — Placeholder detection in headers, body, URLs
- `credential-proxy/proxy/sanitizer_test.go` — Credential scrubbing from JSON/HTML/text responses
- `credential-proxy/workflows/activities_test.go` — ValidateIdentity, EvaluatePolicy, FetchAndInject
- `credential-proxy/workflows/proxy_workflow_test.go` — ProxyRequestWorkflow via testsuite

### Phase 3: Implementation (make tests pass)
- `credential-proxy/vault/client.go` — OpenBao client with DI interface
- `credential-proxy/proxy/gateway.go` — Gateway router (now holds RequestRegistry)
- `credential-proxy/proxy/handlers.go` — OnRequest (start workflow + block on ch), OnResponse (scrub + signal)
- `credential-proxy/workflows/proxy_workflow.go` — ProxyRequestWorkflow (full lifecycle + signal)
- `credential-proxy/workflows/activities.go` — ValidateIdentity, EvaluatePolicy, FetchAndInject
- `credential-proxy/main.go` — VSOCK listener, goproxy setup, Temporal worker

### Phase 4: NixOS Integration
- `modules/credential-proxy/default.nix` — Host module (proxy + Temporal + CA gen)
- `modules/credential-proxy/guest.nix` — Guest module (VSOCK bridge, CA cert, env vars)
- `modules/credential-proxy/openbao-policy.nix` — Read-only policy
- `flake.nix` — `buildGoModule` package, module imports, test-vm config
- `modules/openclaw-vm/default.nix` — Wire in credentialProxy options, VSOCK port 18790
- `modules/openclaw-vm/guest.nix` — HTTP_PROXY/HTTPS_PROXY, CA cert, placeholder env vars

### Phase 5: VM Network Lockdown
- Extend nftables in `modules/openclaw-vm/default.nix` — block all external network when proxy enabled
- Only VSOCK communication allowed

---

## Verification

1. **Nix evaluation**: `nix flake check --no-build` passes
2. **Module evaluation**: `nix eval .#nixosConfigurations.test-vm.config.system.build.toplevel --apply 'x: "ok"'` → `"ok"`
3. **Go build**: `nix build .#credential-proxy` succeeds
4. **Go tests**: `cd credential-proxy && go test ./...` — all pass
5. **Placeholder detection**: Unit tests verify extraction from HTTP headers, JSON body, URL query params
6. **Sanitization**: Unit tests verify credential values scrubbed from responses (JSON, HTML, plaintext)
7. **Domain binding**: Unit tests verify mismatch → denied (fail-closed), match → allowed
8. **MITM TLS**: Integration test with custom CA cert — proxy decrypts HTTPS, injects credentials
9. **Temporal workflow**: Integration test with `go.temporal.io/sdk/testsuite` — ProxyRequestWorkflow completes full lifecycle (authn → authz → inject → signal → audit)
10. **Forward proxy**: Integration test — `curl -x http://proxy:18790 https://httpbin.org/get` works with placeholder substitution
11. **Network lockdown**: Agent cannot reach external network without proxy (no DNS, no TCP out)

---

## Existing Code to Reuse

| Pattern | Source | Reuse |
|---------|--------|-------|
| VSOCK socat bridge | `modules/openclaw-vm/guest.nix:466-488` (vsock-gateway-proxy) | Same pattern for credproxy VSOCK bridge |
| fw_cfg credential injection | `modules/openclaw-vm/default.nix:397-440` (sops.templates + fw_cfg) | Same pattern for placeholder config |
| systemd hardening | `modules/openclaw-vm/guest.nix:293-370` (openclaw-gateway service) | Copy hardening directives for proxy service |
| nftables VM isolation | `modules/openclaw-vm/default.nix:190-260` (nftables rules) | Extend for full network lockdown |
| OpenBao policy gen | `modules/openclaw/openbao.nix:42-70` (per-instance policies) | Same pattern for proxy read-only policy |
| CA cert install | NixOS `security.pki.certificateFiles` | Standard NixOS pattern for custom CAs |

NOTES
Reopened: Proposal must remain open until user performs UAT. Was closed without user review.

LABELS: aura:plan:proposal

DEPENDS ON
  → ○ nix-openclaw-vm-7xk: CREDENTIAL-PROXY: Implement credential proxy security layer for openclaw-vm ● P1

BLOCKS
  ← ○ nix-openclaw-vm-whp: URE: Credential proxy scope and MVP ● P1

