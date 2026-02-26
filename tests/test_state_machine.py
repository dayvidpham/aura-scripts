"""Tests for aura_protocol.state_machine — 12-phase epoch lifecycle state machine.

BDD Acceptance Criteria:
    AC1: Given epoch in P1, advance(p2) transitions and records; advance(p8) raises TransitionError.
    AC2: Given advance(timestamp=custom_ts), TransitionRecord.timestamp == custom_ts.
    AC3: Given epoch in P4 with 2/3 ACCEPT, advance(p5) raises TransitionError (needs consensus).
         Given epoch in P10 without consensus, advance(p11) raises TransitionError (matching P4→P5).
    AC4: Given epoch in P4 with REVISE, available_transitions returns only [p3].
    AC5: Given epoch entering P10, severity_groups auto-populated with 3 SeverityLevel keys.
    AC6: Given epoch in P10 with blocker_count > 0, advance(p11) raises TransitionError.

Additional coverage:
    - Transition history recording
    - Valid sequential progression p1→p2→...→p12→complete
    - Invalid skip transitions rejected
    - Vote recording and clearing on phase change
    - record_blocker increment/decrement
    - has_consensus logic
    - validate_advance dry-run
    - COMPLETE sentinel behaviour
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aura_protocol.state_machine import (
    EpochState,
    EpochStateMachine,
    TransitionError,
    TransitionRecord,
)
from aura_protocol.types import PhaseId, ReviewAxis, RoleId, SeverityLevel, VoteType

# Import shared helpers from conftest (module-level, not fixtures).
from conftest import _advance_to, _make_state


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_sm(epoch_id: str = "test-epoch") -> EpochStateMachine:
    """Return a fresh EpochStateMachine starting at P1."""
    return EpochStateMachine(epoch_id)


# ─── AC1: State Machine Transitions ───────────────────────────────────────────


class TestAC1Transitions:
    """AC1: Given epoch in P1, advance(p2) → transitions; advance(p8) → TransitionError."""

    def test_advance_p1_to_p2_transitions(self) -> None:
        sm = _make_sm()
        assert sm.state.current_phase == PhaseId.P1_REQUEST

        record = sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="classification confirmed, research and explore complete",
        )

        assert sm.state.current_phase == PhaseId.P2_ELICIT
        assert isinstance(record, TransitionRecord)
        assert record.from_phase == PhaseId.P1_REQUEST
        assert record.to_phase == PhaseId.P2_ELICIT

    def test_advance_p1_to_p8_raises_transition_error(self) -> None:
        sm = _make_sm()
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P8_IMPL_PLAN,
                triggered_by="architect",
                condition_met="skipping phases",
            )
        assert exc_info.value.violations
        assert "p8" in exc_info.value.violations[0] or "p8" in str(exc_info.value)

    def test_invalid_skip_p1_to_p6_raises_transition_error(self) -> None:
        sm = _make_sm()
        with pytest.raises(TransitionError):
            sm.advance(PhaseId.P6_RATIFY, triggered_by="test", condition_met="skip")

    def test_transition_recorded_in_history(self) -> None:
        sm = _make_sm()
        assert sm.state.transition_history == []

        sm.advance(PhaseId.P2_ELICIT, triggered_by="architect", condition_met="done")

        assert len(sm.state.transition_history) == 1
        assert sm.state.transition_history[0].from_phase == PhaseId.P1_REQUEST
        assert sm.state.transition_history[0].to_phase == PhaseId.P2_ELICIT

    def test_completed_phases_updated(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="test", condition_met="done")

        assert PhaseId.P1_REQUEST in sm.state.completed_phases

    def test_current_phase_updated(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="test", condition_met="done")
        assert sm.state.current_phase == PhaseId.P2_ELICIT

    def test_transition_record_has_timestamp(self) -> None:
        sm = _make_sm()
        record = sm.advance(
            PhaseId.P2_ELICIT, triggered_by="test", condition_met="done"
        )
        assert record.timestamp is not None

    def test_transition_record_preserves_triggered_by(self) -> None:
        sm = _make_sm()
        record = sm.advance(
            PhaseId.P2_ELICIT, triggered_by="my-role", condition_met="done"
        )
        assert record.triggered_by == "my-role"

    def test_transition_record_preserves_condition_met(self) -> None:
        sm = _make_sm()
        record = sm.advance(
            PhaseId.P2_ELICIT, triggered_by="test", condition_met="my-condition"
        )
        assert record.condition_met == "my-condition"


# ─── AC2: Consensus Gate ──────────────────────────────────────────────────────


class TestAC2ConsensusGate:
    """AC2: Given epoch in P4 with 2/3 ACCEPT, advance(p5) → TransitionError."""

    def _sm_at_p4(self) -> EpochStateMachine:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P4_REVIEW)
        return sm

    def test_advance_p4_to_p5_without_any_votes_raises(self) -> None:
        sm = self._sm_at_p4()
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P5_UAT,
                triggered_by="test",
                condition_met="premature",
            )
        assert exc_info.value.violations
        assert "consensus" in exc_info.value.violations[0].lower()

    def test_advance_p4_to_p5_with_2_of_3_accept_raises(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        # C axis not voted

        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P5_UAT,
                triggered_by="test",
                condition_met="2/3 ACCEPT",
            )
        assert exc_info.value.violations
        assert "consensus" in exc_info.value.violations[0].lower()

    def test_advance_p4_to_p5_with_all_3_accept_succeeds(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        record = sm.advance(
            PhaseId.P5_UAT, triggered_by="reviewer", condition_met="all 3 vote ACCEPT"
        )
        assert sm.state.current_phase == PhaseId.P5_UAT
        assert record.from_phase == PhaseId.P4_REVIEW
        assert record.to_phase == PhaseId.P5_UAT

    def test_advance_p4_to_p5_with_1_of_3_accept_raises(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        # B and C not voted

        with pytest.raises(TransitionError):
            sm.advance(PhaseId.P5_UAT, triggered_by="test", condition_met="1/3 ACCEPT")

    def test_advance_p4_to_p5_with_revise_vote_raises(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.REVISE)

        with pytest.raises(TransitionError):
            sm.advance(PhaseId.P5_UAT, triggered_by="test", condition_met="has revise")

    def test_validate_advance_returns_violations_for_missing_consensus(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)

        violations = sm.validate_advance(PhaseId.P5_UAT)
        assert len(violations) == 1
        assert "consensus" in violations[0].lower()

    def test_validate_advance_returns_empty_when_consensus_met(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        violations = sm.validate_advance(PhaseId.P5_UAT)
        assert violations == []


# ─── AC3: Revision Loop ───────────────────────────────────────────────────────


class TestAC3RevisionLoop:
    """AC3: Given epoch in P4 with REVISE, available_transitions → only p3."""

    def _sm_at_p4(self) -> EpochStateMachine:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P4_REVIEW)
        return sm

    def test_at_p4_with_revise_only_p3_available(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)

        targets = {t.to_phase for t in sm.available_transitions}
        assert targets == {PhaseId.P3_PROPOSE}

    def test_at_p4_with_revise_on_any_axis_only_p3_available(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.REVISE)

        targets = {t.to_phase for t in sm.available_transitions}
        assert targets == {PhaseId.P3_PROPOSE}

    def test_at_p4_without_votes_no_forward_transition(self) -> None:
        """Without consensus and without REVISE, p5 is NOT available (no votes = not qualified)."""
        sm = self._sm_at_p4()
        # No votes recorded

        targets = {t.to_phase for t in sm.available_transitions}
        # p5 requires consensus (not reached), so only p3 (the non-gated transition) is available.
        assert PhaseId.P5_UAT not in targets

    def test_at_p4_with_all_accept_p5_available(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        targets = {t.to_phase for t in sm.available_transitions}
        # With consensus, p5 is available (and p3 is also a valid transition per spec).
        assert PhaseId.P5_UAT in targets

    def test_at_p10_with_revise_only_p9_available(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)

        targets = {t.to_phase for t in sm.available_transitions}
        assert targets == {PhaseId.P9_SLICE}

    def test_advance_to_p3_from_p4_allowed_with_revise(self) -> None:
        sm = self._sm_at_p4()
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.REVISE)

        # Should not raise
        record = sm.advance(
            PhaseId.P3_PROPOSE, triggered_by="reviewer", condition_met="any reviewer votes REVISE"
        )
        assert record.to_phase == PhaseId.P3_PROPOSE
        assert sm.state.current_phase == PhaseId.P3_PROPOSE


# ─── AC4: BLOCKER Gate ────────────────────────────────────────────────────────


class TestAC4BlockerGate:
    """AC4: Given epoch in P10 with blockers > 0, advance(p11) → TransitionError."""

    def _sm_at_p10(self) -> EpochStateMachine:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        return sm

    def test_advance_p10_to_p11_with_blocker_raises(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker()  # 1 unresolved blocker
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P11_IMPL_UAT,
                triggered_by="test",
                condition_met="has blockers",
            )
        assert exc_info.value.violations
        assert "blocker" in exc_info.value.violations[0].lower()

    def test_advance_p10_to_p11_with_resolved_blockers_succeeds(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker()   # +1 → count = 1
        sm.record_blocker(resolved=True)  # -1 → count = 0
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        record = sm.advance(
            PhaseId.P11_IMPL_UAT,
            triggered_by="supervisor",
            condition_met="all BLOCKERs resolved",
        )
        assert record.to_phase == PhaseId.P11_IMPL_UAT

    def test_advance_p10_to_p11_without_blockers_and_with_consensus_succeeds(self) -> None:
        sm = self._sm_at_p10()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        record = sm.advance(
            PhaseId.P11_IMPL_UAT,
            triggered_by="supervisor",
            condition_met="all BLOCKERs resolved, all 3 ACCEPT",
        )
        assert record.to_phase == PhaseId.P11_IMPL_UAT

    def test_blocker_count_increments(self) -> None:
        sm = self._sm_at_p10()
        assert sm.state.blocker_count == 0
        sm.record_blocker()
        assert sm.state.blocker_count == 1
        sm.record_blocker()
        assert sm.state.blocker_count == 2

    def test_blocker_count_decrements_on_resolved(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker()
        sm.record_blocker()
        sm.record_blocker(resolved=True)
        assert sm.state.blocker_count == 1

    def test_blocker_count_clamped_at_zero(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker(resolved=True)  # already at 0
        assert sm.state.blocker_count == 0

    def test_p11_not_in_available_when_blockers_present(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker()

        targets = {t.to_phase for t in sm.available_transitions}
        assert PhaseId.P11_IMPL_UAT not in targets

    def test_validate_advance_returns_blocker_violation(self) -> None:
        sm = self._sm_at_p10()
        sm.record_blocker()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        violations = sm.validate_advance(PhaseId.P11_IMPL_UAT)
        assert len(violations) == 1
        assert "blocker" in violations[0].lower()


# ─── Transition History Recording ─────────────────────────────────────────────


class TestTransitionHistory:
    """History must record every transition in order."""

    def test_empty_history_on_init(self) -> None:
        sm = _make_sm()
        assert sm.state.transition_history == []

    def test_history_grows_with_each_advance(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="a", condition_met="c")
        sm.advance(PhaseId.P3_PROPOSE, triggered_by="a", condition_met="c")
        assert len(sm.state.transition_history) == 2

    def test_history_records_correct_from_and_to(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="a", condition_met="c")
        rec = sm.state.transition_history[0]
        assert rec.from_phase == PhaseId.P1_REQUEST
        assert rec.to_phase == PhaseId.P2_ELICIT

    def test_history_is_in_order(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="a", condition_met="c")
        sm.advance(PhaseId.P3_PROPOSE, triggered_by="a", condition_met="c")
        assert sm.state.transition_history[0].to_phase == PhaseId.P2_ELICIT
        assert sm.state.transition_history[1].to_phase == PhaseId.P3_PROPOSE

    def test_failed_advance_does_not_add_to_history(self) -> None:
        sm = _make_sm()
        with pytest.raises(TransitionError):
            sm.advance(PhaseId.P8_IMPL_PLAN, triggered_by="a", condition_met="c")
        assert sm.state.transition_history == []


# ─── Full Sequential Progression ──────────────────────────────────────────────


class TestSequentialProgression:
    """Valid p1→p2→...→p12→complete progresses through all phases."""

    def test_full_forward_progression_reaches_complete(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        assert sm.state.current_phase == PhaseId.COMPLETE

    def test_full_progression_records_12_transitions(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        # p1→p2, p2→p3, ..., p12→complete = 12 transitions
        assert len(sm.state.transition_history) == 12

    def test_full_progression_completes_all_12_phases(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        expected = {p for p in PhaseId if p != PhaseId.COMPLETE}
        assert sm.state.completed_phases == expected

    def test_no_transition_from_complete(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(PhaseId.P1_REQUEST, triggered_by="test", condition_met="restart")
        assert exc_info.value.violations
        assert "COMPLETE" in exc_info.value.violations[0]

    def test_available_transitions_empty_at_complete(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        assert sm.available_transitions == []


# ─── Vote Recording and Clearing ──────────────────────────────────────────────


class TestVoteRecording:
    """Votes are phase-scoped and clear on transition."""

    def test_record_vote_stores_vote(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        assert sm.state.review_votes[ReviewAxis.CORRECTNESS] == VoteType.ACCEPT

    def test_record_vote_overwrites_previous(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        assert sm.state.review_votes[ReviewAxis.CORRECTNESS] == VoteType.ACCEPT

    def test_votes_cleared_after_transition(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.advance(PhaseId.P2_ELICIT, triggered_by="test", condition_met="done")
        assert sm.state.review_votes == {}

    def test_invalid_axis_raises_value_error(self) -> None:
        sm = _make_sm()
        with pytest.raises(ValueError):
            sm.record_vote("X", VoteType.ACCEPT)

    def test_record_all_3_axes(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.REVISE)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)
        assert len(sm.state.review_votes) == 3

    def test_has_consensus_false_with_no_votes(self) -> None:
        sm = _make_sm()
        assert sm.has_consensus() is False

    def test_has_consensus_false_with_partial_votes(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        assert sm.has_consensus() is False

    def test_has_consensus_false_with_revise(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.REVISE)
        assert sm.has_consensus() is False

    def test_has_consensus_true_with_all_accept(self) -> None:
        sm = _make_sm()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)
        assert sm.has_consensus() is True


# ─── State Property ───────────────────────────────────────────────────────────


class TestStateProperty:
    """state property returns the EpochState instance."""

    def test_state_returns_epoch_state(self) -> None:
        sm = _make_sm("epoch-abc")
        state = sm.state
        assert isinstance(state, EpochState)
        assert state.epoch_id == "epoch-abc"
        assert state.current_phase == PhaseId.P1_REQUEST

    def test_epoch_id_preserved(self) -> None:
        sm = EpochStateMachine("my-epoch-id")
        assert sm.state.epoch_id == "my-epoch-id"


# ─── validate_advance Dry-Run ─────────────────────────────────────────────────


class TestValidateAdvance:
    """validate_advance is a non-mutating dry run."""

    def test_valid_transition_returns_empty(self) -> None:
        sm = _make_sm()
        violations = sm.validate_advance(PhaseId.P2_ELICIT)
        assert violations == []

    def test_invalid_transition_returns_violations(self) -> None:
        sm = _make_sm()
        violations = sm.validate_advance(PhaseId.P8_IMPL_PLAN)
        assert len(violations) == 1

    def test_does_not_mutate_state(self) -> None:
        sm = _make_sm()
        sm.validate_advance(PhaseId.P2_ELICIT)
        assert sm.state.current_phase == PhaseId.P1_REQUEST
        assert sm.state.transition_history == []

    def test_from_complete_returns_violation(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.COMPLETE)
        violations = sm.validate_advance(PhaseId.P1_REQUEST)
        assert violations
        assert "COMPLETE" in violations[0]


# ─── last_error Field ─────────────────────────────────────────────────────────


class TestLastError:
    """EpochState.last_error tracks errors and clears on successful advance."""

    def test_last_error_starts_as_none(self) -> None:
        sm = _make_sm()
        assert sm.state.last_error is None

    def test_last_error_is_none_after_successful_advance(self) -> None:
        sm = _make_sm()
        sm.advance(PhaseId.P2_ELICIT, triggered_by="test", condition_met="ok")
        assert sm.state.last_error is None


# ─── Dependency Injection ─────────────────────────────────────────────────────


class TestDependencyInjection:
    """Custom specs can be injected for testing minimal state machines."""

    def test_custom_specs_used(self) -> None:
        from aura_protocol.types import Domain, PhaseSpec, Transition

        # Minimal 2-phase spec: p1 → p2 → complete
        custom_specs = {
            PhaseId.P1_REQUEST: PhaseSpec(
                id=PhaseId.P1_REQUEST,
                number=1,
                domain=Domain.USER,
                name="Test Request",
                owner_roles=frozenset({RoleId.EPOCH}),
                transitions=(
                    Transition(
                        to_phase=PhaseId.P2_ELICIT,
                        condition="test condition",
                    ),
                ),
            ),
            PhaseId.P2_ELICIT: PhaseSpec(
                id=PhaseId.P2_ELICIT,
                number=2,
                domain=Domain.USER,
                name="Test Elicit",
                owner_roles=frozenset({RoleId.EPOCH}),
                transitions=(
                    Transition(
                        to_phase=PhaseId.COMPLETE,
                        condition="done",
                    ),
                ),
            ),
        }

        sm = EpochStateMachine("di-test", specs=custom_specs)
        sm.advance(PhaseId.P2_ELICIT, triggered_by="test", condition_met="test condition")
        sm.advance(PhaseId.COMPLETE, triggered_by="test", condition_met="done")
        assert sm.state.current_phase == PhaseId.COMPLETE

    def test_default_specs_are_phase_specs(self) -> None:
        from aura_protocol.types import PHASE_SPECS
        sm = _make_sm()
        # The machine starts at p1 and p2 must be in PHASE_SPECS
        assert PhaseId.P1_REQUEST in PHASE_SPECS
        violations = sm.validate_advance(PhaseId.P2_ELICIT)
        assert violations == []


# ─── AC2 Extension: Custom Timestamp ──────────────────────────────────────────


class TestAdvanceTimestamp:
    """AC2 (extension): advance(timestamp=custom_ts) records exactly that timestamp."""

    def test_custom_timestamp_used_in_record(self) -> None:
        sm = _make_sm()
        custom_ts = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="test",
            condition_met="done",
            timestamp=custom_ts,
        )
        assert record.timestamp == custom_ts

    def test_no_timestamp_defaults_to_now(self) -> None:
        """Without explicit timestamp, advance() uses datetime.now(UTC)."""
        sm = _make_sm()
        before = datetime.now(tz=timezone.utc)
        record = sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="test",
            condition_met="done",
        )
        after = datetime.now(tz=timezone.utc)
        assert before <= record.timestamp <= after

    def test_timestamp_none_defaults_to_now(self) -> None:
        """Passing timestamp=None explicitly also falls back to datetime.now(UTC)."""
        sm = _make_sm()
        before = datetime.now(tz=timezone.utc)
        record = sm.advance(
            PhaseId.P2_ELICIT,
            triggered_by="test",
            condition_met="done",
            timestamp=None,
        )
        after = datetime.now(tz=timezone.utc)
        assert before <= record.timestamp <= after

    def test_custom_timestamp_two_sequential_advances(self) -> None:
        """Each advance can carry an independent deterministic timestamp."""
        sm = _make_sm()
        ts1 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

        sm.advance(PhaseId.P2_ELICIT, triggered_by="a", condition_met="ok", timestamp=ts1)
        sm.advance(PhaseId.P3_PROPOSE, triggered_by="a", condition_met="ok", timestamp=ts2)

        assert sm.state.transition_history[0].timestamp == ts1
        assert sm.state.transition_history[1].timestamp == ts2


# ─── AC3 Extension: P10→P11 Consensus Gate ────────────────────────────────────


class TestP10ConsensusGate:
    """AC3 (extension): P10→P11 without consensus raises TransitionError (same as P4→P5)."""

    def _sm_at_p10(self) -> EpochStateMachine:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        return sm

    def test_advance_p10_to_p11_without_votes_raises(self) -> None:
        sm = self._sm_at_p10()
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P11_IMPL_UAT,
                triggered_by="test",
                condition_met="premature",
            )
        assert exc_info.value.violations
        assert "consensus" in exc_info.value.violations[0].lower()

    def test_advance_p10_to_p11_with_2_of_3_accept_raises(self) -> None:
        sm = self._sm_at_p10()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        # C axis not voted
        with pytest.raises(TransitionError) as exc_info:
            sm.advance(
                PhaseId.P11_IMPL_UAT,
                triggered_by="test",
                condition_met="2/3 ACCEPT",
            )
        assert exc_info.value.violations
        assert "consensus" in exc_info.value.violations[0].lower()

    def test_advance_p10_to_p11_with_all_3_accept_and_no_blockers_succeeds(self) -> None:
        sm = self._sm_at_p10()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)
        record = sm.advance(
            PhaseId.P11_IMPL_UAT,
            triggered_by="supervisor",
            condition_met="all 3 ACCEPT, no blockers",
        )
        assert record.to_phase == PhaseId.P11_IMPL_UAT

    def test_validate_advance_returns_consensus_violation_at_p10(self) -> None:
        sm = self._sm_at_p10()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)

        violations = sm.validate_advance(PhaseId.P11_IMPL_UAT)
        assert any("consensus" in v.lower() for v in violations)

    def test_validate_advance_no_violation_when_consensus_met_at_p10(self) -> None:
        sm = self._sm_at_p10()
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
        sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        violations = sm.validate_advance(PhaseId.P11_IMPL_UAT)
        assert violations == []


# ─── AC5: severity_groups Auto-Population ─────────────────────────────────────


class TestSeverityGroupsAutoPopulation:
    """AC5: When advance() transitions TO P10, severity_groups is populated with 3 SeverityLevel keys."""

    def test_severity_groups_empty_before_p10(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P9_SLICE)
        assert sm.state.severity_groups == {}

    def test_severity_groups_populated_on_entry_to_p10(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        groups = sm.state.severity_groups
        assert len(groups) == 3
        assert SeverityLevel.BLOCKER in groups
        assert SeverityLevel.IMPORTANT in groups
        assert SeverityLevel.MINOR in groups

    def test_severity_groups_values_are_empty_sets_on_entry(self) -> None:
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        for level in SeverityLevel:
            assert isinstance(sm.state.severity_groups[level], set)
            assert len(sm.state.severity_groups[level]) == 0

    def test_severity_groups_not_populated_on_p4_entry(self) -> None:
        """P4 (plan review) must NOT trigger severity group creation (C-severity-not-plan)."""
        sm = _make_sm()
        _advance_to(sm, PhaseId.P4_REVIEW)
        assert sm.state.severity_groups == {}

    def test_severity_groups_preserved_if_already_populated(self) -> None:
        """If severity_groups is already non-empty when re-entering P10, it is NOT overwritten."""
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        # Manually add an entry to simulate a finding already recorded.
        sm.state.severity_groups[SeverityLevel.BLOCKER].add("finding-abc")

        # Simulate revision loop: p10 → p9 → p10.
        sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)
        sm.advance(PhaseId.P9_SLICE, triggered_by="test", condition_met="revise")
        sm.advance(PhaseId.P10_CODE_REVIEW, triggered_by="test", condition_met="re-review")

        # Pre-existing data must not be wiped.
        assert "finding-abc" in sm.state.severity_groups[SeverityLevel.BLOCKER]

    def test_severity_groups_has_exactly_3_severity_level_keys_at_p10(self) -> None:
        """severity_groups at P10 contains EXACTLY the 3 SeverityLevel keys — no more, no fewer.

        Frozen-keys invariant: the auto-population on P10 entry pre-seeds all 3
        SeverityLevel enum values. Since SeverityLevel has exactly 3 members
        (BLOCKER, IMPORTANT, MINOR), no other key can exist. This test asserts
        both the lower bound (all 3 present) and the upper bound (no extras).
        """
        sm = _make_sm()
        _advance_to(sm, PhaseId.P10_CODE_REVIEW)
        groups = sm.state.severity_groups

        expected_keys = set(SeverityLevel)
        actual_keys = set(groups.keys())

        # Exactly the 3 SeverityLevel values — no missing keys, no extra keys.
        assert actual_keys == expected_keys, (
            f"severity_groups keys {actual_keys!r} != expected {expected_keys!r}; "
            "frozen-keys invariant violated"
        )


# ─── EpochState Type Safety ───────────────────────────────────────────────────


class TestEpochStateTypeSafety:
    """AC1 (type safety): EpochState.current_role is RoleId, not plain str."""

    def test_current_role_default_is_role_id_epoch(self) -> None:
        sm = _make_sm()
        assert sm.state.current_role is RoleId.EPOCH

    def test_current_role_is_role_id_instance(self) -> None:
        sm = _make_sm()
        assert isinstance(sm.state.current_role, RoleId)

    def test_current_role_value_matches_epoch_string(self) -> None:
        sm = _make_sm()
        # RoleId is a str enum, so equality with "epoch" still holds.
        assert sm.state.current_role == "epoch"

    def test_make_state_accepts_role_id_current_role(self) -> None:
        state = _make_state(phase=PhaseId.P1_REQUEST, current_role=RoleId.SUPERVISOR)
        assert state.current_role is RoleId.SUPERVISOR
