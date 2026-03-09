#!/usr/bin/env bash
# Called on SessionStart. Registers this Claude session with the active epoch.
# Exits 0 even on failure — hooks must not block the session.
# Error reporting is handled by aura-msg (structured via report_error).
set -euo pipefail
if [[ -z "${AURA_EPOCH_ID:-}" ]]; then
    exit 0
fi
SESSION_ID="${CLAUDE_SESSION_ID:-$(uuidgen)}"

aura-msg session register \
    --epoch-id "$AURA_EPOCH_ID" \
    --session-id "$SESSION_ID" \
    --role "${AURA_ROLE:-worker}" \
    --model-harness "${AURA_MODEL_HARNESS:-claude-code}" \
    --model "${CLAUDE_MODEL:-unknown}" || exit 0

aura-msg query state --epoch-id "$AURA_EPOCH_ID" --format text 2>/dev/null || true
