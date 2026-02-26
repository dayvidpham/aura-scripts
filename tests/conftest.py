"""Shared pytest fixtures and helpers for aura_protocol test suite.

Provides:
- Module-level helper functions (_advance_to, _make_state) importable directly
  by any test module that needs them without going through pytest fixture injection.
- pytest fixtures for common EpochStateMachine setup patterns.
- Module-level _PROTOCOL_FIXTURE singleton for YAML-driven combinatorial tests.

Module-level helpers (import directly):
    _advance_to(sm, target) — drive a state machine through the forward phase path.
    _make_state(phase, epoch_id, **kwargs) — construct a bare EpochState.

Module-level fixtures (import directly):
    _PROTOCOL_FIXTURE — ProtocolFixture singleton (loaded once, shared across tests).

pytest fixtures:
    epoch_id            — canonical test epoch ID string.
    sm                  — fresh EpochStateMachine at P1.
    sm_at_p4            — state machine advanced to P4 (review phase).
    sm_at_p4_with_consensus — sm_at_p4 with all 3 ACCEPT votes recorded.
    protocol_fixture    — ProtocolFixture singleton (YAML-driven test data).
"""

from __future__ import annotations

import pytest

from aura_protocol.state_machine import EpochState, EpochStateMachine
from aura_protocol.types import PhaseId, ReviewAxis, VoteType

# Import after production imports so PYTHONPATH=scripts:tests resolves fixtures/
from fixtures.fixture_loader import ProtocolFixture


# ─── Protocol Fixture Singleton ───────────────────────────────────────────────
# Loaded once at module import time; shared across all test modules.
# Use the pytest fixture `protocol_fixture` for injection, or import
# _PROTOCOL_FIXTURE directly in parametrize decorators (module-level eval).

_PROTOCOL_FIXTURE = ProtocolFixture()


# ─── Module-Level Helpers ─────────────────────────────────────────────────────
# These are plain functions (not fixtures) so any test module can import them
# directly. They capture the canonical phase order and gate-satisfaction logic
# in one place; updating here keeps test_state_machine.py and test_workflow.py
# in sync automatically.


# Manually ordered forward phase sequence — NOT derived from PHASE_SPECS because
# PHASE_SPECS transitions include revision loops (e.g. P4→P3, P10→P9) and
# COMPLETE is not in PHASE_SPECS at all. This list represents the single happy
# path with no revisions, used by _advance_to() to drive the state machine
# forward. Do not reorder or derive from dict iteration (dict order is insertion
# order but PHASE_SPECS is keyed by enum, not by phase number).
_FORWARD_PHASES: list[PhaseId] = [
    PhaseId.P1_REQUEST,
    PhaseId.P2_ELICIT,
    PhaseId.P3_PROPOSE,
    PhaseId.P4_REVIEW,
    PhaseId.P5_UAT,
    PhaseId.P6_RATIFY,
    PhaseId.P7_HANDOFF,
    PhaseId.P8_IMPL_PLAN,
    PhaseId.P9_SLICE,
    PhaseId.P10_CODE_REVIEW,
    PhaseId.P11_IMPL_UAT,
    PhaseId.P12_LANDING,
    PhaseId.COMPLETE,
]


def _advance_to(sm: EpochStateMachine, target: PhaseId) -> None:
    """Advance a state machine through all forward phases sequentially up to target.

    Uses only the first (forward) transition at each step. Populates required
    gates along the way:
    - At P4 (plan review): records 3 ACCEPT votes before advancing to P5.
    - At P10 (code review): records 3 ACCEPT votes before advancing to P11.

    Args:
        sm: The state machine to advance. Must be at a phase earlier than target.
        target: The phase to stop at (inclusive — the machine will be AT target).
    """
    current_idx = _FORWARD_PHASES.index(sm.state.current_phase)
    target_idx = _FORWARD_PHASES.index(target)

    for i in range(current_idx, target_idx):
        frm = _FORWARD_PHASES[i]
        nxt = _FORWARD_PHASES[i + 1]

        # Populate consensus gate before P4→P5 (plan review).
        if frm == PhaseId.P4_REVIEW and nxt == PhaseId.P5_UAT:
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        # Populate consensus + blocker-clear gate before P10→P11 (code review).
        if frm == PhaseId.P10_CODE_REVIEW and nxt == PhaseId.P11_IMPL_UAT:
            sm.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
            sm.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)

        sm.advance(nxt, triggered_by="test", condition_met="test-condition")


def _make_state(
    phase: PhaseId = PhaseId.P1_REQUEST,
    epoch_id: str = "test-epoch",
    **kwargs,
) -> EpochState:
    """Return a fresh EpochState at the given phase.

    Args:
        phase: The current_phase for the new state. Defaults to P1_REQUEST.
        epoch_id: The epoch identifier string. Defaults to "test-epoch".
        **kwargs: Additional keyword arguments forwarded to EpochState constructor
            (e.g. blocker_count, current_role, review_votes).

    Returns:
        A new EpochState instance; no transitions are recorded.
    """
    return EpochState(epoch_id=epoch_id, current_phase=phase, **kwargs)


# ─── pytest Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def epoch_id() -> str:
    return "test-epoch-001"


@pytest.fixture
def sm(epoch_id: str) -> EpochStateMachine:
    return EpochStateMachine(epoch_id)


@pytest.fixture
def sm_at_p4(sm: EpochStateMachine) -> EpochStateMachine:
    """State machine advanced to P4 (review phase)."""
    sm.advance(PhaseId.P2_ELICIT, triggered_by="epoch", condition_met="ok")
    sm.advance(PhaseId.P3_PROPOSE, triggered_by="architect", condition_met="ok")
    sm.advance(PhaseId.P4_REVIEW, triggered_by="architect", condition_met="ok")
    return sm


@pytest.fixture
def sm_at_p4_with_consensus(sm_at_p4: EpochStateMachine) -> EpochStateMachine:
    """State machine at P4 with all 3 ACCEPT votes."""
    sm_at_p4.record_vote(ReviewAxis.CORRECTNESS, VoteType.ACCEPT)
    sm_at_p4.record_vote(ReviewAxis.TEST_QUALITY, VoteType.ACCEPT)
    sm_at_p4.record_vote(ReviewAxis.ELEGANCE, VoteType.ACCEPT)
    return sm_at_p4


@pytest.fixture
def protocol_fixture() -> ProtocolFixture:
    """Return the module-level ProtocolFixture singleton.

    Loads protocol.yaml once at import time; this fixture just provides
    the singleton via pytest injection for tests that prefer injection
    over direct import.
    """
    return _PROTOCOL_FIXTURE
