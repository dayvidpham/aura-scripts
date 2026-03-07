"""Tests for scripts/aura_protocol/sqlite_audit.py — SLICE-5-L2.

BDD Acceptance Criteria (D25):
    AC-S1: _ensure_schema() creates audit_events table with correct columns
    AC-S2: record_event() stores all AuditEvent fields in DB
    AC-S3: query_events(epoch_id="E1") returns only E1 events
    AC-S4: query_events(phase=PhaseId.P9_SLICE) filters by phase.value
    AC-S5: query_events(role=None) returns all roles (no filter)
    AC-S6: query_events() with all None returns all events

Tests use tmp_path for DB isolation.
Tests FAIL on record_event/query_events until SLICE-5-L3 implements them.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import pytest_asyncio

from aura_protocol.sqlite_audit import SqliteAuditTrail, _ensure_schema
from aura_protocol.types import AuditEvent, PhaseId, RoleId


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_event(
    epoch_id: str = "ep-1",
    event_type: str = "phase_advance",
    phase: PhaseId = PhaseId.P9_SLICE,
    role: RoleId = RoleId.WORKER,
    payload: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        epoch_id=epoch_id,
        event_type=event_type,
        phase=phase,
        role=role,
        payload=payload or {"detail": "test"},
    )


# ─── AC-S1: _ensure_schema ────────────────────────────────────────────────────


class TestEnsureSchema:
    """AC-S1: _ensure_schema creates table with correct columns."""

    def test_creates_table(self, tmp_path: Path) -> None:
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
            )
            assert cursor.fetchone() is not None, "audit_events table not created"

    def test_table_has_required_columns(self, tmp_path: Path) -> None:
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("PRAGMA table_info(audit_events)")
            columns = {row[1] for row in cursor.fetchall()}

        required = {"id", "epoch_id", "phase", "role", "event_type", "payload", "timestamp"}
        assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_idempotent_double_call(self, tmp_path: Path) -> None:
        """Calling _ensure_schema twice must not raise."""
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)
        _ensure_schema(db_path)  # Second call must be a no-op

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nested" / "deep" / "audit.db"
        _ensure_schema(db_path)
        assert db_path.exists()


# ─── AC-S2: record_event ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRecordEvent:
    """AC-S2: record_event stores all AuditEvent fields."""

    async def test_stores_epoch_id(self, tmp_path: Path) -> None:
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)
        trail = SqliteAuditTrail(db_path=db_path)
        event = _make_event(epoch_id="ep-x")

        await trail.record_event(event)

        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute("SELECT epoch_id FROM audit_events").fetchone()
        assert row is not None
        assert row[0] == "ep-x"

    async def test_stores_all_fields(self, tmp_path: Path) -> None:
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)
        trail = SqliteAuditTrail(db_path=db_path)
        event = _make_event(
            epoch_id="ep-all",
            event_type="test_event",
            phase=PhaseId.P9_SLICE,
            role=RoleId.WORKER,
            payload={"key": "val"},
        )

        await trail.record_event(event)

        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT epoch_id, event_type, phase, role FROM audit_events"
            ).fetchone()
        assert row[0] == "ep-all"
        assert row[1] == "test_event"
        assert row[2] == PhaseId.P9_SLICE.value
        assert row[3] == RoleId.WORKER.value

    async def test_multiple_events_all_stored(self, tmp_path: Path) -> None:
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)
        trail = SqliteAuditTrail(db_path=db_path)

        for i in range(3):
            await trail.record_event(_make_event(epoch_id=f"ep-{i}"))

        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        assert count == 3


# ─── AC-S3/S4/S5/S6: query_events ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestQueryEvents:
    """AC-S3/S4/S5/S6: query_events filters."""

    @pytest.fixture(autouse=True)
    async def _seed(self, tmp_path: Path) -> None:
        """Seed the database with 3 events across 2 epochs + 2 phases."""
        db_path = tmp_path / "audit.db"
        _ensure_schema(db_path)
        self.trail = SqliteAuditTrail(db_path=db_path)
        self.db_path = db_path

        await self.trail.record_event(
            _make_event(
                epoch_id="ep-1",
                phase=PhaseId.P9_SLICE,
                role=RoleId.WORKER,
            )
        )
        await self.trail.record_event(
            _make_event(
                epoch_id="ep-1",
                phase=PhaseId.P10_CODE_REVIEW,
                role=RoleId.REVIEWER,
            )
        )
        await self.trail.record_event(
            _make_event(
                epoch_id="ep-2",
                phase=PhaseId.P9_SLICE,
                role=RoleId.WORKER,
            )
        )

    async def test_AC_S3_filter_by_epoch_id(self) -> None:
        """AC-S3: query_events(epoch_id='ep-1') returns only ep-1 events."""
        events = await self.trail.query_events(epoch_id="ep-1")
        assert len(events) == 2
        assert all(e.epoch_id == "ep-1" for e in events)

    async def test_AC_S4_filter_by_phase(self) -> None:
        """AC-S4: query_events(phase=P9_SLICE) filters by phase.value."""
        events = await self.trail.query_events(phase=PhaseId.P9_SLICE)
        assert len(events) == 2
        assert all(e.phase == PhaseId.P9_SLICE for e in events)

    async def test_AC_S5_no_role_filter_returns_all_roles(self) -> None:
        """AC-S5: query_events(role=None) returns events from all roles."""
        events = await self.trail.query_events(role=None)
        assert len(events) == 3
        roles = {e.role for e in events}
        assert RoleId.WORKER in roles
        assert RoleId.REVIEWER in roles

    async def test_AC_S6_all_none_returns_all(self) -> None:
        """AC-S6: query_events() with all None returns all events."""
        events = await self.trail.query_events()
        assert len(events) == 3

    async def test_epoch_and_phase_combined(self) -> None:
        """Combining epoch_id and phase filters by both."""
        events = await self.trail.query_events(
            epoch_id="ep-1",
            phase=PhaseId.P9_SLICE,
        )
        assert len(events) == 1
        assert events[0].epoch_id == "ep-1"
        assert events[0].phase == PhaseId.P9_SLICE

    async def test_empty_result_when_no_match(self) -> None:
        events = await self.trail.query_events(epoch_id="nonexistent-epoch")
        assert events == []

    async def test_results_in_chronological_order(self) -> None:
        """Events returned in insertion order (by id)."""
        events = await self.trail.query_events(epoch_id="ep-1")
        assert len(events) == 2
        # First ep-1 event is P9, second is P10
        assert events[0].phase == PhaseId.P9_SLICE
        assert events[1].phase == PhaseId.P10_CODE_REVIEW
