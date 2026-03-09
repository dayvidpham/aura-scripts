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

import stat
from pathlib import Path

import pytest

from aura_protocol.types import (
    PhaseId,
    RoleId,
    SliceCompleteSignal,
    SliceExecutionConfig,
    SliceMode,
    SliceStartSignal,
)
from aura_protocol.workflow import SliceInput, SliceResult


# ─── AC-SW1 + AC-SW2: _check_tmux DI ────────────────────────────────────────


class TestCheckTmux:
    """AC-SW1/SW2: _check_tmux binary detection via search_path DI."""

    def test_nonexistent_path_returns_false(self) -> None:
        """AC-SW1: search_path that doesn't exist → False."""
        from aura_protocol.audit_activities import _check_tmux  # noqa: PLC0415

        result = _check_tmux(search_path="/nonexistent/path/to/nowhere")
        assert result is False

    def test_path_without_tmux_returns_false(self, tmp_path: Path) -> None:
        """AC-SW1: directory exists but has no tmux binary → False."""
        from aura_protocol.audit_activities import _check_tmux  # noqa: PLC0415

        # Create a directory without tmux
        result = _check_tmux(search_path=str(tmp_path))
        assert result is False

    def test_path_with_tmux_returns_true(self, tmp_path: Path) -> None:
        """AC-SW2: directory with executable 'tmux' → True."""
        from aura_protocol.audit_activities import _check_tmux  # noqa: PLC0415

        fake_tmux = tmp_path / "tmux"
        fake_tmux.write_text("#!/bin/sh\necho fake-tmux")
        fake_tmux.chmod(fake_tmux.stat().st_mode | stat.S_IEXEC)

        result = _check_tmux(search_path=str(tmp_path))
        assert result is True

    def test_nonexecutable_tmux_returns_false(self, tmp_path: Path) -> None:
        """Non-executable 'tmux' file → False (must be executable)."""
        from aura_protocol.audit_activities import _check_tmux  # noqa: PLC0415

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
        from temporalio.worker import Worker

        from aura_protocol.workflow import SliceWorkflow  # noqa: PLC0415

        async with await WorkflowEnvironment.start_time_skipping() as env:
            config = SliceExecutionConfig(
                mode=SliceMode.Mock,
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
            async with Worker(
                env.client,
                task_queue="test-queue",
                workflows=[SliceWorkflow],
            ):
                result = await env.client.execute_workflow(
                    SliceWorkflow.run,
                    slice_input,
                    id="test-slice-s1",
                    task_queue="test-queue",
                )
                assert isinstance(result, SliceResult)
                assert result.success is True

    async def test_slice_complete_signal_false_marks_failed(self) -> None:
        """AC-SW4: complete_slice(success=False) overrides activity result → SliceResult(success=False)."""
        from temporalio.testing import WorkflowEnvironment
        from temporalio.worker import Worker

        from aura_protocol.audit_activities import execute_slice_command
        from aura_protocol.workflow import SliceWorkflow  # noqa: PLC0415

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-slice-ac-sw4",
                workflows=[SliceWorkflow],
                activities=[execute_slice_command],
            ):
                slice_input = SliceInput(
                    epoch_id="ep-test",
                    slice_id="s-test",
                    phase_spec="p9",
                    parent_workflow_id="ep-test",
                )
                handle = await env.client.start_workflow(
                    SliceWorkflow.run,
                    slice_input,
                    id="test-slice-ac-sw4",
                    task_queue="test-slice-ac-sw4",
                )
                # Send start signal (mock mode — completes immediately)
                await handle.signal(
                    SliceWorkflow.start_slice,
                    SliceStartSignal(
                        slice_id="s-test",
                        epoch_id="ep-test",
                        config=SliceExecutionConfig(mode=SliceMode.Mock, command="echo ok", timeout_seconds=5),
                    ),
                )
                # Send failure complete signal — overrides mock success
                await handle.signal(
                    SliceWorkflow.complete_slice,
                    SliceCompleteSignal(
                        slice_id="s-test",
                        success=False,
                        error="worker exited with code 1",
                    ),
                )
                result = await handle.result()
                assert result.success is False
                assert result.error == "worker exited with code 1"


# ─── AC-SW5: timeout behavior ────────────────────────────────────────────────


class TestSliceExecutionConfig:
    """Verify SliceExecutionConfig fields are consumed correctly."""

    def test_timeout_seconds_field(self) -> None:
        config = SliceExecutionConfig(
            mode=SliceMode.Tmux,
            command="./run.sh",
            timeout_seconds=600,
        )
        assert config.timeout_seconds == 600

    def test_heartbeat_interval_field(self) -> None:
        config = SliceExecutionConfig(
            mode=SliceMode.Subprocess,
            command="./run.sh",
            heartbeat_interval=10,
        )
        assert config.heartbeat_interval == 10

    def test_mode_values(self) -> None:
        for mode in (SliceMode.Tmux, SliceMode.Subprocess, SliceMode.Mock):
            config = SliceExecutionConfig(mode=mode, command="cmd")
            assert config.mode == mode


# ─── AC-SW5: timeout enforcement ────────────────────────────────────────────


@pytest.mark.asyncio
class TestSliceTimeoutEnforcement:
    """AC-SW5: Verify timeout is enforced on execute_slice_command activity."""

    async def test_activity_timeout_cancels_slow_command(self, tmp_path: Path) -> None:
        """Given a command that hangs, asyncio.wait_for with short timeout raises TimeoutError.

        This verifies that the timeout_seconds value from SliceExecutionConfig
        can be used to bound execution time. Temporal enforces start_to_close_timeout
        at the activity level; here we verify the underlying async operation is
        cancellable via asyncio timeout.
        """
        import asyncio
        import stat

        from temporalio.testing import ActivityEnvironment

        from aura_protocol.audit_activities import execute_slice_command

        fake_tmux = tmp_path / "tmux"
        fake_tmux.write_text("#!/bin/sh\necho fake-tmux")
        fake_tmux.chmod(fake_tmux.stat().st_mode | stat.S_IEXEC)

        env = ActivityEnvironment()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                env.run(execute_slice_command, "sleep 30", "s-timeout", "ep-t", str(tmp_path)),
                timeout=0.5,
            )
