"""Configuration module for aurad and aura-msg.

Provides frozen dataclasses for connection and daemon configuration,
plus functions to resolve config from CLI args, environment variables,
and YAML config files with priority: CLI > env > YAML > defaults.

Config file location: ~/.config/aura/plugins/aurad.config.yaml
Sections: 'aurad' and 'aura-msg', each with connection params.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from aura_protocol.types import AuditTrailBackend, OutputFormat


# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_NAMESPACE = "default"
DEFAULT_TASK_QUEUE = "aura"
DEFAULT_SERVER_ADDRESS = "localhost:7233"
DEFAULT_AUDIT_DB_PATH = Path.home() / ".local" / "share" / "aura" / "plugin" / "audit.db"

# ─── Env var names ───────────────────────────────────────────────────────────

ENV_NAMESPACE = "TEMPORAL_NAMESPACE"
ENV_TASK_QUEUE = "TEMPORAL_TASK_QUEUE"
ENV_SERVER_ADDRESS = "TEMPORAL_ADDRESS"
ENV_AUDIT_TRAIL = "AURAD_AUDIT_TRAIL"
ENV_AUDIT_DB_PATH = "AURAD_AUDIT_DB_PATH"


# ─── Frozen Dataclasses ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectionConfig:
    """Temporal connection parameters (shared by aurad and aura-msg)."""

    namespace: str = DEFAULT_NAMESPACE
    task_queue: str = DEFAULT_TASK_QUEUE
    server_address: str = DEFAULT_SERVER_ADDRESS


@dataclass(frozen=True)
class AuradConfig:
    """Configuration for the aurad Temporal worker daemon."""

    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    audit_trail: AuditTrailBackend = AuditTrailBackend.Memory
    audit_db_path: Path = field(default_factory=lambda: DEFAULT_AUDIT_DB_PATH)


@dataclass(frozen=True)
class AuraMsgConfig:
    """Configuration for the aura-msg CLI tool."""

    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    default_format: OutputFormat = OutputFormat.Text


# ─── Functions ───────────────────────────────────────────────────────────────


def default_config_path() -> Path:
    """Return the default config file path: ~/.config/aura/plugins/aurad.config.yaml."""
    return Path.home() / ".config" / "aura" / "plugins" / "aurad.config.yaml"


def load_yaml_section(path: Path | str, section: str) -> dict[str, Any]:
    """Load a named section from a YAML config file.

    Args:
        path: Path to the YAML config file.
        section: Top-level key to extract (e.g. 'aurad' or 'aura-msg').

    Returns:
        Dict of key-value pairs from the section, or empty dict if
        the file is missing, unreadable, malformed, or lacks the section.
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return {}

    if not isinstance(data, dict):
        return {}

    result = data.get(section)
    if not isinstance(result, dict):
        return {}

    return result


def resolve_connection(
    *,
    cli_args: dict[str, str] | None = None,
    env_dict: dict[str, str] | None = None,
    yaml_section: dict[str, Any] | None = None,
) -> ConnectionConfig:
    """Resolve connection config with priority: CLI > env > YAML > defaults.

    All parameters use DI for testability — no sys.argv or os.environ access.

    Args:
        cli_args: Dict with optional keys 'namespace', 'task_queue', 'server_address'.
                  Values of None within the dict are treated as unset.
        env_dict: Dict with optional keys matching TEMPORAL_NAMESPACE,
                  TEMPORAL_TASK_QUEUE, TEMPORAL_ADDRESS env var names.
        yaml_section: Dict loaded from YAML config section, with optional keys
                      'namespace', 'task_queue', 'server_address'.

    Returns:
        Frozen ConnectionConfig with resolved values.
    """
    cli = cli_args or {}
    env = env_dict or {}
    yml = yaml_section or {}

    def _resolve(cli_key: str, env_key: str, yaml_key: str, default: str) -> str:
        # CLI highest priority
        cli_val = cli.get(cli_key)
        if cli_val is not None:
            return cli_val
        # Env next
        env_val = env.get(env_key)
        if env_val is not None:
            return env_val
        # YAML next
        yaml_val = yml.get(yaml_key)
        if yaml_val is not None:
            return str(yaml_val)
        # Default
        return default

    return ConnectionConfig(
        namespace=_resolve("namespace", ENV_NAMESPACE, "namespace", DEFAULT_NAMESPACE),
        task_queue=_resolve("task_queue", ENV_TASK_QUEUE, "task_queue", DEFAULT_TASK_QUEUE),
        server_address=_resolve(
            "server_address", ENV_SERVER_ADDRESS, "server_address", DEFAULT_SERVER_ADDRESS
        ),
    )


def resolve_aurad_config(
    *,
    cli_args: dict[str, str] | None = None,
    env_dict: dict[str, str] | None = None,
    yaml_section: dict[str, Any] | None = None,
) -> AuradConfig:
    """Resolve full aurad config with priority: CLI > env > YAML > defaults.

    Args:
        cli_args: Dict with connection keys + optional 'audit_trail', 'audit_db_path'.
        env_dict: Dict with env vars (TEMPORAL_*, AURAD_AUDIT_TRAIL, AURAD_AUDIT_DB_PATH).
        yaml_section: Dict from YAML 'aurad' section.

    Returns:
        Frozen AuradConfig with resolved values.
    """
    conn = resolve_connection(cli_args=cli_args, env_dict=env_dict, yaml_section=yaml_section)
    cli = cli_args or {}
    env = env_dict or {}
    yml = yaml_section or {}

    # Resolve audit_trail: CLI > env > YAML > default
    trail_str = (
        cli.get("audit_trail")
        or env.get(ENV_AUDIT_TRAIL)
        or yml.get("audit_trail")
    )
    audit_trail = AuditTrailBackend(trail_str) if trail_str else AuditTrailBackend.Memory

    # Resolve audit_db_path: CLI > YAML > XDG_DATA_HOME > default
    db_path_str = (
        cli.get("audit_db_path")
        or yml.get("audit_db_path")
        or env.get(ENV_AUDIT_DB_PATH)
    )
    audit_db_path = Path(db_path_str) if db_path_str else DEFAULT_AUDIT_DB_PATH

    return AuradConfig(
        connection=conn,
        audit_trail=audit_trail,
        audit_db_path=audit_db_path,
    )


def resolve_aura_msg_config(
    *,
    cli_args: dict[str, str] | None = None,
    env_dict: dict[str, str] | None = None,
    yaml_section: dict[str, Any] | None = None,
) -> AuraMsgConfig:
    """Resolve full aura-msg config with priority: CLI > env > YAML > defaults.

    Args:
        cli_args: Dict with connection keys + optional 'default_format'.
        env_dict: Dict with env vars (TEMPORAL_*).
        yaml_section: Dict from YAML 'aura-msg' section.

    Returns:
        Frozen AuraMsgConfig with resolved values.
    """
    conn = resolve_connection(cli_args=cli_args, env_dict=env_dict, yaml_section=yaml_section)
    yml = yaml_section or {}
    cli = cli_args or {}

    fmt_str = cli.get("default_format") or yml.get("default_format")
    default_format = OutputFormat(fmt_str) if fmt_str else OutputFormat.Text

    return AuraMsgConfig(
        connection=conn,
        default_format=default_format,
    )
