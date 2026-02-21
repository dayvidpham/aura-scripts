# Changelog

## [0.3.1] - 2026-02-21

### Added
- feat(validator): add validation for startup-sequence, standing-teams, and skill-invocation

### Fixed
- fix(schema): resolve h5 handoff target-role 'followup' → 'supervisor'

## [0.3.0] - 2026-02-21

### Added
- feat: add bin/aura-release for automated version bumping and tagging
- feat: add schema.xml validator with 3-layer validation and mutation tests
- feat(marketplace): add agentfilter plugin from external repo
- feat(plugin): migrate commands/ to skills/ plugin layout
- feat(protocol): complete Aura protocol v2 MVP — skills, process, and schema updates
- feat(commands): update phase 8-12 skills (supervisor + worker + impl) to v2 protocol
- feat(commands): update phase 3-7 skills (architect + reviewer) to v2 protocol
- feat(commands): update phase 1-2 skills to v2 protocol
- feat(commands): update utility and messaging skills to v2 protocol
- feat(protocol): update protocol core to v2 label schema and conventions
- feat: adds good URE -> research example
- feat: adds good handoff examples; adds v2 feature request
- feat(protocol): introduce URD concept and fix dependency direction across 22 files
- feat: print prompt file path in aura-swarm start output
- feat: add HM module, aura commands/agents, and UAT protocol docs
- feat(protocol): extract reusable Aura protocol docs from project-specific files
- feat: adds python flake from template
- feat: add aura-swarm worktree agent workflow script
- feat: initial extraction from dotfiles monorepo

### Fixed
- fix(protocol): enforce supervisor skill invocation, leaf tasks, and standing explore team
- fix(.beads): untrack dolt database and ephemeral runtime files
- fix(aura-release): improve CLI error messages with actionable guidance
- fix(supervisor): require full Beads context in TeamCreate assignments
- fix(supervisor): require leaf tasks within slices, fix severity routing
- fix(flake): replace rec inputs with follows for nixpkgs alias
- fix(plugin): update install instructions to real CLI, fix marketplace schema
- fix(plugin): resolve review findings — Nix paths, cross-refs, stale docs
- fix(protocol): add follow-up lifecycle to protocol SKILL.md quick reference
- fix(protocol): add all 15 files to protocol SKILL.md document table
- fix(protocol): update Beads task titles, fix label typos, add protocol docs
- fix(protocol): replace TypeScript examples with Go, fix LLM tool call fences, update reviewer naming
- fix: use ~/.local/share/aura/aura-swarm/prompts/ for prompt files
- fix(swarm): move prompt state dir to XDG-compliant ~/.local/state/aura/aura-swarm/prompt/
- fix: write prompt to file to avoid tmux command length limit
- fix: stop gitignoring .beads/ — beads db should be tracked
- fix: disables cuda; unnecessary here

### Changed
- refactor: writes to skills/ instead of docs/
- refactor: move scripts/ → bin/ for aura-swarm and aura-parallel

### Documentation
- docs: add aura-release usage to README.md and AGENTS.md
- docs(research): add Opus vs Sonnet model selection research report
- docs(skills): clarify skills vs subagent types, improve UAT/URE question guidance, add supervisor delegation constraint
- docs(readme): add plugin install quick start, fix stale script paths
- docs: update prompt file path to ~/.local/state/aura/
- docs: update README with prompt file state management
- docs: rewrite README with comprehensive aura-swarm and launch-parallel reference

### Other
- chore: bd sync
- doc: Claude Code research agent results
- chore: bump version to 0.2.1
- chore: rename repo aura-scripts → aura-plugins
