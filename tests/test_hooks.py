"""Tests for hooks/scripts/session-register.sh — subprocess-based per D23.

BDD Acceptance Criteria:
    AC-H1: Given AURA_EPOCH_ID is not set, when session-register.sh runs,
           then it exits 0 silently without calling aura-msg.
    AC-H2: Given AURA_EPOCH_ID is set, when session-register.sh runs,
           then it calls aura-msg session register with correct args.
    AC-H3: Given a mock aura-msg that captures args, when session-register.sh
           is called with CLAUDE_SESSION_ID set, then session-id matches.

Coverage strategy:
    - Mock aura-msg script on PATH captures args to a temp file.
    - Real session-register.sh is invoked via subprocess.
    - No Temporal connectivity required (D23).

Also includes workflow-level unit tests for SessionRegisterSignal idempotency.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

# ─── Constants ─────────────────────────────────────────────────────────────────

HOOK_SCRIPT = Path(__file__).parent.parent / "hooks" / "scripts" / "session-register.sh"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
BASH = shutil.which("bash") or "bash"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _test_env() -> dict[str, str]:
    """Curated env for subprocess tests."""
    env = {"PYTHONPATH": str(SCRIPTS_DIR)}
    for key in ("HOME", "PATH", "VIRTUAL_ENV", "PYTHONHOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_aura_msg(tmp_path: Path) -> Path:
    """Create a mock aura-msg script that captures invocations to a JSON file.

    Returns the directory containing the mock (add to PATH).
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "aura-msg-calls.json"
    log_file.write_text("[]")

    mock_script = bin_dir / "aura-msg"
    mock_script.write_text(
        f"""#!/usr/bin/env python3
import json, sys
log = {str(log_file)!r}
with open(log) as f:
    calls = json.load(f)
calls.append(sys.argv[1:])
with open(log, "w") as f:
    json.dump(calls, f)
"""
    )
    mock_script.chmod(mock_script.stat().st_mode | stat.S_IEXEC)

    return tmp_path


def _run_hook(
    mock_dir: Path,
    *,
    epoch_id: str | None = None,
    session_id: str | None = None,
    role: str | None = None,
    model_harness: str | None = None,
    model: str | None = None,
) -> subprocess.CompletedProcess:
    """Run session-register.sh with optional env vars and mock aura-msg on PATH.

    The mock bin/ dir is prepended to PATH so mock aura-msg is found first.
    The system PATH is preserved so bash builtins (uuidgen, etc.) work.
    """
    # Prepend mock bin dir; keep system PATH for coreutils/uuidgen
    system_path = os.environ.get("PATH", "/usr/bin:/bin")
    env: dict[str, str] = {
        "PATH": f"{mock_dir / 'bin'}:{system_path}",
        "HOME": str(mock_dir),
    }
    if epoch_id is not None:
        env["AURA_EPOCH_ID"] = epoch_id
    if session_id is not None:
        env["CLAUDE_SESSION_ID"] = session_id
    if role is not None:
        env["AURA_ROLE"] = role
    if model_harness is not None:
        env["AURA_MODEL_HARNESS"] = model_harness
    if model is not None:
        env["CLAUDE_MODEL"] = model

    return subprocess.run(
        [BASH, str(HOOK_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _read_calls(mock_dir: Path) -> list[list[str]]:
    """Read captured aura-msg invocations from the log file."""
    log_file = mock_dir / "aura-msg-calls.json"
    return json.loads(log_file.read_text())


# ─── Hook Script Tests (D23: subprocess, no Temporal) ─────────────────────────


class TestSessionRegisterHookScript:
    """AC-H1/H2/H3: session-register.sh behavior via subprocess."""

    def test_hook_script_exists(self) -> None:
        assert HOOK_SCRIPT.exists(), f"Hook script not found at {HOOK_SCRIPT}"

    def test_hook_script_is_executable(self) -> None:
        assert os.access(HOOK_SCRIPT, os.X_OK), f"Hook script is not executable: {HOOK_SCRIPT}"

    def test_exits_zero_when_epoch_id_not_set(self, mock_aura_msg: Path) -> None:
        """AC-H1: exits 0 silently when AURA_EPOCH_ID is not set."""
        result = _run_hook(mock_aura_msg)
        assert result.returncode == 0, (
            f"Expected exit 0 when AURA_EPOCH_ID not set, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        calls = _read_calls(mock_aura_msg)
        assert calls == [], f"Expected no aura-msg calls, got {calls}"

    def test_calls_session_register_when_epoch_id_set(self, mock_aura_msg: Path) -> None:
        """AC-H2: calls aura-msg session register with correct args."""
        result = _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-1",
            session_id="sess-abc",
            role="worker",
        )
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr!r}"
        )
        calls = _read_calls(mock_aura_msg)
        assert len(calls) >= 1, f"Expected at least 1 aura-msg call, got {calls}"

        # First call should be session register
        register_call = calls[0]
        assert register_call[:2] == ["session", "register"], (
            f"Expected 'session register', got {register_call[:2]}"
        )
        assert "--epoch-id" in register_call
        idx = register_call.index("--epoch-id")
        assert register_call[idx + 1] == "test-epoch-1"
        assert "--session-id" in register_call
        idx = register_call.index("--session-id")
        assert register_call[idx + 1] == "sess-abc"
        assert "--role" in register_call
        idx = register_call.index("--role")
        assert register_call[idx + 1] == "worker"

    def test_calls_query_state_after_register(self, mock_aura_msg: Path) -> None:
        """Hook also calls aura-msg query state after registration."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-2",
            session_id="sess-xyz",
        )
        calls = _read_calls(mock_aura_msg)
        assert len(calls) == 2, f"Expected 2 calls (register + query), got {len(calls)}"
        assert calls[1][:2] == ["query", "state"], (
            f"Expected second call to be 'query state', got {calls[1][:2]}"
        )

    def test_uses_claude_session_id_env(self, mock_aura_msg: Path) -> None:
        """AC-H3: CLAUDE_SESSION_ID env var is used as --session-id."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-3",
            session_id="my-custom-session-id",
        )
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        idx = register_call.index("--session-id")
        assert register_call[idx + 1] == "my-custom-session-id"

    def test_default_role_is_worker(self, mock_aura_msg: Path) -> None:
        """When AURA_ROLE is not set, default role is 'worker'."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-4",
            session_id="sess-default-role",
            # role not set
        )
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        idx = register_call.index("--role")
        assert register_call[idx + 1] == "worker"

    def test_custom_role(self, mock_aura_msg: Path) -> None:
        """AURA_ROLE env var overrides default role."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-5",
            session_id="sess-custom-role",
            role="supervisor",
        )
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        idx = register_call.index("--role")
        assert register_call[idx + 1] == "supervisor"


# ─── Workflow-level session registration tests ─────────────────────────────────


class TestSessionRegisterSignalIdempotency:
    """Workflow signal handler idempotency: duplicate session_id is a no-op."""

    def test_register_session_adds_to_active_sessions(self) -> None:
        from aura_protocol.workflow import EpochWorkflow, SessionRegisterSignal

        wf = EpochWorkflow()
        signal = SessionRegisterSignal(
            epoch_id="e1", session_id="sess-1", role="worker"
        )
        wf.register_session(signal)
        assert len(wf._active_sessions) == 1
        assert wf._active_sessions[0].session_id == "sess-1"

    def test_duplicate_session_id_is_noop(self) -> None:
        from aura_protocol.workflow import EpochWorkflow, SessionRegisterSignal

        wf = EpochWorkflow()
        signal1 = SessionRegisterSignal(
            epoch_id="e1", session_id="sess-dup", role="worker"
        )
        signal2 = SessionRegisterSignal(
            epoch_id="e1", session_id="sess-dup", role="supervisor"
        )
        wf.register_session(signal1)
        wf.register_session(signal2)
        assert len(wf._active_sessions) == 1
        assert wf._active_sessions[0].role == "worker"

    def test_different_session_ids_both_registered(self) -> None:
        from aura_protocol.workflow import EpochWorkflow, SessionRegisterSignal

        wf = EpochWorkflow()
        wf.register_session(
            SessionRegisterSignal(epoch_id="e1", session_id="sess-a", role="worker")
        )
        wf.register_session(
            SessionRegisterSignal(epoch_id="e1", session_id="sess-b", role="reviewer")
        )
        assert len(wf._active_sessions) == 2
        ids = {s.session_id for s in wf._active_sessions}
        assert ids == {"sess-a", "sess-b"}


# ─── aura-msg session register CLI parsing tests ──────────────────────────────


class TestSessionRegisterCLIParsing:
    """Verify aura-msg session register parses arguments correctly."""

    def test_session_register_parsed(self) -> None:
        import importlib.machinery
        import importlib.util

        aura_msg_path = Path(__file__).parent.parent / "bin" / "aura-msg"
        scripts_str = str(SCRIPTS_DIR)
        inserted = False
        if scripts_str not in sys.path:
            sys.path.insert(0, scripts_str)
            inserted = True
        try:
            loader = importlib.machinery.SourceFileLoader("aura_msg_test", str(aura_msg_path))
            spec = importlib.util.spec_from_loader("aura_msg_test", loader, origin=str(aura_msg_path))
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)

            args = module.parse_args(
                ["session", "register", "--epoch-id", "E1", "--session-id", "S1", "--role", "worker"]
            )
            assert args.group == "session"
            assert args.subcommand == "register"
            assert args.epoch_id == "E1"
            assert args.session_id == "S1"
            assert args.role == "worker"
        finally:
            if inserted and scripts_str in sys.path:
                sys.path.remove(scripts_str)

    def test_session_register_parsed_with_model_fields(self) -> None:
        """aura-msg session register accepts --model-harness and --model flags."""
        import importlib.machinery
        import importlib.util

        aura_msg_path = Path(__file__).parent.parent / "bin" / "aura-msg"
        scripts_str = str(SCRIPTS_DIR)
        inserted = False
        if scripts_str not in sys.path:
            sys.path.insert(0, scripts_str)
            inserted = True
        try:
            loader = importlib.machinery.SourceFileLoader("aura_msg_test2", str(aura_msg_path))
            spec = importlib.util.spec_from_loader("aura_msg_test2", loader, origin=str(aura_msg_path))
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)

            args = module.parse_args(
                [
                    "session", "register",
                    "--epoch-id", "E1",
                    "--session-id", "S1",
                    "--role", "worker",
                    "--model-harness", "claude-code",
                    "--model", "claude-sonnet-4",
                ]
            )
            assert args.model_harness == "claude-code"
            assert args.model == "claude-sonnet-4"
        finally:
            if inserted and scripts_str in sys.path:
                sys.path.remove(scripts_str)

    def test_session_register_subprocess_exits_nonzero_no_temporal(self) -> None:
        """Without Temporal, session register exits 2 (connection error), not 1."""
        aura_msg_path = Path(__file__).parent.parent / "bin" / "aura-msg"
        result = subprocess.run(
            [
                sys.executable,
                str(aura_msg_path),
                "session",
                "register",
                "--epoch-id",
                "E1",
                "--session-id",
                "S1",
                "--role",
                "worker",
            ],
            capture_output=True,
            text=True,
            env=_test_env(),
            timeout=15,
        )
        # Should be exit 2 (connection) or 3 (workflow), NOT 1 (not implemented)
        assert result.returncode in (2, 3), (
            f"Expected exit 2 or 3 (implemented but no Temporal), got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "not implemented" not in result.stderr.lower(), (
            f"session register should be implemented, but got 'not implemented'.\n"
            f"stderr: {result.stderr!r}"
        )


# ─── Hook script: model_harness and model flags ────────────────────────────────


class TestSessionRegisterModelFlags:
    """session-register.sh passes --model-harness and --model to aura-msg."""

    def test_passes_model_harness_and_model_env_vars(self, mock_aura_msg: Path) -> None:
        """Hook passes AURA_MODEL_HARNESS and CLAUDE_MODEL as CLI flags."""
        result = _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-model",
            session_id="sess-model",
            model_harness="claude-code",
            model="claude-sonnet-4",
        )
        assert result.returncode == 0
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        assert "--model-harness" in register_call
        idx = register_call.index("--model-harness")
        assert register_call[idx + 1] == "claude-code"
        assert "--model" in register_call
        idx = register_call.index("--model")
        assert register_call[idx + 1] == "claude-sonnet-4"

    def test_default_model_harness_is_claude_code(self, mock_aura_msg: Path) -> None:
        """When AURA_MODEL_HARNESS is not set, defaults to 'claude-code'."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-default-harness",
            session_id="sess-dh",
        )
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        idx = register_call.index("--model-harness")
        assert register_call[idx + 1] == "claude-code"

    def test_default_model_is_unknown(self, mock_aura_msg: Path) -> None:
        """When CLAUDE_MODEL is not set, defaults to 'unknown'."""
        _run_hook(
            mock_aura_msg,
            epoch_id="test-epoch-default-model",
            session_id="sess-dm",
        )
        calls = _read_calls(mock_aura_msg)
        register_call = calls[0]
        idx = register_call.index("--model")
        assert register_call[idx + 1] == "unknown"


# ─── Hook script: error handling (R-11) ────────────────────────────────────────


@pytest.fixture
def failing_aura_msg(tmp_path: Path) -> Path:
    """Create a mock aura-msg that fails (exit 2) for register with structured error,
    simulating how real aura-msg reports errors via report_error()."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "aura-msg-calls.json"
    log_file.write_text("[]")

    mock_script = bin_dir / "aura-msg"
    # Fail on 'session register' with structured error output, succeed on everything else
    mock_script.write_text(
        f"""#!/usr/bin/env python3
import json, sys
log = {str(log_file)!r}
with open(log) as f:
    calls = json.load(f)
calls.append(sys.argv[1:])
with open(log, "w") as f:
    json.dump(calls, f)
if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "register":
    print("connection error: failed to connect to Temporal at localhost:7233", file=sys.stderr)
    print("  why: Connection refused", file=sys.stderr)
    print("  impact: session registration cannot reach the Temporal server", file=sys.stderr)
    print("  fix: ensure aurad is running and Temporal is reachable", file=sys.stderr)
    sys.exit(2)
"""
    )
    mock_script.chmod(mock_script.stat().st_mode | stat.S_IEXEC)

    return tmp_path


class TestSessionRegisterErrorHandling:
    """R-11: When aura-msg fails, hook still exits 0. Errors reported by Python (report_error)."""

    def test_exits_zero_on_register_failure(self, failing_aura_msg: Path) -> None:
        """Hook exits 0 even when aura-msg session register fails."""
        result = _run_hook(
            failing_aura_msg,
            epoch_id="test-epoch-fail",
            session_id="sess-fail",
        )
        assert result.returncode == 0, (
            f"Expected exit 0 on register failure, got {result.returncode}.\n"
            f"stderr: {result.stderr!r}"
        )

    def test_error_from_python_has_structured_format(self, failing_aura_msg: Path) -> None:
        """Error output from aura-msg (Python) uses structured report_error format."""
        result = _run_hook(
            failing_aura_msg,
            epoch_id="test-epoch-fail2",
            session_id="sess-fail2",
        )
        assert "connection error:" in result.stderr

    def test_error_message_has_why_impact_fix(self, failing_aura_msg: Path) -> None:
        """Structured error from aura-msg includes why, impact, fix lines."""
        result = _run_hook(
            failing_aura_msg,
            epoch_id="test-epoch-fail3",
            session_id="sess-fail3",
        )
        for keyword in ["why:", "impact:", "fix:"]:
            assert keyword in result.stderr, (
                f"Expected '{keyword}' in stderr, got: {result.stderr!r}"
            )


# ─── Workflow-level: ReviewCycleSignal + SessionRegisterSignal fields ──────────


class TestReviewCycleSignal:
    """SliceWorkflow review_cycle signal handler and query."""

    def test_slice_workflow_has_review_cycle_signal(self) -> None:
        from aura_protocol.workflow import SliceWorkflow

        wf = SliceWorkflow()
        assert hasattr(wf, "review_cycle"), "SliceWorkflow must have review_cycle signal"

    def test_review_cycle_increments_count(self) -> None:
        from aura_protocol.types import ReviewCycleSignal
        from aura_protocol.workflow import SliceWorkflow

        wf = SliceWorkflow()
        assert wf.review_cycle_count() == 0
        wf.review_cycle(ReviewCycleSignal(cycle_number=1, reviewer_feedback="fix tests"))
        assert wf.review_cycle_count() == 1
        wf.review_cycle(ReviewCycleSignal(cycle_number=2, reviewer_feedback="lgtm"))
        assert wf.review_cycle_count() == 2

    def test_review_cycles_query_returns_records(self) -> None:
        from aura_protocol.types import ReviewCycleRecord, ReviewCycleSignal
        from aura_protocol.workflow import SliceWorkflow

        wf = SliceWorkflow()
        assert wf.review_cycles() == []
        wf.review_cycle(ReviewCycleSignal(cycle_number=1, reviewer_feedback="fix tests"))
        wf.review_cycle(ReviewCycleSignal(cycle_number=2, reviewer_feedback="lgtm"))
        records = wf.review_cycles()
        assert len(records) == 2
        assert records[0] == ReviewCycleRecord(cycle_number=1, reviewer_feedback="fix tests")
        assert records[1] == ReviewCycleRecord(cycle_number=2, reviewer_feedback="lgtm")

    def test_review_cycles_returns_defensive_copy(self) -> None:
        from aura_protocol.types import ReviewCycleSignal
        from aura_protocol.workflow import SliceWorkflow

        wf = SliceWorkflow()
        wf.review_cycle(ReviewCycleSignal(cycle_number=1, reviewer_feedback="ok"))
        copy = wf.review_cycles()
        copy.clear()
        assert wf.review_cycle_count() == 1

    def test_review_cycle_record_is_frozen(self) -> None:
        from aura_protocol.types import ReviewCycleRecord

        rec = ReviewCycleRecord(cycle_number=1, reviewer_feedback="ok")
        with pytest.raises(AttributeError):
            rec.cycle_number = 2  # type: ignore[misc]

    def test_review_cycle_signal_is_frozen(self) -> None:
        from aura_protocol.types import ReviewCycleSignal

        sig = ReviewCycleSignal(cycle_number=1, reviewer_feedback="ok")
        with pytest.raises(AttributeError):
            sig.cycle_number = 2  # type: ignore[misc]


class TestSessionRegisterSignalModelFields:
    """SessionRegisterSignal has model_harness and model fields."""

    def test_default_model_fields_are_empty(self) -> None:
        from aura_protocol.workflow import SessionRegisterSignal

        sig = SessionRegisterSignal(epoch_id="e1", session_id="s1")
        assert sig.model_harness == ""
        assert sig.model == ""

    def test_model_fields_set(self) -> None:
        from aura_protocol.workflow import SessionRegisterSignal

        sig = SessionRegisterSignal(
            epoch_id="e1",
            session_id="s1",
            model_harness="claude-code",
            model="claude-sonnet-4",
        )
        assert sig.model_harness == "claude-code"
        assert sig.model == "claude-sonnet-4"
