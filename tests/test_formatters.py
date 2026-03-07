"""Tests for aura_protocol.formatters and aura-msg query state — SLICE-3-L2.

BDD Acceptance Criteria:
    AC-F1: QueryStateResult has all required fields including active_session_count=0
    AC-F2: format_epoch_state json output contains required fields
    AC-F3: format_epoch_state text output is human-readable (non-JSON string)
    AC-F4: aura-msg query state with bogus server exits 2 (connection error)
    AC-F5: aura-msg query state with nonexistent epoch exits 3 (workflow not found)

Note: AC-F4 and AC-F5 FAIL until SLICE-3-L3 implements full_state query + aura-msg subcommand.
AC-F2 and AC-F3 FAIL until SLICE-3-L3 implements format_epoch_state.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aura_protocol.workflow import QueryStateResult
from aura_protocol.formatters import (
    format_epoch_state,
    format_start_result,
    format_signal_result,
)

AURA_MSG_PATH = Path(__file__).parent.parent / "bin" / "aura-msg"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


# ── AC-F1: QueryStateResult fields ───────────────────────────────────────────


class TestQueryStateResult:
    """AC-F1: QueryStateResult has all required fields."""

    def test_all_fields_present(self) -> None:
        r = QueryStateResult(
            current_phase="p9",
            current_role="worker",
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
            active_session_count=0,
        )
        assert r.current_phase == "p9"
        assert r.current_role == "worker"
        assert r.transition_history == []
        assert r.votes == {}
        assert r.last_error is None
        assert r.available_transitions == []
        assert r.active_session_count == 0

    def test_active_session_count_defaults_to_zero(self) -> None:
        r = QueryStateResult(
            current_phase="p1",
            current_role="epoch",
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        assert r.active_session_count == 0

    def test_frozen(self) -> None:
        r = QueryStateResult(
            current_phase="p9",
            current_role="worker",
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        with pytest.raises((TypeError, AttributeError)):
            r.current_phase = "p10"  # type: ignore[misc]

    def test_last_error_can_be_string(self) -> None:
        r = QueryStateResult(
            current_phase="p9",
            current_role="worker",
            transition_history=[],
            votes={},
            last_error="constraint violation",
            available_transitions=[],
        )
        assert r.last_error == "constraint violation"


# ── AC-F2 + AC-F3: format_epoch_state ────────────────────────────────────────


class TestFormatEpochState:
    """AC-F2: json output has required fields; AC-F3: text is human-readable."""

    @pytest.fixture
    def sample_result(self) -> QueryStateResult:
        return QueryStateResult(
            current_phase="p9",
            current_role="worker",
            transition_history=[],
            votes={"correctness": "accept"},
            last_error=None,
            available_transitions=[],
            active_session_count=2,
        )

    def test_json_output_is_valid_json(self, sample_result: QueryStateResult) -> None:
        out = format_epoch_state(sample_result, fmt="json")
        # Should parse as JSON without error
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_json_output_has_required_fields(self, sample_result: QueryStateResult) -> None:
        out = format_epoch_state(sample_result, fmt="json")
        data = json.loads(out)
        assert "current_phase" in data
        assert "current_role" in data
        assert "active_session_count" in data
        assert data["current_phase"] == "p9"
        assert data["active_session_count"] == 2

    def test_text_output_is_string(self, sample_result: QueryStateResult) -> None:
        out = format_epoch_state(sample_result, fmt="text")
        assert isinstance(out, str)
        assert len(out) > 0

    def test_text_output_not_json(self, sample_result: QueryStateResult) -> None:
        out = format_epoch_state(sample_result, fmt="text")
        # Text format should not be raw JSON
        try:
            json.loads(out)
            # If it parses as JSON, it's not in "text" mode
            pytest.fail("text output should not be JSON")
        except (json.JSONDecodeError, ValueError):
            pass  # Expected — text is not JSON


class TestFormatStartResult:
    def test_json_output(self) -> None:
        out = format_start_result("wf-123", "run-abc", fmt="json")
        data = json.loads(out)
        assert data["workflow_id"] == "wf-123"
        assert data["run_id"] == "run-abc"

    def test_text_output(self) -> None:
        out = format_start_result("wf-123", "run-abc", fmt="text")
        assert isinstance(out, str)
        assert "wf-123" in out


class TestFormatSignalResult:
    def test_json_success(self) -> None:
        out = format_signal_result(True, fmt="json")
        data = json.loads(out)
        assert data["success"] is True

    def test_json_failure(self) -> None:
        out = format_signal_result(False, fmt="json")
        data = json.loads(out)
        assert data["success"] is False

    def test_text_output(self) -> None:
        out = format_signal_result(True, fmt="text")
        assert isinstance(out, str)


# ── AC-F4 + AC-F5: aura-msg subprocess exit codes ────────────────────────────


def _run_aura_msg(*args: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run aura-msg as a subprocess with PYTHONPATH set to scripts/."""
    return subprocess.run(
        [sys.executable, str(AURA_MSG_PATH), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(SCRIPTS_DIR),
        },
    )


class TestAuraMsgQueryStateExitCodes:
    """AC-F4: connection error → exit 2; AC-F5: not found → exit 3."""

    @pytest.mark.xfail(
        reason="Not implemented until SLICE-3-L3 implements full_state query",
        strict=False,
    )
    def test_bogus_server_exits_2(self) -> None:
        """AC-F4: aura-msg query state with unreachable server → exit 2."""
        result = _run_aura_msg(
            "query", "state",
            "--epoch-id", "test-epoch",
            "--server-address", "localhost:1",
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (connection error), got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    @pytest.mark.xfail(
        reason="Not implemented until SLICE-3-L3 implements full_state query",
        strict=False,
    )
    def test_nonexistent_epoch_exits_3(self) -> None:
        """AC-F5: aura-msg query state with nonexistent epoch → exit 3."""
        result = _run_aura_msg(
            "query", "state",
            "--epoch-id", "nonexistent-epoch-xyzzy-99999",
            "--server-address", "localhost:7233",
        )
        assert result.returncode == 3, (
            f"Expected exit 3 (workflow not found), got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
