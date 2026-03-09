"""Output formatters for aura-msg CLI results.

Provides format_epoch_state(), format_start_result(), and format_signal_result()
for JSON and human-readable text output.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from aura_protocol.types import OutputFormat

if TYPE_CHECKING:
    from aura_protocol.workflow import QueryStateResult


def format_epoch_state(result: QueryStateResult, fmt: OutputFormat) -> str:
    """Format a QueryStateResult for CLI output.

    Args:
        result: QueryStateResult from EpochWorkflow.full_state() query.
        fmt: Output format enum — OutputFormat.Json or OutputFormat.Text.

    Returns:
        Formatted string for stdout.
    """
    if fmt == OutputFormat.Json:
        data = {
            "current_phase": result.current_phase.value,
            "current_role": result.current_role.value,
            "transition_history": [
                {
                    "from_phase": r.from_phase.value,
                    "to_phase": r.to_phase.value,
                    "timestamp": r.timestamp.isoformat(),
                    "triggered_by": r.triggered_by,
                    "condition_met": r.condition_met,
                    "success": r.success,
                }
                for r in result.transition_history
            ],
            "votes": {
                axis.value: vote.value
                for axis, vote in result.votes.items()
            },
            "last_error": result.last_error,
            "available_transitions": [
                {
                    "to_phase": t.to_phase.value,
                    "condition": t.condition,
                }
                for t in result.available_transitions
            ],
            "active_session_count": result.active_session_count,
        }
        return json.dumps(data, indent=2)

    # text format
    lines = [
        f"Phase: {result.current_phase.value}",
        f"Role:  {result.current_role.value}",
    ]

    if result.votes:
        vote_strs = [
            f"  {axis.value}: {vote.value}"
            for axis, vote in result.votes.items()
        ]
        lines.append("Votes:")
        lines.extend(vote_strs)
    else:
        lines.append("Votes: (none)")

    if result.last_error:
        lines.append(f"Last Error: {result.last_error}")

    if result.available_transitions:
        lines.append("Available Transitions:")
        for t in result.available_transitions:
            lines.append(f"  -> {t.to_phase.value} ({t.condition})")

    lines.append(f"Transitions: {len(result.transition_history)}")
    lines.append(f"Active Sessions: {result.active_session_count}")

    return "\n".join(lines)


def format_start_result(workflow_id: str, run_id: str, fmt: OutputFormat) -> str:
    """Format an epoch start result for CLI output.

    Args:
        workflow_id: Temporal workflow ID of the started epoch.
        run_id: Temporal run ID of the started epoch.
        fmt: Output format enum — OutputFormat.Json or OutputFormat.Text.

    Returns:
        Formatted string for stdout.
    """
    if fmt == OutputFormat.Json:
        return json.dumps({"workflow_id": workflow_id, "run_id": run_id}, indent=2)
    return f"Started epoch: workflow_id={workflow_id}, run_id={run_id}"


def format_signal_result(success: bool, fmt: OutputFormat) -> str:
    """Format a signal result for CLI output.

    Args:
        success: Whether the signal was delivered successfully.
        fmt: Output format enum — OutputFormat.Json or OutputFormat.Text.

    Returns:
        Formatted string for stdout.
    """
    if fmt == OutputFormat.Json:
        return json.dumps({"success": success})
    return "Signal delivered successfully" if success else "Signal delivery failed"
