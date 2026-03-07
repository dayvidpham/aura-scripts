"""Tests for aura_protocol.formatters and aura-msg query state (SLICE-3-L2).

BDD Acceptance Criteria:
    AC-F1: QueryStateResult has all 7 fields including active_session_count=0.
    AC-F2: format_epoch_state(result, "json") outputs valid JSON with all fields.
    AC-F3: format_epoch_state(result, "text") outputs human-readable text.
    AC-F4: format_start_result outputs workflow_id and run_id in both formats.
    AC-F5: format_signal_result outputs success/failure in both formats.
    AC-E1: aura-msg query state with bogus --server-address exits 2.
    AC-E2: aura-msg query state --epoch-id nonexistent exits 3.

DI approach:
    - QueryStateResult: direct construction, no mocks.
    - Formatters: pure functions, tested directly.
    - Exit codes: subprocess integration tests against bin/aura-msg.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aura_protocol.state_machine import TransitionRecord
from aura_protocol.types import PhaseId, ReviewAxis, RoleId, Transition, VoteType
from aura_protocol.workflow import QueryStateResult
from aura_protocol.formatters import (
    format_epoch_state,
    format_start_result,
    format_signal_result,
)

# ─── Constants ─────────────────────────────────────────────────────────────────

AURA_MSG_PATH = Path(__file__).parent.parent / "bin" / "aura-msg"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
PYTHON = sys.executable


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_result() -> QueryStateResult:
    """A representative QueryStateResult for formatter tests."""
    return QueryStateResult(
        current_phase=PhaseId.P4_REVIEW,
        current_role=RoleId.REVIEWER,
        transition_history=[
            TransitionRecord(
                from_phase=PhaseId.P1_REQUEST,
                to_phase=PhaseId.P2_ELICIT,
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                triggered_by="architect",
                condition_met="classification confirmed",
            ),
        ],
        votes={ReviewAxis.CORRECTNESS: VoteType.ACCEPT},
        last_error=None,
        available_transitions=[
            Transition(to_phase=PhaseId.P5_UAT, condition="all 3 vote ACCEPT"),
            Transition(to_phase=PhaseId.P3_PROPOSE, condition="any REVISE"),
        ],
        active_session_count=0,
    )


# ─── QueryStateResult Type Tests ──────────────────────────────────────────────


class TestQueryStateResult:
    """AC-F1: QueryStateResult has correct fields and defaults."""

    def test_all_seven_fields_present(self) -> None:
        fields = list(QueryStateResult.__dataclass_fields__.keys())
        assert fields == [
            "current_phase",
            "current_role",
            "transition_history",
            "votes",
            "last_error",
            "available_transitions",
            "active_session_count",
        ]

    def test_active_session_count_default_zero(self) -> None:
        result = QueryStateResult(
            current_phase=PhaseId.P1_REQUEST,
            current_role=RoleId.EPOCH,
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        assert result.active_session_count == 0

    def test_is_frozen(self) -> None:
        result = QueryStateResult(
            current_phase=PhaseId.P1_REQUEST,
            current_role=RoleId.EPOCH,
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        with pytest.raises(AttributeError):
            result.current_phase = PhaseId.P2_ELICIT  # type: ignore[misc]

    def test_votes_sourced_from_review_votes(self, sample_result: QueryStateResult) -> None:
        """D20: votes field contains ReviewAxis keys (from state.review_votes)."""
        assert ReviewAxis.CORRECTNESS in sample_result.votes
        assert sample_result.votes[ReviewAxis.CORRECTNESS] == VoteType.ACCEPT


# ─── Formatter Tests ──────────────────────────────────────────────────────────


class TestFormatEpochState:
    """AC-F2, AC-F3: format_epoch_state in json and text formats."""

    def test_json_output_is_valid_json(self, sample_result: QueryStateResult) -> None:
        output = format_epoch_state(sample_result, "json")
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_contains_all_fields(self, sample_result: QueryStateResult) -> None:
        output = format_epoch_state(sample_result, "json")
        data = json.loads(output)
        assert data["current_phase"] == "p4"
        assert data["current_role"] == "reviewer"
        assert data["last_error"] is None
        assert data["active_session_count"] == 0
        assert isinstance(data["transition_history"], list)
        assert len(data["transition_history"]) == 1
        assert isinstance(data["votes"], dict)
        assert data["votes"]["correctness"] == "ACCEPT"
        assert isinstance(data["available_transitions"], list)
        assert len(data["available_transitions"]) == 2

    def test_text_output_contains_phase_and_role(
        self, sample_result: QueryStateResult
    ) -> None:
        output = format_epoch_state(sample_result, "text")
        assert "p4" in output
        assert "reviewer" in output

    def test_text_output_contains_votes(
        self, sample_result: QueryStateResult
    ) -> None:
        output = format_epoch_state(sample_result, "text")
        assert "correctness" in output.lower() or "CORRECTNESS" in output
        assert "ACCEPT" in output

    def test_json_transition_history_fields(
        self, sample_result: QueryStateResult
    ) -> None:
        output = format_epoch_state(sample_result, "json")
        data = json.loads(output)
        rec = data["transition_history"][0]
        assert rec["from_phase"] == "p1"
        assert rec["to_phase"] == "p2"
        assert rec["triggered_by"] == "architect"
        assert rec["success"] is True

    def test_text_with_last_error(self) -> None:
        result = QueryStateResult(
            current_phase=PhaseId.P3_PROPOSE,
            current_role=RoleId.ARCHITECT,
            transition_history=[],
            votes={},
            last_error="Something went wrong",
            available_transitions=[],
        )
        output = format_epoch_state(result, "text")
        assert "Something went wrong" in output


class TestFormatStartResult:
    """AC-F4: format_start_result outputs workflow_id and run_id."""

    def test_json_output(self) -> None:
        output = format_start_result("wf-123", "run-456", "json")
        data = json.loads(output)
        assert data["workflow_id"] == "wf-123"
        assert data["run_id"] == "run-456"

    def test_text_output(self) -> None:
        output = format_start_result("wf-123", "run-456", "text")
        assert "wf-123" in output
        assert "run-456" in output


class TestFormatSignalResult:
    """AC-F5: format_signal_result outputs success/failure."""

    def test_json_success(self) -> None:
        output = format_signal_result(True, "json")
        data = json.loads(output)
        assert data["success"] is True

    def test_json_failure(self) -> None:
        output = format_signal_result(False, "json")
        data = json.loads(output)
        assert data["success"] is False

    def test_text_success(self) -> None:
        output = format_signal_result(True, "text")
        assert "success" in output.lower() or "ok" in output.lower()

    def test_text_failure(self) -> None:
        output = format_signal_result(False, "text")
        assert "fail" in output.lower() or "error" in output.lower()


# ─── Integration Tests: Exit Codes ────────────────────────────────────────────


class TestAuraMsgExitCodes:
    """AC-E1, AC-E2: subprocess integration tests for exit codes 2 and 3."""

    def test_connection_error_exits_2(self) -> None:
        """AC-E1: bogus --server-address → exit 2."""
        result = subprocess.run(
            [
                PYTHON,
                str(AURA_MSG_PATH),
                "query",
                "state",
                "--epoch-id",
                "test-epoch",
                "--server-address",
                "localhost:1",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert result.returncode == 2, (
            f"Expected exit 2 for connection error, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "connection error" in result.stderr.lower()

    def test_workflow_not_found_exits_3(self) -> None:
        """AC-E2: nonexistent epoch-id → exit 3 (requires Temporal server)."""
        result = subprocess.run(
            [
                PYTHON,
                str(AURA_MSG_PATH),
                "query",
                "state",
                "--epoch-id",
                "nonexistent-epoch-99999",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert result.returncode == 3, (
            f"Expected exit 3 for workflow error, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "workflow" in result.stderr.lower() or "not found" in result.stderr.lower()
