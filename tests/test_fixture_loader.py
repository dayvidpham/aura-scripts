"""Tests for tests/fixtures/fixture_loader.py.

Validates the ProtocolFixture loader itself: file loading, property access,
generator correctness, and build_vote_dict behavior.

These are unit tests of the fixture infrastructure — they do NOT exercise the
protocol state machine. They verify that the fixture contract is stable so that
combinatorial tests built on top of it can be trusted.

Test classes:
    TestProtocolFixtureInit         — fixture loads default and custom paths
    TestProtocolFixtureProperties   — properties return correct types/contents
    TestTransitionTestCaseGenerator — generate_transition_test_cases() contract
    TestForwardPathGenerator        — generate_forward_path_transition_cases() contract
    TestVoteTestCaseGenerator       — generate_vote_test_cases() contract
    TestAuditEventTestCaseGenerator — generate_audit_event_test_cases() contract
    TestBuildVoteDict               — build_vote_dict() typed output
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aura_protocol.types import PhaseId, ReviewAxis, RoleId, VoteType
from fixtures.fixture_loader import (
    AuditEventTestCase,
    ProtocolFixture,
    TransitionTestCase,
    VoteTestCase,
)

# Path to protocol.yaml (resolved relative to this file's location)
_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "protocol.yaml"


# ─── TestProtocolFixtureInit ──────────────────────────────────────────────────


class TestProtocolFixtureInit:
    """Verify ProtocolFixture initialises correctly from default and custom paths."""

    def test_default_path_loads_successfully(self) -> None:
        """ProtocolFixture() with no argument loads from default location."""
        fixture = ProtocolFixture()
        assert fixture.phase_specs is not None

    def test_custom_path_loads_successfully(self) -> None:
        """ProtocolFixture(path) with explicit path loads the same data."""
        fixture = ProtocolFixture(str(_FIXTURE_PATH))
        assert fixture.phase_specs is not None

    def test_custom_pathlib_path_loads_successfully(self) -> None:
        """ProtocolFixture accepts a pathlib.Path object."""
        fixture = ProtocolFixture(_FIXTURE_PATH)
        assert fixture.phase_specs is not None

    def test_missing_file_raises_error(self) -> None:
        """ProtocolFixture raises FileNotFoundError for a non-existent path."""
        with pytest.raises(FileNotFoundError):
            ProtocolFixture("/nonexistent/path/protocol.yaml")

    def test_default_and_explicit_paths_yield_same_data(self) -> None:
        """Default path and explicit path produce identical data."""
        f1 = ProtocolFixture()
        f2 = ProtocolFixture(_FIXTURE_PATH)
        assert list(f1.phase_specs.keys()) == list(f2.phase_specs.keys())
        assert list(f1.vote_combinations.keys()) == list(f2.vote_combinations.keys())


# ─── TestProtocolFixtureProperties ────────────────────────────────────────────


class TestProtocolFixtureProperties:
    """Verify that each property returns the correct type and has content."""

    @pytest.fixture(scope="class")
    def fixture(self) -> ProtocolFixture:
        return ProtocolFixture()

    def test_phase_specs_is_dict(self, fixture: ProtocolFixture) -> None:
        assert isinstance(fixture.phase_specs, dict)
        assert len(fixture.phase_specs) > 0

    def test_epoch_states_is_dict(self, fixture: ProtocolFixture) -> None:
        assert isinstance(fixture.epoch_states, dict)
        assert len(fixture.epoch_states) > 0

    def test_vote_combinations_is_dict(self, fixture: ProtocolFixture) -> None:
        assert isinstance(fixture.vote_combinations, dict)
        assert len(fixture.vote_combinations) > 0

    def test_audit_events_is_dict(self, fixture: ProtocolFixture) -> None:
        assert isinstance(fixture.audit_events, dict)
        assert len(fixture.audit_events) > 0

    def test_forward_phase_path_is_list(self, fixture: ProtocolFixture) -> None:
        path = fixture.forward_phase_path
        assert isinstance(path, list)
        assert len(path) > 0

    def test_transition_matrix_is_dict(self, fixture: ProtocolFixture) -> None:
        assert isinstance(fixture.transition_matrix, dict)

    def test_phase_specs_values_are_dicts(self, fixture: ProtocolFixture) -> None:
        for name, spec in fixture.phase_specs.items():
            assert isinstance(spec, dict), f"{name}: expected dict, got {type(spec)}"

    def test_epoch_states_values_are_dicts(self, fixture: ProtocolFixture) -> None:
        for name, state in fixture.epoch_states.items():
            assert isinstance(state, dict), f"{name}: expected dict, got {type(state)}"

    def test_vote_combinations_values_are_dicts(self, fixture: ProtocolFixture) -> None:
        for name, combo in fixture.vote_combinations.items():
            assert isinstance(combo, dict), f"{name}: expected dict, got {type(combo)}"

    def test_audit_events_values_are_dicts(self, fixture: ProtocolFixture) -> None:
        for name, event in fixture.audit_events.items():
            assert isinstance(event, dict), f"{name}: expected dict, got {type(event)}"


# ─── TestTransitionTestCaseGenerator ─────────────────────────────────────────


class TestTransitionTestCaseGenerator:
    """Verify generate_transition_test_cases() produces well-formed TransitionTestCase objects."""

    @pytest.fixture(scope="class")
    def cases(self) -> list[TransitionTestCase]:
        return list(ProtocolFixture().generate_transition_test_cases())

    def test_produces_cases(self, cases: list[TransitionTestCase]) -> None:
        assert len(cases) > 0

    def test_each_case_is_dataclass(self, cases: list[TransitionTestCase]) -> None:
        for tc in cases:
            assert isinstance(tc, TransitionTestCase)

    def test_each_case_has_non_empty_id(self, cases: list[TransitionTestCase]) -> None:
        for tc in cases:
            assert tc.id, f"TransitionTestCase must have non-empty id: {tc}"

    def test_ids_are_unique(self, cases: list[TransitionTestCase]) -> None:
        ids = [tc.id for tc in cases]
        assert len(ids) == len(set(ids)), "TransitionTestCase IDs must be unique"

    def test_source_phases_are_valid_phase_ids(self, cases: list[TransitionTestCase]) -> None:
        valid = {p.value for p in PhaseId}
        for tc in cases:
            assert tc.source_phase in valid, (
                f"Invalid source_phase '{tc.source_phase}' in {tc.id}"
            )

    def test_target_phases_are_valid_phase_ids(self, cases: list[TransitionTestCase]) -> None:
        valid = {p.value for p in PhaseId}
        for tc in cases:
            assert tc.target_phase in valid, (
                f"Invalid target_phase '{tc.target_phase}' in {tc.id}"
            )

    def test_expected_success_is_bool(self, cases: list[TransitionTestCase]) -> None:
        for tc in cases:
            assert isinstance(tc.expected_success, bool)

    def test_has_both_success_and_failure_cases(self, cases: list[TransitionTestCase]) -> None:
        successes = [tc for tc in cases if tc.expected_success]
        failures = [tc for tc in cases if not tc.expected_success]
        assert len(successes) > 0, "Need at least one expected-success case"
        assert len(failures) > 0, "Need at least one expected-failure case"

    def test_consensus_gated_cases_marked(self, cases: list[TransitionTestCase]) -> None:
        """P4→P5 and P10→P11 cases are marked requires_consensus=True."""
        p4_to_p5 = [tc for tc in cases if tc.source_phase == "p4" and tc.target_phase == "p5"]
        if p4_to_p5:
            assert p4_to_p5[0].requires_consensus is True

        p10_to_p11 = [tc for tc in cases if tc.source_phase == "p10" and tc.target_phase == "p11"]
        if p10_to_p11:
            assert p10_to_p11[0].requires_consensus is True

    def test_blocker_gated_case_marked(self, cases: list[TransitionTestCase]) -> None:
        """P10→P11 case is marked requires_blocker_clear=True."""
        p10_to_p11 = [tc for tc in cases if tc.source_phase == "p10" and tc.target_phase == "p11"]
        if p10_to_p11:
            assert p10_to_p11[0].requires_blocker_clear is True


# ─── TestForwardPathGenerator ────────────────────────────────────────────────


class TestForwardPathGenerator:
    """Verify generate_forward_path_transition_cases() contract."""

    @pytest.fixture(scope="class")
    def cases(self) -> list[TransitionTestCase]:
        return list(ProtocolFixture().generate_forward_path_transition_cases())

    def test_produces_cases(self, cases: list[TransitionTestCase]) -> None:
        assert len(cases) > 0

    def test_covers_all_consecutive_pairs(self, cases: list[TransitionTestCase]) -> None:
        """Each case covers one consecutive pair in the forward path."""
        fixture = ProtocolFixture()
        path = fixture.forward_phase_path
        expected_count = len(path) - 1
        assert len(cases) == expected_count

    def test_all_cases_expect_success(self, cases: list[TransitionTestCase]) -> None:
        for tc in cases:
            assert tc.expected_success is True, (
                f"Forward path case should be expected_success=True: {tc.id}"
            )

    def test_first_case_starts_at_p1(self, cases: list[TransitionTestCase]) -> None:
        assert cases[0].source_phase == "p1"

    def test_last_case_ends_at_complete(self, cases: list[TransitionTestCase]) -> None:
        assert cases[-1].target_phase == "complete"

    def test_ids_follow_forward_prefix(self, cases: list[TransitionTestCase]) -> None:
        for tc in cases:
            assert tc.id.startswith("forward:"), f"Expected 'forward:' prefix: {tc.id}"


# ─── TestVoteTestCaseGenerator ────────────────────────────────────────────────


class TestVoteTestCaseGenerator:
    """Verify generate_vote_test_cases() contract."""

    @pytest.fixture(scope="class")
    def cases(self) -> list[VoteTestCase]:
        return list(ProtocolFixture().generate_vote_test_cases())

    def test_produces_cases(self, cases: list[VoteTestCase]) -> None:
        assert len(cases) > 0

    def test_each_case_is_dataclass(self, cases: list[VoteTestCase]) -> None:
        for tc in cases:
            assert isinstance(tc, VoteTestCase)

    def test_ids_are_unique(self, cases: list[VoteTestCase]) -> None:
        ids = [tc.id for tc in cases]
        assert len(ids) == len(set(ids)), "VoteTestCase IDs must be unique"

    def test_covers_both_review_phases(self, cases: list[VoteTestCase]) -> None:
        phases = {tc.phase for tc in cases}
        assert "p4" in phases
        assert "p10" in phases

    def test_total_count_is_combos_times_two(self, cases: list[VoteTestCase]) -> None:
        fixture = ProtocolFixture()
        expected = len(fixture.vote_combinations) * 2  # p4 + p10
        assert len(cases) == expected

    def test_has_consensus_matches_votes(self, cases: list[VoteTestCase]) -> None:
        """has_consensus is True iff votes dict has all 3 axes as ACCEPT."""
        axes = {"correctness", "test_quality", "elegance"}
        for tc in cases:
            all_accept = (
                set(tc.votes.keys()) == axes
                and all(v == "ACCEPT" for v in tc.votes.values())
            )
            assert tc.has_consensus == all_accept, (
                f"{tc.id}: has_consensus mismatch. votes={tc.votes}, "
                f"expected has_consensus={all_accept}"
            )

    def test_has_revise_matches_votes(self, cases: list[VoteTestCase]) -> None:
        """has_revise is True iff any vote in the combo is REVISE."""
        for tc in cases:
            any_revise = any(v == "REVISE" for v in tc.votes.values())
            assert tc.has_revise == any_revise, (
                f"{tc.id}: has_revise mismatch. votes={tc.votes}, "
                f"expected has_revise={any_revise}"
            )

    def test_votes_are_valid_strings(self, cases: list[VoteTestCase]) -> None:
        valid_axes = {a.value for a in ReviewAxis}
        valid_votes = {v.value for v in VoteType}
        for tc in cases:
            for axis_str, vote_str in tc.votes.items():
                assert axis_str in valid_axes, (
                    f"{tc.id}: invalid axis '{axis_str}'"
                )
                assert vote_str in valid_votes, (
                    f"{tc.id}: invalid vote '{vote_str}'"
                )


# ─── TestAuditEventTestCaseGenerator ─────────────────────────────────────────


class TestAuditEventTestCaseGenerator:
    """Verify generate_audit_event_test_cases() contract."""

    @pytest.fixture(scope="class")
    def cases(self) -> list[AuditEventTestCase]:
        return list(ProtocolFixture().generate_audit_event_test_cases())

    def test_produces_cases(self, cases: list[AuditEventTestCase]) -> None:
        assert len(cases) > 0

    def test_each_case_is_dataclass(self, cases: list[AuditEventTestCase]) -> None:
        for tc in cases:
            assert isinstance(tc, AuditEventTestCase)

    def test_ids_are_unique(self, cases: list[AuditEventTestCase]) -> None:
        ids = [tc.id for tc in cases]
        assert len(ids) == len(set(ids)), "AuditEventTestCase IDs must be unique"

    def test_ids_follow_audit_prefix(self, cases: list[AuditEventTestCase]) -> None:
        for tc in cases:
            assert tc.id.startswith("audit:"), f"Expected 'audit:' prefix: {tc.id}"

    def test_events_have_valid_phase_ids(self, cases: list[AuditEventTestCase]) -> None:
        valid = {p.value for p in PhaseId}
        for tc in cases:
            assert tc.event.phase.value in valid, (
                f"{tc.id}: event phase '{tc.event.phase}' not a valid PhaseId"
            )

    def test_events_have_valid_role_ids(self, cases: list[AuditEventTestCase]) -> None:
        valid = {r.value for r in RoleId}
        for tc in cases:
            assert tc.event.role.value in valid, (
                f"{tc.id}: event role '{tc.event.role}' not a valid RoleId"
            )

    def test_events_have_non_empty_epoch_ids(self, cases: list[AuditEventTestCase]) -> None:
        for tc in cases:
            assert tc.event.epoch_id, f"{tc.id}: epoch_id must be non-empty"

    def test_events_have_payload_dicts(self, cases: list[AuditEventTestCase]) -> None:
        for tc in cases:
            assert isinstance(tc.event.payload, dict), (
                f"{tc.id}: payload must be a dict, got {type(tc.event.payload)}"
            )

    def test_covers_phase_advance_events(self, cases: list[AuditEventTestCase]) -> None:
        phase_advance_cases = [tc for tc in cases if tc.event_type == "phase_advance"]
        assert len(phase_advance_cases) >= 2, "Need at least 2 phase_advance events"

    def test_covers_vote_recorded_events(self, cases: list[AuditEventTestCase]) -> None:
        vote_cases = [tc for tc in cases if tc.event_type == "vote_recorded"]
        assert len(vote_cases) >= 1, "Need at least 1 vote_recorded event"


# ─── TestBuildVoteDict ────────────────────────────────────────────────────────


class TestBuildVoteDict:
    """Verify build_vote_dict() returns correctly typed ReviewAxis → VoteType dicts."""

    @pytest.fixture(scope="class")
    def fixture(self) -> ProtocolFixture:
        return ProtocolFixture()

    def test_all_accept_returns_typed_dict(self, fixture: ProtocolFixture) -> None:
        votes = fixture.build_vote_dict("all_accept")
        assert isinstance(votes, dict)
        assert votes[ReviewAxis.CORRECTNESS] == VoteType.ACCEPT
        assert votes[ReviewAxis.TEST_QUALITY] == VoteType.ACCEPT
        assert votes[ReviewAxis.ELEGANCE] == VoteType.ACCEPT

    def test_all_revise_returns_typed_dict(self, fixture: ProtocolFixture) -> None:
        votes = fixture.build_vote_dict("all_revise")
        assert votes[ReviewAxis.CORRECTNESS] == VoteType.REVISE
        assert votes[ReviewAxis.TEST_QUALITY] == VoteType.REVISE
        assert votes[ReviewAxis.ELEGANCE] == VoteType.REVISE

    def test_partial_one_axis_returns_partial_dict(self, fixture: ProtocolFixture) -> None:
        votes = fixture.build_vote_dict("partial_one_axis")
        assert ReviewAxis.CORRECTNESS in votes
        assert ReviewAxis.TEST_QUALITY not in votes
        assert ReviewAxis.ELEGANCE not in votes

    def test_empty_returns_empty_dict(self, fixture: ProtocolFixture) -> None:
        votes = fixture.build_vote_dict("empty")
        assert votes == {}

    def test_unknown_combo_name_raises_key_error(self, fixture: ProtocolFixture) -> None:
        with pytest.raises(KeyError):
            fixture.build_vote_dict("nonexistent_combo")

    def test_keys_are_review_axis_enums(self, fixture: ProtocolFixture) -> None:
        """Keys in the returned dict are ReviewAxis enum instances, not plain strings."""
        votes = fixture.build_vote_dict("all_accept")
        for key in votes:
            assert isinstance(key, ReviewAxis), (
                f"Key should be ReviewAxis enum, got {type(key)}: {key}"
            )

    def test_values_are_vote_type_enums(self, fixture: ProtocolFixture) -> None:
        """Values in the returned dict are VoteType enum instances, not plain strings."""
        votes = fixture.build_vote_dict("all_accept")
        for value in votes.values():
            assert isinstance(value, VoteType), (
                f"Value should be VoteType enum, got {type(value)}: {value}"
            )

    def test_mixed_combos_have_correct_types(self, fixture: ProtocolFixture) -> None:
        """Mixed vote combos return correctly typed values."""
        for combo_name in fixture.vote_combinations:
            votes = fixture.build_vote_dict(combo_name)
            for axis, vote in votes.items():
                assert isinstance(axis, ReviewAxis)
                assert isinstance(vote, VoteType)
