"""Tests for scripts/aura_protocol/config.py — SLICE-2-L2.

8-row test matrix (T1-T8) covering all priority pairs and error cases.
Priority: CLI > env > YAML > defaults.

BDD Acceptance Criteria (D24):
    T1: CLI wins — namespace=dev when cli=dev, env=staging, yaml=prod
    T2: Env wins over YAML+default — namespace=staging when cli=None, env=staging, yaml=prod
    T3: YAML wins over default — namespace=prod when cli=None, env=None, yaml=prod
    T4: Default used when all empty — namespace=default
    T5: CLI wins over YAML — namespace=dev when cli=dev, env=None, yaml=prod
    T6: Env wins over default — namespace=staging when cli=None, env=staging, yaml=None
    T7: Missing config file → graceful fallback to built-in defaults
    T8: Malformed YAML → graceful fallback to built-in defaults

DI pattern: resolve_connection(cli_args=..., env_dict=..., yaml_section=...)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aura_protocol.config import (
    ConnectionConfig,
    AuradConfig,
    AuraMsgConfig,
    default_config_path,
    load_yaml_section,
    resolve_connection,
)


# ── Dataclass smoke tests ────────────────────────────────────────────────────


class TestConnectionConfig:
    def test_defaults(self) -> None:
        cfg = ConnectionConfig()
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"

    def test_frozen(self) -> None:
        cfg = ConnectionConfig(namespace="prod")
        with pytest.raises((TypeError, AttributeError)):
            cfg.namespace = "dev"  # type: ignore[misc]


class TestAuradConfig:
    def test_defaults(self) -> None:
        cfg = AuradConfig()
        assert isinstance(cfg.connection, ConnectionConfig)
        assert cfg.audit_trail == "memory"

    def test_frozen(self) -> None:
        cfg = AuradConfig()
        with pytest.raises((TypeError, AttributeError)):
            cfg.audit_trail = "sqlite"  # type: ignore[misc]


class TestAuraMsgConfig:
    def test_defaults(self) -> None:
        cfg = AuraMsgConfig()
        assert isinstance(cfg.connection, ConnectionConfig)
        assert cfg.default_format == "json"

    def test_frozen(self) -> None:
        cfg = AuraMsgConfig()
        with pytest.raises((TypeError, AttributeError)):
            cfg.default_format = "text"  # type: ignore[misc]


# ── default_config_path ──────────────────────────────────────────────────────


class TestDefaultConfigPath:
    def test_returns_path(self) -> None:
        p = default_config_path()
        assert isinstance(p, Path)

    def test_contains_expected_segments(self) -> None:
        p = default_config_path()
        assert ".config" in str(p)
        assert "aura" in str(p)
        assert "aurad.config.yaml" in str(p)


# ── load_yaml_section ────────────────────────────────────────────────────────


class TestLoadYamlSection:
    def test_loads_section(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "cfg.yaml"
        yaml_file.write_text("aurad:\n  namespace: prod\n")
        result = load_yaml_section(yaml_file, "aurad")
        assert result == {"namespace": "prod"}

    def test_missing_section_returns_empty(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "cfg.yaml"
        yaml_file.write_text("aurad:\n  namespace: prod\n")
        result = load_yaml_section(yaml_file, "aura-msg")
        assert result == {}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_yaml_section(tmp_path / "nonexistent.yaml", "aurad")
        assert result == {}

    def test_malformed_yaml_returns_empty(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("aurad: [unclosed")
        result = load_yaml_section(yaml_file, "aurad")
        assert result == {}


# ── resolve_connection — 8-row matrix ────────────────────────────────────────


class TestResolveConnection:
    """T1-T8: priority resolution matrix."""

    def test_T1_cli_wins_over_all(self) -> None:
        """T1: CLI wins — namespace=dev when cli=dev, env=staging, yaml=prod."""
        cfg = resolve_connection(
            cli_args={"namespace": "dev", "task_queue": None, "server_address": None},
            env_dict={"TEMPORAL_NAMESPACE": "staging"},
            yaml_section={"namespace": "prod"},
        )
        assert cfg.namespace == "dev"

    def test_T2_env_wins_over_yaml_and_default(self) -> None:
        """T2: Env wins — namespace=staging when cli=None, env=staging, yaml=prod."""
        cfg = resolve_connection(
            cli_args={"namespace": None, "task_queue": None, "server_address": None},
            env_dict={"TEMPORAL_NAMESPACE": "staging"},
            yaml_section={"namespace": "prod"},
        )
        assert cfg.namespace == "staging"

    def test_T3_yaml_wins_over_default(self) -> None:
        """T3: YAML wins — namespace=prod when cli=None, env=None, yaml=prod."""
        cfg = resolve_connection(
            cli_args={"namespace": None, "task_queue": None, "server_address": None},
            env_dict={},
            yaml_section={"namespace": "prod"},
        )
        assert cfg.namespace == "prod"

    def test_T4_default_when_all_empty(self) -> None:
        """T4: Default used when all empty."""
        cfg = resolve_connection(
            cli_args={"namespace": None, "task_queue": None, "server_address": None},
            env_dict={},
            yaml_section={},
        )
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"

    def test_T5_cli_wins_over_yaml(self) -> None:
        """T5: CLI wins — namespace=dev when cli=dev, env=None, yaml=prod."""
        cfg = resolve_connection(
            cli_args={"namespace": "dev", "task_queue": None, "server_address": None},
            env_dict={},
            yaml_section={"namespace": "prod"},
        )
        assert cfg.namespace == "dev"

    def test_T6_env_wins_over_default(self) -> None:
        """T6: Env wins — namespace=staging when cli=None, env=staging, yaml=None."""
        cfg = resolve_connection(
            cli_args={"namespace": None, "task_queue": None, "server_address": None},
            env_dict={"TEMPORAL_NAMESPACE": "staging"},
            yaml_section={},
        )
        assert cfg.namespace == "staging"

    def test_T7_missing_yaml_file_uses_defaults(self) -> None:
        """T7: Missing config file → graceful fallback to built-in defaults."""
        # Simulate caller passing empty yaml_section (from failed load_yaml_section)
        cfg = resolve_connection(
            cli_args=None,
            env_dict={},
            yaml_section={},
        )
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"

    def test_T8_malformed_yaml_uses_defaults(self) -> None:
        """T8: Malformed YAML → graceful fallback to built-in defaults."""
        # Caller passes empty dict from failed load_yaml_section (malformed yaml)
        cfg = resolve_connection(
            cli_args=None,
            env_dict=None,
            yaml_section={},
        )
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"

    def test_all_fields_resolved_independently(self) -> None:
        """Each field resolves independently by priority."""
        cfg = resolve_connection(
            cli_args={"namespace": "cli-ns", "task_queue": None, "server_address": None},
            env_dict={"TEMPORAL_TASK_QUEUE": "env-queue"},
            yaml_section={"server_address": "yaml-host:9999"},
        )
        assert cfg.namespace == "cli-ns"
        assert cfg.task_queue == "env-queue"
        assert cfg.server_address == "yaml-host:9999"

    def test_none_args_uses_defaults(self) -> None:
        """Passing all None falls back to defaults."""
        cfg = resolve_connection()
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"
