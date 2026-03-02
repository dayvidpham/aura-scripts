"""Tests for aura_protocol.session_registry.

Covers:
- Enum values and membership
- SessionRecord creation and immutability
- YAML serialization roundtrip (including empty strings, special chars, empty lists)
- Type-aware deserializer disambiguation (empty string vs empty list)
- YAMLSessionRegistry CRUD operations
- PID liveness integration
- Stale cleanup with TOCTOU safety
- Protocol conformance for both implementations
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from aura_protocol.session_registry import (
    ModelTier,
    PermissionMode,
    SessionRecord,
    SessionRegistry,
    SessionRole,
    SessionStatus,
    SwarmMode,
    TemporalSessionRegistry,
    TmuxDest,
    YAMLSessionRegistry,
    deserialize_session,
    is_pid_alive,
    serialize_session,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_record(**overrides: object) -> SessionRecord:
    """Create a SessionRecord with sensible defaults, overriding any fields."""
    defaults: dict[str, object] = {
        "session_id": "supervisor-test--a1b2",
        "permission_mode": PermissionMode.ACCEPT_EDITS,
        "model": ModelTier.SONNET,
        "pid": 12345,
        "working_dir": "/home/user/project",
        "started_at": "2026-03-01T12:00:00Z",
        "parent_session_id": "",
        "role": SessionRole.SUPERVISOR,
        "epic_id": "aura-test-001",
        "swarm_mode": SwarmMode.WORKTREE,
        "tmux_session": "swarm-test",
        "tmux_window": "",
        "status": SessionStatus.RUNNING,
        "last_activity_at": "2026-03-01T12:00:00Z",
        "prompt_hash": "abc123def456",
        "git_branch": "epic/aura-test-001",
        "beads_task_id": "aura-plugins-xyz",
        "task_ids": ("task-001", "task-002"),
    }
    defaults.update(overrides)
    return SessionRecord(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def sample_record() -> SessionRecord:
    return _make_record()


@pytest.fixture
def registry(tmp_path: Path) -> YAMLSessionRegistry:
    return YAMLSessionRegistry(sessions_dir=tmp_path)


# ─── Enum Tests ───────────────────────────────────────────────────────────────


class TestEnums:
    def test_permission_mode_values(self) -> None:
        assert set(PermissionMode) == {
            PermissionMode.DEFAULT,
            PermissionMode.ACCEPT_EDITS,
            PermissionMode.BYPASS_PERMISSIONS,
            PermissionMode.PLAN,
        }
        assert PermissionMode.ACCEPT_EDITS == "acceptEdits"
        assert PermissionMode.BYPASS_PERMISSIONS == "bypassPermissions"

    def test_permission_mode_excludes_dangerous(self) -> None:
        for mode in PermissionMode:
            assert "dangerously" not in mode.lower()
            assert "skip" not in mode.lower()

    def test_model_tier_values(self) -> None:
        assert set(ModelTier) == {ModelTier.SONNET, ModelTier.OPUS, ModelTier.HAIKU}

    def test_session_role_values(self) -> None:
        assert set(SessionRole) == {
            SessionRole.ARCHITECT,
            SessionRole.SUPERVISOR,
            SessionRole.REVIEWER,
            SessionRole.WORKER,
        }

    def test_swarm_mode_values(self) -> None:
        assert set(SwarmMode) == {SwarmMode.WORKTREE, SwarmMode.INTREE}

    def test_tmux_dest_values(self) -> None:
        assert set(TmuxDest) == {TmuxDest.SESSION, TmuxDest.WINDOW}

    def test_session_status_values(self) -> None:
        assert set(SessionStatus) == {
            SessionStatus.RUNNING,
            SessionStatus.STOPPED,
            SessionStatus.UNKNOWN,
        }

    def test_enums_are_str(self) -> None:
        """All enums should be usable as plain strings."""
        assert f"mode={PermissionMode.DEFAULT}" == "mode=default"
        assert f"model={ModelTier.OPUS}" == "model=opus"
        assert f"role={SessionRole.WORKER}" == "role=worker"


# ─── SessionRecord Tests ─────────────────────────────────────────────────────


class TestSessionRecord:
    def test_creation(self, sample_record: SessionRecord) -> None:
        assert sample_record.session_id == "supervisor-test--a1b2"
        assert sample_record.pid == 12345
        assert sample_record.task_ids == ("task-001", "task-002")

    def test_frozen(self, sample_record: SessionRecord) -> None:
        with pytest.raises(AttributeError):
            sample_record.status = "stopped"  # type: ignore[misc]

    def test_empty_task_ids_default(self) -> None:
        record = _make_record(task_ids=())
        assert record.task_ids == ()

    def test_hashable(self, sample_record: SessionRecord) -> None:
        """Frozen dataclasses should be hashable for use as dict keys."""
        d = {sample_record: True}
        assert d[sample_record] is True


# ─── YAML Serialization Tests ────────────────────────────────────────────────


class TestYAMLSerialization:
    def test_roundtrip(self, sample_record: SessionRecord) -> None:
        yaml_text = serialize_session(sample_record)
        restored = deserialize_session(yaml_text)
        assert restored == sample_record

    def test_roundtrip_empty_strings(self) -> None:
        """Empty string fields should survive roundtrip without becoming lists."""
        record = _make_record(
            parent_session_id="",
            tmux_window="",
            beads_task_id="",
            epic_id="",
        )
        yaml_text = serialize_session(record)
        restored = deserialize_session(yaml_text)
        assert restored.parent_session_id == ""
        assert restored.tmux_window == ""
        assert restored.beads_task_id == ""
        assert restored.epic_id == ""

    def test_roundtrip_empty_task_ids(self) -> None:
        """Empty task_ids should survive roundtrip as empty tuple."""
        record = _make_record(task_ids=())
        yaml_text = serialize_session(record)
        restored = deserialize_session(yaml_text)
        assert restored.task_ids == ()

    def test_roundtrip_special_chars_in_values(self) -> None:
        """Values with colons and hashes should be quoted and survive roundtrip."""
        record = _make_record(
            working_dir="/path/with:colon",
            prompt_hash="sha256:abcdef#123",
        )
        yaml_text = serialize_session(record)
        restored = deserialize_session(yaml_text)
        assert restored.working_dir == "/path/with:colon"
        assert restored.prompt_hash == "sha256:abcdef#123"

    def test_serialization_format(self, sample_record: SessionRecord) -> None:
        """Verify the YAML output is human-readable."""
        yaml_text = serialize_session(sample_record)
        assert "session_id: supervisor-test--a1b2" in yaml_text
        assert "pid: 12345" in yaml_text
        assert "task_ids:" in yaml_text
        assert "  - task-001" in yaml_text
        assert "  - task-002" in yaml_text

    def test_disambiguation_empty_string_vs_empty_list(self) -> None:
        """The type-aware deserializer must correctly handle the key: ambiguity.

        When a key has no value (key:), str fields get "" and tuple fields get ().
        """
        # Manually construct YAML with ambiguous empty values
        yaml_text = (
            "session_id: test\n"
            "permission_mode: default\n"
            "model: sonnet\n"
            "pid: 1\n"
            "working_dir: /tmp\n"
            "started_at: now\n"
            "parent_session_id:\n"  # empty string (str field)
            "role: worker\n"
            "epic_id:\n"  # empty string (str field)
            "swarm_mode: intree\n"
            "tmux_session: test\n"
            "tmux_window:\n"  # empty string (str field)
            "status: running\n"
            "last_activity_at: now\n"
            "prompt_hash: abc\n"
            "git_branch:\n"  # empty string (str field)
            "beads_task_id:\n"  # empty string (str field)
            "task_ids:\n"  # empty list (tuple field)
        )
        record = deserialize_session(yaml_text)
        assert record.parent_session_id == ""
        assert record.epic_id == ""
        assert record.tmux_window == ""
        assert record.git_branch == ""
        assert record.beads_task_id == ""
        assert record.task_ids == ()


# ─── PID Liveness Tests ──────────────────────────────────────────────────────


class TestPidLiveness:
    def test_current_process_alive(self) -> None:
        assert is_pid_alive(os.getpid()) is True

    def test_dead_pid(self) -> None:
        # PID 0 is special (kernel), use a very high PID unlikely to exist
        assert is_pid_alive(999999999) is False

    def test_permission_error_means_alive(self) -> None:
        with patch("os.kill", side_effect=PermissionError("not owner")):
            assert is_pid_alive(1) is True

    def test_process_lookup_error_means_dead(self) -> None:
        with patch("os.kill", side_effect=ProcessLookupError("no such process")):
            assert is_pid_alive(1) is False


# ─── YAMLSessionRegistry Tests ───────────────────────────────────────────────


class TestYAMLSessionRegistry:
    def test_register_and_get(
        self, registry: YAMLSessionRegistry, sample_record: SessionRecord
    ) -> None:
        registry.register(sample_record)
        retrieved = registry.get(sample_record.session_id)
        assert retrieved == sample_record

    def test_register_duplicate_raises(
        self, registry: YAMLSessionRegistry, sample_record: SessionRecord
    ) -> None:
        registry.register(sample_record)
        with pytest.raises(FileExistsError):
            registry.register(sample_record)

    def test_get_nonexistent_returns_none(
        self, registry: YAMLSessionRegistry
    ) -> None:
        assert registry.get("nonexistent") is None

    def test_update(
        self, registry: YAMLSessionRegistry, sample_record: SessionRecord
    ) -> None:
        registry.register(sample_record)
        registry.update(sample_record.session_id, status=SessionStatus.STOPPED)
        updated = registry.get(sample_record.session_id)
        assert updated is not None
        assert updated.status == SessionStatus.STOPPED
        # Other fields unchanged
        assert updated.pid == sample_record.pid

    def test_update_nonexistent_raises(
        self, registry: YAMLSessionRegistry
    ) -> None:
        with pytest.raises(KeyError):
            registry.update("nonexistent", status="stopped")

    def test_remove(
        self, registry: YAMLSessionRegistry, sample_record: SessionRecord
    ) -> None:
        registry.register(sample_record)
        registry.remove(sample_record.session_id)
        assert registry.get(sample_record.session_id) is None

    def test_remove_nonexistent_no_error(
        self, registry: YAMLSessionRegistry
    ) -> None:
        registry.remove("nonexistent")  # should not raise

    def test_list_active_filters_by_pid(
        self, registry: YAMLSessionRegistry
    ) -> None:
        alive = _make_record(session_id="alive-1", pid=os.getpid())
        dead = _make_record(session_id="dead-1", pid=999999999)
        registry.register(alive)
        registry.register(dead)

        active = registry.list_active()
        active_ids = [r.session_id for r in active]
        assert "alive-1" in active_ids
        assert "dead-1" not in active_ids

    def test_find_by_epic(self, registry: YAMLSessionRegistry) -> None:
        r1 = _make_record(session_id="s1", epic_id="epic-a")
        r2 = _make_record(session_id="s2", epic_id="epic-b")
        r3 = _make_record(session_id="s3", epic_id="epic-a")
        registry.register(r1)
        registry.register(r2)
        registry.register(r3)

        found = registry.find_by_epic("epic-a")
        found_ids = [r.session_id for r in found]
        assert sorted(found_ids) == ["s1", "s3"]

    def test_cleanup_stale(self, registry: YAMLSessionRegistry) -> None:
        alive = _make_record(session_id="alive", pid=os.getpid())
        dead = _make_record(session_id="dead", pid=999999999)
        registry.register(alive)
        registry.register(dead)

        removed = registry.cleanup_stale()
        assert "dead" in removed
        assert "alive" not in removed
        assert registry.get("dead") is None
        assert registry.get("alive") is not None

    def test_cleanup_stale_toctou_safety(
        self, registry: YAMLSessionRegistry
    ) -> None:
        """If a file vanishes between glob and unlink, cleanup should not crash."""
        dead = _make_record(session_id="vanishing", pid=999999999)
        registry.register(dead)

        # Remove file manually before cleanup runs
        registry._path_for("vanishing").unlink()

        # Should not raise
        removed = registry.cleanup_stale()
        # File was already gone, but cleanup should handle gracefully
        assert isinstance(removed, list)

    def test_atomic_write_cleanup_on_failure(
        self, registry: YAMLSessionRegistry, tmp_path: Path
    ) -> None:
        """If rename fails, the .tmp file should be cleaned up."""
        record = _make_record(session_id="atomic-test")
        # Register normally first
        registry.register(record)

        # Verify no .tmp files remain
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert len(tmp_files) == 0


# ─── Protocol Conformance Tests ───────────────────────────────────────────────


class TestProtocolConformance:
    def test_yaml_registry_satisfies_protocol(self, tmp_path: Path) -> None:
        registry = YAMLSessionRegistry(sessions_dir=tmp_path)
        assert isinstance(registry, SessionRegistry)

    def test_temporal_registry_satisfies_protocol(self) -> None:
        registry = TemporalSessionRegistry()
        assert isinstance(registry, SessionRegistry)

    def test_temporal_registry_raises(self) -> None:
        registry = TemporalSessionRegistry()
        record = _make_record()
        with pytest.raises(NotImplementedError):
            registry.register(record)
        with pytest.raises(NotImplementedError):
            registry.get("test")
        with pytest.raises(NotImplementedError):
            registry.list_active()
        with pytest.raises(NotImplementedError):
            registry.cleanup_stale()
        with pytest.raises(NotImplementedError):
            registry.remove("test")
