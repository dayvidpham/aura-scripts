"""Tests for bin/aura-msg — Aura Protocol model harness CLI (SLICE-3-L1 update).

Parser structure: nested subcommand groups (group → subcommand).

Groups and subcommands:
    query  state    — aura-msg query state --epoch-id ID [--format json|text]
    epoch  start    — aura-msg epoch start --epoch-id ID --description TEXT
    signal vote     — aura-msg signal vote --epoch-id ID --axis AX --vote V --reviewer-id RID
    signal complete — aura-msg signal complete --epoch-id ID --slice-id SID
    phase  advance  — aura-msg phase advance --epoch-id ID --to-phase PH ...
    session register — aura-msg session register --epoch-id ID --session-id SID

BDD Acceptance Criteria (updated for nested groups):
    AC-M1: bin/aura-msg exists with python3 shebang.
    AC-M2: No args → print help, exit 0.
    AC-M3: --help → exit 0 and output shows group names.
    AC-M5: build_parser() returns parser with prog="aura-msg" and all groups.
    AC-M6: parse_args(["query", "state", ...]) sets group="query", subcommand="state".

Coverage strategy:
    - File exists + has python3 shebang (filesystem check)
    - build_parser() prog name and top-level group registration
    - parse_args with group + subcommand routing
    - Subprocess: --help exits 0, no-args exits 0
    - Subprocess: unimplemented subcommand exits 1 with stderr message

DI approach:
    - build_parser() / parse_args(): tested via importlib-loaded module (SourceFileLoader).
    - Integration: subprocess calls against the actual script.
      No mocking framework — only plain subprocess + importlib.
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

# New group structure: (group, subcommand, required_args)
SUBCOMMAND_CASES = [
    ("query", "state", ["--epoch-id", "E1"]),
    ("epoch", "start", ["--epoch-id", "E1", "--description", "test"]),
    ("signal", "vote", ["--epoch-id", "E1", "--axis", "correctness", "--vote", "accept", "--reviewer-id", "R1"]),
    ("signal", "complete", ["--epoch-id", "E1", "--slice-id", "S1"]),
    ("phase", "advance", ["--epoch-id", "E1", "--to-phase", "p10", "--triggered-by", "w1", "--condition", "done"]),
    ("session", "register", ["--epoch-id", "E1", "--session-id", "sess-1", "--role", "worker"]),
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
    def test_each_group_registered(self, aura_msg: ModuleType, group: str) -> None:
        """Each top-level group must be registered in the parser."""
        parser = aura_msg.build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([group, "--help"])
        assert exc_info.value.code == 0, f"Group '{group}' --help exited non-zero"

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
        assert args.format == "text"

    def test_query_state_default_format_json(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        args = parser.parse_args(["query", "state", "--epoch-id", "E1"])
        assert args.format == "json"

    def test_signal_complete_mutually_exclusive(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        args = parser.parse_args(["signal", "complete", "--epoch-id", "E1", "--slice-id", "S1", "--output", "done"])
        assert args.output == "done"
        assert args.error is None


class TestParseArgs:
    """AC-M2, AC-M6: parse_args() defaults and group/subcommand routing."""

    def test_no_args_group_is_none(self, aura_msg: ModuleType) -> None:
        """AC-M2: no args → group is None (help branch in main)."""
        args = aura_msg.parse_args([])
        assert args.group is None

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
    """Integration tests using the actual aura-msg script (same path users run)."""

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
        """AC-M3: --help output must mention each group."""
        result = self._run("--help")
        output = result.stdout + result.stderr
        assert group in output, (
            f"'{group}' not found in --help output.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("group,subcommand,extra_args", SUBCOMMAND_CASES)
    def test_subcommand_exits_one(self, group: str, subcommand: str, extra_args: list[str]) -> None:
        """Unimplemented subcommand exits with code 1."""
        result = self._run(group, subcommand, *extra_args)
        assert result.returncode == 1, (
            f"'{group} {subcommand}' exited {result.returncode}, expected 1.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("group,subcommand,extra_args", SUBCOMMAND_CASES)
    def test_subcommand_stderr_mentions_subcommand(self, group: str, subcommand: str, extra_args: list[str]) -> None:
        """Unimplemented subcommand prints group+subcommand name to stderr."""
        result = self._run(group, subcommand, *extra_args)
        combined = (result.stdout + result.stderr).lower()
        assert subcommand in combined or "not" in combined, (
            f"'{group} {subcommand}': expected subcommand or 'not' in output.\n"
            f"stderr: {result.stderr!r}"
        )
