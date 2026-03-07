"""Tests for bin/aura-msg — Aura Protocol CLI (SLICE-2/SLICE-3).

BDD Acceptance Criteria:
    AC-M1: Given bin/aura-msg exists, when checked, then the file is present
           with a python3 shebang.
    AC-M2: Given aura-msg with no args, when invoked, then --help is printed and
           exit code is 0.
    AC-M3: Given aura-msg --help, when invoked, then output contains all five
           subcommand groups: query, epoch, signal, phase, session.
    AC-P1: Given parse_args(["query", "state", ...]), when parsed, then group="query"
           and subcommand="state" with correct options.
    AC-P2: Given parse_args for unimplemented subcommands, when invoked, then
           exits 1 with "not implemented" in stderr.

Coverage strategy:
    - File exists + has python3 shebang (filesystem check)
    - Module importable via importlib (build_parser / parse_args present)
    - parse_args([]) → group is None (AC-M2 unit)
    - parse_args(["query", "state", ...]) → correct routing (AC-P1 unit)
    - --help subprocess output contains all groups (AC-M3 integration)
    - Unimplemented subcommands → exit 1 (AC-P2 integration)
    - No-args subprocess → exit 0 (AC-M2 integration)

DI approach:
    - build_parser() / parse_args(): tested via importlib-loaded module.
    - Integration: subprocess calls against the actual script.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ─── Constants ─────────────────────────────────────────────────────────────────

AURA_MSG_PATH = Path(__file__).parent.parent / "bin" / "aura-msg"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
PYTHON = sys.executable

# All subcommand cases: (group, subcommand, required_args)
SUBCOMMAND_CASES = [
    ("query", "state", ["--epoch-id", "E1"]),
    ("epoch", "start", ["--epoch-id", "E1", "--description", "test"]),
    ("signal", "vote", ["--epoch-id", "E1", "--axis", "correctness", "--vote", "accept", "--reviewer-id", "R1"]),
    ("signal", "complete", ["--slice-id", "S1"]),
    ("phase", "advance", ["--epoch-id", "E1", "--to-phase", "p10", "--triggered-by", "w1", "--condition", "done"]),
    ("session", "register", ["--epoch-id", "E1", "--session-id", "sess-1", "--role", "worker"]),
]

# Implemented subcommands (exit 2/3 on Temporal errors, not exit 1).
IMPLEMENTED_SUBCOMMANDS = {
    ("query", "state"),
    ("signal", "vote"),
    ("signal", "complete"),
    ("phase", "advance"),
    ("epoch", "start"),
    ("session", "register"),
}

# Subcommands not yet implemented (exit 1 with "not implemented" message).
UNIMPLEMENTED_SUBCOMMAND_CASES = [
    c for c in SUBCOMMAND_CASES if c[:2] not in IMPLEMENTED_SUBCOMMANDS
]

GROUPS = ["query", "epoch", "signal", "phase", "session"]

# ─── Module loader ────────────────────────────────────────────────────────────


def _load_aura_msg() -> ModuleType:
    """Load bin/aura-msg as a Python module via importlib.

    Uses SourceFileLoader because the file has no .py extension.
    Adds scripts/ to sys.path so aura_protocol imports resolve.
    """
    scripts_str = str(SCRIPTS_DIR)
    inserted = False
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)
        inserted = True
    try:
        loader = importlib.machinery.SourceFileLoader("aura_msg", str(AURA_MSG_PATH))
        spec = importlib.util.spec_from_loader("aura_msg", loader, origin=str(AURA_MSG_PATH))
        assert spec is not None, f"Could not create module spec for {AURA_MSG_PATH}"
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_str in sys.path:
            sys.path.remove(scripts_str)


@pytest.fixture(scope="module")
def aura_msg() -> ModuleType:
    return _load_aura_msg()


# ─── Filesystem checks ────────────────────────────────────────────────────────


class TestAuraMsgFile:
    """AC-M1: file exists and has correct shebang."""

    def test_file_exists(self) -> None:
        assert AURA_MSG_PATH.exists(), f"bin/aura-msg not found at {AURA_MSG_PATH}"

    def test_file_has_python3_shebang(self) -> None:
        first_line = AURA_MSG_PATH.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env python3", (
            f"Expected python3 shebang, got: {first_line!r}"
        )


# ─── Unit tests (importlib-loaded module) ─────────────────────────────────────


class TestBuildParser:
    """AC-M5: build_parser() returns parser with correct prog and groups."""

    def test_parser_prog(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        assert parser.prog == "aura-msg"

    @pytest.mark.parametrize("group", GROUPS)
    def test_each_group_registered(
        self, aura_msg: ModuleType, group: str
    ) -> None:
        """Each subcommand group must be recognized by the parser."""
        parser = aura_msg.build_parser()
        args = parser.parse_args([group])
        assert args.group == group

    @pytest.mark.parametrize("group,subcommand,extra_args", SUBCOMMAND_CASES)
    def test_each_subcommand_registered(
        self, aura_msg: ModuleType, group: str, subcommand: str, extra_args: list[str]
    ) -> None:
        """Each subcommand must parse without error."""
        parser = aura_msg.build_parser()
        args = parser.parse_args([group, subcommand] + extra_args)
        assert args.group == group
        assert args.subcommand == subcommand


class TestBuildParserGroups:
    """Additional parser structural checks."""

    def test_query_state_has_format(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        args = parser.parse_args(["query", "state", "--epoch-id", "E1", "--format", "text"])
        assert args.output_format == "text"

    def test_query_state_default_format_text(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        args = parser.parse_args(["query", "state", "--epoch-id", "E1"])
        assert args.output_format == "text"

    def test_signal_complete_mutually_exclusive(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        args = parser.parse_args(["signal", "complete", "--epoch-id", "E1", "--slice-id", "S1", "--output", "done"])
        assert args.output == "done"
        assert args.error is None


class TestParseArgs:
    """AC-P1: parse_args() routing for query state subcommand."""

    def test_no_args_group_is_none(self, aura_msg: ModuleType) -> None:
        args = aura_msg.parse_args([])
        assert args.group is None

    def test_query_state_parsed(self, aura_msg: ModuleType) -> None:
        args = aura_msg.parse_args(
            ["query", "state", "--epoch-id", "test-epoch"]
        )
        assert args.group == "query"
        assert args.subcommand == "state"
        assert args.epoch_id == "test-epoch"
        assert args.output_format == "text"  # default

    def test_query_state_json_format(self, aura_msg: ModuleType) -> None:
        args = aura_msg.parse_args(
            ["query", "state", "--epoch-id", "E1", "--format", "json"]
        )
        assert args.output_format == "json"

    def test_query_state_server_address_override(self, aura_msg: ModuleType) -> None:
        args = aura_msg.parse_args(
            [
                "query",
                "state",
                "--epoch-id",
                "E1",
                "--server-address",
                "remote:7233",
            ]
        )
        assert args.server_address == "remote:7233"

    def test_query_state_namespace_override(self, aura_msg: ModuleType) -> None:
        args = aura_msg.parse_args(
            [
                "query",
                "state",
                "--epoch-id",
                "E1",
                "--namespace",
                "custom-ns",
            ]
        )
        assert args.namespace == "custom-ns"

    @pytest.mark.parametrize("group,subcommand,extra_args", SUBCOMMAND_CASES)
    def test_group_and_subcommand_parsed_correctly(
        self, aura_msg: ModuleType, group: str, subcommand: str, extra_args: list[str]
    ) -> None:
        """AC-M6: group+subcommand parsed correctly."""
        args = aura_msg.parse_args([group, subcommand] + extra_args)
        assert args.group == group
        assert args.subcommand == subcommand


# ─── Integration tests (subprocess against production code path) ───────────────


class TestAuraMsgSubprocess:
    """Integration tests using the actual aura-msg script."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PYTHON, str(AURA_MSG_PATH)] + list(args),
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/bin"},
        )

    def test_no_args_exits_zero(self) -> None:
        """AC-M2: no group → print help and exit 0."""
        result = self._run()
        assert result.returncode == 0, (
            f"Expected exit 0 with no args, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    def test_help_exits_zero(self) -> None:
        """AC-M3 (exit code): --help must exit 0."""
        result = self._run("--help")
        assert result.returncode == 0, (
            f"--help exited {result.returncode}.\nstdout: {result.stdout!r}"
        )

    @pytest.mark.parametrize("group", GROUPS)
    def test_help_contains_group(self, group: str) -> None:
        """AC-M3: --help output must mention each subcommand group."""
        result = self._run("--help")
        output = result.stdout + result.stderr
        assert group in output, (
            f"'{group}' not found in --help output.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("group,subcommand,extra_args", UNIMPLEMENTED_SUBCOMMAND_CASES)
    def test_unimplemented_subcommand_exits_one(
        self, group: str, subcommand: str, extra_args: list[str]
    ) -> None:
        """AC-P2: unimplemented subcommands exit 1 with 'not implemented'."""
        result = self._run(group, subcommand, *extra_args)
        assert result.returncode == 1, (
            f"'{group} {subcommand}' exited {result.returncode}, expected 1.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "not implemented" in result.stderr.lower(), (
            f"'{group} {subcommand}': expected 'not implemented' in stderr.\n"
            f"stderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("group,subcommand,extra_args", UNIMPLEMENTED_SUBCOMMAND_CASES)
    def test_subcommand_stderr_mentions_subcommand(self, group: str, subcommand: str, extra_args: list[str]) -> None:
        """Unimplemented subcommand prints group+subcommand name to stderr."""
        result = self._run(group, subcommand, *extra_args)
        combined = (result.stdout + result.stderr).lower()
        assert subcommand in combined or "not" in combined, (
            f"'{group} {subcommand}': expected subcommand or 'not' in output.\n"
            f"stderr: {result.stderr!r}"
        )


# ─── SLICE-4 Tests ─────────────────────────────────────────────────────────────


class TestSignalVoteNormalization:
    """D13: VoteType .upper() normalization at CLI boundary."""

    def test_vote_uppercase_normalization(self, aura_msg: ModuleType) -> None:
        """parse_args for signal vote with lowercase vote → .upper() == 'ACCEPT'."""
        args = aura_msg.parse_args(
            ["signal", "vote", "--epoch-id", "E", "--axis", "correctness", "--vote", "accept"]
        )
        assert args.vote.upper() == "ACCEPT"

    def test_vote_mixed_case_normalization(self, aura_msg: ModuleType) -> None:
        """parse_args for signal vote with mixed-case vote → .upper() == 'REVISE'."""
        args = aura_msg.parse_args(
            ["signal", "vote", "--epoch-id", "E", "--axis", "correctness", "--vote", "Revise"]
        )
        assert args.vote.upper() == "REVISE"

    def test_reviewer_id_optional(self, aura_msg: ModuleType) -> None:
        """--reviewer-id is optional, defaults to empty string."""
        args = aura_msg.parse_args(
            ["signal", "vote", "--epoch-id", "E", "--axis", "correctness", "--vote", "accept"]
        )
        assert args.reviewer_id == ""


class TestPhaseAdvanceValidation:
    """D15: PhaseId validation for phase advance subcommand."""

    def test_invalid_phase_exits_one(self) -> None:
        """Invalid --to-phase exits 1 with valid phases listed in stderr."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "phase", "advance", "--epoch-id", "E", "--to-phase", "invalid-phase"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 1, (
            f"Expected exit 1 for invalid phase, got {result.returncode}.\n"
            f"stderr: {result.stderr!r}"
        )
        assert "invalid-phase" in result.stderr, (
            f"Expected invalid phase name in stderr.\nstderr: {result.stderr!r}"
        )
        # Valid phases should be listed
        assert "p1" in result.stderr, (
            f"Expected valid phase values listed in stderr.\nstderr: {result.stderr!r}"
        )

    def test_valid_phase_parses(self, aura_msg: ModuleType) -> None:
        """Valid --to-phase is accepted by the parser."""
        args = aura_msg.parse_args(
            ["phase", "advance", "--epoch-id", "E", "--to-phase", "p10"]
        )
        assert args.to_phase == "p10"

    def test_triggered_by_optional(self, aura_msg: ModuleType) -> None:
        """--triggered-by is optional, defaults to empty string."""
        args = aura_msg.parse_args(
            ["phase", "advance", "--epoch-id", "E", "--to-phase", "p10"]
        )
        assert args.triggered_by == ""

    def test_condition_optional(self, aura_msg: ModuleType) -> None:
        """--condition is optional, defaults to empty string."""
        args = aura_msg.parse_args(
            ["phase", "advance", "--epoch-id", "E", "--to-phase", "p10"]
        )
        assert args.condition == ""


class TestSignalCompleteBDD:
    """BDD criteria for signal complete subcommand."""

    def test_output_flag_creates_success_signal(self, aura_msg: ModuleType) -> None:
        """--output done → SliceCompleteSignal(success=True, output='done')."""
        args = aura_msg.parse_args(
            ["signal", "complete", "--epoch-id", "E", "--slice-id", "S1", "--output", "done"]
        )
        assert args.output == "done"
        assert args.error is None

    def test_error_flag_creates_failure_signal(self, aura_msg: ModuleType) -> None:
        """--error failed → SliceCompleteSignal(success=False, error='failed')."""
        args = aura_msg.parse_args(
            ["signal", "complete", "--epoch-id", "E", "--slice-id", "S1", "--error", "failed"]
        )
        assert args.error == "failed"
        assert args.output is None

    def test_missing_slice_id_exits_with_error(self) -> None:
        """Without --slice-id → exits with usage error."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "signal", "complete", "--epoch-id", "E"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit for missing --slice-id, got {result.returncode}"
        )

    def test_default_success_when_no_output_or_error(self, aura_msg: ModuleType) -> None:
        """Neither --output nor --error → defaults to success=True, output=''."""
        args = aura_msg.parse_args(
            ["signal", "complete", "--epoch-id", "E", "--slice-id", "S1"]
        )
        assert args.output is None
        assert args.error is None


class TestSignalVoteValidation:
    """I-4.1: _cmd_signal_vote must validate VoteType and ReviewAxis."""

    def test_invalid_vote_exits_one(self) -> None:
        """Invalid --vote exits 1 with 'validation error' in stderr."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "signal", "vote",
             "--epoch-id", "E", "--axis", "correctness", "--vote", "BOGUS"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 1, (
            f"Expected exit 1 for invalid vote, got {result.returncode}.\n"
            f"stderr: {result.stderr!r}"
        )
        assert "validation error" in result.stderr, (
            f"Expected 'validation error' in stderr.\nstderr: {result.stderr!r}"
        )
        assert "BOGUS" in result.stderr, (
            f"Expected invalid vote value in stderr.\nstderr: {result.stderr!r}"
        )
        assert "ACCEPT" in result.stderr, (
            f"Expected valid votes listed in stderr.\nstderr: {result.stderr!r}"
        )

    def test_invalid_axis_exits_one(self) -> None:
        """Invalid --axis exits 1 with 'validation error' in stderr."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "signal", "vote",
             "--epoch-id", "E", "--axis", "nonexistent", "--vote", "accept"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 1, (
            f"Expected exit 1 for invalid axis, got {result.returncode}.\n"
            f"stderr: {result.stderr!r}"
        )
        assert "validation error" in result.stderr, (
            f"Expected 'validation error' in stderr.\nstderr: {result.stderr!r}"
        )
        assert "nonexistent" in result.stderr, (
            f"Expected invalid axis value in stderr.\nstderr: {result.stderr!r}"
        )
        assert "correctness" in result.stderr, (
            f"Expected valid axes listed in stderr.\nstderr: {result.stderr!r}"
        )


class TestSignalCompleteEpochIdOptional:
    """I-4.2: --epoch-id is optional for signal complete (handle is slice-id)."""

    def test_signal_complete_without_epoch_id(self, aura_msg: ModuleType) -> None:
        """signal complete parses successfully without --epoch-id."""
        args = aura_msg.parse_args(
            ["signal", "complete", "--slice-id", "S1"]
        )
        assert args.slice_id == "S1"
        assert args.epoch_id is None

    def test_signal_complete_with_epoch_id_still_accepted(self, aura_msg: ModuleType) -> None:
        """signal complete still accepts --epoch-id for backward compatibility."""
        args = aura_msg.parse_args(
            ["signal", "complete", "--epoch-id", "E", "--slice-id", "S1"]
        )
        assert args.epoch_id == "E"
        assert args.slice_id == "S1"


class TestEpochStartParser:
    """Parser tests for epoch start subcommand."""

    def test_description_optional(self, aura_msg: ModuleType) -> None:
        """--description is optional, defaults to empty string."""
        args = aura_msg.parse_args(["epoch", "start", "--epoch-id", "E"])
        assert args.description == ""

    def test_description_provided(self, aura_msg: ModuleType) -> None:
        """--description value is preserved."""
        args = aura_msg.parse_args(
            ["epoch", "start", "--epoch-id", "E", "--description", "Test epoch"]
        )
        assert args.description == "Test epoch"
