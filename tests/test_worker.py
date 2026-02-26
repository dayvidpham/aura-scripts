"""Tests for bin/worker.py — Temporal worker entry point (SLICE-4-L2).

BDD Acceptance Criteria:
    AC-W1: Given bin/worker.py exists, when imported, then parse_args and main
           are present. Should not require a running Temporal server.
    AC-W2: Given bin/worker.py with no args, when parse_args() is called, then
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
    - parse_args() default values (AC-W2)
    - parse_args() CLI override (AC-W3)
    - parse_args() env var fallback (AC-W4)
    - parse_args() CLI wins over env var (AC-W5)
    - --help output contains expected flags (AC-W6)
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────

WORKER_PATH = Path(__file__).parent.parent / "bin" / "worker.py"
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _load_worker() -> ModuleType:
    """Load bin/worker.py as a Python module via importlib.

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
        spec = importlib.util.spec_from_file_location("worker", WORKER_PATH)
        assert spec is not None, f"Could not create module spec for {WORKER_PATH}"
        assert spec.loader is not None, "Module spec has no loader"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    finally:
        if inserted and scripts_str in sys.path:
            sys.path.remove(scripts_str)


# ─── Filesystem checks ────────────────────────────────────────────────────────


class TestWorkerFile:
    def test_worker_script_exists(self) -> None:
        assert WORKER_PATH.exists(), f"bin/worker.py not found at {WORKER_PATH}"

    def test_worker_script_is_executable(self) -> None:
        assert os.access(WORKER_PATH, os.X_OK), (
            f"bin/worker.py is not executable — run: chmod +x {WORKER_PATH}"
        )


# ─── Import tests ─────────────────────────────────────────────────────────────


class TestWorkerImport:
    """AC-W1: Module importable; exposes expected callables."""

    def test_module_imports_successfully(self) -> None:
        module = _load_worker()
        assert module is not None

    def test_module_has_parse_args(self) -> None:
        module = _load_worker()
        assert hasattr(module, "parse_args"), "parse_args() not found in worker.py"
        assert callable(module.parse_args)

    def test_module_has_main(self) -> None:
        module = _load_worker()
        assert hasattr(module, "main"), "main() not found in worker.py"
        assert callable(module.main)

    def test_module_has_run_worker(self) -> None:
        module = _load_worker()
        assert hasattr(module, "run_worker"), "run_worker() not found in worker.py"
        assert callable(module.run_worker)


# ─── Arg parsing: defaults ────────────────────────────────────────────────────


class TestArgParsingDefaults:
    """AC-W2: Default values when no CLI args and no env vars."""

    def _parse(self, argv: list[str] | None = None, env: dict | None = None) -> object:
        module = _load_worker()
        argv = argv or ["worker"]
        # Scrub Temporal env vars so test environment doesn't interfere.
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("TEMPORAL_NAMESPACE", "TEMPORAL_TASK_QUEUE", "TEMPORAL_ADDRESS")
        }
        if env:
            clean_env.update(env)
        with mock.patch("sys.argv", argv), mock.patch.dict(
            "os.environ", clean_env, clear=True
        ):
            return module.parse_args()

    def test_default_namespace(self) -> None:
        args = self._parse()
        assert args.namespace == "default"

    def test_default_task_queue(self) -> None:
        args = self._parse()
        assert args.task_queue == "aura"

    def test_default_server_address(self) -> None:
        args = self._parse()
        assert args.server_address == "localhost:7233"


# ─── Arg parsing: CLI overrides ───────────────────────────────────────────────


class TestArgParsingCLI:
    """AC-W3: Explicit CLI flags override defaults."""

    def _parse(self, extra_argv: list[str], env: dict | None = None) -> object:
        module = _load_worker()
        argv = ["worker"] + extra_argv
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("TEMPORAL_NAMESPACE", "TEMPORAL_TASK_QUEUE", "TEMPORAL_ADDRESS")
        }
        if env:
            clean_env.update(env)
        with mock.patch("sys.argv", argv), mock.patch.dict(
            "os.environ", clean_env, clear=True
        ):
            return module.parse_args()

    def test_cli_namespace(self) -> None:
        args = self._parse(["--namespace", "my-namespace"])
        assert args.namespace == "my-namespace"

    def test_cli_task_queue(self) -> None:
        args = self._parse(["--task-queue", "my-queue"])
        assert args.task_queue == "my-queue"

    def test_cli_server_address(self) -> None:
        args = self._parse(["--server-address", "remote-host:7233"])
        assert args.server_address == "remote-host:7233"

    def test_all_cli_args_together(self) -> None:
        args = self._parse(
            [
                "--namespace", "prod",
                "--task-queue", "aura-prod",
                "--server-address", "temporal.example.com:7233",
            ]
        )
        assert args.namespace == "prod"
        assert args.task_queue == "aura-prod"
        assert args.server_address == "temporal.example.com:7233"


# ─── Arg parsing: env var fallbacks ──────────────────────────────────────────


class TestArgParsingEnvVars:
    """AC-W4: Env vars used when CLI args absent."""

    def _parse(self, env: dict) -> object:
        module = _load_worker()
        # Start from a clean env to avoid interference from test runner env.
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("TEMPORAL_NAMESPACE", "TEMPORAL_TASK_QUEUE", "TEMPORAL_ADDRESS")
        }
        clean_env.update(env)
        with mock.patch("sys.argv", ["worker"]), mock.patch.dict(
            "os.environ", clean_env, clear=True
        ):
            return module.parse_args()

    def test_env_namespace(self) -> None:
        args = self._parse({"TEMPORAL_NAMESPACE": "env-namespace"})
        assert args.namespace == "env-namespace"

    def test_env_task_queue(self) -> None:
        args = self._parse({"TEMPORAL_TASK_QUEUE": "env-queue"})
        assert args.task_queue == "env-queue"

    def test_env_server_address(self) -> None:
        args = self._parse({"TEMPORAL_ADDRESS": "env-host:7233"})
        assert args.server_address == "env-host:7233"

    def test_all_env_vars(self) -> None:
        args = self._parse(
            {
                "TEMPORAL_NAMESPACE": "env-ns",
                "TEMPORAL_TASK_QUEUE": "env-q",
                "TEMPORAL_ADDRESS": "env-addr:7233",
            }
        )
        assert args.namespace == "env-ns"
        assert args.task_queue == "env-q"
        assert args.server_address == "env-addr:7233"


# ─── Arg parsing: CLI wins over env var ──────────────────────────────────────


class TestArgParsingPriority:
    """AC-W5: CLI flag wins over env var."""

    def _parse(self, extra_argv: list[str], env: dict) -> object:
        module = _load_worker()
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("TEMPORAL_NAMESPACE", "TEMPORAL_TASK_QUEUE", "TEMPORAL_ADDRESS")
        }
        clean_env.update(env)
        with mock.patch("sys.argv", ["worker"] + extra_argv), mock.patch.dict(
            "os.environ", clean_env, clear=True
        ):
            return module.parse_args()

    def test_cli_namespace_wins_over_env(self) -> None:
        args = self._parse(
            ["--namespace", "cli-ns"],
            {"TEMPORAL_NAMESPACE": "env-ns"},
        )
        assert args.namespace == "cli-ns"

    def test_cli_task_queue_wins_over_env(self) -> None:
        args = self._parse(
            ["--task-queue", "cli-queue"],
            {"TEMPORAL_TASK_QUEUE": "env-queue"},
        )
        assert args.task_queue == "cli-queue"

    def test_cli_address_wins_over_env(self) -> None:
        args = self._parse(
            ["--server-address", "cli-host:7233"],
            {"TEMPORAL_ADDRESS": "env-host:7233"},
        )
        assert args.server_address == "cli-host:7233"

    def test_only_overridden_flag_wins(self) -> None:
        """CLI overrides only the flag it specifies; env var wins for the rest."""
        args = self._parse(
            ["--namespace", "cli-ns"],
            {
                "TEMPORAL_NAMESPACE": "env-ns",
                "TEMPORAL_TASK_QUEUE": "env-queue",
            },
        )
        assert args.namespace == "cli-ns"       # CLI wins
        assert args.task_queue == "env-queue"   # env var wins (no CLI flag)


# ─── --help output ────────────────────────────────────────────────────────────


class TestWorkerHelp:
    """AC-W6: --help shows usage with expected flags."""

    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(WORKER_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert result.returncode == 0, f"--help exited {result.returncode}: {result.stderr}"

    def test_help_mentions_namespace(self) -> None:
        result = subprocess.run(
            [sys.executable, str(WORKER_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--namespace" in result.stdout, "--namespace not in --help output"

    def test_help_mentions_task_queue(self) -> None:
        result = subprocess.run(
            [sys.executable, str(WORKER_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--task-queue" in result.stdout, "--task-queue not in --help output"

    def test_help_mentions_server_address(self) -> None:
        result = subprocess.run(
            [sys.executable, str(WORKER_PATH), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        assert "--server-address" in result.stdout, "--server-address not in --help output"
