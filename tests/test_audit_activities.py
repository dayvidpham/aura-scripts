"""Tests for aura_protocol.audit_activities — AuditTrail singleton + activities.

BDD Acceptance Criteria (from SLICE-3 handoff):
    AC1: Given init_audit_trail(InMemoryAuditTrail()), when record_audit_event
         called, then event stored in trail.
    AC2: Given query_audit_events(epoch_id="e1"), when events exist for e1,
         then returns filtered list.
    AC3: Given _AUDIT_TRAIL is None, when any activity called, then raises
         ApplicationError(non_retryable=True).
    AC4: Should never use class-method activities or execute_activity_method.

Coverage:
    - init_audit_trail() injects singleton
    - _AUDIT_TRAIL singleton is None before init
    - record_audit_event stores via trail
    - query_audit_events filters by epoch_id (required) and optional phase
    - ApplicationError raised when uninitialized (non_retryable=True)
    - InMemoryAuditTrail: record_event + query_events semantics
    - AuditTrail Protocol: InMemoryAuditTrail satisfies isinstance check
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

import aura_protocol.audit_activities as audit_mod
from aura_protocol.audit_activities import (
    InMemoryAuditTrail,
    init_audit_trail,
    query_audit_events,
    record_audit_event,
)
from aura_protocol.interfaces import AuditTrail
from aura_protocol.types import AuditEvent, PhaseId, RoleId


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_event(
    epoch_id: str = "epoch-1",
    event_type: str = "phase_transition",
    phase: PhaseId = PhaseId.P9_SLICE,
    role: RoleId = RoleId.WORKER,
    payload: dict | None = None,
) -> AuditEvent:
    return AuditEvent(
        epoch_id=epoch_id,
        event_type=event_type,
        phase=phase,
        role=role,
        payload=payload or {},
    )


# ─── Fixture: reset singleton before each test ────────────────────────────────


@pytest.fixture(autouse=True)
def reset_audit_trail():
    """Reset the module-level singleton before and after each test."""
    audit_mod._AUDIT_TRAIL = None
    yield
    audit_mod._AUDIT_TRAIL = None


# ─── InMemoryAuditTrail unit tests ────────────────────────────────────────────


class TestInMemoryAuditTrail:
    """Unit tests for InMemoryAuditTrail concrete implementation."""

    @pytest.mark.asyncio
    async def test_record_event_stores_event(self) -> None:
        """Given InMemoryAuditTrail, when record_event called, then event stored."""
        trail = InMemoryAuditTrail()
        event = _make_event(epoch_id="e1")
        await trail.record_event(event)
        events = await trail.query_events(epoch_id="e1")
        assert event in events

    @pytest.mark.asyncio
    async def test_query_events_returns_empty_when_no_events(self) -> None:
        """Given empty trail, when query_events called, then returns empty list."""
        trail = InMemoryAuditTrail()
        events = await trail.query_events(epoch_id="nonexistent")
        assert events == []

    @pytest.mark.asyncio
    async def test_query_events_filters_by_epoch_id(self) -> None:
        """Given events from two epochs, query_events returns only matching epoch."""
        trail = InMemoryAuditTrail()
        event_e1 = _make_event(epoch_id="epoch-1")
        event_e2 = _make_event(epoch_id="epoch-2")
        await trail.record_event(event_e1)
        await trail.record_event(event_e2)

        result = await trail.query_events(epoch_id="epoch-1")
        assert event_e1 in result
        assert event_e2 not in result

    @pytest.mark.asyncio
    async def test_query_events_filters_by_phase(self) -> None:
        """Given events from two phases, query_events(phase=...) filters correctly."""
        trail = InMemoryAuditTrail()
        event_p9 = _make_event(epoch_id="e1", phase=PhaseId.P9_SLICE)
        event_p10 = _make_event(epoch_id="e1", phase=PhaseId.P10_CODE_REVIEW)
        await trail.record_event(event_p9)
        await trail.record_event(event_p10)

        result = await trail.query_events(epoch_id="e1", phase=PhaseId.P9_SLICE)
        assert event_p9 in result
        assert event_p10 not in result

    @pytest.mark.asyncio
    async def test_query_events_no_phase_filter_returns_all_for_epoch(self) -> None:
        """Given events from two phases, query_events(epoch_id) returns all."""
        trail = InMemoryAuditTrail()
        event_p9 = _make_event(epoch_id="e1", phase=PhaseId.P9_SLICE)
        event_p10 = _make_event(epoch_id="e1", phase=PhaseId.P10_CODE_REVIEW)
        await trail.record_event(event_p9)
        await trail.record_event(event_p10)

        result = await trail.query_events(epoch_id="e1")
        assert event_p9 in result
        assert event_p10 in result

    @pytest.mark.asyncio
    async def test_query_events_epoch_id_none_returns_all(self) -> None:
        """Given epoch_id=None, query_events returns all events (no epoch filter)."""
        trail = InMemoryAuditTrail()
        event_e1 = _make_event(epoch_id="epoch-1")
        event_e2 = _make_event(epoch_id="epoch-2")
        await trail.record_event(event_e1)
        await trail.record_event(event_e2)

        result = await trail.query_events(epoch_id=None)
        assert event_e1 in result
        assert event_e2 in result

    @pytest.mark.asyncio
    async def test_multiple_record_events_stored_in_order(self) -> None:
        """Given multiple events recorded, they are returned in insertion order."""
        trail = InMemoryAuditTrail()
        events = [_make_event(epoch_id="e1", event_type=f"event-{i}") for i in range(5)]
        for e in events:
            await trail.record_event(e)
        result = await trail.query_events(epoch_id="e1")
        assert result == events

    def test_in_memory_audit_trail_satisfies_audit_trail_protocol(self) -> None:
        """InMemoryAuditTrail satisfies AuditTrail Protocol (isinstance check)."""
        trail = InMemoryAuditTrail()
        assert isinstance(trail, AuditTrail)


# ─── init_audit_trail tests ───────────────────────────────────────────────────


class TestInitAuditTrail:
    """Tests for the init_audit_trail() injection function."""

    def test_singleton_is_none_before_init(self) -> None:
        """Given fresh module state, _AUDIT_TRAIL is None before init."""
        assert audit_mod._AUDIT_TRAIL is None

    def test_init_sets_singleton(self) -> None:
        """Given InMemoryAuditTrail, when init_audit_trail called, then singleton set."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        assert audit_mod._AUDIT_TRAIL is trail

    def test_init_can_be_called_multiple_times(self) -> None:
        """Given two trails, when init called twice, second replaces first."""
        trail1 = InMemoryAuditTrail()
        trail2 = InMemoryAuditTrail()
        init_audit_trail(trail1)
        init_audit_trail(trail2)
        assert audit_mod._AUDIT_TRAIL is trail2

    def test_init_returns_none(self) -> None:
        """init_audit_trail() returns None."""
        result = init_audit_trail(InMemoryAuditTrail())
        assert result is None


# ─── record_audit_event activity tests ───────────────────────────────────────


class TestRecordAuditEventActivity:
    """Tests for the @activity.defn record_audit_event activity."""

    @pytest.mark.asyncio
    async def test_record_audit_event_stores_event_after_init(self) -> None:
        """AC1: Given init_audit_trail called, when record_audit_event then event stored."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        event = _make_event(epoch_id="epoch-1")

        env = ActivityEnvironment()
        result = await env.run(record_audit_event, event)
        assert result is None

        stored = await trail.query_events(epoch_id="epoch-1")
        assert event in stored

    @pytest.mark.asyncio
    async def test_record_audit_event_raises_application_error_when_not_initialized(
        self,
    ) -> None:
        """AC3: Given uninitialized trail, when record_audit_event then ApplicationError."""
        event = _make_event()
        env = ActivityEnvironment()
        with pytest.raises(ApplicationError) as exc_info:
            await env.run(record_audit_event, event)
        assert exc_info.value.non_retryable is True

    @pytest.mark.asyncio
    async def test_record_audit_event_error_message_is_actionable(self) -> None:
        """ApplicationError message tells caller what to do."""
        event = _make_event()
        env = ActivityEnvironment()
        with pytest.raises(ApplicationError) as exc_info:
            await env.run(record_audit_event, event)
        assert "init_audit_trail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_audit_event_multiple_events(self) -> None:
        """record_audit_event can be called multiple times — all events accumulate."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        env = ActivityEnvironment()

        events = [_make_event(epoch_id="e1", event_type=f"type-{i}") for i in range(3)]
        for e in events:
            await env.run(record_audit_event, e)

        stored = await trail.query_events(epoch_id="e1")
        assert stored == events


# ─── query_audit_events activity tests ───────────────────────────────────────


class TestQueryAuditEventsActivity:
    """Tests for the @activity.defn query_audit_events activity."""

    @pytest.mark.asyncio
    async def test_query_returns_events_for_epoch(self) -> None:
        """AC2: Given events for epoch-1, query_audit_events(epoch_id='epoch-1') returns them."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        event = _make_event(epoch_id="epoch-1")
        await trail.record_event(event)

        env = ActivityEnvironment()
        result = await env.run(query_audit_events, "epoch-1", None)
        assert event in result

    @pytest.mark.asyncio
    async def test_query_filters_by_epoch_id(self) -> None:
        """query_audit_events does not return events from other epochs."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        event_e1 = _make_event(epoch_id="epoch-1")
        event_e2 = _make_event(epoch_id="epoch-2")
        await trail.record_event(event_e1)
        await trail.record_event(event_e2)

        env = ActivityEnvironment()
        result = await env.run(query_audit_events, "epoch-1", None)
        assert event_e1 in result
        assert event_e2 not in result

    @pytest.mark.asyncio
    async def test_query_filters_by_phase(self) -> None:
        """query_audit_events(epoch_id, phase) filters by phase."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        event_p9 = _make_event(epoch_id="e1", phase=PhaseId.P9_SLICE)
        event_p10 = _make_event(epoch_id="e1", phase=PhaseId.P10_CODE_REVIEW)
        await trail.record_event(event_p9)
        await trail.record_event(event_p10)

        env = ActivityEnvironment()
        result = await env.run(query_audit_events, "e1", PhaseId.P9_SLICE)
        assert event_p9 in result
        assert event_p10 not in result

    @pytest.mark.asyncio
    async def test_query_returns_empty_for_unknown_epoch(self) -> None:
        """query_audit_events returns empty list when no events match epoch."""
        trail = InMemoryAuditTrail()
        init_audit_trail(trail)

        env = ActivityEnvironment()
        result = await env.run(query_audit_events, "nonexistent-epoch", None)
        assert result == []

    @pytest.mark.asyncio
    async def test_query_raises_application_error_when_not_initialized(self) -> None:
        """AC3: Given uninitialized trail, when query_audit_events then ApplicationError."""
        env = ActivityEnvironment()
        with pytest.raises(ApplicationError) as exc_info:
            await env.run(query_audit_events, "epoch-1", None)
        assert exc_info.value.non_retryable is True

    @pytest.mark.asyncio
    async def test_query_error_message_is_actionable(self) -> None:
        """ApplicationError message tells caller what to do."""
        env = ActivityEnvironment()
        with pytest.raises(ApplicationError) as exc_info:
            await env.run(query_audit_events, "epoch-1", None)
        assert "init_audit_trail" in str(exc_info.value)
