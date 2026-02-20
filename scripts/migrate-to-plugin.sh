#!/usr/bin/env bash
# migrate-to-plugin.sh — Convert aura-scripts from commands/ layout to plugin skills/ layout
#
# This script performs 3 phases:
#   Phase A: Update cross-references via sed (on existing file paths)
#   Phase B: Create skills/ directory structure and move files
#   Phase C: Set up scripts/ directory with renamed tools
#
# Usage: bash scripts/migrate-to-plugin.sh
#
# Safe to inspect with --dry-run (reads only, prints plan):
#   bash scripts/migrate-to-plugin.sh --dry-run

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN — no changes will be made ==="
fi

echo "=== Aura Plugin Migration ==="
echo "Repo root: $REPO_ROOT"
echo ""

# ── Validation ──
if [[ ! -d "commands" ]]; then
  echo "ERROR: commands/ directory not found. Already migrated?" >&2
  exit 1
fi

if [[ -d "skills" ]]; then
  echo "ERROR: skills/ directory already exists. Already migrated?" >&2
  exit 1
fi

# ── Build name mapping ──
# Strip 'aura:' prefix, replace remaining colons with hyphens
declare -A NAME_MAP
for f in commands/aura:*.md; do
  base="$(basename "$f" .md)"          # e.g. "aura:user:request"
  stripped="${base#aura:}"              # e.g. "user:request"
  skill_name="${stripped//:/-}"         # e.g. "user-request"
  NAME_MAP["$stripped"]="$skill_name"
done

echo "Migrating ${#NAME_MAP[@]} commands to skills:"
for old in $(echo "${!NAME_MAP[@]}" | tr ' ' '\n' | sort); do
  printf "  %-30s → %s\n" "$old" "${NAME_MAP[$old]}"
done
echo ""

if $DRY_RUN; then
  echo "=== DRY RUN complete — would migrate ${#NAME_MAP[@]} commands ==="
  exit 0
fi

# Helper: run sed in-place on a file (skips if file doesn't exist)
sedi() {
  local file="$1"; shift
  [[ -f "$file" ]] && sed -i "$@" "$file"
}

# ══════════════════════════════════════════════════════════════════
# PHASE A: Cross-reference updates (sed on existing file paths)
# ══════════════════════════════════════════════════════════════════

echo "── Phase A: Cross-reference updates ──"
echo ""

# ── A1: Slash command references ──
# /aura:X:Y → /aura:X-Y  (e.g. /aura:user:request → /aura:user-request)
# Pattern: after /aura: match [a-z]+ then replace the next colon with hyphen
# This is safe because beads labels (aura:p1-user:...) never have a leading /

echo "A1: Slash command references: /aura:X:Y → /aura:X-Y"
find . \( -name "*.md" -o -name "*.xml" \) \
  -not -path "./.git/*" -not -path "./.beads/*" -not -path "./.direnv/*" \
  -exec sed -i 's|/aura:\([a-z][a-z]*\):|/aura:\1-|g' {} +
echo "  done"

# ── A2: Frontmatter updates in command files ──
# name: X:Y → name: X-Y  (colons to hyphens)
# Remove tools: line entirely

echo "A2: Frontmatter updates (name colons→hyphens, remove tools line)"
for f in commands/aura:*.md; do
  base="$(basename "$f" .md)"
  stripped="${base#aura:}"
  skill_name="${NAME_MAP[$stripped]}"

  # Replace name value: colons → hyphens
  # The name field value is the stripped name (without aura: prefix)
  sed -i "s|^name: ${stripped}$|name: ${skill_name}|" "$f"

  # Remove tools: line
  sed -i '/^tools: /d' "$f"
done
echo "  done"

# ── A3: File path refs in commands/*.md ──
# These files will become skills/<name>/SKILL.md (sibling dirs under skills/)

echo "A3: File path refs in commands/*.md"
for f in commands/aura:*.md; do
  # ../../protocol/ → ../protocol/ (from skills/<name>/ to skills/protocol/)
  sed -i 's|../../protocol/|../protocol/|g' "$f"

  # Markdown href: (aura:X:Y.md) → (../X-Y/SKILL.md) — multi-segment
  sed -i 's|(aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md)|(../\1-\2/SKILL.md)|g' "$f"

  # Markdown href: (aura:X.md) → (../X/SKILL.md) — single-segment
  sed -i 's|(aura:\([a-z][a-z-]*\)\.md)|(../\1/SKILL.md)|g' "$f"

  # Link text: commands/aura:X:Y.md → skills/X-Y/SKILL.md — multi-segment
  sed -i 's|commands/aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md|skills/\1-\2/SKILL.md|g' "$f"

  # Link text: commands/aura:X.md → skills/X/SKILL.md — single-segment
  sed -i 's|commands/aura:\([a-z][a-z-]*\)\.md|skills/\1/SKILL.md|g' "$f"

  # .claude/commands/aura:X:Y.md → ../X-Y/SKILL.md (multi-segment, will be sibling under skills/)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md|../\1-\2/SKILL.md|g' "$f"

  # .claude/commands/aura:X.md → ../X/SKILL.md (single-segment)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z-]*\)\.md|../\1/SKILL.md|g' "$f"

  # Generic .claude/commands/ → skills/
  sed -i 's|\.claude/commands/|skills/|g' "$f"
done
echo "  done"

# ── A4: File path refs in protocol/*.md and protocol/*.xml ──
# These files will become skills/protocol/* (sibling to other skill dirs)

echo "A4: File path refs in protocol/"
for f in protocol/*.md protocol/schema.xml; do
  [[ -f "$f" ]] || continue

  # .claude/commands/aura:X:Y.md → ../X-Y/SKILL.md (multi-segment)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md|../\1-\2/SKILL.md|g' "$f"

  # .claude/commands/aura:X.md → ../X/SKILL.md (single-segment)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z-]*\)\.md|../\1/SKILL.md|g' "$f"

  # .claude/commands/aura:*.md → skills/*/SKILL.md (wildcard)
  sed -i 's|\.claude/commands/aura:\*\.md|skills/*/SKILL.md|g' "$f"

  # .claude/commands/*.md → skills/*/SKILL.md (wildcard without aura: prefix)
  sed -i 's|\.claude/commands/\*\.md|skills/*/SKILL.md|g' "$f"

  # commands/aura:*.md → skills/*/SKILL.md
  sed -i 's|commands/aura:\*\.md|skills/*/SKILL.md|g' "$f"

  # commands/aura:X:Y.md → skills/X-Y/SKILL.md (multi-segment)
  sed -i 's|commands/aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md|skills/\1-\2/SKILL.md|g' "$f"

  # commands/aura:X.md → skills/X/SKILL.md (single-segment)
  sed -i 's|commands/aura:\([a-z][a-z-]*\)\.md|skills/\1/SKILL.md|g' "$f"

  # Generic .claude/commands/ → skills/
  sed -i 's|\.claude/commands/|skills/|g' "$f"

  # Generic commands/ directory ref → skills/ (only in directory listings)
  # Be careful: only replace "commands/" when it refers to the directory, not prose
  sed -i 's|`commands/`|`skills/`|g' "$f"
done
echo "  done"

# ── A5: File path refs in root files ──
# README.md and AGENTS.md stay at root, so paths are skills/X/SKILL.md

echo "A5: File path refs in root files"
for f in README.md AGENTS.md; do
  [[ -f "$f" ]] || continue

  # .claude/commands/aura:X:Y.md → skills/X-Y/SKILL.md (multi-segment)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z]*\):\([a-z][a-z-]*\)\.md|skills/\1-\2/SKILL.md|g' "$f"

  # .claude/commands/aura:X.md → skills/X/SKILL.md (single-segment)
  sed -i 's|\.claude/commands/aura:\([a-z][a-z-]*\)\.md|skills/\1/SKILL.md|g' "$f"

  # .claude/commands/aura:*.md → skills/*/SKILL.md (wildcard)
  sed -i 's|\.claude/commands/aura:\*\.md|skills/*/SKILL.md|g' "$f"

  # commands/aura:*.md → skills/*/SKILL.md
  sed -i 's|commands/aura:\*\.md|skills/*/SKILL.md|g' "$f"

  # Generic .claude/commands/ → skills/
  sed -i 's|\.claude/commands/|skills/|g' "$f"

  # Directory tree listings
  sed -i 's|commands/               # Slash commands.*|skills/                 # Plugin skills (SKILL.md per directory)|g' "$f"
  sed -i 's|commands/                  Slash commands.*|skills/                  Plugin skills (SKILL.md per directory)|g' "$f"
done
echo "  done"

# ── A6: Python script path updates ──
# aura-swarm and launch-parallel.py construct paths to .claude/commands/aura:{role}.md
# Update to look for skills/{role}/SKILL.md instead

echo "A6: Python script path updates"

# launch-parallel.py
if [[ -f "launch-parallel.py" ]]; then
  # Update path construction
  sed -i 's|\.claude/commands/aura:{role}\.md|skills/{role}/SKILL.md|g' "launch-parallel.py"
  sed -i "s|f\".claude/commands/aura:{role}.md\"|f\"skills/{role}/SKILL.md\"|g" "launch-parallel.py"
  sed -i "s|\.claude/commands/aura:{args\.role}\.md|skills/{args.role}/SKILL.md|g" "launch-parallel.py"

  # Update path construction using f-strings
  sed -i 's|f"\.claude/commands/aura:{role}\.md"|f"skills/{role}/SKILL.md"|g' "launch-parallel.py"

  # Update directory references in comments/help text
  sed -i 's|\.claude/commands/aura:{role}\.md|skills/{role}/SKILL.md|g' "launch-parallel.py"
  sed -i 's|~/.claude/commands/|skills/|g' "launch-parallel.py"
  sed -i 's|\.claude/commands/|skills/|g' "launch-parallel.py"

  # Update role file help text
  sed -i 's|loads from .claude/commands/aura:{role}.md|loads from skills/{role}/SKILL.md|g' "launch-parallel.py"
fi

# aura-swarm
if [[ -f "aura-swarm" ]]; then
  sed -i 's|\.claude/commands/aura:{role}\.md|skills/{role}/SKILL.md|g' "aura-swarm"
  sed -i 's|~/.claude/commands/|skills/|g' "aura-swarm"
  sed -i 's|\.claude/commands/|skills/|g' "aura-swarm"
fi

echo "  done"

# ── A7: Nix module updates ──
echo "A7: Nix module path references"
if [[ -f "nix/hm-module.nix" ]]; then
  sed -i 's|\.claude/commands/|skills/|g' "nix/hm-module.nix"
  sed -i 's|Slash commands|Plugin skills|g' "nix/hm-module.nix"
  sed -i 's|slash command .md files|skill SKILL.md files|g' "nix/hm-module.nix"
fi
echo "  done"

echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE B: Create directory structure and move files
# ══════════════════════════════════════════════════════════════════

echo "── Phase B: Create directories and move files ──"
echo ""

# ── B1: Create skill directories ──
echo "B1: Creating skill directories..."
for skill_name in $(echo "${NAME_MAP[@]}" | tr ' ' '\n' | sort); do
  mkdir -p "skills/$skill_name"
done
mkdir -p "skills/protocol"
echo "  Created ${#NAME_MAP[@]} skill directories + skills/protocol/"

# ── B2: Move command files → SKILL.md ──
echo "B2: Moving command files to skills/<name>/SKILL.md..."
for f in commands/aura:*.md; do
  base="$(basename "$f" .md)"
  stripped="${base#aura:}"
  skill_name="${NAME_MAP[$stripped]}"

  mv "$f" "skills/$skill_name/SKILL.md"
  echo "  $f → skills/$skill_name/SKILL.md"
done

# ── B3: Move protocol files → skills/protocol/ ──
echo "B3: Moving protocol files to skills/protocol/..."
for f in protocol/*; do
  [[ -f "$f" ]] || continue
  fname="$(basename "$f")"
  mv "$f" "skills/protocol/$fname"
  echo "  $f → skills/protocol/$fname"
done

# ── B4: Clean up empty directories ──
echo "B4: Cleaning up empty directories..."
rmdir commands 2>/dev/null && echo "  Removed empty commands/" || echo "  commands/ not empty, skipping"
rmdir protocol 2>/dev/null && echo "  Removed empty protocol/" || echo "  protocol/ not empty, skipping"

echo ""

# ══════════════════════════════════════════════════════════════════
# PHASE C: Set up scripts/ directory
# ══════════════════════════════════════════════════════════════════

echo "── Phase C: Set up scripts/ ──"
echo ""

mkdir -p scripts

# ── C1: Move aura-swarm to scripts/ ──
if [[ -f "aura-swarm" ]]; then
  mv "aura-swarm" "scripts/aura-swarm"
  chmod +x "scripts/aura-swarm"
  echo "C1: aura-swarm → scripts/aura-swarm"
fi

# ── C2: Rename launch-parallel.py → scripts/aura-parallel ──
if [[ -f "launch-parallel.py" ]]; then
  mv "launch-parallel.py" "scripts/aura-parallel"
  chmod +x "scripts/aura-parallel"
  # Ensure proper shebang (should already have #!/usr/bin/env python3)
  if ! head -1 "scripts/aura-parallel" | grep -q '^#!'; then
    sed -i '1i#!/usr/bin/env python3' "scripts/aura-parallel"
  fi
  echo "C2: launch-parallel.py → scripts/aura-parallel"
fi

echo ""

# ══════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════

echo "=== Migration complete ==="
echo ""
echo "New structure:"
echo "  skills/           — ${#NAME_MAP[@]} skill directories + protocol/"
echo "  scripts/          — aura-swarm, aura-parallel"
echo ""
echo "Next steps:"
echo "  1. Verify: grep -r '.claude/commands/' skills/ scripts/ *.md"
echo "  2. Create skills/swarm/SKILL.md and skills/parallel/SKILL.md"
echo "  3. Create skills/protocol/SKILL.md"
echo "  4. Create .claude-plugin/plugin.json and marketplace.json"
echo "  5. Commit with: git agent-commit -m 'feat(plugin): migrate commands to skills layout'"
