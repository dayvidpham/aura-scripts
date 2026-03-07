"""Tests for scripts/aura_protocol/config.py — config resolution module (SLICE-2).

BDD Acceptance Criteria (D24 — 8-row config resolution matrix):
    T1: CLI wins over env and YAML (--namespace dev overrides env staging, yaml prod)
    T2: Env wins over YAML and default
    T3: YAML wins over default
    T4: Default used when all sources empty
    T5: CLI wins over YAML (no env)
    T6: Env wins over default (no YAML)
    T7: Missing config file → graceful fallback to defaults
    T8: Malformed YAML → graceful fallback to defaults

DI approach:
    resolve_connection(cli_args=..., env_dict=..., yaml_section=...) accepts
    all sources as explicit parameters — no sys.argv or os.environ patching.
    load_yaml_section() tested with tmp_path fixture files.
"""

from __future__ import annotations

from pathlib import Path

from aura_protocol.config import (
    DEFAULT_NAMESPACE,
    DEFAULT_SERVER_ADDRESS,
    DEFAULT_TASK_QUEUE,
    AuradConfig,
    AuraMsgConfig,
    ConnectionConfig,
    default_config_path,
    load_yaml_section,
    resolve_connection,
)


# ─── Dataclass tests ────────────────────────────────────────────────────────


class TestConnectionConfig:
    def test_defaults(self) -> None:
        cfg = ConnectionConfig()
        assert cfg.namespace == "default"
        assert cfg.task_queue == "aura"
        assert cfg.server_address == "localhost:7233"

    def test_frozen(self) -> None:
        cfg = ConnectionConfig()
        try:
            cfg.namespace = "changed"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_custom_values(self) -> None:
        cfg = ConnectionConfig(namespace="prod", task_queue="q", server_address="host:1234")
        assert cfg.namespace == "prod"
        assert cfg.task_queue == "q"
        assert cfg.server_address == "host:1234"


class TestAuradConfig:
    def test_defaults(self) -> None:
        cfg = AuradConfig()
        assert cfg.connection == ConnectionConfig()
        assert cfg.audit_trail == "memory"

    def test_frozen(self) -> None:
        cfg = AuradConfig()
        try:
            cfg.audit_trail = "sqlite"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_custom_connection(self) -> None:
        conn = ConnectionConfig(namespace="dev")
        cfg = AuradConfig(connection=conn, audit_trail="sqlite")
        assert cfg.connection.namespace == "dev"
        assert cfg.audit_trail == "sqlite"


class TestAuraMsgConfig:
    def test_defaults(self) -> None:
        cfg = AuraMsgConfig()
        assert cfg.connection == ConnectionConfig()
        assert cfg.default_format == "text"

    def test_frozen(self) -> None:
        cfg = AuraMsgConfig()
        try:
            cfg.default_format = "json"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_custom(self) -> None:
        conn = ConnectionConfig(namespace="staging")
        cfg = AuraMsgConfig(connection=conn, default_format="json")
        assert cfg.connection.namespace == "staging"
        assert cfg.default_format == "json"


# ─── default_config_path ────────────────────────────────────────────────────


class TestDefaultConfigPath:
    def test_returns_path(self) -> None:
        p = default_config_path()
        assert isinstance(p, Path)

    def test_path_ends_with_expected(self) -> None:
        p = default_config_path()
        assert p.name == "aurad.config.yaml"
        assert p.parent.name == "plugins"
        assert p.parent.parent.name == "aura"


# ─── load_yaml_section ─────────────────────────────────────────────────────


class TestLoadYamlSection:
    def test_loads_existing_section(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "aurad:\n"
            "  namespace: yaml-ns\n"
            "  task_queue: yaml-q\n"
            "aura-msg:\n"
            "  namespace: msg-ns\n"
        )
        result = load_yaml_section(cfg_file, "aurad")
        assert result == {"namespace": "yaml-ns", "task_queue": "yaml-q"}

    def test_missing_section_returns_empty(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("aurad:\n  namespace: x\n")
        result = load_yaml_section(cfg_file, "nonexistent")
        assert result == {}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_yaml_section(tmp_path / "does_not_exist.yaml", "aurad")
        assert result == {}

    def test_malformed_yaml_returns_empty(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text("{{{{not yaml at all: [[[")
        result = load_yaml_section(cfg_file, "aurad")
        assert result == {}

    def test_non_dict_yaml_returns_empty(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "scalar.yaml"
        cfg_file.write_text("just a string\n")
        result = load_yaml_section(cfg_file, "aurad")
        assert result == {}

    def test_section_value_not_dict_returns_empty(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("aurad: just-a-string\n")
        result = load_yaml_section(cfg_file, "aurad")
        assert result == {}


# ─── resolve_connection: 8-row matrix (T1-T8) ──────────────────────────────


class TestResolveConnectionMatrix:
    """D24: Config test matrix — 8 rows covering all priority pairs + error cases."""

    def test_t1_cli_wins_over_all(self) -> None:
        """T1: CLI=dev, env=staging, yaml=prod → dev (CLI wins)."""
        result = resolve_connection(
            cli_args={"namespace": "dev", "task_queue": "cli-q", "server_address": "cli:7233"},
            env_dict={
                "TEMPORAL_NAMESPACE": "staging",
                "TEMPORAL_TASK_QUEUE": "env-q",
                "TEMPORAL_ADDRESS": "env:7233",
            },
            yaml_section={
                "namespace": "prod",
                "task_queue": "yaml-q",
                "server_address": "yaml:7233",
            },
        )
        assert result.namespace == "dev"
        assert result.task_queue == "cli-q"
        assert result.server_address == "cli:7233"

    def test_t2_env_wins_over_yaml_and_default(self) -> None:
        """T2: No CLI, env=staging, yaml=prod → staging (env wins)."""
        result = resolve_connection(
            cli_args=None,
            env_dict={
                "TEMPORAL_NAMESPACE": "staging",
                "TEMPORAL_TASK_QUEUE": "env-q",
                "TEMPORAL_ADDRESS": "env:7233",
            },
            yaml_section={
                "namespace": "prod",
                "task_queue": "yaml-q",
                "server_address": "yaml:7233",
            },
        )
        assert result.namespace == "staging"
        assert result.task_queue == "env-q"
        assert result.server_address == "env:7233"

    def test_t3_yaml_wins_over_default(self) -> None:
        """T3: No CLI, no env, yaml=prod → prod (YAML wins)."""
        result = resolve_connection(
            cli_args=None,
            env_dict=None,
            yaml_section={
                "namespace": "prod",
                "task_queue": "yaml-q",
                "server_address": "yaml:7233",
            },
        )
        assert result.namespace == "prod"
        assert result.task_queue == "yaml-q"
        assert result.server_address == "yaml:7233"

    def test_t4_default_used_when_all_empty(self) -> None:
        """T4: No CLI, no env, no YAML → built-in defaults."""
        result = resolve_connection(
            cli_args=None,
            env_dict=None,
            yaml_section=None,
        )
        assert result.namespace == DEFAULT_NAMESPACE
        assert result.task_queue == DEFAULT_TASK_QUEUE
        assert result.server_address == DEFAULT_SERVER_ADDRESS

    def test_t5_cli_wins_over_yaml_no_env(self) -> None:
        """T5: CLI=dev, no env, yaml=prod → dev (CLI wins over YAML)."""
        result = resolve_connection(
            cli_args={"namespace": "dev", "task_queue": "cli-q", "server_address": "cli:7233"},
            env_dict=None,
            yaml_section={
                "namespace": "prod",
                "task_queue": "yaml-q",
                "server_address": "yaml:7233",
            },
        )
        assert result.namespace == "dev"
        assert result.task_queue == "cli-q"
        assert result.server_address == "cli:7233"

    def test_t6_env_wins_over_default_no_yaml(self) -> None:
        """T6: No CLI, env=staging, no YAML → staging (env wins over default)."""
        result = resolve_connection(
            cli_args=None,
            env_dict={
                "TEMPORAL_NAMESPACE": "staging",
                "TEMPORAL_TASK_QUEUE": "env-q",
                "TEMPORAL_ADDRESS": "env:7233",
            },
            yaml_section=None,
        )
        assert result.namespace == "staging"
        assert result.task_queue == "env-q"
        assert result.server_address == "env:7233"

    def test_t7_missing_yaml_file_uses_defaults(self, tmp_path: Path) -> None:
        """T7: No YAML file → graceful fallback to built-in defaults."""
        yaml_section = load_yaml_section(tmp_path / "nonexistent.yaml", "aurad")
        result = resolve_connection(
            cli_args=None,
            env_dict=None,
            yaml_section=yaml_section,
        )
        assert result.namespace == DEFAULT_NAMESPACE
        assert result.task_queue == DEFAULT_TASK_QUEUE
        assert result.server_address == DEFAULT_SERVER_ADDRESS

    def test_t8_malformed_yaml_uses_defaults(self, tmp_path: Path) -> None:
        """T8: Malformed YAML → graceful fallback to built-in defaults."""
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text("{{{{not yaml at all: [[[")
        yaml_section = load_yaml_section(cfg_file, "aurad")
        result = resolve_connection(
            cli_args=None,
            env_dict=None,
            yaml_section=yaml_section,
        )
        assert result.namespace == DEFAULT_NAMESPACE
        assert result.task_queue == DEFAULT_TASK_QUEUE
        assert result.server_address == DEFAULT_SERVER_ADDRESS


# ─── resolve_connection: partial overrides ──────────────────────────────────


class TestResolveConnectionPartialOverrides:
    """Edge cases: partial sources, mixed levels."""

    def test_cli_partial_override(self) -> None:
        """CLI overrides only namespace; env provides task_queue; YAML provides server_address."""
        result = resolve_connection(
            cli_args={"namespace": "cli-ns"},
            env_dict={"TEMPORAL_TASK_QUEUE": "env-q"},
            yaml_section={"server_address": "yaml:7233"},
        )
        assert result.namespace == "cli-ns"
        assert result.task_queue == "env-q"
        assert result.server_address == "yaml:7233"

    def test_cli_none_values_treated_as_unset(self) -> None:
        """CLI dict with None values falls through to next priority."""
        result = resolve_connection(
            cli_args={"namespace": None, "task_queue": "cli-q"},
            env_dict={"TEMPORAL_NAMESPACE": "env-ns"},
            yaml_section=None,
        )
        assert result.namespace == "env-ns"
        assert result.task_queue == "cli-q"

    def test_empty_dicts_use_defaults(self) -> None:
        """Empty dicts (not None) still fall through to defaults."""
        result = resolve_connection(
            cli_args={},
            env_dict={},
            yaml_section={},
        )
        assert result == ConnectionConfig()
