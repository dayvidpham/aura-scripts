"""Tests for bin/aurad.py — Temporal worker entry point (SLICE-1-L2).

BDD Acceptance Criteria:
    AC-W1: Given bin/aurad.py exists, when imported, then parse_args and main
           are present. Should not require a running Temporal server.
    AC-W2: Given bin/aurad.py with no args, when parse_args() is called, then
           namespace='default', task_queue='aura', server_address='localhost:7233'.
    AC-W3: Given explicit CLI flags, when parse_args() is called, then those
           values override defaults.
    AC-W4: Given TEMPORAL_NAMESPACE/TEMPORAL_TASK_QUEUE/TEMPORAL_ADDRESS env vars,
           when parse_args() is called with no CLI flags, then env var values used.
    AC-W5: Given both CLI flag and matching env var, when parse_args() is called,
           then CLI flag wins.
    AC-W6: Given --help flag, when invoked, then usage includes namespace,
           task-queue, and server-address.

Coverage strategy:
    - File exists + is executable (filesystem check)
    - Module importable via importlib (no Temporal server needed)
    - parse_args() default values (AC-W2) — pass argv=[] directly (no sys.argv patching)
    - parse_args() CLI override (AC-W3) — pass argv=[...] directly
    - parse_args() env var fallback (AC-W4) — use os.environ dict merge + restore
    - parse_args() CLI wins over env var (AC-W5) — combine argv + env dict
    - --help output contains expected flags (AC-W6)

DI approach:
    - parse_args(argv=...) accepts argv directly: no sys.argv patching needed.
    - Env var isolation: save/restore os.environ entries around each test.
      No mocking framework used — plain dict operations only.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Generator

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────

AURAD_PATH = Path(__file__).parent.parent / "bin" / "aurad.py"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

# Temporal env vars controlled by aurad.py
_TEMPORAL_ENV_VARS = ("TEMPORAL_NAMESPACE", "TEMPORAL_TASK_QUEUE", "TEMPORAL_ADDRESS")


def _load_aurad() -> ModuleType:
    """Load bin/aurad.py as a Python module via importlib.

    Each call returns a fresh module (re-executed). This ensures test
    isolation for global state (e.g. _AUDIT_TRAIL singleton reset).
    """
    # Ensure scripts/ is on sys.path so aura_protocol imports resolve.
    scripts_str = str(SCRIPTS_DIR)
    inserted = False
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)
        inserted = True
    try:
        spec = importlib.util.spec_from_file_location("aurad", AURAD_PATH)
        assert spec is not None, f"Could not create module spec for {AURAD_PATH}"
        assert spec.loader is not None, "Module spec has no loader"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    finally:
        if inserted and scripts_str in sys.path:
            sys.path.remove(scripts_str)


@contextmanager
def _clean_env(**overrides: str) -> Generator[None, None, None]:
    """Context manager that removes Temporal env vars then optionally sets overrides.

    Saves and restores any Temporal env vars that were set before the test.
    Uses plain dict operations — no mocking framework.

    Args:
        **overrides: Env var key=value pairs to set for the duration of the block.
    """
    saved: dict[str, str] = {}
    removed: list[str] = []

    # Save or note absence of each Temporal env var.
    for key in _TEMPORAL_ENV_VARS:
        if key in os.environ:
            saved[key] = os.environ[key]
            del os.environ[key]
        else:
            removed.append(key)

    # Apply any test-specific overrides.
    for key, value in overrides.items():
        os.environ[key] = value

    try:
        yield
    finally:
        # Remove any overrides we set.
        for key in overrides:
            if key in os.environ:
                del os.environ[key]
        # Restore previously-set Temporal env vars.
        for key, value in saved.items():
            os.environ[key] = value


# ─── Filesystem checks ────────────────────────────────────────────────────────


class TestAuradFile:
    def test_aurad_script_exists(self) -> None:
        assert AURAD_PATH.exists(), f"bin/aurad.py not found at {AURAD_PATH}"

    def test_aurad_script_is_executable(self) -> None:
        assert os.access(AURAD_PATH, os.X_OK), (
            f"bin/aurad.py is not executable — run: chmod +x {AURAD_PATH}"
        )


# ─── Import tests ─────────────────────────────────────────────────────────────


class TestAuradImport:
    """AC-W1: Module importable; exposes expected callables."""

    def test_module_imports_successfully(self) -> None:
        module = _load_aurad()
        assert module is not None

    def test_module_has_parse_args(self) -> None:
        module = _load_aurad()
        assert hasattr(module, "parse_args"), "parse_args() not found in aurad.py"
        assert callable(module.parse_args)

    def test_module_has_main(self) -> None:
        module = _load_aurad()
        assert hasattr(module, "main"), "main() not found in aurad.py"
        assert callable(module.main)

    def test_module_has_run_worker(self) -> None:
        module = _load_aurad()
        assert hasattr(module, "run_worker"), "run_worker() not found in aurad.py"
        assert callable(module.run_worker)


# ─── Arg parsing: defaults ────────────────────────────────────────────────────


class TestArgParsingDefaults:
    """AC-W2: Default values when no CLI args and no env vars."""

    def test_default_namespace(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args([])
        assert args.namespace == "default"

    def test_default_task_queue(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args([])
        assert args.task_queue == "aura"

    def test_default_server_address(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args([])
        assert args.server_address == "localhost:7233"


# ─── Arg parsing: CLI overrides ───────────────────────────────────────────────


class TestArgParsingCLI:
    """AC-W3: Explicit CLI flags override defaults."""

    def test_cli_namespace(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args(["--namespace", "my-namespace"])
        assert args.namespace == "my-namespace"

    def test_cli_task_queue(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args(["--task-queue", "my-queue"])
        assert args.task_queue == "my-queue"

    def test_cli_server_address(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args(["--server-address", "remote-host:7233"])
        assert args.server_address == "remote-host:7233"

    def test_all_cli_args_together(self) -> None:
        module = _load_aurad()
        with _clean_env():
            args = module.parse_args([
                "--namespace", "prod",
                "--task-queue", "aura-prod",
                "--server-address", "temporal.example.com:7233",
            ])
        assert args.namespace == "prod"
        assert args.task_queue == "aura-prod"
        assert args.server_address == "temporal.example.com:7233"


# ─── Arg parsing: env var fallbacks ──────────────────────────────────────────


class TestArgParsingEnvVars:
    """AC-W4: Env vars used when CLI args absent."""

    def test_env_namespace(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_NAMESPACE="env-namespace"):
            args = module.parse_args([])
        assert args.namespace == "env-namespace"

    def test_env_task_queue(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_TASK_QUEUE="env-queue"):
            args = module.parse_args([])
        assert args.task_queue == "env-queue"

    def test_env_server_address(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_ADDRESS="env-host:7233"):
            args = module.parse_args([])
        assert args.server_address == "env-host:7233"

    def test_all_env_vars(self) -> None:
        module = _load_aurad()
        with _clean_env(
            TEMPORAL_NAMESPACE="env-ns",
            TEMPORAL_TASK_QUEUE="env-q",
            TEMPORAL_ADDRESS="env-addr:7233",
        ):
            args = module.parse_args([])
        assert args.namespace == "env-ns"
        assert args.task_queue == "env-q"
        assert args.server_address == "env-addr:7233"


# ─── Arg parsing: CLI wins over env var ──────────────────────────────────────


class TestArgParsingPriority:
    """AC-W5: CLI flag wins over env var."""

    def test_cli_namespace_wins_over_env(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_NAMESPACE="env-ns"):
            args = module.parse_args(["--namespace", "cli-ns"])
        assert args.namespace == "cli-ns"

    def test_cli_task_queue_wins_over_env(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_TASK_QUEUE="env-queue"):
            args = module.parse_args(["--task-queue", "cli-queue"])
        assert args.task_queue == "cli-queue"

    def test_cli_address_wins_over_env(self) -> None:
        module = _load_aurad()
        with _clean_env(TEMPORAL_ADDRESS="env-host:7233"):
            args = module.parse_args(["--server-address", "cli-host:7233"])
        assert args.server_address == "cli-host:7233"

    def test_only_overridden_flag_wins(self) -> None:
        """CLI overrides only the flag it specifies; env var wins for the rest."""
        module = _load_aurad()
        with _clean_env(
            TEMPORAL_NAMESPACE="env-ns",
            TEMPORAL_TASK_QUEUE="env-queue",
        ):
            args = module.parse_args(["--namespace", "cli-ns"])
        assert args.namespace == "cli-ns"       # CLI wins
        assert args.task_queue == "env-queue"   # env var wins (no CLI flag)


# ─── --help output ────────────────────────────────────────────────────────────


class TestAuradHelp:
    """AC-W6: --help shows usage with expected flags."""

    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(AURAD_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert result.returncode == 0, f"--help exited {result.returncode}: {result.stderr}"

    def test_help_mentions_namespace(self) -> None:
        result = subprocess.run(
            [sys.executable, str(AURAD_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--namespace" in result.stdout, "--namespace not in --help output"

    def test_help_mentions_task_queue(self) -> None:
        result = subprocess.run(
            [sys.executable, str(AURAD_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--task-queue" in result.stdout, "--task-queue not in --help output"

    def test_help_mentions_server_address(self) -> None:
        result = subprocess.run(
            [sys.executable, str(AURAD_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--server-address" in result.stdout, "--server-address not in --help output"
