"""Session registry for aura-swarm agent session tracking.

Provides typed enums, a frozen SessionRecord dataclass, and a file-per-session
YAML-based registry for observability, permission inheritance, and stale cleanup.

Enums:
    PermissionMode  — Claude permission modes (excludes dangerously-skip-permissions)
    ModelTier       — Claude model tiers
    SessionRole     — Agent roles for session context (subset of protocol RoleId)
    SwarmMode       — worktree (isolated branch) vs intree (in-place)
    TmuxDest        — session (one tmux session per agent) vs window (accumulate in one)
    SessionStatus   — running, stopped, unknown

Frozen Dataclass:
    SessionRecord   — all scalar session fields + task_ids tuple

Protocol:
    SessionRegistry — @runtime_checkable interface for register/get/list/cleanup

Implementations:
    YAMLSessionRegistry     — file-per-session at $XDG_STATE_HOME/aura/sessions/
    TemporalSessionRegistry — stub (NotImplementedError)
"""

from __future__ import annotations

import os
import secrets
import typing
from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable


# ─── Enums ────────────────────────────────────────────────────────────────────


class PermissionMode(StrEnum):
    """Claude permission modes.

    Excludes dangerously-skip-permissions by design — that mode is forbidden.
    """

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    PLAN = "plan"


class ModelTier(StrEnum):
    """Claude model tiers."""

    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"


class SessionRole(StrEnum):
    """Agent roles for session context.

    Matches the swarm/parallel launcher roles (subset of protocol RoleId).
    """

    ARCHITECT = "architect"
    SUPERVISOR = "supervisor"
    REVIEWER = "reviewer"
    WORKER = "worker"


class SwarmMode(StrEnum):
    """Swarm operation mode."""

    WORKTREE = "worktree"
    INTREE = "intree"


class TmuxDest(StrEnum):
    """Tmux launch destination."""

    SESSION = "session"
    WINDOW = "window"


class SessionStatus(StrEnum):
    """Session liveness status."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


# ─── SessionRecord ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SessionRecord:
    """Immutable record of a single agent session.

    BCNF: session_id is the sole determinant for all scalar fields.
    task_ids is a denormalized 1:N junction (SessionTask) stored inline.
    """

    session_id: str
    permission_mode: str
    model: str
    pid: int
    working_dir: str
    started_at: str
    parent_session_id: str
    role: str
    epic_id: str
    swarm_mode: str
    tmux_session: str
    tmux_window: str
    status: str
    last_activity_at: str
    prompt_hash: str
    git_branch: str
    beads_task_id: str
    task_ids: tuple[str, ...] = ()


# ─── SessionRegistry Protocol ────────────────────────────────────────────────


@runtime_checkable
class SessionRegistry(Protocol):
    """Interface for session lifecycle management.

    Implementations must handle concurrent access safely.
    """

    def register(self, record: SessionRecord) -> None:
        """Persist a new session record. Raises if session_id already exists."""
        ...

    def update(self, session_id: str, **kwargs: object) -> None:
        """Update fields on an existing session. Raises KeyError if not found."""
        ...

    def get(self, session_id: str) -> SessionRecord | None:
        """Return session record or None if not found."""
        ...

    def list_active(self) -> list[SessionRecord]:
        """Return all sessions with status == running (PID-verified)."""
        ...

    def find_by_epic(self, epic_id: str) -> list[SessionRecord]:
        """Return all sessions associated with a given epic."""
        ...

    def cleanup_stale(self) -> list[str]:
        """Remove sessions whose PID is no longer alive. Returns removed IDs."""
        ...

    def remove(self, session_id: str) -> None:
        """Delete a session record. No-op if not found."""
        ...


# ─── YAML Serialization Helpers ───────────────────────────────────────────────


def _yaml_quote(value: str) -> str:
    """Quote a YAML value if it contains special characters."""
    if not value:
        return value
    if ":" in value or "#" in value or value.startswith('"') or value.startswith("'"):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _yaml_unquote(value: str) -> str:
    """Remove YAML quoting from a value."""
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def serialize_session(record: SessionRecord) -> str:
    """Serialize a SessionRecord to minimal YAML (stdlib-only, no pyyaml).

    Format: flat key-value pairs + one list field (task_ids).
    """
    lines: list[str] = []
    for f in fields(record):
        value = getattr(record, f.name)
        if f.name == "task_ids":
            lines.append("task_ids:")
            for tid in value:
                lines.append(f"  - {_yaml_quote(tid)}")
        elif isinstance(value, int):
            lines.append(f"{f.name}: {value}")
        else:
            lines.append(f"{f.name}: {_yaml_quote(str(value))}")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def deserialize_session(text: str) -> SessionRecord:
    """Deserialize minimal YAML back to a SessionRecord.

    Uses SessionRecord field type annotations to resolve ambiguity:
    - str fields with empty value → ""
    - tuple[str, ...] field with no items → ()
    """
    # Resolve type hints (needed because of `from __future__ import annotations`)
    hints = typing.get_type_hints(SessionRecord)

    raw: dict[str, object] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    for line in text.splitlines():
        # List item
        if line.startswith("  - "):
            if current_list_key is not None:
                current_list.append(_yaml_unquote(line[4:]))
            continue

        # End of list section (new key encountered)
        if current_list_key is not None:
            raw[current_list_key] = tuple(current_list)
            current_list_key = None
            current_list = []

        # Skip blank lines
        if not line.strip():
            continue

        # Key-value pair
        colon_idx = line.index(":")
        key = line[:colon_idx]
        value_part = line[colon_idx + 1 :].strip()

        if not value_part:
            # Ambiguous: could be empty string or start of list.
            # Use type hints to disambiguate.
            hint = hints.get(key)
            if hint is not None and _is_tuple_type(hint):
                current_list_key = key
                current_list = []
            else:
                raw[key] = ""
        elif key == "pid":
            raw[key] = int(value_part)
        else:
            raw[key] = _yaml_unquote(value_part)

    # Flush final list if file ends without trailing key
    if current_list_key is not None:
        raw[current_list_key] = tuple(current_list)

    return SessionRecord(**raw)  # type: ignore[arg-type]


def _is_tuple_type(hint: object) -> bool:
    """Check if a type hint is tuple[str, ...] or similar tuple type."""
    origin = getattr(hint, "__origin__", None)
    return origin is tuple


# ─── PID Liveness ─────────────────────────────────────────────────────────────


def is_pid_alive(pid: int) -> bool:
    """Check if a process is alive via kill(pid, 0).

    Returns True if process exists (even if owned by another user).
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but owned by another user
        return True
    except OSError:
        return False


# ─── XDG State Directory ─────────────────────────────────────────────────────


def get_sessions_dir() -> Path:
    """Return $XDG_STATE_HOME/aura/sessions/, creating if needed."""
    xdg_state = os.environ.get("XDG_STATE_HOME", "")
    if xdg_state:
        base = Path(xdg_state)
    else:
        base = Path.home() / ".local" / "state"
    sessions_dir = base / "aura" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


# ─── YAMLSessionRegistry ─────────────────────────────────────────────────────


class YAMLSessionRegistry:
    """File-per-session YAML registry at $XDG_STATE_HOME/aura/sessions/.

    Concurrency-safe: each session is a separate file, atomic writes via
    .tmp + rename. No global lock needed.
    """

    def __init__(self, sessions_dir: Path | None = None) -> None:
        self._dir = sessions_dir if sessions_dir is not None else get_sessions_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.yaml"

    def register(self, record: SessionRecord) -> None:
        """Persist a new session. Raises FileExistsError if already registered."""
        path = self._path_for(record.session_id)
        if path.exists():
            raise FileExistsError(f"Session already registered: {record.session_id}")
        self._atomic_write(path, serialize_session(record))

    def update(self, session_id: str, **kwargs: object) -> None:
        """Update fields on an existing session. Raises KeyError if not found."""
        record = self.get(session_id)
        if record is None:
            raise KeyError(f"Session not found: {session_id}")
        # Replace fields via dataclass reconstruction
        current = {f.name: getattr(record, f.name) for f in fields(record)}
        current.update(kwargs)
        updated = SessionRecord(**current)  # type: ignore[arg-type]
        self._atomic_write(self._path_for(session_id), serialize_session(updated))

    def get(self, session_id: str) -> SessionRecord | None:
        """Return session record or None if file doesn't exist."""
        path = self._path_for(session_id)
        try:
            text = path.read_text()
        except FileNotFoundError:
            return None
        return deserialize_session(text)

    def list_active(self) -> list[SessionRecord]:
        """Return all sessions whose PID is still alive."""
        result: list[SessionRecord] = []
        for path in self._dir.glob("*.yaml"):
            try:
                record = deserialize_session(path.read_text())
            except (FileNotFoundError, ValueError, KeyError):
                continue
            if is_pid_alive(record.pid):
                result.append(record)
        return result

    def find_by_epic(self, epic_id: str) -> list[SessionRecord]:
        """Return all sessions for a given epic (any status)."""
        result: list[SessionRecord] = []
        for path in self._dir.glob("*.yaml"):
            try:
                record = deserialize_session(path.read_text())
            except (FileNotFoundError, ValueError, KeyError):
                continue
            if record.epic_id == epic_id:
                result.append(record)
        return result

    def cleanup_stale(self) -> list[str]:
        """Remove sessions whose PID is no longer alive. Returns removed IDs."""
        removed: list[str] = []
        for path in self._dir.glob("*.yaml"):
            try:
                record = deserialize_session(path.read_text())
            except (FileNotFoundError, ValueError, KeyError):
                # File vanished or corrupt — remove it
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                removed.append(path.stem)
                continue
            if not is_pid_alive(record.pid):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass  # TOCTOU: another process removed it
                removed.append(record.session_id)
        return removed

    def remove(self, session_id: str) -> None:
        """Delete a session record file. No-op if not found."""
        try:
            self._path_for(session_id).unlink()
        except FileNotFoundError:
            pass

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically via .tmp + rename."""
        tmp_path = path.with_suffix(f".tmp.{secrets.token_hex(4)}")
        try:
            tmp_path.write_text(content)
            tmp_path.rename(path)
        except BaseException:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise


# ─── TemporalSessionRegistry (stub) ──────────────────────────────────────────


class TemporalSessionRegistry:
    """Temporal-backed session registry (future implementation).

    Satisfies the SessionRegistry protocol but raises NotImplementedError
    for all operations.
    """

    def register(self, record: SessionRecord) -> None:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def update(self, session_id: str, **kwargs: object) -> None:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def get(self, session_id: str) -> SessionRecord | None:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def list_active(self) -> list[SessionRecord]:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def find_by_epic(self, epic_id: str) -> list[SessionRecord]:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def cleanup_stale(self) -> list[str]:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")

    def remove(self, session_id: str) -> None:
        raise NotImplementedError("TemporalSessionRegistry is not yet implemented")
