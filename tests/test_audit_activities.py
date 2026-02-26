"""Tests for aura_protocol.audit_activities — AuditTrail singleton + activities.

Tests (all fail until SLICE-3, aura-plugins-sp6y, is merged):
- InMemoryAuditTrail: record_event + query_events filtering
- init_audit_trail(): singleton injection
- record_audit_event @activity via ActivityEnvironment
- query_audit_events @activity via ActivityEnvironment with epoch_id param
- ApplicationError raised when trail not initialized

Coverage strategy:
    Activities are tested via ActivityEnvironment (in-process, no Temporal
    server required). This tests the activity logic directly without the
    Temporal sandbox, consistent with the existing test_workflow.py pattern.

    InMemoryAuditTrail is tested independently as a concrete AuditTrail
    implementation, verifying it satisfies the Protocol interface.
"""

from __future__ import annotations

import pytest

from aura_protocol.types import AuditEvent, PhaseId, RoleId


# ─── InMemoryAuditTrail Tests ─────────────────────────────────────────────────


class TestInMemoryAuditTrail:
    """Tests for InMemoryAuditTrail concrete AuditTrail implementation (SLICE-3)."""

    def test_importable(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail  # noqa: F401

    def test_satisfies_audit_trail_protocol(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail
        from aura_protocol.interfaces import AuditTrail

        trail = InMemoryAuditTrail()
        assert isinstance(trail, AuditTrail), (
            "InMemoryAuditTrail must satisfy the AuditTrail runtime-checkable Protocol"
        )

    @pytest.mark.asyncio
    async def test_record_event_stores_event(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail

        trail = InMemoryAuditTrail()
        event = AuditEvent(
            epoch_id="test-epoch",
            event_type="phase_transition",
            phase=PhaseId.P1_REQUEST,
            role=RoleId.EPOCH,
            payload={},
        )
        await trail.record_event(event)
        results = await trail.query_events()
        assert len(results) == 1
        assert results[0] == event

    @pytest.mark.asyncio
    async def test_query_events_returns_all_without_filter(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail

        trail = InMemoryAuditTrail()
        event1 = AuditEvent(
            epoch_id="test-epoch",
            event_type="phase_transition",
            phase=PhaseId.P1_REQUEST,
            role=RoleId.EPOCH,
            payload={},
        )
        event2 = AuditEvent(
            epoch_id="test-epoch",
            event_type="constraint_check",
            phase=PhaseId.P2_ELICIT,
            role=RoleId.ARCHITECT,
            payload={},
        )
        await trail.record_event(event1)
        await trail.record_event(event2)

        results = await trail.query_events()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_events_filters_by_phase(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail

        trail = InMemoryAuditTrail()
        event1 = AuditEvent(
            epoch_id="test-epoch",
            event_type="phase_transition",
            phase=PhaseId.P1_REQUEST,
            role=RoleId.EPOCH,
            payload={},
        )
        event2 = AuditEvent(
            epoch_id="test-epoch",
            event_type="constraint_check",
            phase=PhaseId.P2_ELICIT,
            role=RoleId.ARCHITECT,
            payload={},
        )
        await trail.record_event(event1)
        await trail.record_event(event2)

        results = await trail.query_events(phase=PhaseId.P1_REQUEST)
        assert len(results) == 1
        assert results[0].phase == PhaseId.P1_REQUEST

    @pytest.mark.asyncio
    async def test_query_events_filters_by_role(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail

        trail = InMemoryAuditTrail()
        event1 = AuditEvent(
            epoch_id="test-epoch",
            event_type="phase_transition",
            phase=PhaseId.P1_REQUEST,
            role=RoleId.EPOCH,
            payload={},
        )
        event2 = AuditEvent(
            epoch_id="test-epoch",
            event_type="constraint_check",
            phase=PhaseId.P2_ELICIT,
            role=RoleId.ARCHITECT,
            payload={},
        )
        await trail.record_event(event1)
        await trail.record_event(event2)

        results = await trail.query_events(role=RoleId.EPOCH)
        assert len(results) == 1
        assert results[0].role == RoleId.EPOCH

    @pytest.mark.asyncio
    async def test_empty_trail_returns_empty_list(self) -> None:
        from aura_protocol.audit_activities import InMemoryAuditTrail

        trail = InMemoryAuditTrail()
        results = await trail.query_events()
        assert results == []


# ─── init_audit_trail Tests ───────────────────────────────────────────────────


class TestInitAuditTrail:
    """Tests for init_audit_trail() singleton injection (SLICE-3)."""

    def test_importable(self) -> None:
        from aura_protocol.audit_activities import init_audit_trail  # noqa: F401

    def test_init_sets_module_singleton(self) -> None:
        from aura_protocol import audit_activities as aa_module
        from aura_protocol.audit_activities import InMemoryAuditTrail, init_audit_trail

        trail = InMemoryAuditTrail()
        init_audit_trail(trail)
        assert aa_module._AUDIT_TRAIL is trail

    def test_init_can_be_called_multiple_times(self) -> None:
        """Reinitializing replaces the singleton (useful for test isolation)."""
        from aura_protocol import audit_activities as aa_module
        from aura_protocol.audit_activities import InMemoryAuditTrail, init_audit_trail

        trail1 = InMemoryAuditTrail()
        trail2 = InMemoryAuditTrail()
        init_audit_trail(trail1)
        init_audit_trail(trail2)
        assert aa_module._AUDIT_TRAIL is trail2


# ─── Audit Activity Tests (via ActivityEnvironment) ───────────────────────────


class TestAuditActivities:
    """Tests for audit Temporal activities via ActivityEnvironment.

    ActivityEnvironment allows testing @activity.defn functions in-process
    without a Temporal test server. Consistent with how check_constraints
    and record_transition are tested in test_workflow.py.
    """

    def test_record_audit_event_importable(self) -> None:
        from aura_protocol.audit_activities import record_audit_event  # noqa: F401

    def test_query_audit_events_importable(self) -> None:
        from aura_protocol.audit_activities import query_audit_events  # noqa: F401

    @pytest.mark.asyncio
    async def test_record_audit_event_via_activity_env(self) -> None:
        from aura_protocol.audit_activities import (
            InMemoryAuditTrail,
            init_audit_trail,
            record_audit_event,
        )
        from temporalio.testing import ActivityEnvironment

        trail = InMemoryAuditTrail()
        init_audit_trail(trail)

        event = AuditEvent(
            epoch_id="act-epoch-001",
            event_type="test_event",
            phase=PhaseId.P1_REQUEST,
            role=RoleId.EPOCH,
            payload={"key": "value"},
        )

        env = ActivityEnvironment()
        await env.run(record_audit_event, event)

        results = await trail.query_events()
        assert any(e == event for e in results), (
            "Recorded event should appear in trail after record_audit_event activity"
        )

    @pytest.mark.asyncio
    async def test_application_error_when_uninitialized(self) -> None:
        """ApplicationError(non_retryable=True) when trail not initialized."""
        from temporalio.exceptions import ApplicationError
        from temporalio.testing import ActivityEnvironment

        import aura_protocol.audit_activities as aa_module

        # Save and clear singleton for this test
        original = aa_module._AUDIT_TRAIL
        aa_module._AUDIT_TRAIL = None
        try:
            event = AuditEvent(
                epoch_id="test-epoch",
                event_type="test",
                phase=PhaseId.P1_REQUEST,
                role=RoleId.EPOCH,
                payload={},
            )
            env = ActivityEnvironment()
            with pytest.raises(ApplicationError):
                await env.run(aa_module.record_audit_event, event)
        finally:
            # Restore original state for other tests
            aa_module._AUDIT_TRAIL = original

    @pytest.mark.asyncio
    async def test_query_audit_events_via_activity_env(self) -> None:
        from aura_protocol.audit_activities import (
            InMemoryAuditTrail,
            init_audit_trail,
            query_audit_events,
            record_audit_event,
        )
        from temporalio.testing import ActivityEnvironment

        trail = InMemoryAuditTrail()
        init_audit_trail(trail)

        # Record an event first
        event = AuditEvent(
            epoch_id="query-epoch-001",
            event_type="test",
            phase=PhaseId.P9_SLICE,
            role=RoleId.WORKER,
            payload={"slice": "1"},
        )
        env = ActivityEnvironment()
        await env.run(record_audit_event, event)

        # Query by epoch_id
        results = await env.run(query_audit_events, "query-epoch-001")
        assert len(results) >= 1
        assert all(r.epoch_id == "query-epoch-001" for r in results)

    @pytest.mark.asyncio
    async def test_query_audit_events_with_phase_filter(self) -> None:
        from aura_protocol.audit_activities import (
            InMemoryAuditTrail,
            init_audit_trail,
            query_audit_events,
            record_audit_event,
        )
        from temporalio.testing import ActivityEnvironment

        trail = InMemoryAuditTrail()
        init_audit_trail(trail)

        # Record events at different phases
        env = ActivityEnvironment()
        for phase in (PhaseId.P1_REQUEST, PhaseId.P9_SLICE):
            evt = AuditEvent(
                epoch_id="filter-epoch",
                event_type="test",
                phase=phase,
                role=RoleId.EPOCH,
                payload={},
            )
            await env.run(record_audit_event, evt)

        # Query filtered by phase
        results = await env.run(query_audit_events, "filter-epoch", PhaseId.P9_SLICE)
        assert all(r.phase == PhaseId.P9_SLICE for r in results)
