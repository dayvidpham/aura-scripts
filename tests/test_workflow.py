"""Tests for aura_protocol.workflow — Temporal workflow wrapper.

BDD Acceptance Criteria:
    AC6: Given running EpochWorkflow, when advance_phase signal then state + search
         attrs updated atomically. Should not have non-deterministic ops.
    AC7: Given workflow at P9, when querying AuraPhase="p9" then workflow returned.
         Should not have stale search attrs.

Coverage strategy:
    - Types importable and structurally correct (AC6/AC7 foundation)
    - Search attribute keys correct (name + type)
    - Activity: check_constraints delegates to RuntimeConstraintChecker
    - Activity: record_transition is a no-op stub (v1)
    - EpochWorkflow class has correct signal/query decorators
    - Signal/advance logic via direct state machine integration tests
    - Review vote signals correctly queued and applied
    - WorkflowEnvironment.start_time_skipping() end-to-end sandbox tests
      (skip-safe when Temporal test server binary is unavailable)

Note on Temporal sandbox testing:
    WorkflowEnvironment.start_time_skipping() requires a Temporal test server
    binary (downloaded at runtime). In environments without network access or
    a cached binary, we test:
    1. Activities via ActivityEnvironment (in-process, no server required)
    2. Workflow logic via direct integration with EpochStateMachine
       (same deterministic code path the workflow uses)
    3. Structural invariants via introspection of @workflow.defn decorators

    When a Temporal server is available, full end-to-end sandbox tests use
    WorkflowEnvironment.start_time_skipping() with the EpochWorkflow class
    (see TestWorkflowEnvironmentSandbox at the bottom of this file).
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import os
from dataclasses import fields
from datetime import timedelta

import pytest
import pytest_asyncio

from aura_protocol.constraints import ConstraintViolation, RuntimeConstraintChecker
from aura_protocol.state_machine import (
    EpochState,
    EpochStateMachine,
    TransitionError,
    TransitionRecord,
)
from aura_protocol.types import PhaseId, ReviewAxis, Transition, VoteType
from aura_protocol.workflow import (
    SA_DOMAIN,
    SA_EPOCH_ID,
    SA_PHASE,
    SA_ROLE,
    SA_STATUS,
    EpochInput,
    EpochResult,
    EpochWorkflow,
    PhaseAdvanceSignal,
    ReviewVoteSignal,
    check_constraints,
    record_transition,
)
from conftest import _advance_to
from temporalio.common import SearchAttributeKey
from temporalio.testing import ActivityEnvironment


# ─── Activity Registration ─────────────────────────────────────────────────────
# Centralized list of @activity.defn functions registered with Temporal workers
# in sandbox tests. Extend here when new activity modules are added.

_TEMPORAL_ACTIVITIES: list = [check_constraints, record_transition]

try:
    from aura_protocol.audit_activities import query_audit_events, record_audit_event

    _TEMPORAL_ACTIVITIES = [
        check_constraints,
        record_transition,
        record_audit_event,
        query_audit_events,
    ]
except ImportError:
    pass  # SLICE-3 (aura-plugins-sp6y) not yet merged


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_sm(epoch_id: str = "test-epoch") -> EpochStateMachine:
    """Return a fresh EpochStateMachine at P1."""
    return EpochStateMachine(epoch_id)


# ─── L1: Type Definitions ─────────────────────────────────────────────────────


class TestSearchAttributeKeys:
    """Search attribute keys are correctly named and typed."""

    def test_sa_epoch_id_is_text(self) -> None:
        """SA_EPOCH_ID must be a text key named 'AuraEpochId'."""
        assert SA_EPOCH_ID.name == "AuraEpochId"
        # text keys accept str values — verify value_set works
        update = SA_EPOCH_ID.value_set("epoch-123")
        assert update is not None

    def test_sa_phase_is_keyword(self) -> None:
        """SA_PHASE must be a keyword key named 'AuraPhase'."""
        assert SA_PHASE.name == "AuraPhase"
        update = SA_PHASE.value_set("p9")
        assert update is not None

    def test_sa_role_is_keyword(self) -> None:
        """SA_ROLE must be a keyword key named 'AuraRole'."""
        assert SA_ROLE.name == "AuraRole"
        update = SA_ROLE.value_set("supervisor")
        assert update is not None

    def test_sa_status_is_keyword(self) -> None:
        """SA_STATUS must be a keyword key named 'AuraStatus'."""
        assert SA_STATUS.name == "AuraStatus"
        update = SA_STATUS.value_set("running")
        assert update is not None

    def test_sa_domain_is_keyword(self) -> None:
        """SA_DOMAIN must be a keyword key named 'AuraDomain'."""
        assert SA_DOMAIN.name == "AuraDomain"
        update = SA_DOMAIN.value_set("impl")
        assert update is not None

    def test_all_sa_keys_are_search_attribute_keys(self) -> None:
        """All SA_* constants must be SearchAttributeKey instances."""
        for key in [SA_EPOCH_ID, SA_PHASE, SA_ROLE, SA_STATUS, SA_DOMAIN]:
            assert isinstance(key, SearchAttributeKey)


class TestSignalQueryTypes:
    """Signal/query type dataclasses are correctly structured."""

    def test_epoch_input_is_frozen_dataclass(self) -> None:
        """EpochInput must be a frozen dataclass with epoch_id and request_description."""
        inp = EpochInput(epoch_id="ep-1", request_description="test request")
        assert inp.epoch_id == "ep-1"
        assert inp.request_description == "test request"
        # Frozen: must raise on attribute set
        with pytest.raises((AttributeError, TypeError)):
            inp.epoch_id = "changed"  # type: ignore[misc]

    def test_epoch_result_is_frozen_dataclass(self) -> None:
        """EpochResult must be a frozen dataclass with the correct fields."""
        result = EpochResult(
            epoch_id="ep-1",
            final_phase=PhaseId.COMPLETE,
            transition_count=12,
            successful_transition_count=12,
            constraint_violations_total=0,
        )
        assert result.epoch_id == "ep-1"
        assert result.final_phase == PhaseId.COMPLETE
        assert result.transition_count == 12
        assert result.successful_transition_count == 12
        assert result.constraint_violations_total == 0
        with pytest.raises((AttributeError, TypeError)):
            result.transition_count = 0  # type: ignore[misc]

    def test_phase_advance_signal_is_frozen_dataclass(self) -> None:
        """PhaseAdvanceSignal must be a frozen dataclass with to_phase, triggered_by, condition_met."""
        sig = PhaseAdvanceSignal(
            to_phase=PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="classification confirmed",
        )
        assert sig.to_phase == PhaseId.P2_ELICIT
        assert sig.triggered_by == "architect"
        assert sig.condition_met == "classification confirmed"
        with pytest.raises((AttributeError, TypeError)):
            sig.to_phase = PhaseId.P3_PROPOSE  # type: ignore[misc]

    def test_review_vote_signal_is_frozen_dataclass(self) -> None:
        """ReviewVoteSignal must be a frozen dataclass with axis, vote, reviewer_id."""
        sig = ReviewVoteSignal(axis=ReviewAxis.CORRECTNESS, vote=VoteType.ACCEPT, reviewer_id="reviewer-1")
        assert sig.axis == ReviewAxis.CORRECTNESS
        assert sig.vote == VoteType.ACCEPT
        assert sig.reviewer_id == "reviewer-1"
        with pytest.raises((AttributeError, TypeError)):
            sig.axis = ReviewAxis.TEST_QUALITY  # type: ignore[misc]

    def test_phase_advance_signal_uses_phase_id_enum(self) -> None:
        """PhaseAdvanceSignal.to_phase must be a PhaseId enum."""
        sig = PhaseAdvanceSignal(
            to_phase=PhaseId.P9_SLICE,
            triggered_by="supervisor",
            condition_met="slices created",
        )
        assert sig.to_phase is PhaseId.P9_SLICE
        assert isinstance(sig.to_phase, PhaseId)

    def test_review_vote_signal_uses_vote_type_enum(self) -> None:
        """ReviewVoteSignal.vote must be a VoteType enum."""
        sig = ReviewVoteSignal(axis=ReviewAxis.TEST_QUALITY, vote=VoteType.REVISE, reviewer_id="reviewer-2")
        assert sig.vote is VoteType.REVISE
        assert isinstance(sig.vote, VoteType)


class TestWorkflowStructure:
    """EpochWorkflow has correct Temporal decorator structure (introspection).

    temporalio attaches double-underscore attributes (e.g. __temporal_signal_definition)
    to decorated methods. We check for these to verify the decorators were applied
    correctly without running the full Temporal test server.
    """

    def test_workflow_defn_applied(self) -> None:
        """EpochWorkflow must have @workflow.defn applied (has __temporal_workflow_definition)."""
        # @workflow.defn attaches __temporal_workflow_definition to the class
        assert hasattr(EpochWorkflow, "__temporal_workflow_definition")

    def test_advance_phase_is_signal(self) -> None:
        """advance_phase must be a @workflow.signal handler."""
        method = EpochWorkflow.advance_phase
        assert hasattr(method, "__temporal_signal_definition")

    def test_submit_vote_is_signal(self) -> None:
        """submit_vote must be a @workflow.signal handler."""
        method = EpochWorkflow.submit_vote
        assert hasattr(method, "__temporal_signal_definition")

    def test_current_state_is_query(self) -> None:
        """current_state must be a @workflow.query handler."""
        method = EpochWorkflow.current_state
        assert hasattr(method, "__temporal_query_definition")

    def test_available_transitions_is_query(self) -> None:
        """available_transitions must be a @workflow.query handler."""
        method = EpochWorkflow.available_transitions
        assert hasattr(method, "__temporal_query_definition")

    def test_run_is_workflow_run(self) -> None:
        """run must be the @workflow.run entry point."""
        method = EpochWorkflow.run
        assert hasattr(method, "__temporal_workflow_run")


# ─── L2: Activity Tests ────────────────────────────────────────────────────────
# Using ActivityEnvironment — runs activities in-process without a Temporal server.


class TestCheckConstraintsActivity:
    """AC6: check_constraints activity validates protocol constraints."""

    @pytest.mark.asyncio
    async def test_valid_p1_to_p2_advance_has_no_violations(self) -> None:
        """check_constraints at P1 proposing P2 returns no violations.

        This is the simplest forward transition with no gate conditions.
        """
        sm = _make_sm("epoch-test-1")
        env = ActivityEnvironment()
        violations = await env.run(check_constraints, sm.state, PhaseId.P2_ELICIT)
        assert isinstance(violations, list)
        assert violations == []

    @pytest.mark.asyncio
    async def test_p4_to_p5_without_consensus_has_violations(self) -> None:
        """check_constraints at P4 proposing P5 without consensus returns violations.

        C-review-consensus: all 3 axes (A, B, C) must ACCEPT before advancing.
        """
        sm = _make_sm("epoch-test-2")
        _advance_to(sm, PhaseId.P4_REVIEW)
        # No votes recorded — consensus not reached.
        env = ActivityEnvironment()
        violations = await env.run(check_constraints, sm.state, PhaseId.P5_UAT)
        assert len(violations) > 0
        constraint_ids = [v.constraint_id for v in violations]
        assert "C-review-consensus" in constraint_ids

    @pytest.mark.asyncio
    async def test_p4_to_p5_with_consensus_has_no_violations(self) -> None:
        """check_constraints at P4 with all 3 ACCEPT returns no violations."""
        sm = _make_sm("epoch-test-3")
        _advance_to(sm, PhaseId.P4_REVIEW)
        # Record all 3 ACCEPT votes (satisfied in _advance_to already, but let's be explicit).
        # _advance_to stops before advancing through the gate; re-record.
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)
        env = ActivityEnvironment()
        violations = await env.run(check_constraints, sm.state, PhaseId.P5_UAT)
        # No consensus violations (only handoff-required violations for actor-change transitions).
        consensus_violations = [v for v in violations if v.constraint_id == "C-review-consensus"]
        assert consensus_violations == []

    @pytest.mark.asyncio
    async def test_check_constraints_returns_list_of_constraint_violations(self) -> None:
        """check_constraints always returns list[ConstraintViolation]."""
        sm = _make_sm("epoch-test-4")
        env = ActivityEnvironment()
        result = await env.run(check_constraints, sm.state, PhaseId.P2_ELICIT)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, ConstraintViolation)


class TestRecordTransitionActivity:
    """record_transition activity is a no-op stub that does not raise."""

    @pytest.mark.asyncio
    async def test_record_transition_succeeds_without_side_effects(self) -> None:
        """record_transition completes without raising for a valid TransitionRecord."""
        from datetime import datetime, timezone

        record = TransitionRecord(
            from_phase=PhaseId.P1_REQUEST,
            to_phase=PhaseId.P2_ELICIT,
            timestamp=datetime.now(tz=timezone.utc),
            triggered_by="architect",
            condition_met="classification confirmed",
        )
        env = ActivityEnvironment()
        # Should not raise.
        result = await env.run(record_transition, record)
        assert result is None

    @pytest.mark.asyncio
    async def test_record_transition_accepts_any_phase_pair(self) -> None:
        """record_transition works for all valid phase pairs."""
        from datetime import datetime, timezone

        for from_p, to_p in [
            (PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE),
            (PhaseId.P9_SLICE, PhaseId.P10_CODE_REVIEW),
            (PhaseId.P12_LANDING, PhaseId.COMPLETE),
        ]:
            record = TransitionRecord(
                from_phase=from_p,
                to_phase=to_p,
                timestamp=datetime.now(tz=timezone.utc),
                triggered_by="supervisor",
                condition_met="all conditions met",
            )
            env = ActivityEnvironment()
            result = await env.run(record_transition, record)
            assert result is None


# ─── L3: AC6 / AC7 — State Machine Integration ───────────────────────────────
# These tests verify the SAME deterministic logic that EpochWorkflow.run() uses.
# When a Temporal sandbox is available, these assertions hold end-to-end.


class TestAC6AdvancePhaseSignalLogic:
    """AC6: advance_phase signal causes state transitions and search attr updates.

    Tests the underlying deterministic logic that EpochWorkflow.run() executes
    on receiving an advance_phase signal. This is the same code path; the
    workflow wraps it with Temporal's signal delivery mechanism.
    """

    def test_advance_p1_to_p2_updates_state(self) -> None:
        """Advance from P1 to P2 transitions state atomically.

        AC6: state transitions must be atomic — no partial state visible.
        """
        sm = _make_sm("ac6-epoch-1")
        assert sm.state.current_phase == PhaseId.P1_REQUEST

        record = sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="classification confirmed",
        )

        # State updated atomically.
        assert sm.state.current_phase == PhaseId.P2_ELICIT
        assert PhaseId.P1_REQUEST in sm.state.completed_phases
        assert record.from_phase == PhaseId.P1_REQUEST
        assert record.to_phase == PhaseId.P2_ELICIT

    def test_advance_records_transition_history(self) -> None:
        """Each advance appends to transition_history (audit trail preserved).

        AC6: should not have non-deterministic ops — history is deterministic.
        """
        sm = _make_sm("ac6-epoch-2")
        sm.advance(PhaseId.P2_ELICIT, triggered_by="architect", condition_met="confirmed")
        sm.advance(PhaseId.P3_PROPOSE, triggered_by="architect", condition_met="URD created")

        assert len(sm.state.transition_history) == 2
        assert sm.state.transition_history[0].from_phase == PhaseId.P1_REQUEST
        assert sm.state.transition_history[0].to_phase == PhaseId.P2_ELICIT
        assert sm.state.transition_history[1].from_phase == PhaseId.P2_ELICIT
        assert sm.state.transition_history[1].to_phase == PhaseId.P3_PROPOSE

    def test_invalid_advance_raises_transition_error(self) -> None:
        """Attempting an invalid transition raises TransitionError (not a silent skip).

        AC6: signal-driven advancement must reject invalid transitions.
        """
        sm = _make_sm("ac6-epoch-3")
        # P1 cannot directly advance to P9.
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(PhaseId.P9_SLICE, triggered_by="architect", condition_met="invalid")
        assert len(exc_info.value.violations) > 0

    def test_advance_through_multiple_phases_sequentially(self) -> None:
        """Signal-driven progression through P1 → P2 → P3 advances state correctly.

        Simulates 3 successive advance_phase signals processed in order.
        """
        sm = _make_sm("ac6-epoch-4")

        signals = [
            PhaseAdvanceSignal(
                to_phase=PhaseId.P2_ELICIT,
                triggered_by="architect",
                condition_met="classification confirmed",
            ),
            PhaseAdvanceSignal(
                to_phase=PhaseId.P3_PROPOSE,
                triggered_by="architect",
                condition_met="URD created",
            ),
            PhaseAdvanceSignal(
                to_phase=PhaseId.P4_REVIEW,
                triggered_by="architect",
                condition_met="proposal created",
            ),
        ]

        for signal in signals:
            sm.advance(
                signal.to_phase,
                triggered_by=signal.triggered_by,
                condition_met=signal.condition_met,
            )

        assert sm.state.current_phase == PhaseId.P4_REVIEW
        assert len(sm.state.transition_history) == 3
        expected_completed = {PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P3_PROPOSE}
        assert expected_completed.issubset(sm.state.completed_phases)

    def test_search_attributes_values_are_correct_after_advance(self) -> None:
        """After advance, the values used for search attribute upsert are correct.

        AC6: search attrs must be updated atomically with the state transition.
        We verify the source values (current phase, role) that the workflow
        would use in upsert_search_attributes().
        """
        from aura_protocol.types import PHASE_DOMAIN

        sm = _make_sm("ac6-epoch-5")
        sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="confirmed",
        )

        # Values that the workflow.upsert_search_attributes() call would use.
        expected_phase = sm.state.current_phase.value
        expected_role = sm.state.current_role
        expected_domain = PHASE_DOMAIN.get(sm.state.current_phase)

        assert expected_phase == "p2"
        assert expected_role is not None
        assert expected_domain is not None  # P2 is in USER domain

    def test_review_vote_signal_recorded_before_advance(self) -> None:
        """ReviewVoteSignal: submit_vote queues votes, applied before next advance.

        Simulates the workflow's vote-draining logic: votes are applied
        before processing the advance signal.
        """
        sm = _make_sm("ac6-epoch-6")
        _advance_to(sm, PhaseId.P4_REVIEW)

        # Simulate 3 ReviewVoteSignals being received.
        vote_signals = [
            ReviewVoteSignal(axis=ReviewAxis.CORRECTNESS, vote=VoteType.ACCEPT, reviewer_id="reviewer-correctness"),
            ReviewVoteSignal(axis=ReviewAxis.TEST_QUALITY, vote=VoteType.ACCEPT, reviewer_id="reviewer-test_quality"),
            ReviewVoteSignal(axis=ReviewAxis.ELEGANCE, vote=VoteType.ACCEPT, reviewer_id="reviewer-elegance"),
        ]

        # Apply votes (drain, as workflow.run() does).
        for v_signal in vote_signals:
            sm.record_vote(v_signal.axis, v_signal.vote)

        # Now advance should succeed.
        assert sm.has_consensus()
        record = sm.advance(
            PhaseId.P5_UAT,
            triggered_by="reviewer",
            condition_met="all 3 vote ACCEPT",
        )
        assert record.to_phase == PhaseId.P5_UAT
        assert sm.state.current_phase == PhaseId.P5_UAT

    def test_revise_vote_blocks_forward_advance(self) -> None:
        """A single REVISE vote makes only the backward transition available.

        AC6: vote signals must affect available_transitions atomically.
        """
        sm = _make_sm("ac6-epoch-7")
        _advance_to(sm, PhaseId.P4_REVIEW)

        # One REVISE vote — consensus blocked.
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)

        # Forward transition (P4→P5) no longer in available_transitions.
        available = sm.available_transitions
        to_phases = {t.to_phase for t in available}
        assert PhaseId.P5_UAT not in to_phases
        assert PhaseId.P3_PROPOSE in to_phases


class TestAC7QueryCurrentState:
    """AC7: Query current_state returns correct phase; search attrs not stale.

    Tests verify that after state machine transitions, the state exposed via
    current_state() query reflects the actual current phase — no stale data.
    """

    def test_initial_state_is_p1(self) -> None:
        """AC7: Before any advance, current_state().current_phase == P1."""
        sm = _make_sm("ac7-epoch-1")
        # current_state() in the workflow returns sm.state directly.
        state = sm.state
        assert state.current_phase == PhaseId.P1_REQUEST

    def test_state_after_p9_advance_reflects_p9(self) -> None:
        """AC7: After advancing to P9, current_state query returns P9 phase.

        This is the AC7 scenario: AuraPhase='p9' query should return the workflow.
        """
        sm = _make_sm("ac7-epoch-2")
        _advance_to(sm, PhaseId.P9_SLICE)

        # The workflow current_state() query returns sm.state.
        state = sm.state
        assert state.current_phase == PhaseId.P9_SLICE
        assert state.current_phase.value == "p9"

    def test_current_state_reflects_completed_phases(self) -> None:
        """AC7: current_state includes completed_phases — no stale phase info."""
        sm = _make_sm("ac7-epoch-3")
        _advance_to(sm, PhaseId.P3_PROPOSE)

        state = sm.state
        assert PhaseId.P1_REQUEST in state.completed_phases
        assert PhaseId.P2_ELICIT in state.completed_phases
        assert PhaseId.P3_PROPOSE not in state.completed_phases  # current, not completed

    def test_available_transitions_query_correct_at_p9(self) -> None:
        """AC7: available_transitions() at P9 returns P10 as the valid next step."""
        sm = _make_sm("ac7-epoch-4")
        _advance_to(sm, PhaseId.P9_SLICE)

        # available_transitions() is the same logic the workflow query exposes.
        transitions = sm.available_transitions
        assert len(transitions) == 1
        assert transitions[0].to_phase == PhaseId.P10_CODE_REVIEW

    def test_available_transitions_empty_at_complete(self) -> None:
        """AC7: available_transitions() at COMPLETE returns empty list."""
        sm = _make_sm("ac7-epoch-5")
        _advance_to(sm, PhaseId.COMPLETE)

        transitions = sm.available_transitions
        assert transitions == []

    def test_vote_state_visible_in_current_state(self) -> None:
        """AC7: review votes appear in current_state().review_votes (no stale state)."""
        sm = _make_sm("ac7-epoch-6")
        _advance_to(sm, PhaseId.P4_REVIEW)
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.REVISE)

        state = sm.state
        assert state.review_votes.get(ReviewAxis.CORRECTNESS) == VoteType.ACCEPT
        assert state.review_votes.get(ReviewAxis.TEST_QUALITY) == VoteType.REVISE

    def test_state_search_attr_values_match_current_phase(self) -> None:
        """AC7: The phase value used for SA_PHASE upsert matches current state.

        Verifies no stale search attributes — the values come directly from
        sm.state.current_phase.value after each transition.
        """
        sm = _make_sm("ac7-epoch-7")
        _advance_to(sm, PhaseId.P9_SLICE)

        # This is what the workflow would set for AuraPhase after reaching P9.
        phase_sa_value = sm.state.current_phase.value
        assert phase_sa_value == "p9"

        # Also verify the SA_PHASE key name matches what Temporal would index.
        assert SA_PHASE.name == "AuraPhase"


# ─── last_error: Workflow Error Observability ─────────────────────────────────


class TestLastErrorObservability:
    """Workflow error handling: last_error stored in EpochState for query observability.

    The workflow narrows 'except Exception' to 'except TransitionError' and stores
    the error message in state.last_error. Callers can query current_state().last_error
    to inspect the last failure without needing to catch exceptions.
    """

    def test_invalid_signal_stores_last_error(self) -> None:
        """After an invalid advance (TransitionError), last_error is not None.

        Simulates the workflow's catch block: sm.advance() raises TransitionError,
        which is caught and stored in state.last_error.
        """
        from aura_protocol.state_machine import TransitionError

        sm = _make_sm("last-error-epoch-1")
        # Attempt an invalid advance (P1 cannot go to P9).
        try:
            sm.advance(PhaseId.P9_SLICE, triggered_by="architect", condition_met="invalid")
        except TransitionError as e:
            sm.state.last_error = str(e)

        # Query current_state().last_error — should reflect the failure.
        state = sm.state
        assert state.last_error is not None
        assert len(state.last_error) > 0

    def test_valid_signal_after_invalid_clears_last_error(self) -> None:
        """After a valid advance following a failed one, last_error is cleared.

        EpochStateMachine.advance() clears last_error on success. This verifies
        the full error → recovery → clear cycle.
        """
        from aura_protocol.state_machine import TransitionError

        sm = _make_sm("last-error-epoch-2")
        # First: invalid advance sets last_error.
        try:
            sm.advance(PhaseId.P9_SLICE, triggered_by="architect", condition_met="invalid")
        except TransitionError as e:
            sm.state.last_error = str(e)

        assert sm.state.last_error is not None

        # Then: valid advance clears last_error.
        sm.advance(PhaseId.P2_ELICIT, triggered_by="architect", condition_met="confirmed")
        assert sm.state.last_error is None

    def test_last_error_starts_none_before_any_signals(self) -> None:
        """Before any signals are processed, last_error is None."""
        sm = _make_sm("last-error-epoch-3")
        state = sm.state
        assert state.last_error is None


# ─── Failed Transition Audit Trail (No Sandbox) ───────────────────────────────


class TestFailedTransitionAuditTrailUnit:
    """Unit tests for the failed transition audit trail pattern (no Temporal sandbox).

    The workflow records failed transition attempts in transition_history with
    condition_met="FAILED: {error}" convention. These tests verify that pattern
    directly on EpochStateMachine without requiring the Temporal test server.

    The sandbox tests (TestWorkflowEnvironmentSandbox) cover the same behavior
    end-to-end; these unit tests ensure the pattern is testable in isolation.
    """

    def test_failed_attempt_appended_to_transition_history(self) -> None:
        """A failed transition attempt is recorded in transition_history with FAILED: prefix.

        Simulates the workflow's catch block:
            except TransitionError as e:
                failed_record = TransitionRecord(...)
                self._sm.state.transition_history.append(failed_record)
        """
        from datetime import datetime, timezone

        sm = _make_sm("audit-trail-epoch-1")
        assert sm.state.current_phase == PhaseId.P1_REQUEST

        # Attempt an invalid transition (P1 cannot go to P9).
        try:
            sm.advance(PhaseId.P9_SLICE, triggered_by="architect", condition_met="invalid")
        except TransitionError as e:
            # Simulate the workflow's catch block.
            failed_record = TransitionRecord(
                from_phase=sm.state.current_phase,
                to_phase=PhaseId.P9_SLICE,
                timestamp=datetime.now(tz=timezone.utc),
                triggered_by="architect",
                condition_met=f"FAILED: {e}",
                success=False,
            )
            sm.state.transition_history.append(failed_record)
            sm.state.last_error = str(e)

        # The failed attempt must appear in transition_history.
        assert len(sm.state.transition_history) == 1
        failed = sm.state.transition_history[0]
        assert failed.from_phase == PhaseId.P1_REQUEST
        assert failed.to_phase == PhaseId.P9_SLICE
        assert failed.condition_met.startswith("FAILED:")
        assert failed.triggered_by == "architect"
        # Programmatic success check: use r.success, not the string prefix.
        assert failed.success is False

        # The workflow phase must remain at P1 (transition was rejected).
        assert sm.state.current_phase == PhaseId.P1_REQUEST

    def test_failed_attempt_does_not_count_as_successful_transition(self) -> None:
        """Failed records are included in total history but excluded from successful count.

        Verifies the semantics of transition_count vs successful_transition_count:
        a FAILED record increments transition_count but not successful_transition_count.
        """
        from datetime import datetime, timezone

        sm = _make_sm("audit-trail-epoch-2")

        # Attempt an invalid transition.
        try:
            sm.advance(PhaseId.P9_SLICE, triggered_by="architect", condition_met="invalid")
        except TransitionError as e:
            failed_record = TransitionRecord(
                from_phase=sm.state.current_phase,
                to_phase=PhaseId.P9_SLICE,
                timestamp=datetime.now(tz=timezone.utc),
                triggered_by="architect",
                condition_met=f"FAILED: {e}",
                success=False,
            )
            sm.state.transition_history.append(failed_record)

        # Then a successful transition.
        sm.advance(PhaseId.P2_ELICIT, triggered_by="architect", condition_met="confirmed")

        history = sm.state.transition_history
        total_count = len(history)
        # Programmatic success check: use r.success, not the string prefix.
        successful_count = sum(1 for r in history if r.success)

        # Total = 2 (1 failed + 1 successful); successful = 1.
        assert total_count == 2
        assert successful_count == 1
        # Verify the individual records carry the correct success flag.
        assert history[0].success is False   # the failed attempt
        assert history[1].success is True    # the successful advance

    def test_multiple_failed_attempts_all_recorded(self) -> None:
        """Multiple failed attempts are each appended to transition_history.

        Verifies the audit trail captures every failed attempt, not just the first.
        """
        from datetime import datetime, timezone

        sm = _make_sm("audit-trail-epoch-3")
        invalid_targets = [PhaseId.P9_SLICE, PhaseId.P12_LANDING, PhaseId.COMPLETE]

        for target in invalid_targets:
            try:
                sm.advance(target, triggered_by="architect", condition_met="invalid")
            except TransitionError as e:
                failed_record = TransitionRecord(
                    from_phase=sm.state.current_phase,
                    to_phase=target,
                    timestamp=datetime.now(tz=timezone.utc),
                    triggered_by="architect",
                    condition_met=f"FAILED: {e}",
                    success=False,
                )
                sm.state.transition_history.append(failed_record)

        # All 3 failed attempts are recorded.
        assert len(sm.state.transition_history) == 3
        for record in sm.state.transition_history:
            assert record.condition_met.startswith("FAILED:")
            assert record.success is False

        # Workflow still at P1 (all transitions were rejected).
        assert sm.state.current_phase == PhaseId.P1_REQUEST


# ─── Full Lifecycle Integration ────────────────────────────────────────────────


class TestFullLifecycleIntegration:
    """Full lifecycle test: P1 → COMPLETE via forward path."""

    def test_full_forward_path_completes(self) -> None:
        """The state machine can complete the full 12-phase lifecycle."""
        sm = _make_sm("full-lifecycle-epoch")
        _advance_to(sm, PhaseId.COMPLETE)
        assert sm.state.current_phase == PhaseId.COMPLETE
        assert len(sm.state.transition_history) == 12

    def test_transition_count_matches_history_length(self) -> None:
        """EpochResult.transition_count matches the actual transition_history length.

        transition_count is the raw total including failed attempts.
        successful_transition_count excludes records where success is False.
        """
        sm = _make_sm("transition-count-epoch")
        _advance_to(sm, PhaseId.P6_RATIFY)

        history = sm.state.transition_history
        transition_count = len(history)
        successful_count = sum(1 for r in history if r.success)
        # Verify this is what EpochResult would capture.
        result = EpochResult(
            epoch_id=sm.state.epoch_id,
            final_phase=sm.state.current_phase,
            transition_count=transition_count,
            successful_transition_count=successful_count,
            constraint_violations_total=0,
        )
        assert result.transition_count == len(sm.state.transition_history)
        # No failed attempts in a clean forward path — counts are equal.
        assert result.successful_transition_count == result.transition_count


# ─── WorkflowEnvironment Sandbox Tests ────────────────────────────────────────
# End-to-end tests using Temporal's time-skipping WorkflowEnvironment.
# These require the Temporal test server binary (lazily downloaded on first run).
#
# The availability check is LAZY — it does NOT run at module import time and
# does NOT run during `pytest --collect-only`. It is cached via functools.cache
# so it executes at most once per process, only when a sandbox test is selected.


@functools.cache
def _temporal_sandbox_works() -> bool:
    """Probe whether the full Temporal sandbox pipeline works end-to-end.

    Tests start_time_skipping() AND that a workflow using custom search
    attributes can run. Returns False if:
    - The test server binary can't be downloaded/started
    - Custom search attributes (AuraPhase, etc.) aren't registered
    - Any other environment issue prevents workflow execution

    Result is cached — only runs once per process. Does NOT execute at module
    import time; it is called lazily from the sandbox class's skip check so
    that `pytest --collect-only` and normal imports are not affected.
    """
    try:
        from temporalio.testing import WorkflowEnvironment
        from temporalio.worker import Worker

        async def _probe() -> bool:
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="probe-q",
                    workflows=[EpochWorkflow],
                    activities=[check_constraints, record_transition],
                ):
                    handle = await env.client.start_workflow(
                        EpochWorkflow.run,
                        EpochInput(epoch_id="probe", request_description="probe"),
                        id="probe-wf",
                        task_queue="probe-q",
                    )
                    # If we can query, the full pipeline works.
                    await handle.query(EpochWorkflow.current_state)
                    await handle.terminate("probe done")
                    return True

        return asyncio.run(_probe())
    except (
        ImportError,           # temporalio not installed
        OSError,               # test server binary not found / not executable
        RuntimeError,          # miscellaneous runtime failures
        asyncio.TimeoutError,  # probe timed out waiting for the server
    ):
        return False
    except Exception:  # noqa: BLE001
        # Broad safety net for Temporal-specific errors that are not subclasses
        # of the above (e.g. temporalio.service.RPCError when custom search
        # attributes such as AuraPhase are not registered in the test server
        # namespace). The probe must never raise — any failure means unavailable.
        return False


_SKIP_REASON = (
    "Temporal sandbox unavailable (test server binary missing, "
    "or custom search attributes not registered)"
)


class TestWorkflowEnvironmentSandbox:
    """End-to-end WorkflowEnvironment.start_time_skipping() integration tests.

    Tests that exercise the full Temporal signal → workflow → query cycle,
    verifying that EpochWorkflow correctly handles signals and exposes
    consistent state through queries.

    Skipped entirely when the Temporal test server binary is not available.
    The probe runs lazily (cached) — it does NOT execute at module import time
    or during `pytest --collect-only`; it runs only when a test in this class
    is actually selected for execution.
    """

    @pytest.fixture(autouse=True)
    def _require_temporal_sandbox(self) -> None:
        """Skip (or fail) this test if the Temporal sandbox is unavailable.

        Calls _temporal_sandbox_works() which is cached via functools.cache —
        the probe runs at most once per process and only when a sandbox test
        is actually selected (not at collection time).

        Behaviour is controlled by TEMPORAL_REQUIRED env var:
        - Default (unset / "0"): skip gracefully when Temporal is unavailable.
        - TEMPORAL_REQUIRED=1: fail hard instead of skip (for CI environments
          that are expected to have a working Temporal test server).
        """
        if not _temporal_sandbox_works():
            if os.environ.get("TEMPORAL_REQUIRED", "").strip() == "1":
                pytest.fail(
                    "Temporal sandbox required (TEMPORAL_REQUIRED=1) but probe failed"
                )
            pytest.skip(_SKIP_REASON)

    @pytest.mark.asyncio
    async def test_advance_phase_signal_delivery_e2e(self) -> None:
        """advance_phase signal drives P1→P2 transition end-to-end.

        AC7: WorkflowEnvironment sandbox test — advance_phase signal delivery.
        Sends a PhaseAdvanceSignal to the running EpochWorkflow and verifies
        that the current_state query returns the updated phase.
        """
        from temporalio.worker import Worker
        from temporalio.testing import WorkflowEnvironment

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-advance-q",
                workflows=[EpochWorkflow],
                activities=[check_constraints, record_transition],
            ):
                handle = await env.client.start_workflow(
                    EpochWorkflow.run,
                    EpochInput(epoch_id="e2e-advance-1", request_description="test"),
                    id="e2e-advance-1",
                    task_queue="test-advance-q",
                )

                # Verify initial state via query.
                initial_state = await handle.query(EpochWorkflow.current_state)
                assert initial_state.current_phase == PhaseId.P1_REQUEST

                # Send advance signal: P1 → P2.
                await handle.signal(
                    EpochWorkflow.advance_phase,
                    PhaseAdvanceSignal(
                        to_phase=PhaseId.P2_ELICIT,
                        triggered_by="test-agent",
                        condition_met="classification confirmed",
                    ),
                )

                # Query current state — must reflect the transition.
                state = await handle.query(EpochWorkflow.current_state)
                assert state.current_phase == PhaseId.P2_ELICIT
                assert PhaseId.P1_REQUEST in state.completed_phases
                assert len(state.transition_history) == 1
                assert state.transition_history[0].from_phase == PhaseId.P1_REQUEST
                assert state.transition_history[0].to_phase == PhaseId.P2_ELICIT

                # Terminate workflow to clean up.
                await handle.terminate("test complete")

    @pytest.mark.asyncio
    async def test_submit_vote_signal_delivery_e2e(self) -> None:
        """submit_vote signals are recorded end-to-end.

        AC7: WorkflowEnvironment sandbox test — submit_vote signal delivery.
        Advances workflow to P4 (review), submits vote signals, verifies they
        appear in the current_state query.
        """
        from temporalio.worker import Worker
        from temporalio.testing import WorkflowEnvironment

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-vote-q",
                workflows=[EpochWorkflow],
                activities=[check_constraints, record_transition],
            ):
                handle = await env.client.start_workflow(
                    EpochWorkflow.run,
                    EpochInput(epoch_id="e2e-vote-1", request_description="test"),
                    id="e2e-vote-1",
                    task_queue="test-vote-q",
                )

                # Advance to P4 (review phase) via signals.
                for to_phase, condition in [
                    (PhaseId.P2_ELICIT, "classification confirmed"),
                    (PhaseId.P3_PROPOSE, "URD created"),
                    (PhaseId.P4_REVIEW, "proposal created"),
                ]:
                    await handle.signal(
                        EpochWorkflow.advance_phase,
                        PhaseAdvanceSignal(
                            to_phase=to_phase,
                            triggered_by="test-agent",
                            condition_met=condition,
                        ),
                    )

                # Submit vote signals.
                for axis, vote in [(ReviewAxis.CORRECTNESS, VoteType.ACCEPT), (ReviewAxis.TEST_QUALITY, VoteType.REVISE)]:
                    await handle.signal(
                        EpochWorkflow.submit_vote,
                        ReviewVoteSignal(
                            axis=axis,
                            vote=vote,
                            reviewer_id=f"reviewer-{axis}",
                        ),
                    )

                # Verify votes appear in state after a small wait.
                await env.sleep(timedelta(seconds=1))
                state = await handle.query(EpochWorkflow.current_state)
                assert state.current_phase == PhaseId.P4_REVIEW
                assert state.review_votes.get(ReviewAxis.CORRECTNESS) == VoteType.ACCEPT
                assert state.review_votes.get(ReviewAxis.TEST_QUALITY) == VoteType.REVISE

                await handle.terminate("test complete")

    @pytest.mark.asyncio
    async def test_current_state_query_returns_correct_phase_after_signal(self) -> None:
        """current_state query returns updated phase after advance_phase signal.

        AC7: WorkflowEnvironment sandbox test — query returns correct phase.
        Verifies that the Temporal query handler reflects the state machine's
        current phase immediately after a signal-driven transition.
        """
        from temporalio.worker import Worker
        from temporalio.testing import WorkflowEnvironment

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-query-q",
                workflows=[EpochWorkflow],
                activities=[check_constraints, record_transition],
            ):
                handle = await env.client.start_workflow(
                    EpochWorkflow.run,
                    EpochInput(epoch_id="e2e-query-1", request_description="test"),
                    id="e2e-query-1",
                    task_queue="test-query-q",
                )

                # Advance through P2 → P3.
                await handle.signal(
                    EpochWorkflow.advance_phase,
                    PhaseAdvanceSignal(
                        to_phase=PhaseId.P2_ELICIT,
                        triggered_by="test",
                        condition_met="ok",
                    ),
                )
                await handle.signal(
                    EpochWorkflow.advance_phase,
                    PhaseAdvanceSignal(
                        to_phase=PhaseId.P3_PROPOSE,
                        triggered_by="test",
                        condition_met="URD created",
                    ),
                )

                state = await handle.query(EpochWorkflow.current_state)
                assert state.current_phase == PhaseId.P3_PROPOSE
                assert state.current_phase.value == "p3"
                # Transition history should have 2 successful transitions.
                successful = [
                    r for r in state.transition_history if r.success
                ]
                assert len(successful) == 2

                await handle.terminate("test complete")

    @pytest.mark.asyncio
    async def test_failed_transition_recorded_in_history_e2e(self) -> None:
        """Failed transitions are recorded in transition_history with FAILED: prefix.

        AC7 + AC6: WorkflowEnvironment sandbox test — failed transition audit trail.
        Sends an invalid advance signal (P1→P9, which is not a valid transition)
        and verifies that the failed attempt appears in transition_history with
        condition_met="FAILED: ..." and that the workflow remains at P1.
        """
        from temporalio.worker import Worker
        from temporalio.testing import WorkflowEnvironment

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="test-failed-q",
                workflows=[EpochWorkflow],
                activities=[check_constraints, record_transition],
            ):
                handle = await env.client.start_workflow(
                    EpochWorkflow.run,
                    EpochInput(epoch_id="e2e-failed-1", request_description="test"),
                    id="e2e-failed-1",
                    task_queue="test-failed-q",
                )

                # Send an invalid advance (P1 cannot go directly to P9).
                await handle.signal(
                    EpochWorkflow.advance_phase,
                    PhaseAdvanceSignal(
                        to_phase=PhaseId.P9_SLICE,
                        triggered_by="test-agent",
                        condition_met="invalid attempt",
                    ),
                )

                # Workflow should remain at P1 — the invalid advance was rejected.
                state = await handle.query(EpochWorkflow.current_state)
                assert state.current_phase == PhaseId.P1_REQUEST

                # The failed attempt must appear in transition_history.
                failed = [
                    r for r in state.transition_history if not r.success
                ]
                assert len(failed) == 1
                assert failed[0].from_phase == PhaseId.P1_REQUEST
                assert failed[0].to_phase == PhaseId.P9_SLICE
                assert "FAILED:" in failed[0].condition_met

                # last_error must also be set.
                assert state.last_error is not None

                await handle.terminate("test complete")


# ─── P9 Fail-Fast Pattern Tests ───────────────────────────────────────────────


class TestP9SliceFailFastPattern:
    """Tests for P9_SLICE fail-fast pattern: asyncio.wait(FIRST_EXCEPTION).

    Tests the asyncio pattern that the P9 supervisor uses to run parallel slices
    and cancel remaining slices on first failure. This tests the PATTERN — not an
    actual P9 Temporal workflow (child workflows are future work per PROPOSAL-11
    UAT-3).

    Verifies:
    1. FIRST_EXCEPTION returns as soon as any coroutine raises.
    2. Pending tasks receive CancelledError after first failure and cancellation.
    3. Happy path: all tasks complete successfully before FIRST_EXCEPTION returns.
    """

    @pytest.mark.asyncio
    async def test_first_exception_returns_on_first_failure(self) -> None:
        """asyncio.wait(FIRST_EXCEPTION) returns immediately when a task fails."""

        async def fast_fail() -> None:
            raise RuntimeError("Slice 0 failed with BLOCKER")

        async def long_slice() -> None:
            await asyncio.sleep(100)  # Would not finish in test time

        tasks = [
            asyncio.create_task(fast_fail(), name="fast-fail"),
            asyncio.create_task(long_slice(), name="long-slice"),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # Clean up pending tasks before assertions
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        # At least one done task raised an exception
        exceptions = [t.exception() for t in done if not t.cancelled()]
        assert any(e is not None for e in exceptions), (
            "Expected at least one task to have raised an exception"
        )

    @pytest.mark.asyncio
    async def test_pending_tasks_cancelled_after_first_failure(self) -> None:
        """Pending slice handles are cancelled when the first slice fails."""
        cancellation_received = asyncio.Event()

        async def failing_slice() -> None:
            raise ValueError("BLOCKER found in slice")

        async def pending_slice() -> None:
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                cancellation_received.set()
                raise

        tasks = [
            asyncio.create_task(failing_slice()),
            asyncio.create_task(pending_slice()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # Simulate supervisor cancel-on-failure
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        assert cancellation_received.is_set(), (
            "Pending slice should receive CancelledError when cancelled after first failure"
        )

    @pytest.mark.asyncio
    async def test_happy_path_all_slices_complete(self) -> None:
        """Happy path: all slices complete successfully with FIRST_EXCEPTION wait."""
        results: list[str] = []

        async def successful_slice(slice_id: int) -> str:
            await asyncio.sleep(0)  # Yield to event loop
            results.append(f"slice-{slice_id}")
            return f"done-{slice_id}"

        tasks = [asyncio.create_task(successful_slice(i)) for i in range(3)]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # When no exceptions occur, FIRST_EXCEPTION waits for ALL tasks
        assert len(pending) == 0, "All slices should have completed"
        assert len(done) == 3
        assert all(t.exception() is None for t in done)
        assert len(results) == 3
