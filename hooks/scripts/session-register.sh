#!/usr/bin/env bash
# Called on SessionStart. Registers this Claude session with the active epoch.
# Exits silently if AURA_EPOCH_ID is not set.
set -euo pipefail
if [[ -z "${AURA_EPOCH_ID:-}" ]]; then
    exit 0
fi
SESSION_ID="${CLAUDE_SESSION_ID:-$(uuidgen)}"
aura-msg session register --epoch-id "$AURA_EPOCH_ID" --session-id "$SESSION_ID" --role "${AURA_ROLE:-worker}" || true
aura-msg query state --epoch-id "$AURA_EPOCH_ID" --format text || true
