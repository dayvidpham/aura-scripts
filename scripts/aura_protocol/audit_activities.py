"""Temporal activity functions for the Aura Protocol v3 audit trail.

This module provides:
- Module-level AuditTrail singleton (injected via init_audit_trail)
- record_audit_event: @activity.defn to persist an AuditEvent
- query_audit_events: @activity.defn to filter events by epoch_id/phase
- InMemoryAuditTrail: in-memory AuditTrail implementation for dev/testing

SLICE-4 stub — SLICE-3 (aura-plugins-sp6y) will expand with full Temporal-backed
persistence, additional event types, and the epoch_id parameter added to the
AuditTrail Protocol in interfaces.py.

IP-3 contract (consumed by SLICE-4 worker, SLICE-5 tests):
    init_audit_trail(trail: AuditTrail) -> None
    record_audit_event(event: AuditEvent) -> None  (@activity.defn)
    query_audit_events(epoch_id: str, phase: PhaseId | None) -> list[AuditEvent]
        (@activity.defn)
"""

from __future__ import annotations

import logging
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from aura_protocol.interfaces import AuditTrail
from aura_protocol.types import AuditEvent, PhaseId, RoleId

logger = logging.getLogger(__name__)

# ─── Singleton ────────────────────────────────────────────────────────────────

_AUDIT_TRAIL: AuditTrail | None = None


def init_audit_trail(trail: AuditTrail) -> None:
    """Inject the AuditTrail implementation used by all audit activity functions.

    Must be called before the Temporal worker starts. Calling again replaces
    the existing trail (useful in tests for resetting state between runs).

    Args:
        trail: Any object satisfying the AuditTrail Protocol.

    Where:
        Called from bin/worker.py before Worker() starts.
    """
    global _AUDIT_TRAIL
    _AUDIT_TRAIL = trail
    logger.info("AuditTrail initialized: %s", type(trail).__name__)


def _require_trail() -> AuditTrail:
    """Return the initialized trail or raise ApplicationError (non-retryable).

    Raises:
        ApplicationError: If init_audit_trail() was not called first.
            non_retryable=True so Temporal does not retry on misconfiguration.
    """
    if _AUDIT_TRAIL is None:
        raise ApplicationError(
            "AuditTrail not initialized — call init_audit_trail() before starting "
            "the Temporal worker (bin/worker.py:main).",
            non_retryable=True,
        )
    return _AUDIT_TRAIL


# ─── Activities ───────────────────────────────────────────────────────────────


@activity.defn
async def record_audit_event(event: AuditEvent) -> None:
    """Persist an audit event to the configured AuditTrail.

    Args:
        event: The audit event to record.

    Raises:
        ApplicationError (non_retryable): If init_audit_trail() was not called.
    """
    trail = _require_trail()
    await trail.record_event(event)
    logger.debug(
        "Audit event recorded: epoch=%s type=%s phase=%s",
        event.epoch_id,
        event.event_type,
        event.phase,
    )


@activity.defn
async def query_audit_events(
    epoch_id: str, phase: PhaseId | None = None
) -> list[AuditEvent]:
    """Query audit events filtered by epoch_id and optional phase.

    Args:
        epoch_id: Return only events for this epoch.
        phase: Optional phase filter; None returns all phases.

    Returns:
        Matching audit events in chronological order.

    Raises:
        ApplicationError (non_retryable): If init_audit_trail() was not called.

    Note:
        The current AuditTrail Protocol (interfaces.py) does not yet have an
        epoch_id param on query_events. SLICE-3 will add it. Until then,
        InMemoryAuditTrail.query_events_by_epoch handles epoch filtering.
    """
    trail = _require_trail()
    # InMemoryAuditTrail exposes query_events_by_epoch for epoch+phase filtering.
    # Temporal-backed implementations will use search attribute queries.
    if hasattr(trail, "query_events_by_epoch"):
        return await trail.query_events_by_epoch(epoch_id=epoch_id, phase=phase)
    # Fallback: filter in-memory using the base Protocol method.
    all_events = await trail.query_events(phase=phase)
    return [e for e in all_events if e.epoch_id == epoch_id]


# ─── InMemoryAuditTrail ───────────────────────────────────────────────────────


class InMemoryAuditTrail:
    """In-memory AuditTrail for development and testing.

    Satisfies the AuditTrail Protocol (structural subtyping). Stores events
    in a list; thread-safe for single-threaded asyncio workers.

    Usage:
        from aura_protocol.audit_activities import InMemoryAuditTrail, init_audit_trail
        init_audit_trail(InMemoryAuditTrail())
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    async def record_event(self, event: AuditEvent) -> None:
        """Append event to in-memory list."""
        self._events.append(event)

    async def query_events(
        self,
        *,
        phase: PhaseId | None = None,
        role: RoleId | None = None,
    ) -> list[AuditEvent]:
        """Filter events by phase and/or role (AuditTrail Protocol signature)."""
        results = list(self._events)
        if phase is not None:
            results = [e for e in results if e.phase == phase]
        if role is not None:
            results = [e for e in results if e.role == role]
        return results

    async def query_events_by_epoch(
        self,
        *,
        epoch_id: str,
        phase: PhaseId | None = None,
    ) -> list[AuditEvent]:
        """Filter events by epoch_id and optional phase.

        Extended method consumed by query_audit_events() activity.
        This signature anticipates the SLICE-3 update to the AuditTrail Protocol.
        """
        results = [e for e in self._events if e.epoch_id == epoch_id]
        if phase is not None:
            results = [e for e in results if e.phase == phase]
        return results

    @property
    def events(self) -> list[AuditEvent]:
        """Read-only snapshot of all recorded events (for test assertions)."""
        return list(self._events)
