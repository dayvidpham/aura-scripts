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
PYTHON = sys.executable

SUBCOMMAND_GROUPS = ["query", "epoch", "signal", "phase", "session"]

# ─── Module loader ────────────────────────────────────────────────────────────


def _load_aura_msg() -> ModuleType:
    """Load bin/aura-msg as a Python module via importlib."""
    loader = importlib.machinery.SourceFileLoader("aura_msg", str(AURA_MSG_PATH))
    spec = importlib.util.spec_from_file_location("aura_msg", AURA_MSG_PATH, loader=loader)
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

    @pytest.mark.parametrize("group", SUBCOMMAND_GROUPS)
    def test_each_group_registered(
        self, aura_msg: ModuleType, group: str
    ) -> None:
        """Each subcommand group must be recognized by the parser."""
        parser = aura_msg.build_parser()
        args = parser.parse_args([group])
        assert args.group == group


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


# ─── Integration tests (subprocess against production code path) ───────────────


class TestAuraMsgSubprocess:
    """Integration tests using the actual aura-msg script."""

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
        assert result.returncode == 0

    @pytest.mark.parametrize("group", SUBCOMMAND_GROUPS)
    def test_help_contains_group(self, group: str) -> None:
        """AC-M3: --help output must mention each subcommand group."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert group in output, (
            f"'{group}' not found in --help output.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    @pytest.mark.parametrize(
        "group,subcommand",
        [
            ("epoch", "start"),
            ("signal", "vote"),
            ("signal", "complete"),
            ("phase", "advance"),
            ("session", "register"),
        ],
    )
    def test_unimplemented_subcommand_exits_one(
        self, group: str, subcommand: str
    ) -> None:
        """AC-P2: unimplemented subcommands exit 1 with 'not implemented'."""
        result = subprocess.run(
            [PYTHON, str(AURA_MSG_PATH), group, subcommand],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"'{group} {subcommand}' exited {result.returncode}, expected 1.\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        assert "not implemented" in result.stderr.lower(), (
            f"'{group} {subcommand}': expected 'not implemented' in stderr.\n"
            f"stderr: {result.stderr!r}"
        )
