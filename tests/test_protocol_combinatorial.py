"""Combinatorial tests for aura_protocol using YAML-driven fixtures.

Uses the ProtocolFixture class (tests/fixtures/fixture_loader.py) to load
protocol.yaml and generate comprehensive parametrized test cases without
manually enumerating hundreds of combinations.

The fixture defines 4 axes:
    1. phase_specs       — 12-phase PHASE_SPECS entries
    2. epoch_states      — pre-built epoch state snapshots
    3. vote_combinations — review vote combinations for consensus testing
    4. audit_events      — sample AuditEvent objects

Generators yield TestCase objects with a consistent `id` field used in
pytest.param(id=...) for readable test names.

Test classes:
    TestFixtureLoading              — fixture loads correctly, axes are populated
    TestFixtureLoaderGenerators     — generators yield well-formed TestCase objects
    TestPhaseSpecsFixture           — fixture phase_specs matches live PHASE_SPECS
    TestTransitionCombinatorial     — parametrized transition success/failure
    TestForwardPathCombinatorial    — every forward-path pair passes (with gates met)
    TestVoteCombinatorial           — vote combinations drive consensus/revise correctly
    TestAuditEventCombinatorial     — AuditEvent objects are well-formed
    TestFixtureStatistics           — coverage summary (printed, not gating)
"""

from __future__ import annotations

import pytest

from aura_protocol.state_machine import EpochStateMachine, TransitionError
from aura_protocol.types import (
    PHASE_SPECS,
    AuditEvent,
    Domain,
    PhaseId,
    ReviewAxis,
    RoleId,
    VoteType,
)

# Module-level import of singleton: evaluated once at collection time.
# This is the same pattern used in test_patterns_combinatorial.py in agentfilter.
from conftest import _PROTOCOL_FIXTURE
from fixtures.fixture_loader import (
    AuditEventTestCase,
    ProtocolFixture,
    TransitionTestCase,
    VoteTestCase,
)


# ─── Module-level case generation (for parametrize decorators) ─────────────────

_TRANSITION_CASES = list(_PROTOCOL_FIXTURE.generate_transition_test_cases())
_FORWARD_PATH_CASES = list(_PROTOCOL_FIXTURE.generate_forward_path_transition_cases())
_VOTE_CASES = list(_PROTOCOL_FIXTURE.generate_vote_test_cases())
_AUDIT_CASES = list(_PROTOCOL_FIXTURE.generate_audit_event_test_cases())


# ─── TestFixtureLoading ────────────────────────────────────────────────────────


class TestFixtureLoading:
    """Verify that protocol.yaml loads correctly with all required axes."""

    def test_fixture_loads_via_pytest_injection(self, protocol_fixture: ProtocolFixture) -> None:
        """The protocol_fixture pytest fixture provides a ProtocolFixture instance."""
        assert isinstance(protocol_fixture, ProtocolFixture)
        # Both must load the same data (same YAML file)
        assert list(protocol_fixture.phase_specs.keys()) == list(_PROTOCOL_FIXTURE.phase_specs.keys())

    def test_phase_specs_axis_populated(self, protocol_fixture: ProtocolFixture) -> None:
        """phase_specs axis has entries for all 12 phases."""
        assert len(protocol_fixture.phase_specs) == 12

    def test_epoch_states_axis_populated(self, protocol_fixture: ProtocolFixture) -> None:
        """epoch_states axis has at least 10 pre-built states."""
        assert len(protocol_fixture.epoch_states) >= 10

    def test_vote_combinations_axis_populated(self, protocol_fixture: ProtocolFixture) -> None:
        """vote_combinations axis has at least 5 combinations."""
        assert len(protocol_fixture.vote_combinations) >= 5

    def test_audit_events_axis_populated(self, protocol_fixture: ProtocolFixture) -> None:
        """audit_events axis has at least 4 sample events."""
        assert len(protocol_fixture.audit_events) >= 4

    def test_forward_phase_path_complete(self, protocol_fixture: ProtocolFixture) -> None:
        """forward_phase_path covers p1 through complete (13 entries)."""
        path = protocol_fixture.forward_phase_path
        assert len(path) == 13
        assert path[0] == "p1"
        assert path[-1] == "complete"

    def test_transition_matrix_has_all_categories(self, protocol_fixture: ProtocolFixture) -> None:
        """transition_matrix has valid_forward, valid_backward, and invalid_skips."""
        matrix = protocol_fixture.transition_matrix
        assert "valid_forward" in matrix
        assert "valid_backward" in matrix
        assert "invalid_skips" in matrix

    def test_phase_specs_have_required_fields(self, protocol_fixture: ProtocolFixture) -> None:
        """Each phase_spec entry has phase_id, domain, owner_roles, transitions."""
        for name, spec in protocol_fixture.phase_specs.items():
            assert "phase_id" in spec, f"{name}: missing phase_id"
            assert "domain" in spec, f"{name}: missing domain"
            assert "owner_roles" in spec, f"{name}: missing owner_roles"
            assert "transitions" in spec, f"{name}: missing transitions"

    def test_epoch_states_have_required_fields(self, protocol_fixture: ProtocolFixture) -> None:
        """Each epoch_state entry has current_phase, review_votes, blocker_count."""
        for name, state in protocol_fixture.epoch_states.items():
            assert "current_phase" in state, f"{name}: missing current_phase"
            assert "review_votes" in state, f"{name}: missing review_votes"
            assert "blocker_count" in state, f"{name}: missing blocker_count"

    def test_vote_combinations_have_required_fields(self, protocol_fixture: ProtocolFixture) -> None:
        """Each vote_combination has votes, has_consensus, and has_revise."""
        for name, combo in protocol_fixture.vote_combinations.items():
            assert "votes" in combo, f"{name}: missing votes"
            assert "has_consensus" in combo, f"{name}: missing has_consensus"
            assert "has_revise" in combo, f"{name}: missing has_revise"

    def test_audit_events_have_required_fields(self, protocol_fixture: ProtocolFixture) -> None:
        """Each audit_event has epoch_id, event_type, phase, role, payload."""
        for name, event in protocol_fixture.audit_events.items():
            assert "epoch_id" in event, f"{name}: missing epoch_id"
            assert "event_type" in event, f"{name}: missing event_type"
            assert "phase" in event, f"{name}: missing phase"
            assert "role" in event, f"{name}: missing role"
            assert "payload" in event, f"{name}: missing payload"


# ─── TestFixtureLoaderGenerators ──────────────────────────────────────────────


class TestFixtureLoaderGenerators:
    """Verify that generators yield well-formed TestCase objects."""

    def test_transition_cases_generated(self) -> None:
        """generate_transition_test_cases() yields at least 10 cases."""
        assert len(_TRANSITION_CASES) >= 10

    def test_transition_cases_have_ids(self) -> None:
        """All transition cases have non-empty, unique IDs."""
        ids = [tc.id for tc in _TRANSITION_CASES]
        assert len(ids) == len(set(ids)), "Transition case IDs must be unique"
        assert all(ids), "All IDs must be non-empty"

    def test_forward_path_cases_cover_all_pairs(self) -> None:
        """generate_forward_path_transition_cases() covers all 12 consecutive pairs."""
        assert len(_FORWARD_PATH_CASES) == 12

    def test_forward_path_all_success(self) -> None:
        """All forward-path cases expect success=True."""
        assert all(tc.expected_success for tc in _FORWARD_PATH_CASES)

    def test_vote_cases_generated(self) -> None:
        """generate_vote_test_cases() yields (combos × 2 review phases) cases."""
        expected = len(_PROTOCOL_FIXTURE.vote_combinations) * 2
        assert len(_VOTE_CASES) == expected

    def test_vote_cases_cover_both_review_phases(self) -> None:
        """Vote cases include both p4 and p10 review phases."""
        phases = {tc.phase for tc in _VOTE_CASES}
        assert "p4" in phases
        assert "p10" in phases

    def test_audit_cases_generated(self) -> None:
        """generate_audit_event_test_cases() yields one case per audit event."""
        expected = len(_PROTOCOL_FIXTURE.audit_events)
        assert len(_AUDIT_CASES) == expected

    def test_audit_cases_have_real_events(self) -> None:
        """Each audit case carries a proper AuditEvent object."""
        for case in _AUDIT_CASES:
            assert isinstance(case.event, AuditEvent)

    def test_build_vote_dict_all_accept(self) -> None:
        """build_vote_dict('all_accept') returns typed ReviewAxis → VoteType dict."""
        votes = _PROTOCOL_FIXTURE.build_vote_dict("all_accept")
        assert votes[ReviewAxis.CORRECTNESS] == VoteType.ACCEPT
        assert votes[ReviewAxis.TEST_QUALITY] == VoteType.ACCEPT
        assert votes[ReviewAxis.ELEGANCE] == VoteType.ACCEPT

    def test_build_vote_dict_all_revise(self) -> None:
        """build_vote_dict('all_revise') returns all-REVISE dict."""
        votes = _PROTOCOL_FIXTURE.build_vote_dict("all_revise")
        assert votes[ReviewAxis.CORRECTNESS] == VoteType.REVISE
        assert votes[ReviewAxis.TEST_QUALITY] == VoteType.REVISE
        assert votes[ReviewAxis.ELEGANCE] == VoteType.REVISE


# ─── TestPhaseSpecsFixture ─────────────────────────────────────────────────────


class TestPhaseSpecsFixture:
    """Verify that the fixture's phase_specs axis matches the live PHASE_SPECS dict."""

    def test_fixture_phases_match_live_phase_ids(self) -> None:
        """Every phase_id in the fixture is a valid PhaseId."""
        for name, spec in _PROTOCOL_FIXTURE.phase_specs.items():
            phase_id_str = spec["phase_id"]
            # Should not raise
            pid = PhaseId(phase_id_str)
            assert pid.value == phase_id_str, f"{name}: phase_id mismatch"

    def test_fixture_domains_match_live_domains(self) -> None:
        """Every domain in the fixture is a valid Domain."""
        for name, spec in _PROTOCOL_FIXTURE.phase_specs.items():
            domain_str = spec["domain"]
            domain = Domain(domain_str)
            assert domain.value == domain_str, f"{name}: domain mismatch"

    def test_fixture_phases_match_live_phase_count(self) -> None:
        """Fixture has the same number of phases as PHASE_SPECS."""
        assert len(_PROTOCOL_FIXTURE.phase_specs) == len(PHASE_SPECS)

    def test_fixture_transition_targets_are_valid_phases(self) -> None:
        """All transition targets in fixture are valid PhaseId values."""
        valid_phase_values = {p.value for p in PhaseId}
        for name, spec in _PROTOCOL_FIXTURE.phase_specs.items():
            for tx in spec.get("transitions", []):
                target = tx["target"]
                assert target in valid_phase_values, (
                    f"{name}: transition target '{target}' is not a valid PhaseId"
                )

    def test_fixture_owner_roles_are_valid_roles(self) -> None:
        """All owner_roles in fixture are valid RoleId values."""
        valid_role_values = {r.value for r in RoleId}
        for name, spec in _PROTOCOL_FIXTURE.phase_specs.items():
            for role in spec.get("owner_roles", []):
                assert role in valid_role_values, (
                    f"{name}: owner_role '{role}' is not a valid RoleId"
                )


# ─── TestTransitionCombinatorial ──────────────────────────────────────────────


class TestTransitionCombinatorial:
    """Parametrized tests for phase transition success/failure from transition_matrix."""

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _TRANSITION_CASES if tc.expected_success],
    )
    def test_valid_transitions_succeed(self, tc: TransitionTestCase) -> None:
        """Each valid-transition case should succeed (with gates satisfied)."""
        sm = EpochStateMachine("test-epoch")
        # Advance to the source phase using the helper.
        # _advance_to drives the machine through happy-path gates, but stops
        # AT the source phase without casting votes at that phase.
        from conftest import _advance_to

        source = PhaseId(tc.source_phase)
        target = PhaseId(tc.target_phase)

        _advance_to(sm, source)
        assert sm.state.current_phase == source, (
            f"Expected to be at {source}, got {sm.state.current_phase}"
        )

        # Consensus-gated transitions (P4→P5, P10→P11) need all 3 ACCEPT votes
        # before advance(). _advance_to only casts these when going THROUGH the
        # phase (i.e. P4→P5 inside _advance_to), but here we are AT P4 already
        # and need to cast them manually.
        if tc.requires_consensus:
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        # Backward revision transitions (P4→P3, P10→P9) require a REVISE vote.
        if tc.source_phase == "p4" and tc.target_phase == "p3":
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)

        if tc.source_phase == "p10" and tc.target_phase == "p9":
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.REVISE)

        # Advance to target — should not raise
        sm.advance(target, triggered_by="test", condition_met="test-condition")
        assert sm.state.current_phase == target

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _TRANSITION_CASES if not tc.expected_success],
    )
    def test_invalid_transitions_raise(self, tc: TransitionTestCase) -> None:
        """Each invalid-transition case should raise TransitionError."""
        sm = EpochStateMachine("test-epoch")
        from conftest import _advance_to

        source = PhaseId(tc.source_phase)
        target = PhaseId(tc.target_phase)

        _advance_to(sm, source)
        assert sm.state.current_phase == source

        with pytest.raises(TransitionError):
            sm.advance(target, triggered_by="test", condition_met="invalid-skip")


# ─── TestForwardPathCombinatorial ─────────────────────────────────────────────


class TestForwardPathCombinatorial:
    """Parametrized tests for every consecutive pair in the forward phase path."""

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _FORWARD_PATH_CASES],
    )
    def test_forward_path_transitions(self, tc: TransitionTestCase) -> None:
        """Each forward-path pair advances correctly when gates are met."""
        sm = EpochStateMachine("test-epoch")
        from conftest import _advance_to

        # COMPLETE is the sentinel — cannot advance further from it.
        if tc.source_phase == "complete":
            pytest.skip("COMPLETE is terminal; no further transitions")

        source = PhaseId(tc.source_phase)
        target = PhaseId(tc.target_phase)

        # Advance the machine to the source phase (gates handled by _advance_to)
        _advance_to(sm, source)
        assert sm.state.current_phase == source

        # _advance_to already satisfies consensus gates for P4→P5 and P10→P11.
        # The next advance also goes through _advance_to's gate logic for those pairs.
        # Here we call sm.advance directly for the final step.
        if tc.requires_consensus and source == PhaseId.P4_REVIEW:
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        if tc.requires_consensus and source == PhaseId.P10_CODE_REVIEW:
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        sm.advance(target, triggered_by="test", condition_met="forward-path")
        assert sm.state.current_phase == target


# ─── TestVoteCombinatorial ────────────────────────────────────────────────────


class TestVoteCombinatorial:
    """Parametrized tests for vote combinations at both review phases."""

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _VOTE_CASES if tc.has_consensus],
    )
    def test_consensus_vote_combos_allow_forward_advance(self, tc: VoteTestCase) -> None:
        """Vote combinations with has_consensus=True allow advancing past the review phase."""
        sm = EpochStateMachine("test-epoch")
        from conftest import _advance_to

        source = PhaseId(tc.phase)
        # Forward target for each review phase
        targets = {"p4": PhaseId.P5_UAT, "p10": PhaseId.P11_IMPL_UAT}
        target = targets[tc.phase]

        _advance_to(sm, source)

        # Record the votes from the fixture combination
        for axis_str, vote_str in tc.votes.items():
            sm.record_vote(ReviewAxis(axis_str), VoteType(vote_str))

        # Should succeed — has_consensus means all 3 ACCEPT
        sm.advance(target, triggered_by="test", condition_met="all-accept")
        assert sm.state.current_phase == target

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _VOTE_CASES if tc.has_revise],
    )
    def test_revise_vote_combos_make_backward_available(self, tc: VoteTestCase) -> None:
        """Vote combinations with has_revise=True make only the backward transition available."""
        sm = EpochStateMachine("test-epoch")
        from conftest import _advance_to

        source = PhaseId(tc.phase)
        # Backward targets for each review phase
        back_targets = {"p4": PhaseId.P3_PROPOSE, "p10": PhaseId.P9_SLICE}
        fwd_targets = {"p4": PhaseId.P5_UAT, "p10": PhaseId.P11_IMPL_UAT}

        _advance_to(sm, source)

        # Record the votes
        for axis_str, vote_str in tc.votes.items():
            sm.record_vote(ReviewAxis(axis_str), VoteType(vote_str))

        # Forward advance should fail (REVISE vote present)
        fwd_target = fwd_targets[tc.phase]
        with pytest.raises(TransitionError):
            sm.advance(fwd_target, triggered_by="test", condition_met="should-fail")

        # Backward advance should succeed
        back_target = back_targets[tc.phase]
        sm.advance(back_target, triggered_by="test", condition_met="revise-drives-back")
        assert sm.state.current_phase == back_target

    @pytest.mark.parametrize(
        "tc",
        [
            pytest.param(tc, id=tc.id)
            for tc in _VOTE_CASES
            if not tc.has_consensus and not tc.has_revise
        ],
    )
    def test_partial_vote_combos_block_forward(self, tc: VoteTestCase) -> None:
        """Vote combinations with partial/empty votes block forward advance."""
        sm = EpochStateMachine("test-epoch")
        from conftest import _advance_to

        source = PhaseId(tc.phase)
        fwd_targets = {"p4": PhaseId.P5_UAT, "p10": PhaseId.P11_IMPL_UAT}
        fwd_target = fwd_targets[tc.phase]

        _advance_to(sm, source)

        # Record the partial votes
        for axis_str, vote_str in tc.votes.items():
            sm.record_vote(ReviewAxis(axis_str), VoteType(vote_str))

        # Forward advance should fail (no consensus, no REVISE — just incomplete)
        with pytest.raises(TransitionError):
            sm.advance(fwd_target, triggered_by="test", condition_met="partial-votes")


# ─── TestAuditEventCombinatorial ──────────────────────────────────────────────


class TestAuditEventCombinatorial:
    """Parametrized tests for AuditEvent objects generated from the fixture."""

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _AUDIT_CASES],
    )
    def test_audit_event_well_formed(self, tc: AuditEventTestCase) -> None:
        """Each generated AuditEvent has the correct type and valid enum values."""
        event = tc.event
        assert isinstance(event, AuditEvent)
        assert isinstance(event.epoch_id, str)
        assert event.epoch_id, "epoch_id must be non-empty"
        assert isinstance(event.event_type, str)
        assert event.event_type, "event_type must be non-empty"
        # phase and role are enum instances
        assert isinstance(event.phase, PhaseId)
        assert isinstance(event.role, RoleId)
        assert isinstance(event.payload, dict)

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _AUDIT_CASES],
    )
    def test_audit_event_phases_valid(self, tc: AuditEventTestCase) -> None:
        """Each AuditEvent's phase is a valid PhaseId enum member."""
        # If PhaseId(str) raises, the test will fail with a clear ValueError
        pid = PhaseId(tc.event.phase)
        assert pid == tc.event.phase

    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in _AUDIT_CASES],
    )
    def test_audit_event_roles_valid(self, tc: AuditEventTestCase) -> None:
        """Each AuditEvent's role is a valid RoleId enum member."""
        rid = RoleId(tc.event.role)
        assert rid == tc.event.role


# ─── TestFixtureStatistics ────────────────────────────────────────────────────


class TestFixtureStatistics:
    """Coverage summary tests — verify fixture reaches minimum thresholds."""

    def test_total_case_count_meets_minimum(self) -> None:
        """Total generated cases must exceed a meaningful minimum."""
        total = (
            len(_TRANSITION_CASES)
            + len(_FORWARD_PATH_CASES)
            + len(_VOTE_CASES)
            + len(_AUDIT_CASES)
        )
        assert total >= 40, (
            f"Expected at least 40 total test cases, got {total}. "
            "Add more entries to protocol.yaml axes."
        )

    def test_transition_matrix_has_valid_and_invalid_cases(self) -> None:
        """Transition cases cover both expected-success and expected-failure."""
        successes = [tc for tc in _TRANSITION_CASES if tc.expected_success]
        failures = [tc for tc in _TRANSITION_CASES if not tc.expected_success]
        assert len(successes) >= 4, "Need at least 4 valid-transition cases"
        assert len(failures) >= 3, "Need at least 3 invalid-transition cases"

    def test_vote_cases_cover_all_combinations(self) -> None:
        """Vote cases cover all named combinations from the fixture."""
        combo_names = {tc.vote_combo_name for tc in _VOTE_CASES}
        expected = set(_PROTOCOL_FIXTURE.vote_combinations.keys())
        assert combo_names == expected, (
            f"Missing vote combo coverage: {expected - combo_names}"
        )

    def test_audit_cases_cover_all_event_types(self) -> None:
        """Audit cases cover multiple distinct event types."""
        event_types = {tc.event_type for tc in _AUDIT_CASES}
        assert len(event_types) >= 4, (
            f"Expected at least 4 distinct event types, got {len(event_types)}: {event_types}"
        )

    def test_coverage_summary(self, capsys) -> None:
        """Print fixture coverage summary (informational, not a gate)."""
        print("\nProtocol Fixture Coverage Summary:")
        print(f"  phase_specs entries:       {len(_PROTOCOL_FIXTURE.phase_specs)}")
        print(f"  epoch_states entries:      {len(_PROTOCOL_FIXTURE.epoch_states)}")
        print(f"  vote_combinations entries: {len(_PROTOCOL_FIXTURE.vote_combinations)}")
        print(f"  audit_events entries:      {len(_PROTOCOL_FIXTURE.audit_events)}")
        print(f"")
        print(f"  Transition test cases:     {len(_TRANSITION_CASES)}")
        print(f"  Forward path cases:        {len(_FORWARD_PATH_CASES)}")
        print(f"  Vote test cases:           {len(_VOTE_CASES)}")
        print(f"  Audit event cases:         {len(_AUDIT_CASES)}")
        total = len(_TRANSITION_CASES) + len(_FORWARD_PATH_CASES) + len(_VOTE_CASES) + len(_AUDIT_CASES)
        print(f"  Total generated cases:     {total}")
        # This test always passes — it just prints
        assert total > 0
