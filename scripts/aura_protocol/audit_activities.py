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

import asyncio
import logging

from temporalio import activity
from temporalio.exceptions import ApplicationError

from aura_protocol.interfaces import AuditTrail
from aura_protocol.types import AuditEvent, PhaseId, RoleId
from aura_protocol.workflow import SliceResult


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
    role: RoleId | None = None,
) -> list[AuditEvent]:
    """Query recorded audit events for an epoch, with optional phase and role filters.

    Activity: non-deterministic I/O boundary (reads from external store).

    Args:
        epoch_id: The epoch to query events for (required — Temporal activities
                  cannot use keyword-only args directly; this is positional).
        phase:    Optional phase filter — only return events from this phase.
        role:     Optional role filter — only return events from this role
                  (e.g. RoleId.Supervisor, RoleId.Worker). Without this filter,
                  queries that scope to a specific agent role silently return
                  unfiltered results, which is a silent correctness failure.

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
    return await _AUDIT_TRAIL.query_events(epoch_id=epoch_id, phase=phase, role=role)


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


# ─── Slice Execution Activity ───────────────────────────────────────────────


def _check_tmux(search_path: str | None = None) -> bool:
    """Check if tmux is available via shutil.which DI.

    Args:
        search_path: Directory to search for tmux binary. None uses PATH.

    Returns:
        True if tmux executable found at search_path, False otherwise.
    """
    import shutil

    return shutil.which("tmux", path=search_path) is not None


@activity.defn
async def execute_slice_command(
    command: str,
    slice_id: str,
    epoch_id: str,
    search_path: str | None = None,
) -> SliceResult:
    """Execute a slice command via tmux shell launch.

    Checks for tmux availability via _check_tmux(search_path).
    If tmux not found, returns SliceResult(success=False, error="tmux not found").
    If tmux found, launches command via subprocess.

    Args:
        command: Shell command to execute.
        slice_id: Unique slice identifier for result tracking.
        epoch_id: Parent epoch identifier for audit context.
        search_path: Directory to search for tmux binary. None uses PATH.

    Returns:
        SliceResult with success/failure and output/error details.
    """
    logger = logging.getLogger(__name__)

    if not _check_tmux(search_path):
        return SliceResult(
            slice_id=slice_id,
            success=False,
            error="tmux not found",
        )

    logger.info(
        "execute_slice_command(slice=%s, epoch=%s): launching '%s'",
        slice_id,
        epoch_id,
        command,
    )

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return SliceResult(
                slice_id=slice_id,
                success=True,
                output=stdout.decode() if stdout else "",
            )
        return SliceResult(
            slice_id=slice_id,
            success=False,
            error=f"Command exited with code {proc.returncode}: "
            f"{stderr.decode() if stderr else ''}",
        )
    except Exception as e:
        logger.exception(
            "execute_slice_command(slice=%s): failed to execute command",
            slice_id,
        )
        return SliceResult(
            slice_id=slice_id,
            success=False,
            error=f"Failed to execute command: {e}",
        )
