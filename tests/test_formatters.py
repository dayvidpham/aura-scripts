"""Tests for aura_protocol.formatters and aura-msg query state (SLICE-3-L2).

BDD Acceptance Criteria:
    AC-F1: QueryStateResult has all 7 fields including active_session_count=0.
    AC-F2: format_epoch_state(result, "json") outputs valid JSON with all fields.
    AC-F3: format_epoch_state(result, OutputFormat.Text) outputs human-readable text.
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
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aura_protocol.state_machine import TransitionRecord
from aura_protocol.types import OutputFormat, PhaseId, ReviewAxis, RoleId, Transition, VoteType
from aura_protocol.workflow import EpochWorkflow, QueryStateResult
from aura_protocol.formatters import (
    format_epoch_state,
    format_start_result,
    format_signal_result,
)

# ─── Constants ─────────────────────────────────────────────────────────────────

AURA_MSG_PATH = Path(__file__).parent.parent / "bin" / "aura-msg"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
PYTHON = sys.executable


def _test_env() -> dict[str, str]:
    """Curated env for subprocess tests."""
    env = {"PYTHONPATH": str(SCRIPTS_DIR)}
    for key in ("HOME", "PATH", "VIRTUAL_ENV", "PYTHONHOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _temporal_reachable() -> bool:
    """Check if a Temporal server is reachable at localhost:7233."""
    try:
        s = socket.create_connection(("localhost", 7233), timeout=1)
        s.close()
        return True
    except OSError:
        return False


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_result() -> QueryStateResult:
    """A representative QueryStateResult for formatter tests."""
    return QueryStateResult(
        current_phase=PhaseId.P4_Review,
        current_role=RoleId.Reviewer,
        transition_history=[
            TransitionRecord(
                from_phase=PhaseId.P1_Request,
                to_phase=PhaseId.P2_Elicit,
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                triggered_by="architect",
                condition_met="classification confirmed",
            ),
        ],
        votes={ReviewAxis.Correctness: VoteType.Accept},
        last_error=None,
        available_transitions=[
            Transition(to_phase=PhaseId.P5_Uat, condition="all 3 vote ACCEPT"),
            Transition(to_phase=PhaseId.P3_Propose, condition="any REVISE"),
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
            current_phase=PhaseId.P1_Request,
            current_role=RoleId.Epoch,
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        assert result.active_session_count == 0

    def test_is_frozen(self) -> None:
        result = QueryStateResult(
            current_phase=PhaseId.P1_Request,
            current_role=RoleId.Epoch,
            transition_history=[],
            votes={},
            last_error=None,
            available_transitions=[],
        )
        with pytest.raises(AttributeError):
            result.current_phase = PhaseId.P2_Elicit  # type: ignore[misc]

    def test_votes_sourced_from_review_votes(self, sample_result: QueryStateResult) -> None:
        """D20: votes field contains ReviewAxis keys (from state.review_votes)."""
        assert ReviewAxis.Correctness in sample_result.votes
        assert sample_result.votes[ReviewAxis.Correctness] == VoteType.Accept


# ─── Formatter Tests ──────────────────────────────────────────────────────────


class TestFormatEpochState:
    """AC-F2, AC-F3: format_epoch_state in json and text formats."""

    def test_json_output_is_valid_json(self, sample_result: QueryStateResult) -> None:
        output = format_epoch_state(sample_result, OutputFormat.Json)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_contains_all_fields(self, sample_result: QueryStateResult) -> None:
        output = format_epoch_state(sample_result, OutputFormat.Json)
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
        output = format_epoch_state(sample_result, OutputFormat.Text)
        assert "p4" in output
        assert "reviewer" in output

    def test_text_output_contains_votes(
        self, sample_result: QueryStateResult
    ) -> None:
        output = format_epoch_state(sample_result, OutputFormat.Text)
        assert "correctness" in output.lower() or "CORRECTNESS" in output
        assert "ACCEPT" in output

    def test_json_transition_history_fields(
        self, sample_result: QueryStateResult
    ) -> None:
        output = format_epoch_state(sample_result, OutputFormat.Json)
        data = json.loads(output)
        rec = data["transition_history"][0]
        assert rec["from_phase"] == "p1"
        assert rec["to_phase"] == "p2"
        assert rec["triggered_by"] == "architect"
        assert rec["success"] is True

    def test_text_with_last_error(self) -> None:
        result = QueryStateResult(
            current_phase=PhaseId.P3_Propose,
            current_role=RoleId.Architect,
            transition_history=[],
            votes={},
            last_error="Something went wrong",
            available_transitions=[],
        )
        output = format_epoch_state(result, OutputFormat.Text)
        assert "Something went wrong" in output


class TestFormatStartResult:
    """AC-F4: format_start_result outputs workflow_id and run_id."""

    def test_json_output(self) -> None:
        output = format_start_result("wf-123", "run-456", OutputFormat.Json)
        data = json.loads(output)
        assert data["workflow_id"] == "wf-123"
        assert data["run_id"] == "run-456"

    def test_text_output(self) -> None:
        output = format_start_result("wf-123", "run-456", OutputFormat.Text)
        assert "wf-123" in output
        assert "run-456" in output


class TestFormatSignalResult:
    """AC-F5: format_signal_result outputs success/failure."""

    def test_json_success(self) -> None:
        output = format_signal_result(True, OutputFormat.Json)
        data = json.loads(output)
        assert data["success"] is True

    def test_json_failure(self) -> None:
        output = format_signal_result(False, OutputFormat.Json)
        data = json.loads(output)
        assert data["success"] is False

    def test_text_success(self) -> None:
        output = format_signal_result(True, OutputFormat.Text)
        assert "success" in output.lower() or "ok" in output.lower()

    def test_text_failure(self) -> None:
        output = format_signal_result(False, OutputFormat.Text)
        assert "fail" in output.lower() or "error" in output.lower()


# ─── full_state() Production Path (I-3.2) ─────────────────────────────────────


class TestFullStateToQueryStateResult:
    """I-3.2: Verify full_state() produces a QueryStateResult via production path."""

    def test_full_state_returns_query_state_result(self) -> None:
        """full_state() constructs QueryStateResult from EpochStateMachine state."""
        from aura_protocol.state_machine import EpochStateMachine

        wf = EpochWorkflow()
        wf._sm = EpochStateMachine("test-epoch")
        result = wf.full_state()
        assert isinstance(result, QueryStateResult)
        assert result.current_phase == PhaseId.P1_Request
        assert result.active_session_count == 0
        assert result.transition_history == []
        assert result.votes == {}
        assert result.last_error is None
        assert isinstance(result.available_transitions, list)

    def test_full_state_reflects_review_votes(self) -> None:
        """D20: full_state().votes sourced from state.review_votes, not state.votes."""
        from aura_protocol.state_machine import EpochStateMachine

        wf = EpochWorkflow()
        wf._sm = EpochStateMachine("test-epoch")
        wf._sm.state.review_votes[ReviewAxis.Correctness] = VoteType.Accept
        result = wf.full_state()
        assert result.votes == {ReviewAxis.Correctness: VoteType.Accept}


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
            env=_test_env(),
        )
        assert result.returncode == 2, (
            f"Expected exit 2 for connection error, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "connection error" in result.stderr.lower()

    @pytest.mark.skipif(
        not _temporal_reachable(),
        reason="requires live Temporal server at localhost:7233",
    )
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
            env=_test_env(),
        )
        assert result.returncode == 3, (
            f"Expected exit 3 for workflow error, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "workflow" in result.stderr.lower() or "not found" in result.stderr.lower()
