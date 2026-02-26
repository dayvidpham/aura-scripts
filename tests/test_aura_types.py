"""Unit tests for aura_protocol.types.

Tests:
- Enum completeness (all expected values present)
- str Enum serialization (JSON-compatible)
- Spec freezing (frozen dataclasses cannot be mutated)
- PHASE_DOMAIN mapping correctness (covers all 12 phases, correct domains)
- PHASE_SPECS completeness (covers all 12 PhaseId values, no COMPLETE)
- CONSTRAINT_SPECS and HANDOFF_SPECS non-empty
- PhaseSpec structural invariants (number, transitions non-empty)
- HandoffSpec role consistency
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from aura_protocol import (
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    PHASE_DOMAIN,
    PHASE_SPECS,
    ConstraintSpec,
    Domain,
    HandoffSpec,
    PermissionDecision,
    PhaseId,
    PhaseSpec,
    PhaseTransitionEvent,
    RoleId,
    SeverityLevel,
    Transition,
    VoteType,
)


# ─── Enum Completeness ────────────────────────────────────────────────────────


class TestPhaseIdEnum:
    def test_all_13_values_present(self) -> None:
        values = {p.value for p in PhaseId}
        expected = {"p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12", "complete"}
        assert values == expected

    def test_12_numbered_phases(self) -> None:
        numbered = [p for p in PhaseId if p != PhaseId.COMPLETE]
        assert len(numbered) == 12

    def test_complete_sentinel(self) -> None:
        assert PhaseId.COMPLETE.value == "complete"

    def test_is_str_enum(self) -> None:
        assert isinstance(PhaseId.P1_REQUEST, str)
        assert PhaseId.P1_REQUEST == "p1"

    def test_json_serializable(self) -> None:
        encoded = json.dumps({"phase": PhaseId.P9_SLICE})
        decoded = json.loads(encoded)
        assert decoded["phase"] == "p9"


class TestDomainEnum:
    def test_all_3_values_present(self) -> None:
        values = {d.value for d in Domain}
        assert values == {"user", "plan", "impl"}

    def test_is_str_enum(self) -> None:
        assert isinstance(Domain.USER, str)
        assert Domain.USER == "user"
        assert Domain.PLAN == "plan"
        assert Domain.IMPL == "impl"

    def test_json_serializable(self) -> None:
        encoded = json.dumps({"domain": Domain.IMPL})
        decoded = json.loads(encoded)
        assert decoded["domain"] == "impl"


class TestRoleIdEnum:
    def test_all_5_values_present(self) -> None:
        values = {r.value for r in RoleId}
        assert values == {"epoch", "architect", "reviewer", "supervisor", "worker"}

    def test_is_str_enum(self) -> None:
        assert isinstance(RoleId.WORKER, str)
        assert RoleId.WORKER == "worker"

    def test_json_serializable(self) -> None:
        encoded = json.dumps({"role": RoleId.SUPERVISOR})
        decoded = json.loads(encoded)
        assert decoded["role"] == "supervisor"


class TestVoteTypeEnum:
    def test_all_2_values_present(self) -> None:
        values = {v.value for v in VoteType}
        assert values == {"ACCEPT", "REVISE"}

    def test_is_str_enum(self) -> None:
        assert isinstance(VoteType.ACCEPT, str)
        assert VoteType.ACCEPT == "ACCEPT"
        assert VoteType.REVISE == "REVISE"

    def test_json_serializable(self) -> None:
        encoded = json.dumps({"vote": VoteType.ACCEPT})
        decoded = json.loads(encoded)
        assert decoded["vote"] == "ACCEPT"


class TestSeverityLevelEnum:
    def test_all_3_values_present(self) -> None:
        values = {s.value for s in SeverityLevel}
        assert values == {"BLOCKER", "IMPORTANT", "MINOR"}

    def test_is_str_enum(self) -> None:
        assert isinstance(SeverityLevel.BLOCKER, str)
        assert SeverityLevel.BLOCKER == "BLOCKER"

    def test_json_serializable(self) -> None:
        encoded = json.dumps({"severity": SeverityLevel.BLOCKER})
        decoded = json.loads(encoded)
        assert decoded["severity"] == "BLOCKER"


# ─── Spec Freezing ────────────────────────────────────────────────────────────


class TestSpecFreezing:
    """Frozen dataclasses must raise FrozenInstanceError on mutation attempts."""

    def test_transition_is_frozen(self) -> None:
        t = Transition(to_phase=PhaseId.P2_ELICIT, condition="test")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            t.condition = "mutate"  # type: ignore[misc]

    def test_phase_spec_is_frozen(self) -> None:
        spec = PHASE_SPECS[PhaseId.P1_REQUEST]
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.name = "mutate"  # type: ignore[misc]

    def test_constraint_spec_is_frozen(self) -> None:
        spec = next(iter(CONSTRAINT_SPECS.values()))
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.given = "mutate"  # type: ignore[misc]

    def test_handoff_spec_is_frozen(self) -> None:
        spec = HANDOFF_SPECS["h1"]
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            spec.content_level = "mutate"  # type: ignore[misc]

    def test_phase_transition_event_is_frozen(self) -> None:
        event = PhaseTransitionEvent(
            epoch_id="test-epoch",
            from_phase=PhaseId.P1_REQUEST,
            to_phase=PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="classification confirmed",
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            event.epoch_id = "mutate"  # type: ignore[misc]

    def test_permission_decision_is_frozen(self) -> None:
        decision = PermissionDecision(allowed=True, reason="test")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            decision.allowed = False  # type: ignore[misc]


# ─── PHASE_DOMAIN Mapping ─────────────────────────────────────────────────────


class TestPhaseDomainMapping:
    """PHASE_DOMAIN must cover all 12 phases with correct domain assignments."""

    def test_covers_all_12_phases(self) -> None:
        non_complete = {p for p in PhaseId if p != PhaseId.COMPLETE}
        assert set(PHASE_DOMAIN.keys()) == non_complete

    def test_complete_sentinel_not_in_mapping(self) -> None:
        assert PhaseId.COMPLETE not in PHASE_DOMAIN

    def test_user_domain_phases(self) -> None:
        # p1, p2, p5, p11 are user domain
        for phase in (PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P5_UAT, PhaseId.P11_IMPL_UAT):
            assert PHASE_DOMAIN[phase] == Domain.USER, f"{phase} should be USER domain"

    def test_plan_domain_phases(self) -> None:
        # p3, p4, p6, p7 are plan domain
        for phase in (PhaseId.P3_PROPOSE, PhaseId.P4_REVIEW, PhaseId.P6_RATIFY, PhaseId.P7_HANDOFF):
            assert PHASE_DOMAIN[phase] == Domain.PLAN, f"{phase} should be PLAN domain"

    def test_impl_domain_phases(self) -> None:
        # p8, p9, p10, p12 are impl domain
        for phase in (
            PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW, PhaseId.P12_LANDING,
        ):
            assert PHASE_DOMAIN[phase] == Domain.IMPL, f"{phase} should be IMPL domain"

    def test_domain_is_domain_enum(self) -> None:
        for phase, domain in PHASE_DOMAIN.items():
            assert isinstance(domain, Domain), f"{phase} domain is not Domain enum: {domain!r}"


# ─── PHASE_SPECS Completeness ─────────────────────────────────────────────────


class TestPhaseSpecs:
    """PHASE_SPECS must cover all 12 phases with valid specs."""

    def test_covers_all_12_phases(self) -> None:
        assert len(PHASE_SPECS) == 12

    def test_no_complete_sentinel_in_specs(self) -> None:
        assert PhaseId.COMPLETE not in PHASE_SPECS

    def test_all_phase_ids_covered(self) -> None:
        non_complete = {p for p in PhaseId if p != PhaseId.COMPLETE}
        assert set(PHASE_SPECS.keys()) == non_complete

    def test_phase_numbers_sequential(self) -> None:
        numbers = sorted(spec.number for spec in PHASE_SPECS.values())
        assert numbers == list(range(1, 13))

    def test_each_phase_has_transitions(self) -> None:
        for phase_id, spec in PHASE_SPECS.items():
            assert len(spec.transitions) >= 1, f"{phase_id} has no transitions"

    def test_transitions_are_transition_instances(self) -> None:
        for phase_id, spec in PHASE_SPECS.items():
            for t in spec.transitions:
                assert isinstance(t, Transition), f"{phase_id} has non-Transition: {t!r}"

    def test_owner_roles_are_frozenset(self) -> None:
        for phase_id, spec in PHASE_SPECS.items():
            assert isinstance(spec.owner_roles, frozenset), (
                f"{phase_id} owner_roles is not frozenset"
            )

    def test_transitions_are_tuple(self) -> None:
        for phase_id, spec in PHASE_SPECS.items():
            assert isinstance(spec.transitions, tuple), (
                f"{phase_id} transitions is not tuple"
            )

    def test_domain_matches_phase_domain_map(self) -> None:
        for phase_id, spec in PHASE_SPECS.items():
            expected = PHASE_DOMAIN[phase_id]
            assert spec.domain == expected, (
                f"{phase_id} spec.domain={spec.domain} but PHASE_DOMAIN says {expected}"
            )

    def test_revision_loop_phases_have_forward_and_backward_transitions(self) -> None:
        # p4 and p10 have review loops back to earlier phases
        p4 = PHASE_SPECS[PhaseId.P4_REVIEW]
        to_phases = {t.to_phase for t in p4.transitions}
        assert PhaseId.P5_UAT in to_phases  # forward
        assert PhaseId.P3_PROPOSE in to_phases  # revision loop

        p10 = PHASE_SPECS[PhaseId.P10_CODE_REVIEW]
        to_phases_p10 = {t.to_phase for t in p10.transitions}
        assert PhaseId.P11_IMPL_UAT in to_phases_p10  # forward
        assert PhaseId.P9_SLICE in to_phases_p10  # revision loop

    def test_p12_landing_terminates_at_complete(self) -> None:
        p12 = PHASE_SPECS[PhaseId.P12_LANDING]
        assert len(p12.transitions) == 1
        assert p12.transitions[0].to_phase == PhaseId.COMPLETE


# ─── CONSTRAINT_SPECS ─────────────────────────────────────────────────────────


class TestConstraintSpecs:
    def test_non_empty(self) -> None:
        assert len(CONSTRAINT_SPECS) > 0

    def test_all_have_required_fields(self) -> None:
        for cid, spec in CONSTRAINT_SPECS.items():
            assert spec.id == cid, f"Key mismatch: {cid} != {spec.id}"
            assert spec.given, f"{cid} missing 'given'"
            assert spec.when, f"{cid} missing 'when'"
            assert spec.then, f"{cid} missing 'then'"
            assert spec.should_not, f"{cid} missing 'should_not'"

    def test_known_constraints_present(self) -> None:
        for known_id in (
            "C-audit-never-delete", "C-review-consensus", "C-review-binary",
            "C-severity-eager", "C-dep-direction", "C-agent-commit",
            "C-worker-gates", "C-vertical-slices",
        ):
            assert known_id in CONSTRAINT_SPECS, f"Missing constraint: {known_id}"


# ─── HANDOFF_SPECS ────────────────────────────────────────────────────────────


class TestHandoffSpecs:
    def test_exactly_6_handoffs(self) -> None:
        assert len(HANDOFF_SPECS) == 6

    def test_all_handoff_ids_present(self) -> None:
        for hid in ("h1", "h2", "h3", "h4", "h5", "h6"):
            assert hid in HANDOFF_SPECS, f"Missing handoff: {hid}"

    def test_all_have_required_fields(self) -> None:
        for hid, spec in HANDOFF_SPECS.items():
            assert spec.id == hid
            assert isinstance(spec.source_role, RoleId)
            assert isinstance(spec.target_role, RoleId)
            assert isinstance(spec.at_phase, PhaseId)
            assert spec.content_level in ("full-provenance", "summary-with-ids")
            assert isinstance(spec.required_fields, tuple)
            assert len(spec.required_fields) > 0

    def test_h1_architect_to_supervisor(self) -> None:
        h1 = HANDOFF_SPECS["h1"]
        assert h1.source_role == RoleId.ARCHITECT
        assert h1.target_role == RoleId.SUPERVISOR
        assert h1.at_phase == PhaseId.P7_HANDOFF
        assert h1.content_level == "full-provenance"

    def test_h2_supervisor_to_worker(self) -> None:
        h2 = HANDOFF_SPECS["h2"]
        assert h2.source_role == RoleId.SUPERVISOR
        assert h2.target_role == RoleId.WORKER
        assert h2.at_phase == PhaseId.P9_SLICE

    def test_required_fields_are_tuple(self) -> None:
        for hid, spec in HANDOFF_SPECS.items():
            assert isinstance(spec.required_fields, tuple), (
                f"{hid} required_fields is not a tuple"
            )


# ─── Contract Tests: SLICE-2 Types ────────────────────────────────────────────
# Note: SLICE-1 type tests (SerializableTransition, SerializablePhaseSpec,
# PhaseInput, PhaseResult) are covered in tests/test_serializable_phase_spec.py.
# Duplicate tests removed per UAT amendment #6.


class TestFileWithUri:
    """Contract tests for FileWithUri (SLICE-2).

    FileWithUri(uri: str, name: str | None = None, mime_type: str | None = None)
    is a new frozen dataclass for A2A file references, replacing the flattened
    file_uri field on FilePart.
    """

    def test_importable(self) -> None:
        from aura_protocol.interfaces import FileWithUri  # noqa: F401

    def test_is_frozen(self) -> None:
        from aura_protocol.interfaces import FileWithUri

        fwu = FileWithUri(uri="https://example.com/file.txt")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            fwu.uri = "mutate"  # type: ignore[misc]

    def test_required_uri_field(self) -> None:
        from aura_protocol.interfaces import FileWithUri

        fwu = FileWithUri(uri="https://example.com/doc.md")
        assert fwu.uri == "https://example.com/doc.md"

    def test_optional_name_and_mime_type(self) -> None:
        from aura_protocol.interfaces import FileWithUri

        fwu_minimal = FileWithUri(uri="file:///tmp/x.txt")
        assert fwu_minimal.name is None
        assert fwu_minimal.mime_type is None

        fwu_full = FileWithUri(
            uri="file:///tmp/x.txt",
            name="x.txt",
            mime_type="text/plain",
        )
        assert fwu_full.name == "x.txt"
        assert fwu_full.mime_type == "text/plain"


class TestReviewAxisUsedInSignal:
    """ReviewAxis StrEnum typed on ReviewVoteSignal.axis after SLICE-2.

    SLICE-2 changed ReviewVoteSignal.axis from plain str to ReviewAxis, making
    the type system enforce valid axis identifiers. UAT amendment #7 renamed the
    enum values from A/B/C to CORRECTNESS/TEST_QUALITY/ELEGANCE with wire-format
    values "correctness"/"test_quality"/"elegance".
    """

    def test_all_three_axis_members_exist(self) -> None:
        from aura_protocol.types import ReviewAxis

        for name in ("CORRECTNESS", "TEST_QUALITY", "ELEGANCE"):
            assert hasattr(ReviewAxis, name), f"ReviewAxis.{name} not found"

    def test_is_str_enum(self) -> None:
        from aura_protocol.types import ReviewAxis

        assert isinstance(ReviewAxis.CORRECTNESS, str)
        assert isinstance(ReviewAxis.TEST_QUALITY, str)
        assert isinstance(ReviewAxis.ELEGANCE, str)

    def test_values_are_semantic_lowercase(self) -> None:
        from aura_protocol.types import ReviewAxis

        assert ReviewAxis.CORRECTNESS == "correctness"
        assert ReviewAxis.TEST_QUALITY == "test_quality"
        assert ReviewAxis.ELEGANCE == "elegance"

    def test_review_vote_signal_construction_with_review_axis(self) -> None:
        from aura_protocol.types import ReviewAxis, VoteType
        from aura_protocol.workflow import ReviewVoteSignal

        signal = ReviewVoteSignal(
            axis=ReviewAxis.CORRECTNESS,
            vote=VoteType.ACCEPT,
            reviewer_id="reviewer-1",
        )
        assert signal.axis == ReviewAxis.CORRECTNESS
        assert signal.axis == "correctness"  # StrEnum equality with str


class TestToolCallRenames:
    """ToolCall field renames after SLICE-2.

    SLICE-2 renames:
      tool_input → raw_input
      tool_output → raw_output
    And adds:
      tool_call_id: str | None = None

    These tests fail until SLICE-2 (aura-plugins-vhtx) is merged.
    """

    def test_raw_input_field_exists(self) -> None:
        from aura_protocol.interfaces import ToolCall

        tc = ToolCall(tool_name="bash", raw_input={"command": "ls"})
        assert tc.raw_input == {"command": "ls"}

    def test_raw_output_field_with_value(self) -> None:
        from aura_protocol.interfaces import ToolCall

        tc = ToolCall(tool_name="bash", raw_input={}, raw_output={"stdout": "ok"})
        assert tc.raw_output == {"stdout": "ok"}

    def test_tool_call_id_optional_defaults_none(self) -> None:
        from aura_protocol.interfaces import ToolCall

        tc = ToolCall(tool_name="bash", raw_input={})
        assert tc.tool_call_id is None

    def test_tool_call_id_can_be_set(self) -> None:
        from aura_protocol.interfaces import ToolCall

        tc = ToolCall(tool_name="bash", raw_input={}, tool_call_id="call-abc-123")
        assert tc.tool_call_id == "call-abc-123"

    def test_old_tool_input_field_removed(self) -> None:
        from aura_protocol.interfaces import ToolCall

        field_names = {f.name for f in dataclasses.fields(ToolCall)}
        assert "tool_input" not in field_names, (
            "Old field 'tool_input' should be renamed to 'raw_input' by SLICE-2"
        )

    def test_old_tool_output_field_removed(self) -> None:
        from aura_protocol.interfaces import ToolCall

        field_names = {f.name for f in dataclasses.fields(ToolCall)}
        assert "tool_output" not in field_names, (
            "Old field 'tool_output' should be renamed to 'raw_output' by SLICE-2"
        )
