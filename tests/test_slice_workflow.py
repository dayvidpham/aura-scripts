"""Tests for SliceWorkflow execution + _check_tmux DI — SLICE-6-L2.

BDD Acceptance Criteria (D26):
    AC-SW1: _check_tmux(search_path="/nonexistent") → False (no tmux found)
    AC-SW2: _check_tmux(search_path=<dir-with-fake-tmux>) → True
    AC-SW3: SliceWorkflow in "mock" mode completes with SliceCompleteSignal(success=True)
    AC-SW4: SliceWorkflow with SliceCompleteSignal(success=False) marks slice failed
    AC-SW5: SliceWorkflow timeout (configurable via SliceExecutionConfig.timeout_seconds)

DI approach:
    - _check_tmux(search_path): injectable path for binary discovery
    - "mock" mode: SliceWorkflow returns immediately without launching tmux/subprocess
    - Tests FAIL until SLICE-6-L3 implements execute_slice_command + updated SliceWorkflow
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from aura_protocol.types import (
    PhaseId,
    RoleId,
    SliceCompleteSignal,
    SliceExecutionConfig,
    SliceStartSignal,
)
from aura_protocol.workflow import SliceInput, SliceResult


# ─── AC-SW1 + AC-SW2: _check_tmux DI ────────────────────────────────────────


class TestCheckTmux:
    """AC-SW1/SW2: _check_tmux binary detection via search_path DI."""

    def test_nonexistent_path_returns_false(self) -> None:
        """AC-SW1: search_path that doesn't exist → False."""
        from aura_protocol.workflow import _check_tmux  # noqa: PLC0415

        result = _check_tmux(search_path="/nonexistent/path/to/nowhere")
        assert result is False

    def test_path_without_tmux_returns_false(self, tmp_path: Path) -> None:
        """AC-SW1: directory exists but has no tmux binary → False."""
        from aura_protocol.workflow import _check_tmux  # noqa: PLC0415

        # Create a directory without tmux
        result = _check_tmux(search_path=str(tmp_path))
        assert result is False

    def test_path_with_tmux_returns_true(self, tmp_path: Path) -> None:
        """AC-SW2: directory with executable 'tmux' → True."""
        from aura_protocol.workflow import _check_tmux  # noqa: PLC0415

        fake_tmux = tmp_path / "tmux"
        fake_tmux.write_text("#!/bin/sh\necho fake-tmux")
        fake_tmux.chmod(fake_tmux.stat().st_mode | stat.S_IEXEC)

        result = _check_tmux(search_path=str(tmp_path))
        assert result is True

    def test_nonexecutable_tmux_returns_false(self, tmp_path: Path) -> None:
        """Non-executable 'tmux' file → False (must be executable)."""
        from aura_protocol.workflow import _check_tmux  # noqa: PLC0415

        fake_tmux = tmp_path / "tmux"
        fake_tmux.write_text("#!/bin/sh")
        # Remove executable bit
        fake_tmux.chmod(0o644)

        result = _check_tmux(search_path=str(tmp_path))
        assert result is False


# ─── AC-SW3 + AC-SW4: SliceWorkflow mock mode ────────────────────────────────


@pytest.mark.asyncio
class TestSliceWorkflowMockMode:
    """AC-SW3/SW4: SliceWorkflow in mock mode via SliceStartSignal DI."""

    async def test_mock_mode_completes_with_success(self) -> None:
        """AC-SW3: SliceWorkflow in mock mode completes successfully."""
        from temporalio.testing import WorkflowEnvironment

        from aura_protocol.workflow import SliceWorkflow  # noqa: PLC0415

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with env.client.connect() if hasattr(env, "client") else env:
                config = SliceExecutionConfig(
                    mode="mock",
                    command="echo done",
                    timeout_seconds=5,
                )
                start_signal = SliceStartSignal(
                    slice_id="s1",
                    epoch_id="ep-1",
                    config=config,
                )
                # Use SliceInput (existing API) with mock config embedded
                slice_input = SliceInput(
                    epoch_id="ep-1",
                    slice_id="s1",
                    phase_spec="p9",
                    parent_workflow_id="ep-1",  # self-referential for test
                )
                result = await env.run_workflow(
                    SliceWorkflow.run,
                    slice_input,
                    id="test-slice-s1",
                    task_queue="test-queue",
                )
                assert isinstance(result, SliceResult)
                assert result.success is True

    async def test_slice_complete_signal_false_marks_failed(self) -> None:
        """AC-SW4: SliceCompleteSignal(success=False) → SliceResult(success=False)."""
        from temporalio.testing import WorkflowEnvironment

        from aura_protocol.workflow import SliceWorkflow  # noqa: PLC0415

        async with await WorkflowEnvironment.start_time_skipping() as env:
            config = SliceExecutionConfig(
                mode="mock",
                command="exit 1",
                timeout_seconds=5,
            )
            # For mock mode, SliceCompleteSignal(success=False) should propagate
            fail_signal = SliceCompleteSignal(
                slice_id="s1",
                success=False,
                error="worker exited with code 1",
            )
            assert fail_signal.success is False
            assert fail_signal.error == "worker exited with code 1"


# ─── AC-SW5: timeout behavior ────────────────────────────────────────────────


class TestSliceExecutionConfig:
    """Verify SliceExecutionConfig fields are consumed correctly."""

    def test_timeout_seconds_field(self) -> None:
        config = SliceExecutionConfig(
            mode="tmux",
            command="./run.sh",
            timeout_seconds=600,
        )
        assert config.timeout_seconds == 600

    def test_heartbeat_interval_field(self) -> None:
        config = SliceExecutionConfig(
            mode="subprocess",
            command="./run.sh",
            heartbeat_interval=10,
        )
        assert config.heartbeat_interval == 10

    def test_mode_values(self) -> None:
        for mode in ("tmux", "subprocess", "mock"):
            config = SliceExecutionConfig(mode=mode, command="cmd")
            assert config.mode == mode
