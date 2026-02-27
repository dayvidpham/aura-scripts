"""Temporal workflow wrapper for the Aura epoch lifecycle.

Wraps EpochStateMachine with durable Temporal execution. Signals are used for
all state mutations (advance_phase, submit_vote); queries are used for reads
(current_state, available_transitions). Search attributes are updated on every
transition for forensic queryability.

Design rules:
- Workflow code MUST be deterministic: no I/O, no random, no datetime.now().
- Use workflow.now() for timestamps inside workflow code.
- Activities handle non-deterministic operations (constraint checks, recording).
- One workflow per epoch (not per phase) — sufficient for v1.

Key types (all frozen dataclasses):
    EpochInput          — workflow run() input
    EpochResult         — workflow run() return value
    PhaseAdvanceSignal  — advance_phase signal payload
    ReviewVoteSignal    — submit_vote signal payload
    SliceInput          — SliceWorkflow run() input
    SliceResult         — SliceWorkflow run() return value
    SliceProgressSignal — signal from SliceWorkflow → EpochWorkflow per leaf-task
    ReviewInput         — ReviewPhaseWorkflow run() input
    ReviewPhaseResult   — ReviewPhaseWorkflow run() return value

Search attribute keys:
    SA_EPOCH_ID — text key for epoch ID forensic lookup
    SA_PHASE    — keyword key for current phase
    SA_ROLE     — keyword key for current role
    SA_STATUS   — keyword key for workflow status
    SA_DOMAIN   — keyword key for phase domain

Activities:
    check_constraints(state, to_phase) -> list[ConstraintViolation]
    record_transition(record: TransitionRecord) -> None

Child Workflows:
    SliceWorkflow       — single P9_SLICE; runs concurrently with other slices
    ReviewPhaseWorkflow — P10_CODE_REVIEW; receives ReviewAxis votes via signals
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import SearchAttributeKey

from aura_protocol.constraints import ConstraintViolation, RuntimeConstraintChecker
from aura_protocol.state_machine import (
    EpochState,
    EpochStateMachine,
    TransitionError,
    TransitionRecord,
)
from aura_protocol.types import PhaseId, ReviewAxis, Transition, VoteType, PHASE_DOMAIN

# ─── Search Attribute Keys ────────────────────────────────────────────────────
# These keys are registered in the Temporal namespace and used for forensic
# querying: "find all workflows where AuraPhase='p9'" etc.

SA_EPOCH_ID: SearchAttributeKey = SearchAttributeKey.for_text("AuraEpochId")
SA_PHASE: SearchAttributeKey = SearchAttributeKey.for_keyword("AuraPhase")
SA_ROLE: SearchAttributeKey = SearchAttributeKey.for_keyword("AuraRole")
SA_STATUS: SearchAttributeKey = SearchAttributeKey.for_keyword("AuraStatus")
SA_DOMAIN: SearchAttributeKey = SearchAttributeKey.for_keyword("AuraDomain")


# ─── Signal / Query Types (frozen dataclasses) ────────────────────────────────


@dataclass(frozen=True)
class EpochInput:
    """Input for EpochWorkflow.run().

    epoch_id: globally unique epoch identifier (e.g. "aura-plugins-bj1")
    request_description: human-readable description of the work request
    """

    epoch_id: str
    request_description: str


@dataclass(frozen=True)
class EpochResult:
    """Return value of EpochWorkflow.run() when the epoch reaches COMPLETE.

    epoch_id: the epoch that completed
    final_phase: should always be PhaseId.COMPLETE
    transition_count: total number of records in transition_history, including
        failed attempts (those with TransitionRecord.success == False).
        This is the raw audit count; use successful_transition_count for the
        count of successful phase advances only.
    successful_transition_count: number of successful (non-failed) phase
        transitions. Failed attempts (TransitionRecord.success == False) are
        excluded. Equal to transition_count when no failures occurred.
    constraint_violations_total: cumulative violations detected during the run
    """

    epoch_id: str
    final_phase: PhaseId
    transition_count: int
    successful_transition_count: int
    constraint_violations_total: int


@dataclass(frozen=True)
class PhaseAdvanceSignal:
    """Signal payload for EpochWorkflow.advance_phase().

    to_phase: the target phase to advance to
    triggered_by: who or what triggered this transition (role or signal name)
    condition_met: the condition string from the transition table that was satisfied
    """

    to_phase: PhaseId
    triggered_by: str
    condition_met: str


@dataclass(frozen=True)
class ReviewVoteSignal:
    """Signal payload for EpochWorkflow.submit_vote().

    axis: review axis — must be ReviewAxis.CORRECTNESS, ReviewAxis.TEST_QUALITY,
         or ReviewAxis.ELEGANCE. Since ReviewAxis is a StrEnum, callers passing
         raw strings ("correctness", "test_quality", "elegance") continue to work
         at runtime; use ReviewAxis members for type correctness.
    vote: ACCEPT or REVISE
    reviewer_id: unique identifier for the reviewer agent
    """

    axis: ReviewAxis
    vote: VoteType
    reviewer_id: str


# ─── Child Workflow I/O Types (frozen dataclasses) ────────────────────────────


@dataclass(frozen=True)
class SliceProgressSignal:
    """Signal from SliceWorkflow → EpochWorkflow reporting per-leaf-task progress.

    Sent by SliceWorkflow once per leaf-task completion so EpochWorkflow can
    track real-time slice execution state without polling child handles.

    slice_id: which slice emitted this progress event (e.g. "slice-1")
    leaf_task_id: specific leaf task that completed within the slice
    stage_name: human-readable name of the completed stage (e.g. "execute")
    completed: True when this leaf task finished, False for in-progress events

    R12 stub: SliceWorkflow currently emits a single signal on completion.
    Future implementation will emit one signal per leaf task (types, tests, impl).
    """

    slice_id: str
    leaf_task_id: str
    stage_name: str
    completed: bool


@dataclass(frozen=True)
class SliceInput:
    """Input for SliceWorkflow.run().

    epoch_id: the parent epoch this slice belongs to
    slice_id: unique identifier for this slice within the epoch (e.g. "slice-1")
    phase_spec: serializable specification of the phase to execute
    parent_workflow_id: workflow ID of the parent EpochWorkflow; used to signal
        slice progress back to the parent via get_external_workflow_handle().
        Prefer explicit over workflow.info().parent.workflow_id for testability.
    """

    epoch_id: str
    slice_id: str
    phase_spec: str  # R12: SerializablePhaseSpec integration is future work
    parent_workflow_id: str


@dataclass(frozen=True)
class SliceResult:
    """Return value of SliceWorkflow.run().

    slice_id: the slice that completed or failed
    success: True if the slice completed without error
    error: error message if success is False, None otherwise
    """

    slice_id: str
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class ReviewInput:
    """Input for ReviewPhaseWorkflow.run().

    epoch_id: the parent epoch this review belongs to
    phase_id: which review phase this is (e.g. "p4" or "p10")
    """

    epoch_id: str
    phase_id: str


@dataclass(frozen=True)
class ReviewPhaseResult:
    """Return value of ReviewPhaseWorkflow.run().

    phase_id: the review phase that completed
    success: True if the review reached consensus (all axes voted)
    vote_result: mapping of ReviewAxis → VoteType for the final votes.
        Keys are ReviewAxis StrEnum members; values are VoteType StrEnum members.
        StrEnum keys are safe for Temporal JSONPlainPayloadConverter round-trips.
    """

    phase_id: str
    success: bool
    vote_result: dict[ReviewAxis, VoteType] = field(default_factory=dict)


# ─── Activities ───────────────────────────────────────────────────────────────
# Activities handle non-deterministic operations so the workflow remains
# deterministic and replayable.


@activity.defn
async def check_constraints(
    state: EpochState, to_phase: PhaseId
) -> list[ConstraintViolation]:
    """Check protocol constraints for a proposed phase transition.

    Runs RuntimeConstraintChecker.check_transition() against the current state
    and the proposed to_phase. Returns a list of violations (empty = valid).

    This is an activity (not inline workflow code) because constraint checking
    may in future versions involve I/O (reading external beads state, etc.).
    Keeping it as an activity ensures the workflow remains deterministic.
    """
    checker = RuntimeConstraintChecker()
    return checker.check_transition(state, to_phase)


@activity.defn
async def record_transition(record: TransitionRecord) -> None:
    """Persist a transition record to the audit trail.

    In v1, this is a no-op stub — the transition record is already stored in
    EpochState.transition_history (in-memory within the workflow). In v2, this
    would write to a durable store (Beads task comment, database, etc.).

    This activity exists to:
    1. Enforce the design boundary: recording is non-deterministic (I/O)
    2. Provide an extension point for v2 persistence without changing the workflow
    """
    # v1 stub: transition is already recorded in EpochState.transition_history.
    # v2: write to beads/database/audit log here.
    logger = logging.getLogger(__name__)
    logger.info(
        "Transition recorded: %s -> %s (triggered_by=%s)",
        record.from_phase.value,
        record.to_phase.value,
        record.triggered_by,
    )


# ─── Workflow ─────────────────────────────────────────────────────────────────


@workflow.defn
class EpochWorkflow:
    """Durable Temporal workflow wrapping the 12-phase EpochStateMachine.

    Lifecycle:
        1. run() initializes the state machine and updates search attributes.
        2. run() loops, waiting for advance_phase or submit_vote signals.
        3. On advance_phase: constraints are checked (activity), then state
           machine advances, search attributes are updated atomically.
        4. On submit_vote: the vote is recorded in the state machine.
        5. When current_phase reaches COMPLETE, run() returns EpochResult.

    Signals:
        advance_phase(PhaseAdvanceSignal)       — request a phase transition
        submit_vote(ReviewVoteSignal)           — record a reviewer vote
        slice_progress(SliceProgressSignal)    — receive progress from a child SliceWorkflow

    Queries:
        current_state() -> EpochState           — snapshot of epoch runtime state
        available_transitions() -> list[Transition] — valid next transitions
        slice_progress_state() -> list[SliceProgressSignal] — accumulated slice progress log

    Design invariants:
        - No datetime.now() in workflow code (use workflow.now() instead)
        - No I/O in workflow code (all I/O goes through activities)
        - Signal handlers enqueue work; transitions happen in run() loop
        - Search attributes updated via upsert_search_attributes() on every
          transition to keep AuraPhase / AuraStatus always in sync
    """

    def __init__(self) -> None:
        # Pending signals are queued here and processed in the run() loop.
        self._pending_advance: list[PhaseAdvanceSignal] = []
        self._pending_votes: list[ReviewVoteSignal] = []
        # Cumulative violation count across all transitions.
        self._total_violations: int = 0
        # State machine — initialized in run().
        self._sm: EpochStateMachine | None = None
        # Slice progress log — appended by slice_progress signal handler.
        # R12 stub: log is in-memory only; v2 will persist to beads/audit store.
        self._slice_progress_log: list[SliceProgressSignal] = []

    # ── Run ───────────────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, input: EpochInput) -> EpochResult:
        """Main workflow loop: initialize, process signals, advance through phases.

        Starts at P1_REQUEST and runs until COMPLETE. On each iteration:
        1. Drain any pending vote signals into the state machine.
        2. Process the next pending advance signal (if any):
           a. Check constraints via activity.
           b. Advance state machine.
           c. Persist transition record via activity.
           d. Upsert search attributes.
        3. Wait for the next signal (or exit if COMPLETE).
        """
        # Initialize the state machine.
        self._sm = EpochStateMachine(input.epoch_id)

        # Set initial search attributes.
        # SA_EPOCH_ID is immutable for the lifetime of this workflow run — it
        # identifies the epoch and never changes. It is set here (once) and
        # intentionally omitted from per-transition upserts below. Temporal
        # preserves existing search attribute values across upserts, so the
        # epoch ID remains indexed for forensic lookup throughout the run.
        initial_phase = self._sm.state.current_phase
        initial_domain = PHASE_DOMAIN[initial_phase].value if initial_phase in PHASE_DOMAIN else ""
        workflow.upsert_search_attributes(
            [
                SA_EPOCH_ID.value_set(input.epoch_id),
                SA_PHASE.value_set(initial_phase.value),
                SA_ROLE.value_set(self._sm.state.current_role.value),
                SA_STATUS.value_set("running"),
                SA_DOMAIN.value_set(initial_domain),
            ]
        )

        # Main signal-driven loop.
        while self._sm.state.current_phase != PhaseId.COMPLETE:
            # Wait until there is something to process.
            await workflow.wait_condition(
                lambda: bool(self._pending_advance) or bool(self._pending_votes)
            )

            # 1. Drain all pending votes.
            while self._pending_votes:
                vote_signal = self._pending_votes.pop(0)
                self._sm.record_vote(vote_signal.axis, vote_signal.vote)

            # 2. Process the next advance signal.
            if not self._pending_advance:
                continue

            advance_signal = self._pending_advance.pop(0)

            # 2a. Check constraints (activity — non-deterministic allowed here).
            violations = await workflow.execute_activity(
                check_constraints,
                args=[self._sm.state, advance_signal.to_phase],
                start_to_close_timeout=timedelta(seconds=10),
            )
            self._total_violations += len(violations)

            # 2b. Advance state machine (pure, deterministic).
            # Pass timestamp=workflow.now() directly so the record uses
            # deterministic workflow time — no post-hoc mutation needed.
            try:
                record = self._sm.advance(
                    advance_signal.to_phase,
                    triggered_by=advance_signal.triggered_by,
                    condition_met=advance_signal.condition_met,
                    timestamp=workflow.now(),
                )
            except TransitionError as e:
                # Invalid advance — record the failed attempt in the audit trail
                # so the transition_history captures all attempts (not just successes).
                # The failed record uses condition_met="FAILED: {error}" for display
                # and success=False for all programmatic success/failure checks.
                failed_record = TransitionRecord(
                    from_phase=self._sm.state.current_phase,
                    to_phase=advance_signal.to_phase,
                    timestamp=workflow.now(),
                    triggered_by=advance_signal.triggered_by,
                    condition_met=f"FAILED: {e}",
                    success=False,
                )
                self._sm.state.transition_history.append(failed_record)
                self._sm.state.last_error = str(e)
                continue

            # 2c. Record transition (activity — I/O boundary).
            await workflow.execute_activity(
                record_transition,
                args=[record],
                start_to_close_timeout=timedelta(seconds=10),
            )

            # 2d. Upsert search attributes atomically with the transition.
            current = self._sm.state.current_phase
            domain_value = (
                PHASE_DOMAIN[current].value
                if current in PHASE_DOMAIN
                else ""
            )
            workflow.upsert_search_attributes(
                [
                    SA_PHASE.value_set(current.value),
                    SA_ROLE.value_set(self._sm.state.current_role.value),
                    SA_STATUS.value_set(
                        "complete" if current == PhaseId.COMPLETE else "running"
                    ),
                    SA_DOMAIN.value_set(domain_value),
                ]
            )

        history = self._sm.state.transition_history
        successful = sum(1 for r in history if r.success)
        return EpochResult(
            epoch_id=input.epoch_id,
            final_phase=self._sm.state.current_phase,
            transition_count=len(history),
            successful_transition_count=successful,
            constraint_violations_total=self._total_violations,
        )

    # ── Signals ───────────────────────────────────────────────────────────────

    @workflow.signal
    def advance_phase(self, signal: PhaseAdvanceSignal) -> None:
        """Signal: request a phase transition.

        The signal is queued and processed in the next run() loop iteration.
        Transitions are not applied immediately in the signal handler to ensure
        deterministic ordering and proper activity scheduling.
        """
        self._pending_advance.append(signal)

    @workflow.signal
    def submit_vote(self, signal: ReviewVoteSignal) -> None:
        """Signal: record a reviewer vote.

        The vote is queued and applied before the next advance_phase processing
        in the run() loop. Votes affect available_transitions() immediately
        after drain.
        """
        self._pending_votes.append(signal)

    @workflow.signal
    def slice_progress(self, signal: SliceProgressSignal) -> None:
        """Signal: receive a progress update from a child SliceWorkflow.

        Appends the signal to _slice_progress_log for real-time tracking.
        The log is queryable via slice_progress_state().

        R12 stub: log is in-memory only; v2 will persist to beads/audit store.
        """
        self._slice_progress_log.append(signal)

    # ── Queries ───────────────────────────────────────────────────────────────

    @workflow.query
    def current_state(self) -> EpochState:
        """Query: return a snapshot of the current epoch runtime state.

        Returns the EpochState from the underlying state machine.
        The returned state is mutable — callers must not modify it.
        """
        if self._sm is None:
            # Workflow not yet initialized (query before run() starts).
            raise RuntimeError("Workflow not yet initialized — run() has not started.")
        return self._sm.state

    @workflow.query
    def available_transitions(self) -> list[Transition]:
        """Query: return the list of currently available phase transitions.

        Delegates to EpochStateMachine.available_transitions which applies
        all gate rules (consensus, BLOCKER, REVISE vote).
        """
        if self._sm is None:
            return []
        return self._sm.available_transitions

    @workflow.query
    def slice_progress_state(self) -> list[SliceProgressSignal]:
        """Query: return all accumulated slice progress signals so far.

        Returns the ordered list of SliceProgressSignal events received from
        child SliceWorkflows. Callers can use this to track which leaf tasks
        have completed and in what order without polling child handles.

        R12 stub: log is in-memory; empty until SliceWorkflow children signal.
        """
        return list(self._slice_progress_log)

    # ── P9 Slice Execution ────────────────────────────────────────────────────

    async def _run_p9_slices(self, slice_inputs: list[SliceInput]) -> list[SliceResult]:
        """Run P9_SLICE: start N child SliceWorkflows, fail-fast on first exception.

        Starts all SliceWorkflow children concurrently, then waits for them
        using workflow.wait(FIRST_EXCEPTION) — the deterministic Temporal
        equivalent of asyncio.wait. On the first failure, cancels all
        pending handles and propagates the exception.

        Args:
            slice_inputs: List of SliceInput, one per worker slice.

        Returns:
            List of SliceResult from all completed slices (happy path only).

        Raises:
            Exception: The first exception raised by any failing slice.
        """
        # Start all child SliceWorkflows concurrently.
        handles = []
        for si in slice_inputs:
            handle = await workflow.start_child_workflow(
                SliceWorkflow.run,
                si,
                id=f"{si.epoch_id}-slice-{si.slice_id}",
            )
            handles.append(handle)

        if not handles:
            return []

        # Collect result futures from handles. ChildWorkflowHandle IS an
        # asyncio.Task in the Temporal Python SDK, so await it to get the result.
        # Use workflow.wait(FIRST_EXCEPTION) for deterministic fail-fast semantics.
        # IMPORTANT: asyncio.wait is NON-DETERMINISTIC in Temporal replay;
        # workflow.wait is the approved deterministic replacement.
        done, pending = await workflow.wait(
            handles,
            return_when=asyncio.FIRST_EXCEPTION,
        )

        # Cancel remaining pending handles on failure.
        # Awaiting each cancelled handle individually (not asyncio.gather)
        # ensures no parallel fan-out from the supervisor — each cancellation
        # is explicitly drained in sequence.
        if pending:
            for p in pending:
                p.cancel()
            for p in pending:
                try:
                    await p
                except (asyncio.CancelledError, Exception):
                    pass

        # Collect results or re-raise first exception.
        results = []
        for task in done:
            exc = task.exception() if not task.cancelled() else None
            if exc is not None:
                raise exc
            results.append(task.result())

        return results

    # ── P10 Review Phase Execution ────────────────────────────────────────────

    async def _run_p10_review(self, review_input: ReviewInput) -> ReviewPhaseResult:
        """Run P10_CODE_REVIEW: start ReviewPhaseWorkflow child and wait for completion.

        Starts a single ReviewPhaseWorkflow child for the given review phase.
        The child waits for all 3 ReviewAxis members to vote before returning.

        Args:
            review_input: ReviewInput specifying the epoch and phase.

        Returns:
            PhaseResult containing the vote results from all reviewers.
        """
        handle = await workflow.start_child_workflow(
            ReviewPhaseWorkflow.run,
            review_input,
            id=f"{review_input.epoch_id}-review-{review_input.phase_id}",
        )
        return await handle


# ─── Child Workflows ───────────────────────────────────────────────────────────


@workflow.defn
class SliceWorkflow:
    """Child workflow for a single P9_SLICE implementation slice.

    Runs concurrently with other SliceWorkflow instances within the same epoch.
    EpochWorkflow._run_p9_slices() uses workflow.wait(FIRST_EXCEPTION) to
    fail-fast: if any slice raises, remaining slices are cancelled.

    Parent signaling:
        On completion, SliceWorkflow signals the parent EpochWorkflow via
        EpochWorkflow.slice_progress using input.parent_workflow_id. The signal
        uses get_external_workflow_handle() so the parent can be reached even
        from a concurrent child context. Signal delivery is best-effort: if the
        parent has already completed, the exception is caught and logged rather
        than propagated (signal delivery failure must never fail the slice).

    R12 stub: actual slice execution (running the worker agent, checking output,
    parsing results) is future work. This stub returns success immediately so
    that the EpochWorkflow topology and fail-fast wiring can be tested end-to-end
    before slice execution semantics are defined.
    """

    @workflow.run
    async def run(self, input: SliceInput) -> SliceResult:
        """Execute a single implementation slice.

        Args:
            input: SliceInput with epoch_id, slice_id, phase_spec, and
                parent_workflow_id. parent_workflow_id is the workflow ID of
                the EpochWorkflow parent; used to signal slice progress.

        Returns:
            SliceResult indicating success or failure.

        R12 stub: returns SliceResult(success=True) immediately. Future
        implementation will execute the slice via activities (spawn worker,
        collect results, validate output) and return failure on any error.
        """
        # R12 stub: slice execution via activities is future work.
        # When implemented: execute_activity(run_slice_agent, input, ...) etc.

        # Signal parent EpochWorkflow with completion progress.
        # Uses input.parent_workflow_id (explicit) rather than
        # workflow.info().parent.workflow_id (implicit) for testability.
        # Wrapped in try/except: if the parent EpochWorkflow has already
        # completed before this signal is delivered (race condition), the
        # exception is caught and logged. Signal delivery failure must never
        # cause the slice itself to fail — the SliceResult is still returned.
        try:
            parent_handle = workflow.get_external_workflow_handle(input.parent_workflow_id)
            await parent_handle.signal(
                EpochWorkflow.slice_progress,
                SliceProgressSignal(
                    slice_id=input.slice_id,
                    leaf_task_id=input.slice_id,
                    stage_name="execute",
                    completed=True,
                ),
            )
        except Exception as e:  # noqa: BLE001
            # Parent may have completed before signal arrived — non-fatal.
            workflow.logger.warning(
                "SliceWorkflow(%s): parent signal delivery failed (parent_id=%s): %s",
                input.slice_id,
                input.parent_workflow_id,
                e,
            )

        return SliceResult(slice_id=input.slice_id, success=True)


@workflow.defn
class ReviewPhaseWorkflow:
    """Child workflow for P10_CODE_REVIEW (or P4_REVIEW) phase.

    Receives ReviewVoteSignal signals from reviewer agents via submit_vote().
    Waits using workflow.wait_condition() until all 3 ReviewAxis members have
    cast their vote, then returns a PhaseResult with the full vote mapping.

    Signal routing:
        EpochWorkflow sends ReviewVoteSignal to this child via handle.signal().
        The try/except ApplicationError around signal() calls provides race
        protection: if the child completes before a signal arrives, the signal
        is dropped rather than causing an error in the parent.
    """

    def __init__(self) -> None:
        # Votes keyed by ReviewAxis StrEnum for type safety.
        # ReviewAxis is a StrEnum, so its members are also valid str keys and
        # are safely round-tripped by Temporal's JSONPlainPayloadConverter.
        self._votes: dict[ReviewAxis, VoteType] = {}

    @workflow.signal
    async def submit_vote(self, signal: ReviewVoteSignal) -> None:
        """Signal: receive a vote from a reviewer agent.

        Records the vote for the given ReviewAxis. Idempotent: if the same axis
        votes again, the later vote overwrites the earlier one.

        Args:
            signal: ReviewVoteSignal with axis, vote, and reviewer_id.
        """
        self._votes[signal.axis] = signal.vote

    @workflow.run
    async def run(self, input: ReviewInput) -> ReviewPhaseResult:
        """Wait for all 3 ReviewAxis members to vote, then return results.

        Blocks via workflow.wait_condition() until all 3 axes (CORRECTNESS,
        TEST_QUALITY, ELEGANCE) have submitted votes. Returns a ReviewPhaseResult
        with the final vote mapping.

        Args:
            input: ReviewInput with epoch_id and phase_id.

        Returns:
            ReviewPhaseResult with success=True and the complete vote mapping.
        """
        # Wait until all 3 ReviewAxis members have voted.
        all_axes = set(ReviewAxis)
        await workflow.wait_condition(
            lambda: set(self._votes.keys()) >= all_axes
        )
        return ReviewPhaseResult(
            phase_id=input.phase_id,
            success=True,
            vote_result=dict(self._votes),
        )
