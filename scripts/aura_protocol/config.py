"""Shared configuration module for aurad and aura-msg.

Priority (highest → lowest):
    1. Explicit CLI flag (e.g. --namespace my-ns)
    2. Environment variable (e.g. TEMPORAL_NAMESPACE=my-ns)
    3. YAML config file (~/.config/aura/plugins/aurad.config.yaml)
    4. Built-in defaults ("default", "aura", "localhost:7233")

Config file layout:
    aurad:
      namespace: aura
      task_queue: aura
      server_address: localhost:7233

    aura-msg:
      namespace: aura
      task_queue: aura
      server_address: localhost:7233
      default_format: json
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConnectionConfig:
    """Temporal connection parameters shared by aurad and aura-msg."""

    namespace: str = "default"
    task_queue: str = "aura"
    server_address: str = "localhost:7233"


@dataclass(frozen=True)
class AuradConfig:
    """Full configuration for the aurad daemon."""

    connection: ConnectionConfig = None  # type: ignore[assignment]
    audit_trail: str = "memory"

    def __post_init__(self) -> None:
        # Default mutable field workaround for frozen dataclass
        if self.connection is None:
            object.__setattr__(self, "connection", ConnectionConfig())


@dataclass(frozen=True)
class AuraMsgConfig:
    """Full configuration for the aura-msg CLI."""

    connection: ConnectionConfig = None  # type: ignore[assignment]
    default_format: str = "json"

    def __post_init__(self) -> None:
        if self.connection is None:
            object.__setattr__(self, "connection", ConnectionConfig())


# ── Functions ─────────────────────────────────────────────────────────────────


def default_config_path() -> Path:
    """Return the default config file path: ~/.config/aura/plugins/aurad.config.yaml."""
    return Path.home() / ".config" / "aura" / "plugins" / "aurad.config.yaml"


def load_yaml_section(path: Path, section: str) -> dict[str, Any]:
    """Load a named section from a YAML config file.

    Returns an empty dict if the file is missing, the section is absent,
    or the YAML is malformed — callers always get a plain dict.

    Args:
        path:    Path to the YAML config file.
        section: Top-level key to extract (e.g. "aurad" or "aura-msg").

    Returns:
        Dict of values under the section key, or {} on any error.
    """
    try:
        import yaml

        text = path.read_text()
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return {}
        section_data = data.get(section)
        if not isinstance(section_data, dict):
            return {}
        return section_data
    except Exception:
        return {}


def resolve_connection(
    cli_args: dict[str, str | None] | None = None,
    env_dict: dict[str, str] | None = None,
    yaml_section: dict[str, Any] | None = None,
) -> ConnectionConfig:
    """Resolve Temporal connection parameters with CLI > env > YAML > defaults.

    Each field is resolved independently.  The first non-None source wins:
        CLI flag → environment variable → YAML value → built-in default.

    Args:
        cli_args:     Mapping with keys "namespace", "task_queue",
                      "server_address". A None value means "not provided".
        env_dict:     Environment variable mapping.  Expected keys:
                      TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE, TEMPORAL_ADDRESS.
        yaml_section: Pre-parsed YAML section dict (output of load_yaml_section).

    Returns:
        Resolved ConnectionConfig with the highest-priority non-None value
        for each field.
    """
    cli = cli_args or {}
    env = env_dict or {}
    yaml = yaml_section or {}

    _defaults = ConnectionConfig()

    def _resolve(cli_key: str, env_key: str, yaml_key: str, default: str) -> str:
        cli_val = cli.get(cli_key)
        if cli_val is not None:
            return cli_val
        env_val = env.get(env_key)
        if env_val is not None:
            return env_val
        yaml_val = yaml.get(yaml_key)
        if yaml_val is not None:
            return str(yaml_val)
        return default

    return ConnectionConfig(
        namespace=_resolve("namespace", "TEMPORAL_NAMESPACE", "namespace", _defaults.namespace),
        task_queue=_resolve("task_queue", "TEMPORAL_TASK_QUEUE", "task_queue", _defaults.task_queue),
        server_address=_resolve("server_address", "TEMPORAL_ADDRESS", "server_address", _defaults.server_address),
    )
