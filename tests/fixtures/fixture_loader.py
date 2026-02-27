"""Combinatorial protocol test fixture loader and test case generator.

Loads protocol.yaml and provides structured access to protocol fixture axes:
- phase_specs: canonical PHASE_SPECS entries
- epoch_states: pre-built EpochState snapshots
- vote_combinations: vote dictionaries for consensus/revise testing
- audit_events: sample AuditEvent objects
- constraint_violations: all 26 C-* constraints (5 runnable, 21 skipped)

Generators produce TestCase objects suitable for pytest.param() parametrization
with readable IDs.

Usage:
    from tests.fixtures.fixture_loader import ProtocolFixture

    fixture = ProtocolFixture()

    # Generate parametrized cases
    @pytest.mark.parametrize(
        "tc",
        [pytest.param(tc, id=tc.id) for tc in fixture.generate_transition_test_cases()],
    )
    def test_transitions(tc):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

from aura_protocol.state_machine import EpochState
from aura_protocol.types import (
    AuditEvent,
    PhaseId,
    ReviewAxis,
    RoleId,
    SeverityLevel,
    VoteType,
)


# ─── TestCase Dataclasses ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class TransitionTestCase:
    """Generated test case for phase transitions.

    Fields:
        source_phase: PhaseId string value of the starting phase.
        target_phase: PhaseId string value of the destination phase.
        expected_success: True if the transition should succeed.
        requires_consensus: True if the transition needs all-ACCEPT consensus.
        requires_blocker_clear: True if the transition requires blocker_count == 0.
        description: Human-readable description of the case.
        id: Pytest-friendly identifier (used in pytest.param(id=...)).
    """

    source_phase: str
    target_phase: str
    expected_success: bool
    requires_consensus: bool
    requires_blocker_clear: bool
    description: str
    id: str


@dataclass(frozen=True)
class VoteTestCase:
    """Generated test case for vote combinations in review phases.

    Fields:
        phase: PhaseId string value of the review phase (p4 or p10).
        vote_combo_name: Fixture key (e.g. "all_accept", "mixed_one_revise_correctness").
        votes: Mapping of ReviewAxis value → VoteType value (string-keyed).
        has_consensus: True if votes constitute full 3-axis ACCEPT consensus.
        has_revise: True if any axis has a REVISE vote.
        description: Human-readable description.
        id: Pytest-friendly identifier.
    """

    phase: str
    vote_combo_name: str
    votes: dict[str, str]
    has_consensus: bool
    has_revise: bool
    description: str
    id: str


@dataclass(frozen=True)
class AuditEventTestCase:
    """Generated test case for audit event recording.

    Fields:
        event_name: Fixture key for the event.
        event: Constructed AuditEvent object.
        event_type: The event_type string.
        description: Human-readable description.
        id: Pytest-friendly identifier.
    """

    event_name: str
    event: AuditEvent
    event_type: str
    description: str
    id: str


@dataclass(frozen=True)
class ConstraintViolationTestCase:
    """Generated test case for runtime constraint violation checks.

    Each case covers one C-* constraint from CONSTRAINT_SPECS. Cases with
    skip_reason are skipped at collection time via pytest.mark.skip; the
    remaining 5 runnable cases construct an EpochState that violates the
    constraint and verify RuntimeConstraintChecker.check_state() fires it.

    Fields:
        constraint_id: The C-* constraint under test (e.g. "C-review-consensus").
        description: Human-readable description of the violation scenario.
        violation_state: EpochState that violates the constraint (None if skipped).
        skip_reason: If set, this case is skipped; violation_state is None.
        id: Pytest-friendly identifier (used in pytest.param(id=...)).
    """

    constraint_id: str
    description: str
    violation_state: EpochState | None
    skip_reason: str | None
    id: str


# ─── ProtocolFixture ──────────────────────────────────────────────────────────


class ProtocolFixture:
    """Load and generate combinatorial test cases from protocol.yaml.

    The fixture file defines five axes:
    - phase_specs: Canonical PHASE_SPECS entries (12 phases).
    - epoch_states: Pre-built epoch state snapshots.
    - vote_combinations: Review vote combinations for consensus testing.
    - audit_events: Sample AuditEvent objects for audit trail testing.
    - constraint_violations: All 26 C-* constraints (5 runnable, 21 skipped).

    This class provides properties for each axis and generator methods that
    yield pytest-friendly TestCase objects.
    """

    def __init__(self, fixture_path: str | Path | None = None) -> None:
        """Initialize from protocol.yaml.

        Args:
            fixture_path: Path to protocol.yaml. If None, uses the default
                location (same directory as this module).
        """
        if fixture_path is None:
            fixture_path = Path(__file__).parent / "protocol.yaml"
        self._path = Path(fixture_path)

        with open(self._path) as f:
            self._data: dict = yaml.safe_load(f)

    # ─── Axis Properties ──────────────────────────────────────────────────────

    @property
    def phase_specs(self) -> dict:
        """Raw phase_specs axis from YAML (keyed by spec name)."""
        return self._data.get("phase_specs", {})

    @property
    def epoch_states(self) -> dict:
        """Raw epoch_states axis from YAML (keyed by state name)."""
        return self._data.get("epoch_states", {})

    @property
    def vote_combinations(self) -> dict:
        """Raw vote_combinations axis from YAML (keyed by combo name)."""
        return self._data.get("vote_combinations", {})

    @property
    def audit_events(self) -> dict:
        """Raw audit_events axis from YAML (keyed by event name)."""
        return self._data.get("audit_events", {})

    @property
    def forward_phase_path(self) -> list[str]:
        """Ordered list of phase_id strings for the forward (happy) path."""
        return self._data.get("forward_phase_path", [])

    @property
    def transition_matrix(self) -> dict:
        """Predefined transition expectation matrix from YAML."""
        return self._data.get("transition_matrix", {})

    @property
    def constraint_violations(self) -> dict:
        """Raw constraint_violations axis from YAML (keyed by constraint_id).

        Each entry is either:
        - A runnable case: has violation_state dict + no skip_reason.
        - A skipped case: has skip_reason string + no violation_state.
        """
        return self._data.get("constraint_violations", {})

    # ─── Generators ───────────────────────────────────────────────────────────

    def generate_transition_test_cases(self) -> Iterator[TransitionTestCase]:
        """Generate transition test cases from the transition_matrix axis.

        Yields one TransitionTestCase per matrix entry in:
        - transition_matrix.valid_forward
        - transition_matrix.valid_backward
        - transition_matrix.invalid_skips

        Yields:
            TransitionTestCase: Each generated test case.
        """
        matrix = self.transition_matrix

        for category in ("valid_forward", "valid_backward", "invalid_skips"):
            entries = matrix.get(category, [])
            for entry in entries:
                source = entry["source"]
                target = entry["target"]
                expected_success = entry["expected_success"]
                requires_consensus = entry.get("requires_consensus", False)
                requires_blocker_clear = entry.get("requires_blocker_clear", False)
                description = entry.get("description", f"{source}->{target}")

                yield TransitionTestCase(
                    source_phase=source,
                    target_phase=target,
                    expected_success=expected_success,
                    requires_consensus=requires_consensus,
                    requires_blocker_clear=requires_blocker_clear,
                    description=description,
                    id=f"{category}:{source}->{target}",
                )

    def generate_forward_path_transition_cases(self) -> Iterator[TransitionTestCase]:
        """Generate test cases for every consecutive pair in the forward path.

        Uses forward_phase_path to enumerate p1→p2, p2→p3, ..., p12→complete.
        All forward-path transitions are expected to succeed (given gates are met).

        Yields:
            TransitionTestCase: One case per consecutive pair in the path.
        """
        path = self.forward_phase_path
        # Phases that require consensus: p4→p5 and p10→p11
        _CONSENSUS_GATED = {("p4", "p5"), ("p10", "p11")}
        # Phases that also require blocker-clear: p10→p11
        _BLOCKER_GATED = {("p10", "p11")}

        for source, target in zip(path, path[1:]):
            pair = (source, target)
            yield TransitionTestCase(
                source_phase=source,
                target_phase=target,
                expected_success=True,
                requires_consensus=pair in _CONSENSUS_GATED,
                requires_blocker_clear=pair in _BLOCKER_GATED,
                description=f"Happy path: {source} → {target}",
                id=f"forward:{source}->{target}",
            )

    def generate_vote_test_cases(self) -> Iterator[VoteTestCase]:
        """Generate vote test cases by crossing vote_combinations × review phases.

        Review phases: p4 (plan review) and p10 (code review).
        Each combination is tested at both review phases.

        Yields:
            VoteTestCase: One case per (review_phase × vote_combination) pair.
        """
        review_phases = ["p4", "p10"]
        combos = self.vote_combinations

        for phase in review_phases:
            for combo_name, combo_def in combos.items():
                votes = combo_def.get("votes", {})
                has_consensus = combo_def.get("has_consensus", False)
                has_revise = combo_def.get("has_revise", False)
                description = combo_def.get("description", combo_name)

                yield VoteTestCase(
                    phase=phase,
                    vote_combo_name=combo_name,
                    votes=votes,
                    has_consensus=has_consensus,
                    has_revise=has_revise,
                    description=f"phase={phase}, combo={combo_name}: {description}",
                    id=f"{phase}:{combo_name}",
                )

    def generate_audit_event_test_cases(self) -> Iterator[AuditEventTestCase]:
        """Generate audit event test cases from the audit_events axis.

        Constructs real AuditEvent objects from YAML definitions.

        Yields:
            AuditEventTestCase: One case per audit_events entry.
        """
        for event_name, event_def in self.audit_events.items():
            epoch_id = event_def.get("epoch_id", "test-epoch")
            event_type = event_def.get("event_type", "unknown")
            phase_str = event_def.get("phase", "p1")
            role_str = event_def.get("role", "epoch")
            payload = event_def.get("payload", {})
            description = event_def.get("description", event_name)

            # Map string values to enums
            phase = PhaseId(phase_str)
            role = RoleId(role_str)

            event = AuditEvent(
                epoch_id=epoch_id,
                event_type=event_type,
                phase=phase,
                role=role,
                payload=payload,
            )

            yield AuditEventTestCase(
                event_name=event_name,
                event=event,
                event_type=event_type,
                description=description,
                id=f"audit:{event_name}",
            )

    def generate_constraint_violation_test_cases(
        self,
    ) -> Iterator[ConstraintViolationTestCase]:
        """Generate constraint violation test cases from the constraint_violations axis.

        Yields one ConstraintViolationTestCase per entry in constraint_violations.
        Runnable cases (no skip_reason) have a constructed EpochState.
        Skipped cases (skip_reason set) have violation_state=None.

        YAML violation_state fields:
            current_phase: PhaseId string value (required for runnable cases).
            review_votes: dict mapping axis letters (A/B/C) to VoteType values.
                Defaults to empty dict if omitted.
            blocker_count: int. Defaults to 0.
            severity_groups_present: bool. If True, populate all 3 SeverityLevel
                groups with empty sets. Defaults to False (empty severity_groups).

        Yields:
            ConstraintViolationTestCase: Each generated test case.
        """
        for constraint_id, entry in self.constraint_violations.items():
            description = entry.get("description", constraint_id)
            skip_reason: str | None = entry.get("skip_reason")

            if skip_reason:
                yield ConstraintViolationTestCase(
                    constraint_id=constraint_id,
                    description=description,
                    violation_state=None,
                    skip_reason=skip_reason,
                    id=f"constraint:{constraint_id}",
                )
                continue

            # Build EpochState from violation_state dict
            vs = entry.get("violation_state", {})
            phase_str = vs.get("current_phase", "p1")
            current_phase = PhaseId(phase_str)

            raw_votes: dict[str, str] = vs.get("review_votes", {})
            review_votes = {k: VoteType(v) for k, v in raw_votes.items()}

            blocker_count: int = vs.get("blocker_count", 0)

            severity_groups: dict[SeverityLevel, set[str]] = {}
            if vs.get("severity_groups_present", False):
                severity_groups = {
                    SeverityLevel.BLOCKER: set(),
                    SeverityLevel.IMPORTANT: set(),
                    SeverityLevel.MINOR: set(),
                }

            state = EpochState(
                epoch_id=f"test-constraint-{constraint_id}",
                current_phase=current_phase,
                review_votes=review_votes,
                blocker_count=blocker_count,
                severity_groups=severity_groups,
            )

            yield ConstraintViolationTestCase(
                constraint_id=constraint_id,
                description=description,
                violation_state=state,
                skip_reason=None,
                id=f"constraint:{constraint_id}",
            )

    def build_vote_dict(self, combo_name: str) -> dict[ReviewAxis, VoteType]:
        """Build a typed ReviewAxis → VoteType dict for a named vote combination.

        Args:
            combo_name: Key from vote_combinations (e.g. "all_accept").

        Returns:
            Dict mapping ReviewAxis enum → VoteType enum.

        Raises:
            KeyError: If combo_name is not found in vote_combinations.
        """
        combo = self.vote_combinations[combo_name]
        raw_votes: dict[str, str] = combo.get("votes", {})
        return {
            ReviewAxis(axis): VoteType(vote)
            for axis, vote in raw_votes.items()
        }
