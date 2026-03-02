---
title: "Static Cross-Compilation & Binary Distribution for Claude Code Plugins — Domain Research"
date: "2026-02-23"
depth: "deep-dive"
request: "af-9u0 (related: agentfilter config support + binary distribution)"
---

## Executive Summary

This report investigates how Zig-based cross-compilation via Nix can enable statically-compiled binary distribution for Claude Code plugins — specifically for the `agentfilter` security filter (currently Python, ~200ms cold start) and the `aura` analytics CLI (Go + CGo tree-sitter). Four approaches were evaluated: Zicross, nix-zig-stdenv, raw Zig cross-compilation, and Nix's native cross-compilation infrastructure. The recommended direction is a **two-track strategy**: (1) use Go's native cross-compilation via `buildGoModule` + `CGO_ENABLED=0` for the `aura` binary (pure Go core covers 95% of functionality), and (2) use Zig's `cc` wrapper via a minimal Nix overlay for the `agentfilter` C/Rust components if a rewrite is pursued. Distribution should be via a `/aura:install-cli` skill that detects OS/arch and fetches pre-built binaries from GitHub Releases.

---

## 1. Current State Across Projects

### 1.1 agentfilter (Python security filter)

**Location:** `/home/minttea/codebases/dayvidpham/agentfilter/`
**Language:** Python 3.12
**Hook invocation:** `python3 ${CLAUDE_PLUGIN_ROOT}/opencode-security-filter/src/security_filter_hook.py`
**Cold start:** ~200ms (Python interpreter + imports)
**Static compilation:** Not applicable (Python)

The security filter is 38 hardcoded patterns with regex matching, operation-aware filtering, and specificity-level resolution. The entire filter logic is pure computation — no I/O, no network, no FFI. This is an ideal candidate for rewriting in a compiled language.

**Cross-compilation relevance:** If rewritten in Go or Zig, the filter would be a single static binary (~2-5MB) with ~10ms cold start. Given that this hook runs on **every tool call**, the 190ms savings per invocation is significant over a session.

### 1.2 aura (Go analytics CLI)

**Location:** `/home/minttea/dev/agent-data-leverage/main/`
**Language:** Go 1.24.2
**Build:** `buildGoModule` via Nix flake
**CGo dependency:** tree-sitter (Maximum redaction tier only)
**Supported systems:** `eachDefaultSystem` (x86_64-linux, aarch64-linux, x86_64-darwin, aarch64-darwin)

**Key finding:** The aura binary is **almost** pure Go. The only CGo dependency is tree-sitter for AST-based code anonymization (Maximum redaction). The core functionality (ingest pipeline, config, store, API, TUI, Standard/Minimal redaction) is all pure Go and statically linkable with `CGO_ENABLED=0`.

**Cross-compilation story today:**
- Nix `buildGoModule` handles per-system builds
- No cross-compilation infrastructure (each system builds natively)
- `boot.binfmt.emulatedSystems = [ "aarch64-linux" ]` on desktop for aarch64 emulation
- Tree-sitter complicates Windows cross-compilation

### 1.3 aura-plugins (Python orchestration toolkit)

**Location:** `/home/minttea/codebases/dayvidpham/aura-plugins/`
**Language:** Python 3.10+ (stdlib only for CLI tools)
**Config parser:** `schema_parser.py` — XML schema to typed Python specs
**Transpiler:** Bidirectional schema <-> types codegen
**Distribution:** Nix flake + Home Manager module + Claude Code plugin marketplace

**Cross-compilation relevance:** The CLI tools (`aura-swarm`, `aura-release`) are pure Python with no external dependencies. They don't benefit from static compilation. However, the **config parser and constraint checker** could be compiled if performance becomes an issue (currently not a bottleneck).

### 1.4 dotfiles / nix-openclaw-vm (Nix infrastructure)

**Location:** `/home/minttea/dotfiles/`, `/home/minttea/codebases/dayvidpham/nix-openclaw-vm/`
**Current cross-compilation:** Only binfmt emulation for aarch64 on desktop
**MicroVM:** VSOCK-isolated llm-sandbox guest with hardened kernel
**No Zig toolchain** currently configured anywhere

---

## 2. Zig-Based Cross-Compilation Approaches

### 2.1 Zicross

**Source:** https://github.com/flyx/Zicross
**Status:** Pre-alpha ("Use at your own risk. Will likely fail when doing anything complex.")

Zicross is a Nix flake that uses Zig's bundled `clang` as a cross-compilation engine. It provides:
- `zigStdenv` — drop-in replacement for Nix's stdenv using Zig's CC
- `buildGoModule` wrapper for Go projects with C dependencies
- `packageForDebian` — generates `.deb` files
- `packageForWindows` — generates `.zip` archives with bundled DLLs
- `ZIG_TARGET` environment variable for target selection
- Foreign builder injection with pkg-config patching

**Strengths:**
- Handles Go + CGo cross-compilation (relevant for aura's tree-sitter)
- Debian and Windows packaging built in
- Single toolchain for C/Go/Zig projects

**Weaknesses:**
- Pre-alpha; explicitly warns against complex use cases
- Limited documentation (examples only)
- No active maintenance signals (last meaningful commit unclear)
- Would need significant testing for aura's tree-sitter bindings

**Assessment:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| Maturity | Low | Pre-alpha, documentation sparse |
| Go support | Medium | Works for simple Go+CGo; tree-sitter untested |
| Platform coverage | Good | Linux, Windows, Debian ARM |
| Nix integration | Good | Native flake, overlays |
| Maintenance risk | High | Small project, unclear activity |

**Adoption recommendation:** Defer — interesting concept but too immature for production use. Monitor for stability improvements.

### 2.2 nix-zig-stdenv

**Source:** https://github.com/Cloudef/nix-zig-stdenv
**Status:** Archived (January 2024)

Replaced Nix's default stdenv with Zig, enabling cross-compilation to 19+ targets (including Linux aarch64, ARM, MIPS, PowerPC, RISC-V, Windows MinGW, WebAssembly WASI).

**Key achievement:** Successfully cross-compiled `iniparser` package to all targets. Also used for Rust → musl static binaries on aarch64 (AWS Lambda).

**Known issues:**
- Race condition in parallel builds (Zig caching conflict)
- Rust + Zig `libcompiler_rt` ownership disputes
- Archived — no longer maintained

**Assessment:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| Maturity | Medium | Proved the concept with 19+ targets |
| Platform coverage | Excellent | Most comprehensive target list |
| Maintenance | Dead | Archived Jan 2024 |
| Patterns | Valuable | Overlay patterns and target definitions reusable |

**Adoption recommendation:** Skip as a direct dependency, but **Adapt** its overlay patterns for a custom minimal solution.

### 2.3 Raw Zig Cross-Compilation

**Source:** https://ziap.github.io/blog/nixos-cross-compilation/

Zig's built-in cross-compilation is remarkably simple:
```bash
zig build -Dtarget=x86_64-linux-musl    # Static Linux binary
zig build -Dtarget=x86_64-windows-gnu   # Windows binary
zig build -Dtarget=aarch64-linux-musl   # ARM64 Linux static
```

**Key advantages:**
- Everything statically linked by default (libc optional in Zig)
- No toolchain bootstrapping — Zig ships everything
- Can compile C and C++ code with the same ease
- Single `pkgs.zig` package in Nix — no complex overlay needed

**Relevance to our projects:**
- **agentfilter rewrite in Zig:** Would produce ~500KB static binaries with ~1ms cold start. Zig's regex support is limited though — would need a library.
- **agentfilter rewrite in C:** Zig's `cc` wrapper could cross-compile a C security filter trivially.
- **Go projects:** Zig can serve as the CC for CGo (`CC="zig cc"`) but Go already has native cross-compilation for pure Go code.

**Assessment:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| Simplicity | Excellent | 1 line to cross-compile |
| Static linking | Excellent | Default behavior |
| Go integration | Medium | Only needed for CGo; Go handles pure Go natively |
| Binary size | Excellent | Zig produces very small binaries |
| Ecosystem | Growing | Fewer libraries than Go/Rust |

**Adoption recommendation:** Adopt for C/Zig components. For Go, only needed when CGo is involved (tree-sitter).

### 2.4 Nix Native Cross-Compilation

**Source:** https://www.hobson.space/posts/nixcross/

Nix's `buildPlatform`/`hostPlatform`/`targetPlatform` system with `wrapCCWith` and `wrapBintoolsWith`. The blog reveals significant undocumented complexity:
- `wrapCCWith` determines compiler prefixes from platform config
- Requires `host != build` to function correctly
- Internal package set pattern (`cross/default.nix`) must be mimicked
- `replaceStdenv` and `replaceCrossStdenv` needed for custom toolchains

**Key insight:** Nix native cross-compilation is powerful but poorly documented and requires reverse-engineering nixpkgs internals. It's the right foundation for a production system but has a steep learning curve.

**Relevance:** For Go projects, `pkgsCross.aarch64-multiplatform.buildGoModule` is the simplest path. For C projects, Zig-as-CC via a Nix overlay avoids the toolchain bootstrapping complexity entirely.

**Assessment:**

| Aspect | Rating | Notes |
|--------|--------|-------|
| Power | Excellent | Full control over all triples |
| Documentation | Poor | "The documentation seems to not have been written" |
| Go support | Good | `pkgsCross` + `buildGoModule` works |
| Complexity | High | Requires deep Nix internals knowledge |
| Reliability | Good | Battle-tested in nixpkgs |

**Adoption recommendation:** Adapt — use `pkgsCross` for Go binaries, Zig overlay for C/CGo components.

---

## 3. Binary Distribution Strategy

### 3.1 The `/aura:install-cli` Skill Approach

The user's proposed approach: a Claude Code skill that detects OS, CPU architecture, and places a statically cross-compiled binary on `$PATH`.

**Implementation sketch:**

```markdown
# /aura:install-cli SKILL.md
---
description: Install aura CLI binary for your platform
---

Detect the user's platform and install the appropriate pre-built binary:
1. Detect OS: `uname -s` → Linux, Darwin
2. Detect arch: `uname -m` → x86_64, aarch64/arm64
3. Determine binary: `aura-{os}-{arch}` (e.g., `aura-linux-x86_64`)
4. Download from GitHub Releases: `gh release download v{version} -p "aura-{os}-{arch}"`
5. Place on PATH: `~/.local/bin/aura` (XDG standard)
6. Verify: `aura version`
```

**Platform matrix:**

| OS | Arch | Binary name | CGo | Notes |
|----|------|-------------|-----|-------|
| Linux | x86_64 | `aura-linux-x86_64` | Optional | Most common dev environment |
| Linux | aarch64 | `aura-linux-aarch64` | Optional | ARM servers, Raspberry Pi |
| macOS | x86_64 | `aura-darwin-x86_64` | Optional | Intel Macs |
| macOS | arm64 | `aura-darwin-arm64` | Optional | Apple Silicon |

**Windows consideration:** Claude Code runs on Windows via WSL, which is Linux. Native Windows support is low priority.

### 3.2 Build Pipeline: GitHub Actions + Nix

```yaml
# .github/workflows/release.yml
strategy:
  matrix:
    include:
      - { os: ubuntu-latest, goos: linux, goarch: amd64, suffix: linux-x86_64 }
      - { os: ubuntu-latest, goos: linux, goarch: arm64, suffix: linux-aarch64 }
      - { os: macos-latest, goos: darwin, goarch: amd64, suffix: darwin-x86_64 }
      - { os: macos-latest, goos: darwin, goarch: arm64, suffix: darwin-arm64 }

steps:
  - run: |
      CGO_ENABLED=0 GOOS=${{ matrix.goos }} GOARCH=${{ matrix.goarch }} \
        go build -ldflags "-s -w" -o aura-${{ matrix.suffix }} ./cmd/aura
```

**With `CGO_ENABLED=0`:** Pure Go build, no tree-sitter, Maximum redaction unavailable. This is acceptable — Maximum redaction is opt-in and can be offered as a separate Nix-only package.

**With Nix (alternative):**
```nix
# Per-platform builds via pkgsCross
packages.aarch64-linux = pkgs.pkgsCross.aarch64-multiplatform.buildGoModule { ... };
```

### 3.3 agentfilter Binary Distribution

If agentfilter is rewritten (Go or Zig), the same pattern applies but with a twist: the binary needs to be placed where the Claude Code hook can find it.

**Option A: Binary replaces Python hook**
```json
{
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/bin/agentfilter-${OS}-${ARCH}",
  "timeout": 5
}
```
Problem: `hooks.json` doesn't support platform variables.

**Option B: Wrapper script with platform detection**
```json
{
  "type": "command",
  "command": "${CLAUDE_PLUGIN_ROOT}/bin/agentfilter-hook",
  "timeout": 5
}
```
Where `agentfilter-hook` is a thin shell script:
```bash
#!/bin/sh
SELF_DIR="$(dirname "$0")"
exec "${SELF_DIR}/agentfilter-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)" "$@"
```

**Option C: Install binary to PATH via skill, reference by name**
```json
{
  "type": "command",
  "command": "agentfilter",
  "timeout": 5
}
```
Simplest — if the binary is on PATH, the hook just calls it by name. The `/aura:install-cli` skill handles placement.

---

## 4. Convergence Opportunities Across Projects

### 4.1 agentfilter + aura secrets detection

The `aura` project already has a mature secrets detection engine (`internal/redact/`) with:
- 40+ built-in patterns (API keys, tokens, passwords, PII)
- Entropy-based detection for high-information strings
- User-configurable custom patterns via YAML config
- Three redaction tiers (Minimal, Standard, Maximum)

The `agentfilter` security filter has 38 hardcoded path-based patterns focused on file access control (SSH keys, env files, credential directories).

**These serve different purposes but could share a pattern engine:**
- agentfilter: "Should this tool call be allowed?" (pre-tool-use gate)
- aura redact: "Does this content contain secrets?" (post-ingestion scrubbing)

**Convergence path:** Extract a shared Go pattern-matching library that both projects consume. The agentfilter becomes a thin hook binary that imports the library.

### 4.2 aura-plugins config parser + agentfilter config support

The `aura-plugins` project has a sophisticated config parser (`schema_parser.py`) with:
- XML → typed Python specs
- Bidirectional transpilation (schema <-> types)
- Runtime constraint validation
- A2A-compatible content types

The new `af-9u0` REQUEST for agentfilter wants:
1. A config file for user-defined allow/deny patterns
2. Parse `.claude/settings.json` and `.claude/settings.local.json`

**Convergence path:** The config parser in aura-plugins could be extended to understand Claude Code's settings format and transpile it into agentfilter pattern rules. This is the "agent harness config parser and transpiler" the user mentioned.

### 4.3 Unified binary: `aura` subsumes agentfilter

The most elegant convergence: **aura absorbs the security filter as a subcommand**.

```
aura filter check --path ~/.ssh/id_rsa --tool Read    # Security filter
aura filter hook                                       # Hook mode (stdin/stdout)
aura ingest                                            # Transcript ingestion
aura metrics compute                                   # Analytics
```

**Benefits:**
- Single binary to distribute (one `/aura:install-cli` skill)
- Shared pattern engine between filter and redaction
- Config parsing unified (settings.json → both filter rules and redaction rules)
- One Nix flake, one build pipeline, one release process

**Tradeoffs:**
- Larger binary (~15MB vs ~5MB)
- agentfilter currently has no Go code (would need rewrite)
- Coupling between analytics and security concerns

---

## 5. Recommended Architecture

### Track 1: Go Static Binaries via Native Cross-Compilation (Immediate)

For the `aura` binary:

```nix
# flake.nix addition
packages = forAllSystems ({ pkgs, system }: {
  aura = pkgs.buildGoModule {
    pname = "aura";
    version = "0.2.0";
    src = ./.;
    vendorHash = null;
    CGO_ENABLED = 0;  # Pure Go, no tree-sitter
    ldflags = [ "-s" "-w" "-X github.com/dayvidpham/aura/internal/defaults.version=${version}" ];
  };
  # Tree-sitter variant (native platform only)
  aura-full = pkgs.buildGoModule {
    pname = "aura-full";
    version = "0.2.0";
    src = ./.;
    vendorHash = null;
    CGO_ENABLED = 1;
    nativeBuildInputs = [ pkgs.gcc ];
    ldflags = [ "-s" "-w" ];
  };
});
```

**GitHub Actions** for cross-platform releases:
- `CGO_ENABLED=0` builds for all 4 platforms
- Upload as GitHub Release assets
- `/aura:install-cli` skill fetches the right one

### Track 2: Zig-as-CC for CGo Cross-Compilation (Future)

When Maximum redaction (tree-sitter CGo) needs to cross-compile:

```nix
# Zig CC wrapper overlay
zigCcOverlay = final: prev: {
  zigCc = prev.writeShellScriptBin "zigcc" ''
    exec ${prev.zig}/bin/zig cc "$@"
  '';
  zigCxx = prev.writeShellScriptBin "zigcxx" ''
    exec ${prev.zig}/bin/zig c++ "$@"
  '';
};

# Cross-compile Go+CGo with Zig as CC
aura-full-cross = pkgs.buildGoModule {
  pname = "aura-full";
  CGO_ENABLED = 1;
  CC = "${pkgs.zigCc}/bin/zigcc";
  CXX = "${pkgs.zigCxx}/bin/zigcxx";
  # ZIG_TARGET set per platform
};
```

This is the pattern from Zicross, simplified. Only needed when CGo cross-compilation is required.

### Track 3: agentfilter Rewrite (Future)

If agentfilter is rewritten in Go as part of the `aura` binary:
1. Port the 38 patterns + resolver + filter to Go
2. Add `aura filter hook` subcommand (reads stdin, writes stderr, exits 0/2)
3. Update `hooks.json` to call `aura filter hook` instead of Python
4. Cold start drops from ~200ms to ~10ms

---

## Summary

| Topic Area | Recommendation | Rationale |
|------------|---------------|-----------|
| Zicross | Defer | Pre-alpha, too immature for production |
| nix-zig-stdenv | Skip (Adapt patterns) | Archived, but overlay patterns are reusable |
| Raw Zig cross-compilation | Adopt (for C/CGo) | Simple, reliable, static by default |
| Nix pkgsCross | Adopt (for Go) | Battle-tested, works with buildGoModule |
| Go CGO_ENABLED=0 | Adopt (immediate) | Covers 95% of aura functionality, trivial cross-compile |
| /aura:install-cli skill | Adopt | Clean UX for non-Nix users |
| GitHub Releases distribution | Adopt | Standard, well-understood, works with gh CLI |
| agentfilter Go rewrite | Defer (design now) | High value but significant effort |
| Unified aura binary | Adapt (plan for it) | Elegant convergence but requires agentfilter rewrite first |

## Key Takeaways

### Adopt
- `CGO_ENABLED=0` Go cross-compilation for the `aura` binary (4 platforms, immediate)
- GitHub Releases + `/aura:install-cli` skill for distribution
- Zig `cc` wrapper as a Nix overlay for future CGo cross-compilation needs

### Adapt
- nix-zig-stdenv's overlay patterns for a minimal custom Zig-CC overlay
- Unified binary concept (aura absorbing agentfilter) — design the interface now, implement later
- aura-plugins config parser to handle `.claude/settings.json` transpilation

### Defer
- Zicross — monitor for maturity improvements
- Full agentfilter Go rewrite — design the Go interface, keep Python operational
- Maximum redaction cross-compilation (tree-sitter CGo) — only needed for native builds

### Skip
- nix-zig-stdenv as a direct dependency (archived)
- Windows native binaries (WSL covers this)
- Zig rewrite of agentfilter (Go is better fit given aura ecosystem)
