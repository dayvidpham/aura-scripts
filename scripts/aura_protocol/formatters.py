"""Output formatters for aura-msg CLI (SLICE-3).

Three formatter functions, each supporting 'json' and 'text' output formats.
These are the CLI-facing presentation layer — they do not access Temporal.

Functions:
    format_epoch_state(result, fmt)   — format QueryStateResult for query-state
    format_start_result(workflow_id, run_id, fmt) — format epoch start output
    format_signal_result(success, fmt) — format signal send output
"""

from __future__ import annotations

import json


def format_epoch_state(result: object, fmt: str = "json") -> str:
    """Format a QueryStateResult for aura-msg query-state output.

    Args:
        result: QueryStateResult instance with current epoch state.
        fmt:    Output format — "json" (default) or "text".

    Returns:
        Formatted string representation of the epoch state.
    """
    ...


def format_start_result(workflow_id: str, run_id: str, fmt: str = "json") -> str:
    """Format the result of aura-msg epoch start for CLI output.

    Args:
        workflow_id: The Temporal workflow ID of the started epoch.
        run_id:      The Temporal run ID of the started epoch.
        fmt:         Output format — "json" (default) or "text".

    Returns:
        Formatted string with workflow_id and run_id.
    """
    ...


def format_signal_result(success: bool, fmt: str = "json") -> str:
    """Format the result of a signal send (vote, advance-phase) for CLI output.

    Args:
        success: True if the signal was accepted, False otherwise.
        fmt:     Output format — "json" (default) or "text".

    Returns:
        Formatted string indicating success or failure.
    """
    ...
