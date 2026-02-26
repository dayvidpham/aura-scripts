"""Temporal activities for the AuditTrail DI pattern.

Provides a module-level AuditTrail singleton that is injected before the
Temporal worker starts, and two @activity.defn functions that delegate to it.

Design decisions (from UAT-2 and URD R4):
- Module-level singleton (NOT class-based) so activities are module-level
  functions, compatible with workflow.execute_activity (not execute_activity_method).
- ApplicationError with non_retryable=True on uninitialized state — there is no
  point retrying an activity that will fail deterministically until the worker is
  reconfigured.
- InMemoryAuditTrail is the test/dev implementation; production will use Temporal
  event history.

Usage:
    from aura_protocol.audit_activities import init_audit_trail, InMemoryAuditTrail

    # Before starting the Temporal worker:
    init_audit_trail(InMemoryAuditTrail())

    # In a workflow:
    await workflow.execute_activity(
        record_audit_event,
        args=[event],
        start_to_close_timeout=timedelta(seconds=10),
    )
"""

from __future__ import annotations

from aura_protocol.types import AuditEvent, PhaseId, RoleId
from aura_protocol.interfaces import AuditTrail

from temporalio import activity
from temporalio.exceptions import ApplicationError


# ─── Module-Level Singleton ───────────────────────────────────────────────────

_AUDIT_TRAIL: AuditTrail | None = None

_UNINITIALIZED_MSG = (
    "AuditTrail not initialized — call init_audit_trail() before starting worker. "
    "Inject a concrete AuditTrail (e.g. InMemoryAuditTrail()) via init_audit_trail() "
    "in your worker startup code."
)


def init_audit_trail(trail: AuditTrail) -> None:
    """Inject the AuditTrail implementation for this worker process.

    Must be called once before the Temporal worker starts. Replaces any
    previously injected trail (safe to call multiple times in tests).

    Args:
        trail: Concrete AuditTrail implementation to use for all activities
               in this worker process.
    """
    global _AUDIT_TRAIL
    _AUDIT_TRAIL = trail


# ─── Temporal Activities ──────────────────────────────────────────────────────


@activity.defn
async def record_audit_event(event: AuditEvent) -> None:
    """Persist an audit event to the trail.

    Activity: non-deterministic I/O boundary, safe for Temporal retries
    (but ApplicationError is non_retryable when trail is uninitialized).

    Args:
        event: The AuditEvent to record. Must be a frozen dataclass compatible
               with Temporal's JSON serialization.

    Raises:
        ApplicationError: (non_retryable=True) if init_audit_trail() was not
            called before this activity ran. Retrying will not help — the worker
            must be reconfigured and restarted.
    """
    if _AUDIT_TRAIL is None:
        raise ApplicationError(
            _UNINITIALIZED_MSG,
            non_retryable=True,
        )
    await _AUDIT_TRAIL.record_event(event)


@activity.defn
async def query_audit_events(
    epoch_id: str,
    phase: PhaseId | None = None,
) -> list[AuditEvent]:
    """Query recorded audit events for an epoch, with optional phase filter.

    Activity: non-deterministic I/O boundary (reads from external store).

    Args:
        epoch_id: The epoch to query events for (required — Temporal activities
                  cannot use keyword-only args directly; this is positional).
        phase:    Optional phase filter — only return events from this phase.

    Returns:
        List of matching AuditEvent instances in chronological order.

    Raises:
        ApplicationError: (non_retryable=True) if init_audit_trail() was not
            called before this activity ran.
    """
    if _AUDIT_TRAIL is None:
        raise ApplicationError(
            _UNINITIALIZED_MSG,
            non_retryable=True,
        )
    return await _AUDIT_TRAIL.query_events(epoch_id=epoch_id, phase=phase)


# ─── InMemoryAuditTrail ───────────────────────────────────────────────────────


class InMemoryAuditTrail:
    """Concrete AuditTrail implementation backed by an in-memory list.

    Intended for testing and local development. Does NOT persist across
    worker restarts. Production deployments should inject an implementation
    backed by Temporal event history or a durable store.

    Satisfies AuditTrail Protocol (structural subtyping — no inheritance required).
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    async def record_event(self, event: AuditEvent) -> None:
        """Append event to the in-memory list.

        Args:
            event: AuditEvent to persist. Appended in call order.
        """
        self._events.append(event)

    async def query_events(
        self,
        *,
        epoch_id: str | None = None,
        phase: PhaseId | None = None,
        role: RoleId | None = None,
    ) -> list[AuditEvent]:
        """Return events matching the given filters.

        Args:
            epoch_id: If provided, only return events where event.epoch_id matches.
            phase:    If provided, only return events where event.phase matches.
            role:     If provided, only return events where event.role matches.
                      (Included for full AuditTrail Protocol compliance.)

        Returns:
            Matching events in insertion (chronological) order.
        """
        result = self._events
        if epoch_id is not None:
            result = [e for e in result if e.epoch_id == epoch_id]
        if phase is not None:
            result = [e for e in result if e.phase == phase]
        if role is not None:
            result = [e for e in result if e.role == role]
        return list(result)
