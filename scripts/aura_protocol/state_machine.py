"""12-phase epoch lifecycle state machine for the Aura protocol.

Pure Python — no Temporal dependency. Manages epoch lifecycle state and
validates phase transitions against the protocol transition table.

Source of truth for transitions: PHASE_SPECS from types.py, derived from schema.xml.

Key types:
    EpochState          — mutable runtime state for a single epoch
    TransitionRecord    — frozen, immutable audit entry for one transition
    TransitionError     — exception raised when a transition is invalid
    EpochStateMachine   — state machine for the 12-phase epoch lifecycle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from aura_protocol.types import (
    PHASE_SPECS,
    PhaseId,
    PhaseSpec,
    RoleId,
    SeverityLevel,
    Transition,
    VoteType,
)


# ─── State Types ──────────────────────────────────────────────────────────────


@dataclass
class EpochState:
    """Mutable runtime state for a single epoch.

    Tracks the current phase, completed phases, review votes, blocker count,
    current role, and the full transition history.

    review_votes keys are review axis letters: "A", "B", "C".
    """

    epoch_id: str
    current_phase: PhaseId
    completed_phases: set[PhaseId] = field(default_factory=set)
    review_votes: dict[str, VoteType] = field(default_factory=dict)
    blocker_count: int = 0
    current_role: RoleId = RoleId.EPOCH
    severity_groups: dict[SeverityLevel, set[str]] = field(default_factory=dict)
    transition_history: list[TransitionRecord] = field(default_factory=list)
    last_error: str | None = None


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable audit entry for a single phase transition.

    Records what happened, when, who triggered it, and which condition was met.

    success: True for a completed phase advance; False for a failed attempt that
        was rejected (e.g. invalid transition). The condition_met string retains
        the "FAILED: {error}" prefix for display/readability, but ALL programmatic
        checks of success vs. failure MUST use this boolean field, not the string
        prefix (which is brittle and subject to formatting changes).
    """

    from_phase: PhaseId
    to_phase: PhaseId
    timestamp: datetime
    triggered_by: str
    condition_met: str
    success: bool = True


# ─── Exception ────────────────────────────────────────────────────────────────


class TransitionError(Exception):
    """Raised when a requested phase transition is invalid.

    violations is the list of human-readable constraint messages that were
    violated. Always non-empty when raised.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations: list[str] = violations
        super().__init__("; ".join(violations))


# ─── State Machine ────────────────────────────────────────────────────────────

# The 3 canonical review axes used for consensus gating.
_REVIEW_AXES: frozenset[str] = frozenset({"A", "B", "C"})

# Transitions that require consensus (all 3 axes ACCEPT) to proceed.
# Derived from schema.xml: p4→p5 condition "all 3 reviewers vote ACCEPT".
# Also applies to p10→p11: both review phases enforce consensus before proceeding.
_CONSENSUS_GATED: frozenset[tuple[PhaseId, PhaseId]] = frozenset(
    {
        (PhaseId.P4_REVIEW, PhaseId.P5_UAT),
        (PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT),
    }
)

# Transitions that are blocked while blocker_count > 0.
# Derived from schema.xml: p10→p11 condition "all 3 reviewers ACCEPT, all BLOCKERs resolved".
_BLOCKER_GATED: frozenset[tuple[PhaseId, PhaseId]] = frozenset(
    {(PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT)}
)

# Transitions whose availability is determined by vote state (any REVISE present).
# When at p4 with any REVISE vote, only p3 is available (overrides forward p5 transition).
# When at p10 with any REVISE vote, only p9 is available (overrides forward p11 transition).
_REVISE_DRIVES_BACK_PHASES: frozenset[PhaseId] = frozenset(
    {PhaseId.P4_REVIEW, PhaseId.P10_CODE_REVIEW}
)


class EpochStateMachine:
    """State machine for the 12-phase epoch lifecycle.

    Accepts a custom specs dict for dependency injection (testing).
    Defaults to PHASE_SPECS from types.py (the canonical transition table).

    Usage:
        sm = EpochStateMachine("epoch-123")
        record = sm.advance(PhaseId.P2_ELICIT, triggered_by="architect",
                            condition_met="classification confirmed")
        sm.record_vote("A", VoteType.ACCEPT)
        sm.record_vote("B", VoteType.ACCEPT)
        sm.record_vote("C", VoteType.ACCEPT)
        sm.advance(PhaseId.P5_UAT, triggered_by="reviewer", condition_met="all 3 vote ACCEPT")
    """

    def __init__(
        self,
        epoch_id: str,
        specs: dict[PhaseId, PhaseSpec] | None = None,
    ) -> None:
        self._specs: dict[PhaseId, PhaseSpec] = specs if specs is not None else PHASE_SPECS
        self._state = EpochState(
            epoch_id=epoch_id,
            current_phase=PhaseId.P1_REQUEST,
        )

    # ── Public Properties ──────────────────────────────────────────────────────

    @property
    def state(self) -> EpochState:
        """Current epoch state (mutable — do not modify directly)."""
        return self._state

    @property
    def available_transitions(self) -> list[Transition]:
        """Transitions currently available from the current phase.

        Filters the transition table based on current vote and blocker state:

        - If the current phase is a review phase (p4 or p10) and ANY REVISE vote
          is recorded, only the backward revision-loop transition is returned.
          This is the dominant rule — a REVISE vote overrides everything else.
        - If no REVISE vote is present but consensus is required (p4→p5) and has
          not been reached, the forward p5 transition is excluded.
        - If the BLOCKER gate applies (p10→p11) and blocker_count > 0, the
          forward p11 transition is excluded.
        - Returns empty list when current_phase is COMPLETE or not in specs.
        """
        current = self._state.current_phase
        if current == PhaseId.COMPLETE or current not in self._specs:
            return []

        spec = self._specs[current]
        transitions = list(spec.transitions)

        # Rule 1: At a review phase with any REVISE vote — only the backward
        # (revision loop) transition is available. The revision loop targets are
        # the transitions whose to_phase is NOT the forward consensus gate target.
        if current in _REVISE_DRIVES_BACK_PHASES and self._has_any_revise():
            # p4's revision loop goes to p3; p10's revision loop goes to p9.
            # These are the non-consensus-gated transitions in those phases.
            return [
                t for t in transitions
                if (current, t.to_phase) not in _CONSENSUS_GATED
                and (current, t.to_phase) not in _BLOCKER_GATED
            ]

        # Rule 2: Filter out consensus-gated transitions when consensus not reached.
        # Check whether any gated transition exists for the current phase.
        gated_from_current = {to for (frm, to) in _CONSENSUS_GATED if frm == current}
        if gated_from_current and not self.has_consensus():
            transitions = [
                t for t in transitions
                if (current, t.to_phase) not in _CONSENSUS_GATED
            ]

        # Rule 3: Filter out BLOCKER-gated transitions when blockers remain.
        if self._state.blocker_count > 0:
            transitions = [
                t for t in transitions
                if (current, t.to_phase) not in _BLOCKER_GATED
            ]

        return transitions

    # ── Core Methods ──────────────────────────────────────────────────────────

    def advance(
        self,
        to_phase: PhaseId,
        *,
        triggered_by: str,
        condition_met: str,
        timestamp: datetime | None = None,
    ) -> TransitionRecord:
        """Advance the epoch to the requested phase.

        Validates the transition first. If valid, records the transition in
        transition_history and updates current_phase and completed_phases.
        Clears review_votes after any phase change (votes are phase-scoped).

        Args:
            to_phase: The target phase to transition to.
            triggered_by: Who or what triggered this transition (role or signal name).
            condition_met: The condition string that was satisfied.
            timestamp: Optional explicit timestamp for the transition record.
                If None (default), datetime.now(UTC) is used. Pass an explicit
                timestamp (e.g. from workflow.now()) to avoid post-hoc mutation
                of the audit trail by the workflow layer.

        Returns:
            A TransitionRecord for the completed transition.

        Raises:
            TransitionError: If the transition is invalid (violations list non-empty).
        """
        violations = self.validate_advance(to_phase)
        if violations:
            raise TransitionError(violations)

        effective_timestamp = timestamp if timestamp is not None else datetime.now(tz=timezone.utc)

        record = TransitionRecord(
            from_phase=self._state.current_phase,
            to_phase=to_phase,
            timestamp=effective_timestamp,
            triggered_by=triggered_by,
            condition_met=condition_met,
        )

        # Record completed phase before moving on.
        self._state.completed_phases.add(self._state.current_phase)
        self._state.current_phase = to_phase
        self._state.transition_history.append(record)

        # Auto-populate severity_groups with 3 empty SeverityLevel groups when
        # entering P10 (code review). Groups are created eagerly per C-severity-eager.
        #
        # Frozen-keys invariant: after this block executes, severity_groups
        # contains EXACTLY the 3 SeverityLevel enum values (BLOCKER, IMPORTANT,
        # MINOR) as keys — no more, no fewer. This invariant is structurally
        # guaranteed: SeverityLevel is a 3-value enum, so no other key can exist.
        # check_severity_tree() enforces that all 3 keys remain present at
        # validation time. Callers must NOT remove keys or add non-SeverityLevel
        # keys; doing so would violate this invariant and break gate checks.
        if to_phase == PhaseId.P10_CODE_REVIEW and not self._state.severity_groups:
            self._state.severity_groups = {
                SeverityLevel.BLOCKER: set(),
                SeverityLevel.IMPORTANT: set(),
                SeverityLevel.MINOR: set(),
            }

        # Votes are scoped to the phase in which they were cast.
        # Clear after any phase change so they don't bleed across review rounds.
        self._state.review_votes.clear()

        # Clear any previous error now that a valid advance has succeeded.
        self._state.last_error = None

        return record

    def validate_advance(self, to_phase: PhaseId) -> list[str]:
        """Dry-run validation of a proposed transition.

        Returns a list of violation messages. An empty list means the transition
        is valid and advance() would succeed.

        Checks (in order):
        1. Current phase is not COMPLETE (no further transitions).
        2. to_phase is in the transition table for the current phase.
        3. Consensus gate: p4→p5 and p10→p11 require has_consensus().
        4. BLOCKER gate: p10→p11 requires blocker_count == 0.
        """
        violations: list[str] = []
        current = self._state.current_phase

        if current == PhaseId.COMPLETE:
            violations.append(
                f"Epoch is already COMPLETE; no further transitions are possible."
            )
            return violations

        if current not in self._specs:
            violations.append(
                f"Current phase {current!r} has no spec in the transition table."
            )
            return violations

        spec = self._specs[current]
        valid_targets = {t.to_phase for t in spec.transitions}

        if to_phase not in valid_targets:
            violations.append(
                f"Transition {current!r} → {to_phase!r} is not in the transition table. "
                f"Valid targets: {sorted(t.value for t in valid_targets)}"
            )
            # No point checking gates for an invalid target.
            return violations

        # Consensus gate: p4→p5 and p10→p11 require all 3 axes to ACCEPT.
        if (current, to_phase) in _CONSENSUS_GATED and not self.has_consensus():
            have = sorted(self._state.review_votes.keys())
            accepted = [
                ax for ax, v in self._state.review_votes.items()
                if v == VoteType.ACCEPT
            ]
            violations.append(
                f"Consensus required for {current!r} → {to_phase!r}: "
                f"all 3 axes (A, B, C) must ACCEPT. "
                f"Axes with votes: {have}, accepted: {sorted(accepted)}."
            )

        # BLOCKER gate: p10 → p11 requires blocker_count == 0.
        if (current, to_phase) in _BLOCKER_GATED and self._state.blocker_count > 0:
            violations.append(
                f"BLOCKER gate for {current!r} → {to_phase!r}: "
                f"{self._state.blocker_count} unresolved blocker(s) must be resolved first."
            )

        return violations

    def record_vote(self, axis: str, vote: VoteType) -> None:
        """Record a reviewer vote for the given axis.

        axis must be one of "A", "B", "C".
        Recording a vote for the same axis overwrites the previous vote.

        Raises:
            ValueError: If axis is not one of "A", "B", "C".
        """
        if axis not in _REVIEW_AXES:
            raise ValueError(
                f"Invalid review axis {axis!r}. Must be one of {sorted(_REVIEW_AXES)}."
            )
        self._state.review_votes[axis] = vote

    def has_consensus(self) -> bool:
        """Return True if all 3 review axes (A, B, C) have ACCEPT votes.

        Returns False if any axis is missing a vote or voted REVISE.
        """
        return (
            all(axis in self._state.review_votes for axis in _REVIEW_AXES)
            and all(
                self._state.review_votes[axis] == VoteType.ACCEPT
                for axis in _REVIEW_AXES
            )
        )

    def record_blocker(self, *, resolved: bool = False) -> None:
        """Track BLOCKER count for p10→p11 gating.

        Args:
            resolved: If True, decrement blocker_count (blocker resolved).
                      If False (default), increment blocker_count (new blocker added).

        blocker_count is clamped to 0 and cannot go negative.
        """
        if resolved:
            self._state.blocker_count = max(0, self._state.blocker_count - 1)
        else:
            self._state.blocker_count += 1

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _has_any_revise(self) -> bool:
        """Return True if any recorded vote is REVISE."""
        return any(v == VoteType.REVISE for v in self._state.review_votes.values())
