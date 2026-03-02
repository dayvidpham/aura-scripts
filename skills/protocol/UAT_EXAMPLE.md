# UAT Example: Plan Acceptance for aura-scripts Nix Flake REVISION-2

> Source: aura-scripts-ci4

## Beads Commands

```bash
# 1. Create the UAT task with labels and description
bd create --labels "aura:user:uat,proposal-2:uat-1" \
  --title "UAT-1: Plan acceptance for aura-scripts Nix flake REVISION-2" \
  --description "<FULL_DESCRIPTION_BELOW>"

# 2. Link to the proposal being UAT'd (relates, not blocked-by)
bd dep relate aura-scripts-ci4 aura-scripts-82l

# 3. Record post-UAT addenda as comments
bd comments add aura-scripts-ci4 "UAT ADDENDUM (user-initiated, verbatim): ..."

# 4. After UAT passes, ratify the proposal
bd label add aura-scripts-82l aura:plan:ratify
bd comments add aura-scripts-82l "RATIFIED: All 3 reviewers ACCEPT on REVISION-2, UAT passed (aura-scripts-ci4)."
```

## Components Reviewed

### Component 1: Module Structure
**Definition shown:**
```nix
CUSTOM.programs.aura-config-sync = {
  enable = true;
  packages.enable = true;
  commands.enable = true;
  agents.enable = true;
  protocol.enable = false;
};
```
**Motivating example:** Minimal setup enabling only commands (packages/agents disabled).

**Q1: The module uses CUSTOM.programs.aura-config-sync as the namespace. This matches your dotfiles convention (CUSTOM.programs.*). The alternative would be programs.aura-config-sync (standard HM namespace) or services.aura-config-sync. Which namespace is correct?**
Options:
- CUSTOM.programs (current) — Matches your dotfiles convention for custom HM modules — keeps it separate from upstream programs.*
- programs.aura-config-sync — Standard HM namespace — discoverable but risks collision with future upstream modules
- aura.config-sync — Custom top-level namespace — clearly non-standard, no collision risk
**User response:** "The CUSTOM namespace is for the modules defined in the @~/dotfiles repo. Since this is external, should go into aura.config-sync"

**Q2: Protocol docs default to enable = false because installing to ~/.claude/CLAUDE.md would overwrite any personal CLAUDE.md you have there. The alternative is default true with a merge strategy. Is default-off the right call?**
Options:
- Default off (current) — User must opt-in. Safest — never overwrites personal CLAUDE.md. But easy to forget to enable.
- Default on, xdg target — Default to ~/.config/aura/protocol/ instead of ~/.claude/ — always installs but never conflicts with personal CLAUDE.md
- Default on, global target — Installs to ~/.claude/ — convenient but WILL overwrite personal CLAUDE.md on every home-manager switch
**User response:** "Default on, xdg target"

**Decision:** ACCEPT

---

### Component 2: Commands with Role Filtering
**Definition shown:**
```nix
aura.config-sync.commands = {
  enable = true;
  roles = { enableAll = true; architect.enable = ...; supervisor.enable = ...; worker.enable = ...; reviewer.enable = ...; epoch.enable = ...; };
  extraCommands = { "my-custom:command.md" = ./my-command.md; };
};
```
**Motivating example:** Worker-only machine with enableAll=false, worker.enable=true.

**Q1: Currently epoch is classified as a role alongside architect/supervisor/worker/reviewer. But epoch orchestrates ALL roles — setting enableAll=false would hide it, which breaks orchestration. Should epoch be reclassified?**
Core commands (always installed): aura:plan, aura:status, aura:test, aura:feedback, aura:msg:*, aura:impl:*, aura:user:*
Role commands (togglable): aura:architect:*, aura:supervisor:*, aura:worker:*, aura:reviewer:*
Options:
- Move epoch to core commands — Always installed regardless of enableAll. Epoch orchestrates all roles so it should always be available.
- Keep epoch as a role — A machine running only workers doesn't need epoch. User can explicitly enable epoch alongside their chosen roles.
- Separate orchestration tier — Three tiers: core (always), orchestration (epoch), roles (architect/supervisor/worker/reviewer). Adds complexity but models the hierarchy accurately.
**User response:** "Move epoch to core commands"

**Q2: The extraCommands extension point uses attrsOf path — keys are filenames, values are file paths. This means you can add project-specific commands. Is this the right extension mechanism, or should it support inline text too?**
Options:
- Path only (current) — Simple — just point to .md files. Consistent with how all other commands work.
- Path or text — attrsOf (either path or str) — allows inline command definitions in Nix config. More flexible but mixed types add complexity.
- Path only + extraCommandDirs — Add a second option to include entire directories of commands. Useful if you have many project-specific commands.
**User response:** "Path only + extraCommandDirs"

**Q3 (user-initiated comment, verbatim):** "installation should rely mostly on creating mkOutOfStoreSymlink paths, similar to some other existing configs in ~/dotfiles that require more responsiveness and live updating, and don't require an entire build/recompilation step."

**Decision:** ACCEPT with comments (mkOutOfStoreSymlink)

---

### Component 3: Package Wrapping
**Definition shown:**
```nix
# Current (broken): writeScriptBin with shebang replace only
# Proposed: writeShellApplication with runtimeInputs = [ python3 tmux git ]
```
**Motivating example:** aura-swarm fails at runtime because tmux not in PATH.

**Q1: aura-swarm needs tmux and git at runtime (plus bd and claude for worktree mode). Should ALL runtime deps be baked into the Nix wrapper, or should some be expected from the user's PATH?**
Options:
- Bake all in (hermetic) — writeShellApplication with all runtimeInputs. aura-swarm gets python3+tmux+git+bd+claude. Fully reproducible.
- Bake tmux+python, expect claude+bd from PATH — claude and bd are user-managed tools (not in nixpkgs or custom). Wrap what Nix can provide, leave the rest to PATH.
- Expect all from PATH — Only patch the shebang. User is responsible for having tmux, git, claude, bd available. Lightest wrapper.
**User response:** "Bake all in (hermetic)"

**Decision:** ACCEPT

---

### Component 4: settings.json Writeback Strategy (Phase 4)
**Definition shown:** Three options: A) activation copy, B) base+overlay merge, C) nix-only read-only
**Motivating example:** Claude Code writes permissions to settings.json at runtime; home.file symlinks are read-only.

**Q1: Claude Code writes to ~/.claude/settings.json at runtime (e.g., when you grant permissions). Nix home.file creates read-only symlinks. How should Phase 4 handle this conflict?**
Options:
- Activation copy (Option A) — Nix generates file, copies on switch. Runtime edits persist between switches but get overwritten on next rebuild. Simplest to implement.
- Base + overlay (Option B) — Nix writes settings.base.json (immutable), runtime writes to settings.local.json, merged at startup. Never loses runtime changes. But requires custom merge logic and Claude Code doesn't support split configs.
- Nix-only, no runtime writes (Option C) — All settings managed in Nix. home.file symlink, read-only. If Claude Code tries to write, it fails. You manage ALL permissions/settings in your Nix config.
- Defer to Phase 4 — Don't decide now. Phase 4 design will have more context about what Claude Code actually needs at runtime. Just note it as an open question.
**User response:** "Defer to Phase 4" with note: "Can do Option B with some custom script for merging a user's config with the into the final"

**Decision:** ACCEPT

---

### Component 5: mkOutOfStoreSymlink for Live Updates
**Definition shown:**
```nix
# Store symlink (current): source = "${self}/commands/file.md" → /nix/store/...
# Out-of-store (proposed): source = config.lib.file.mkOutOfStoreSymlink "/home/.../aura-scripts/commands/file.md"
```
**Motivating example:** Edits to command files in repo immediately visible without home-manager switch.

**Q1: mkOutOfStoreSymlink needs the absolute path to the aura-scripts repo checkout. How should this be configured?**
Options:
- Explicit repoPath option (required) — User sets the path in their config. Clear, no magic. Fails with assertion if not set.
- Explicit repoPath with default — Default to a conventional path like ~/codebases/dayvidpham/aura-scripts. User can override. Convenient but assumes directory structure.
- Detect from flake input — Use self.outPath or builtins.toString self to derive the path. Works when flake is a local path input, not when fetched from GitHub.
**User response:** "Explicit repoPath option (required)"

**Q2: Should ALL file types use mkOutOfStoreSymlink (commands, agents, protocol docs), or only some?**
Options:
- All files use mkOutOfStoreSymlink — Commands, agents, and protocol docs all live-update. Consistent behavior. All require repoPath.
- Commands + agents live, protocol via store — Commands/agents change often during development. Protocol docs are more stable — store path is fine.
- Make it configurable per section — Add a liveUpdate = true/false toggle per section. Maximum flexibility, more options to manage.
**User response:** "All files use mkOutOfStoreSymlink"

**User comment (verbatim):** "Wondering how this will work with cross-config compilation. Should we adopt a yaml file based approach, some base json schema, or Nix-native? I think the agentconfig repo adopts a yaml file based approach?"

**Decision:** ACCEPT with comments

---

## Addendum (user-initiated, verbatim)

"I think we should have the cross-config compilation step PRODUCE a set of configs at pre-determined locations INSIDE the config-sync repo, then we can use mkOutOfStoreSymlink on the build artifacts of the compilation step."

---

## Final Decision
**ACCEPT** — All 5 components accepted. Key design changes from REVISION-2:
1. Namespace: aura.config-sync (not CUSTOM.programs)
2. Protocol: default on, xdg target
3. Epoch: core command, not a role
4. Extra commands: path + extraCommandDirs
5. Installation: mkOutOfStoreSymlink with required repoPath
6. Package wrapping: hermetic (all deps baked in)
7. settings.json: deferred to Phase 4, Option B likely direction
8. Open question: cross-config compilation strategy (yaml/json/nix-native) for Phase 4
