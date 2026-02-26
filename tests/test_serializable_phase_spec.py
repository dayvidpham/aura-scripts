"""Tests for SerializableTransition, SerializablePhaseSpec, PhaseInput, PhaseResult.

Coverage:
- from_spec() converts every PHASE_SPECS entry correctly
- Serialization roundtrip (JSON encode/decode via dataclasses.asdict)
- Frozen compliance (cannot mutate frozen dataclass fields)
- PhaseInput and PhaseResult construction
- owner_roles is sorted list (not frozenset)
- transitions is list (not tuple)
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from aura_protocol import PHASE_SPECS, PhaseId, PhaseSpec, RoleId, VoteType
from aura_protocol.types import (
    PhaseInput,
    PhaseResult,
    SerializablePhaseSpec,
    SerializableTransition,
)


# ─── L1: Type Definitions ─────────────────────────────────────────────────────


class TestSerializableTransition:
    """SerializableTransition is a frozen, JSON-serializable dataclass."""

    def test_construction(self) -> None:
        t = SerializableTransition(to_phase=PhaseId.P2_ELICIT, condition="always")
        assert t.to_phase == PhaseId.P2_ELICIT
        assert t.condition == "always"
        assert t.action is None

    def test_with_action(self) -> None:
        t = SerializableTransition(
            to_phase=PhaseId.P10_CODE_REVIEW,
            condition="all slices complete",
            action="notify",
        )
        assert t.action == "notify"

    def test_frozen(self) -> None:
        t = SerializableTransition(to_phase=PhaseId.P1_REQUEST, condition="start")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            t.condition = "mutated"  # type: ignore[misc]

    def test_json_serializable(self) -> None:
        t = SerializableTransition(to_phase=PhaseId.P3_PROPOSE, condition="URE done")
        d = dataclasses.asdict(t)
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["to_phase"] == "p3"
        assert decoded["condition"] == "URE done"
        assert decoded["action"] is None


class TestSerializablePhaseSpec:
    """SerializablePhaseSpec is a frozen dataclass with list fields."""

    def _make_spec(self) -> SerializablePhaseSpec:
        return SerializablePhaseSpec(
            id=PhaseId.P9_SLICE,
            number=9,
            domain=PHASE_SPECS[PhaseId.P9_SLICE].domain,
            name="Worker Slices",
            owner_roles=[RoleId.SUPERVISOR, RoleId.WORKER],
            transitions=[
                SerializableTransition(
                    to_phase=PhaseId.P10_CODE_REVIEW,
                    condition="all slices complete",
                )
            ],
        )

    def test_construction(self) -> None:
        spec = self._make_spec()
        assert spec.id == PhaseId.P9_SLICE
        assert spec.number == 9
        assert isinstance(spec.owner_roles, list)
        assert isinstance(spec.transitions, list)

    def test_owner_roles_is_list(self) -> None:
        spec = self._make_spec()
        assert type(spec.owner_roles) is list

    def test_transitions_is_list(self) -> None:
        spec = self._make_spec()
        assert type(spec.transitions) is list

    def test_frozen(self) -> None:
        spec = self._make_spec()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.name = "mutated"  # type: ignore[misc]

    def test_json_serializable(self) -> None:
        spec = self._make_spec()
        d = dataclasses.asdict(spec)
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["id"] == "p9"
        assert isinstance(decoded["owner_roles"], list)
        assert isinstance(decoded["transitions"], list)


class TestFromSpec:
    """from_spec() converts every PHASE_SPECS entry correctly."""

    @pytest.mark.parametrize("phase_id", list(PhaseId)[:-1])  # exclude COMPLETE
    def test_all_phase_specs_convert(self, phase_id: PhaseId) -> None:
        phase_spec = PHASE_SPECS[phase_id]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)

        assert serializable.id == phase_spec.id
        assert serializable.number == phase_spec.number
        assert serializable.domain == phase_spec.domain
        assert serializable.name == phase_spec.name

    @pytest.mark.parametrize("phase_id", list(PhaseId)[:-1])
    def test_owner_roles_sorted(self, phase_id: PhaseId) -> None:
        phase_spec = PHASE_SPECS[phase_id]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)

        assert type(serializable.owner_roles) is list
        sorted_values = sorted(r.value for r in phase_spec.owner_roles)
        assert [r.value for r in serializable.owner_roles] == sorted_values

    @pytest.mark.parametrize("phase_id", list(PhaseId)[:-1])
    def test_transitions_converted(self, phase_id: PhaseId) -> None:
        phase_spec = PHASE_SPECS[phase_id]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)

        assert type(serializable.transitions) is list
        assert len(serializable.transitions) == len(phase_spec.transitions)
        for st, t in zip(serializable.transitions, phase_spec.transitions):
            assert isinstance(st, SerializableTransition)
            assert st.to_phase == t.to_phase
            assert st.condition == t.condition
            assert st.action == t.action

    @pytest.mark.parametrize("phase_id", list(PhaseId)[:-1])
    def test_roundtrip_json(self, phase_id: PhaseId) -> None:
        phase_spec = PHASE_SPECS[phase_id]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)
        d = dataclasses.asdict(serializable)
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["id"] == phase_spec.id.value
        assert isinstance(decoded["owner_roles"], list)
        assert isinstance(decoded["transitions"], list)

    def test_no_frozenset_in_fields(self) -> None:
        phase_spec = PHASE_SPECS[PhaseId.P9_SLICE]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)
        for f in dataclasses.fields(serializable):
            val = getattr(serializable, f.name)
            assert not isinstance(val, frozenset), f"Field {f.name} must not be frozenset"
            assert not isinstance(val, tuple), f"Field {f.name} must not be tuple"

    def test_no_frozenset_in_transitions(self) -> None:
        phase_spec = PHASE_SPECS[PhaseId.P4_REVIEW]
        serializable = SerializablePhaseSpec.from_spec(phase_spec)
        for t in serializable.transitions:
            for f in dataclasses.fields(t):
                val = getattr(t, f.name)
                assert not isinstance(val, (frozenset, tuple, set, dict))


# ─── L2: PhaseInput / PhaseResult ────────────────────────────────────────────


class TestPhaseInput:
    """PhaseInput is a frozen dataclass wrapping epoch_id + SerializablePhaseSpec."""

    def _make_phase_input(self) -> PhaseInput:
        phase_spec = SerializablePhaseSpec.from_spec(PHASE_SPECS[PhaseId.P1_REQUEST])
        return PhaseInput(epoch_id="epoch-abc-123", phase_spec=phase_spec)

    def test_construction(self) -> None:
        pi = self._make_phase_input()
        assert pi.epoch_id == "epoch-abc-123"
        assert isinstance(pi.phase_spec, SerializablePhaseSpec)

    def test_frozen(self) -> None:
        pi = self._make_phase_input()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            pi.epoch_id = "mutated"  # type: ignore[misc]

    def test_json_serializable(self) -> None:
        pi = self._make_phase_input()
        d = dataclasses.asdict(pi)
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["epoch_id"] == "epoch-abc-123"
        assert decoded["phase_spec"]["id"] == "p1"


class TestPhaseResult:
    """PhaseResult is a frozen dataclass with optional vote_result."""

    def test_minimal_construction(self) -> None:
        r = PhaseResult(phase_id=PhaseId.P1_REQUEST, success=True)
        assert r.phase_id == PhaseId.P1_REQUEST
        assert r.success is True
        assert r.blocker_count == 0
        assert r.vote_result is None

    def test_with_blockers(self) -> None:
        r = PhaseResult(phase_id=PhaseId.P10_CODE_REVIEW, success=False, blocker_count=3)
        assert r.blocker_count == 3
        assert r.vote_result is None

    def test_with_vote_result(self) -> None:
        r = PhaseResult(
            phase_id=PhaseId.P4_REVIEW,
            success=True,
            vote_result=VoteType.ACCEPT,
        )
        assert r.vote_result == VoteType.ACCEPT

    def test_frozen(self) -> None:
        r = PhaseResult(phase_id=PhaseId.P9_SLICE, success=True)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            r.success = False  # type: ignore[misc]

    def test_json_serializable(self) -> None:
        r = PhaseResult(
            phase_id=PhaseId.P4_REVIEW,
            success=True,
            blocker_count=0,
            vote_result=VoteType.REVISE,
        )
        d = dataclasses.asdict(r)
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["phase_id"] == "p4"
        assert decoded["success"] is True
        assert decoded["vote_result"] == "REVISE"

    def test_no_forbidden_types(self) -> None:
        r = PhaseResult(phase_id=PhaseId.P9_SLICE, success=True)
        for f in dataclasses.fields(r):
            val = getattr(r, f.name)
            if val is not None:
                assert not isinstance(val, (frozenset, tuple, set, dict))
