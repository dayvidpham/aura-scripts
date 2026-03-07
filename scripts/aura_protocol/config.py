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


# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_NAMESPACE = "default"
DEFAULT_TASK_QUEUE = "aura"
DEFAULT_SERVER_ADDRESS = "localhost:7233"

# ─── Env var names ───────────────────────────────────────────────────────────

ENV_NAMESPACE = "TEMPORAL_NAMESPACE"
ENV_TASK_QUEUE = "TEMPORAL_TASK_QUEUE"
ENV_SERVER_ADDRESS = "TEMPORAL_ADDRESS"


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
    audit_trail: str = "memory"


@dataclass(frozen=True)
class AuraMsgConfig:
    """Configuration for the aura-msg CLI tool."""

    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    default_format: str = "text"


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
