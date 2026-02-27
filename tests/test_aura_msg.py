"""Tests for bin/aura-msg.py — Aura Protocol model harness CLI stub (SLICE-2-L2).

BDD Acceptance Criteria:
    AC-M1: Given bin/aura-msg.py exists, when checked, then the file is present
           with a python3 shebang. Should not require a running Temporal server.
    AC-M2: Given aura-msg with no args, when invoked, then --help is printed and
           exit code is 0 (argparse convention for no-subcommand case).
    AC-M3: Given aura-msg --help, when invoked, then output contains all four
           planned subcommands: start-epoch, signal-vote, query-state, advance-phase.
    AC-M4: Given any planned subcommand (start-epoch, signal-vote, query-state,
           advance-phase), when invoked, then exits with code 1 and stderr contains
           "not implemented".
    AC-M5: Given build_parser(), when called, then parser.prog == "aura-msg" and
           all four subcommands are registered.
    AC-M6: Given parse_args([subcommand]), when called for each planned subcommand,
           then args.subcommand == subcommand.

Coverage strategy:
    - File exists + has python3 shebang (filesystem check)
    - Module importable via importlib (build_parser present + correct prog name)
    - parse_args([]) → subcommand is None (AC-M2 unit)
    - parse_args([sub]) → subcommand matches (AC-M6 unit)
    - --help subprocess output contains all subcommands (AC-M3 integration)
    - subcommand subprocess → exit 1 + stderr "not implemented" (AC-M4 integration)
    - no-args subprocess → exit 0 (AC-M2 integration)

DI approach:
    - build_parser() / parse_args(): tested via importlib-loaded module.
    - Integration: subprocess calls against the actual script (same code path users run).
      No mocking framework — only plain subprocess + importlib.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ─── Constants ─────────────────────────────────────────────────────────────────

AURA_MSG_PATH = Path(__file__).parent.parent / "bin" / "aura-msg.py"
PYTHON = sys.executable

PLANNED_SUBCOMMANDS = [
    "start-epoch",
    "signal-vote",
    "query-state",
    "advance-phase",
]

# ─── Module loader ────────────────────────────────────────────────────────────


def _load_aura_msg() -> ModuleType:
    """Load bin/aura-msg.py as a Python module via importlib.

    Returns a fresh module (re-executed each call) for test isolation.
    aura-msg.py has no project-internal imports so no PYTHONPATH setup needed.
    """
    spec = importlib.util.spec_from_file_location("aura_msg", AURA_MSG_PATH)
    assert spec is not None, f"Could not create module spec for {AURA_MSG_PATH}"
    assert spec.loader is not None, "Module spec has no loader"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def aura_msg() -> ModuleType:
    return _load_aura_msg()


# ─── Filesystem checks ────────────────────────────────────────────────────────


class TestAuraMsgFile:
    """AC-M1: file exists and has correct shebang."""

    def test_file_exists(self) -> None:
        assert AURA_MSG_PATH.exists(), f"bin/aura-msg.py not found at {AURA_MSG_PATH}"

    def test_file_has_python3_shebang(self) -> None:
        first_line = AURA_MSG_PATH.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env python3", (
            f"Expected python3 shebang, got: {first_line!r}"
        )


# ─── Unit tests (importlib-loaded module) ─────────────────────────────────────


class TestBuildParser:
    """AC-M5: build_parser() returns parser with correct prog and subcommands."""

    def test_parser_prog(self, aura_msg: ModuleType) -> None:
        parser = aura_msg.build_parser()
        assert parser.prog == "aura-msg"

    @pytest.mark.parametrize("subcommand", PLANNED_SUBCOMMANDS)
    def test_each_subcommand_registered(
        self, aura_msg: ModuleType, subcommand: str
    ) -> None:
        """Each planned subcommand must be registered in the parser."""
        parser = aura_msg.build_parser()
        # parse_args([sub]) must not raise SystemExit
        args = parser.parse_args([subcommand])
        assert args.subcommand == subcommand


class TestParseArgs:
    """AC-M2, AC-M6: parse_args() defaults and subcommand routing."""

    def test_no_args_subcommand_is_none(self, aura_msg: ModuleType) -> None:
        """AC-M2: no args → subcommand is None (help branch in main)."""
        parser = aura_msg.build_parser()
        args = parser.parse_args([])
        assert args.subcommand is None

    @pytest.mark.parametrize("subcommand", PLANNED_SUBCOMMANDS)
    def test_subcommand_parsed_correctly(
        self, aura_msg: ModuleType, subcommand: str
    ) -> None:
        """AC-M6: each subcommand sets args.subcommand correctly."""
        parser = aura_msg.build_parser()
        args = parser.parse_args([subcommand])
        assert args.subcommand == subcommand


# ─── Integration tests (subprocess against production code path) ───────────────


class TestAuraMsgSubprocess:
    """Integration tests using the actual aura-msg.py script (same path users run)."""

    def test_no_args_exits_zero(self) -> None:
        """AC-M2: no subcommand → print help and exit 0."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 with no args, got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    def test_help_exits_zero(self) -> None:
        """AC-M3 (exit code): --help must exit 0."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"--help exited {result.returncode}.\nstdout: {result.stdout!r}"
        )

    @pytest.mark.parametrize("subcommand", PLANNED_SUBCOMMANDS)
    def test_help_contains_subcommand(self, subcommand: str) -> None:
        """AC-M3: --help output must mention each planned subcommand."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert subcommand in output, (
            f"'{subcommand}' not found in --help output.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("subcommand", PLANNED_SUBCOMMANDS)
    def test_subcommand_exits_one(self, subcommand: str) -> None:
        """AC-M4: each subcommand exits with code 1 (not implemented)."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), subcommand],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"'{subcommand}' exited {result.returncode}, expected 1.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize("subcommand", PLANNED_SUBCOMMANDS)
    def test_subcommand_stderr_not_implemented(self, subcommand: str) -> None:
        """AC-M4: each subcommand prints 'not implemented' to stderr."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), subcommand],
            capture_output=True,
            text=True,
        )
        assert "not implemented" in result.stderr.lower(), (
            f"'{subcommand}': expected 'not implemented' in stderr.\n"
            f"stderr: {result.stderr!r}"
        )
