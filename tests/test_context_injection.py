"""Tests for aura_protocol.context_injection.

Covers:
- AC5: get_role_context(SUPERVISOR) returns RoleContext with p7-p12 phases,
       ConstraintContext objects with typed when+then, relevant commands
- AC5a: SUPERVISOR does NOT include C-worker-gates; WORKER does NOT include C-supervisor-no-impl
- AC6: get_phase_context(P10_CODE_REVIEW) returns PhaseContext with ConstraintContext objects
       with typed when+then, severity constraints, review axes
- AC6a: P4_REVIEW does NOT include C-severity-eager; P9_SLICE does NOT include C-review-consensus
- ConstraintContext field verification: each has id, when, then populated
"""

from __future__ import annotations

import pytest

from aura_protocol.context_injection import (
    PhaseContext,
    RoleContext,
    _PHASE_CONSTRAINTS,
    _ROLE_CONSTRAINTS,
    _build_constraint_contexts,
    get_phase_context,
    get_role_context,
)
from aura_protocol.types import (
    CONSTRAINT_SPECS,
    ConstraintContext,
    PhaseId,
    RoleId,
)


# ─── AC5: Role Context Correctness (SUPERVISOR) ───────────────────────────────


class TestGetRoleContextSupervisor:
    """AC5: get_role_context(SUPERVISOR) returns correct RoleContext."""

    def test_returns_role_context_type(self) -> None:
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert isinstance(ctx, RoleContext)

    def test_role_field_is_supervisor(self) -> None:
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert ctx.role == RoleId.SUPERVISOR

    def test_phases_contains_p7_through_p12(self) -> None:
        """AC5: SUPERVISOR owns phases p7-p12 (from PHASE_SPECS.owner_roles inversion)."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        expected_phases = {
            PhaseId.P7_HANDOFF,
            PhaseId.P8_IMPL_PLAN,
            PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW,
            PhaseId.P11_IMPL_UAT,
            PhaseId.P12_LANDING,
        }
        assert ctx.phases == expected_phases

    def test_phases_does_not_include_p1_through_p6(self) -> None:
        """SUPERVISOR does not own early phases (plan phases)."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        early_phases = {
            PhaseId.P1_REQUEST,
            PhaseId.P2_ELICIT,
            PhaseId.P3_PROPOSE,
            PhaseId.P4_REVIEW,
            PhaseId.P5_UAT,
            PhaseId.P6_RATIFY,
        }
        assert ctx.phases.isdisjoint(early_phases)

    def test_constraints_is_frozenset_of_constraint_contexts(self) -> None:
        """AC5: constraints must be frozenset[ConstraintContext]."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert isinstance(ctx.constraints, frozenset)
        for c in ctx.constraints:
            assert isinstance(c, ConstraintContext)

    def test_constraints_non_empty(self) -> None:
        """SUPERVISOR has non-trivial constraints."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert len(ctx.constraints) > 0

    def test_constraints_have_when_and_then_populated(self) -> None:
        """AC5 (UAT-4): every ConstraintContext has non-empty when and then."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        for c in ctx.constraints:
            assert c.when, f"ConstraintContext {c.id!r} has empty 'when' field"
            assert c.then, f"ConstraintContext {c.id!r} has empty 'then' field"

    def test_constraints_have_id_populated(self) -> None:
        """Every ConstraintContext has a non-empty id."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        for c in ctx.constraints:
            assert c.id, "ConstraintContext has empty 'id' field"

    def test_constraints_include_supervisor_no_impl(self) -> None:
        """SUPERVISOR must be reminded not to implement code directly."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        ids = {c.id for c in ctx.constraints}
        assert "C-supervisor-no-impl" in ids

    def test_constraints_include_review_consensus(self) -> None:
        """SUPERVISOR gates transitions on review consensus."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" in ids

    def test_commands_is_tuple_of_strings(self) -> None:
        """AC5: commands must be tuple[str, ...]."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert isinstance(ctx.commands, tuple)
        for cmd in ctx.commands:
            assert isinstance(cmd, str)

    def test_commands_non_empty_for_supervisor(self) -> None:
        """SUPERVISOR has associated commands."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert len(ctx.commands) > 0

    def test_commands_contain_supervisor_command(self) -> None:
        """SUPERVISOR commands include the main aura:supervisor skill."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert "aura:supervisor" in ctx.commands

    def test_handoffs_is_tuple_of_strings(self) -> None:
        """Handoffs must be tuple[str, ...]."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert isinstance(ctx.handoffs, tuple)
        for h in ctx.handoffs:
            assert isinstance(h, str)

    def test_role_context_is_frozen(self) -> None:
        """RoleContext must be a frozen dataclass."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        with pytest.raises((AttributeError, TypeError)):
            ctx.role = RoleId.WORKER  # type: ignore[misc]


# ─── AC5a: Role Context Absence Tests ─────────────────────────────────────────


class TestRoleContextAbsence:
    """AC5a: verify constraints NOT included in role contexts."""

    def test_supervisor_excludes_c_worker_gates(self) -> None:
        """AC5a: SUPERVISOR must NOT include C-worker-gates (worker-specific)."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        ids = {c.id for c in ctx.constraints}
        assert "C-worker-gates" not in ids, (
            "SUPERVISOR context must not include C-worker-gates — "
            "that constraint is specific to the WORKER role completion gate."
        )

    def test_worker_excludes_c_supervisor_no_impl(self) -> None:
        """AC5a: WORKER must NOT include C-supervisor-no-impl (supervisor-specific)."""
        ctx = get_role_context(RoleId.WORKER)
        ids = {c.id for c in ctx.constraints}
        assert "C-supervisor-no-impl" not in ids, (
            "WORKER context must not include C-supervisor-no-impl — "
            "that constraint is specific to the SUPERVISOR role."
        )

    def test_supervisor_excludes_c_severity_eager(self) -> None:
        """SUPERVISOR is not a reviewer — should not get severity-eager reviewer-specific constraint."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" not in ids

    def test_worker_excludes_c_supervisor_cartographers(self) -> None:
        """WORKER has no Cartographers responsibility."""
        ctx = get_role_context(RoleId.WORKER)
        ids = {c.id for c in ctx.constraints}
        assert "C-supervisor-cartographers" not in ids

    def test_worker_excludes_c_review_consensus(self) -> None:
        """WORKER does not gate review consensus."""
        ctx = get_role_context(RoleId.WORKER)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" not in ids

    def test_architect_excludes_c_worker_gates(self) -> None:
        """ARCHITECT does not complete worker slices."""
        ctx = get_role_context(RoleId.ARCHITECT)
        ids = {c.id for c in ctx.constraints}
        assert "C-worker-gates" not in ids


# ─── AC6: Phase Context Correctness (P10_CODE_REVIEW) ────────────────────────


class TestGetPhaseContextCodeReview:
    """AC6: get_phase_context(P10_CODE_REVIEW) returns correct PhaseContext."""

    def test_returns_phase_context_type(self) -> None:
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert isinstance(ctx, PhaseContext)

    def test_phase_field_is_p10(self) -> None:
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert ctx.phase == PhaseId.P10_CODE_REVIEW

    def test_constraints_is_frozenset_of_constraint_contexts(self) -> None:
        """AC6: constraints must be frozenset[ConstraintContext]."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert isinstance(ctx.constraints, frozenset)
        for c in ctx.constraints:
            assert isinstance(c, ConstraintContext)

    def test_constraints_have_when_and_then_populated(self) -> None:
        """AC6 (UAT-4): every ConstraintContext has non-empty when and then."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        for c in ctx.constraints:
            assert c.when, f"ConstraintContext {c.id!r} has empty 'when' field"
            assert c.then, f"ConstraintContext {c.id!r} has empty 'then' field"

    def test_constraints_have_id_populated(self) -> None:
        """Every ConstraintContext has a non-empty id."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        for c in ctx.constraints:
            assert c.id, "ConstraintContext has empty 'id' field"

    def test_constraints_include_severity_eager(self) -> None:
        """AC6: P10_CODE_REVIEW must include C-severity-eager (code review severity rule)."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" in ids

    def test_constraints_include_review_consensus(self) -> None:
        """AC6: P10_CODE_REVIEW must include C-review-consensus."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" in ids

    def test_constraints_include_blocker_dual_parent(self) -> None:
        """AC6: P10_CODE_REVIEW must include C-blocker-dual-parent (severity constraints)."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-blocker-dual-parent" in ids

    def test_constraints_include_review_binary(self) -> None:
        """P10_CODE_REVIEW uses binary voting — review-binary applies."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-binary" in ids

    def test_labels_is_tuple_of_strings(self) -> None:
        """Labels must be tuple[str, ...]."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert isinstance(ctx.labels, tuple)
        for label in ctx.labels:
            assert isinstance(label, str)

    def test_labels_include_p10_review_label(self) -> None:
        """P10_CODE_REVIEW phase label is present."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert "aura:p10-impl:s10-review" in ctx.labels

    def test_transitions_is_tuple_of_transitions(self) -> None:
        """PhaseContext.transitions must be tuple from PHASE_SPECS."""
        from aura_protocol.types import Transition
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert isinstance(ctx.transitions, tuple)
        for t in ctx.transitions:
            assert isinstance(t, Transition)

    def test_transitions_non_empty(self) -> None:
        """P10_CODE_REVIEW has valid transitions."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        assert len(ctx.transitions) > 0

    def test_phase_context_is_frozen(self) -> None:
        """PhaseContext must be a frozen dataclass."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        with pytest.raises((AttributeError, TypeError)):
            ctx.phase = PhaseId.P9_SLICE  # type: ignore[misc]


# ─── AC6a: Phase Context Absence Tests ───────────────────────────────────────


class TestPhaseContextAbsence:
    """AC6a: verify constraints NOT included in phase contexts."""

    def test_p4_review_excludes_c_severity_eager(self) -> None:
        """AC6a: P4_REVIEW must NOT include C-severity-eager (p10-only severity rule)."""
        ctx = get_phase_context(PhaseId.P4_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" not in ids, (
            "P4_REVIEW context must not include C-severity-eager — "
            "that constraint is specific to P10_CODE_REVIEW (code review only)."
        )

    def test_p9_slice_excludes_c_review_consensus(self) -> None:
        """AC6a: P9_SLICE must NOT include C-review-consensus (review phase only)."""
        ctx = get_phase_context(PhaseId.P9_SLICE)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" not in ids, (
            "P9_SLICE context must not include C-review-consensus — "
            "that constraint only applies to review phases (p4, p10)."
        )

    def test_p4_review_excludes_c_worker_gates(self) -> None:
        """P4_REVIEW is a plan review, not a worker phase — no worker gates."""
        ctx = get_phase_context(PhaseId.P4_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-worker-gates" not in ids

    def test_p4_review_includes_c_severity_not_plan(self) -> None:
        """P4_REVIEW must include C-severity-not-plan (its complementary constraint)."""
        ctx = get_phase_context(PhaseId.P4_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-not-plan" in ids

    def test_p9_slice_excludes_c_severity_eager(self) -> None:
        """P9_SLICE is not a code review phase — no severity-eager requirement."""
        ctx = get_phase_context(PhaseId.P9_SLICE)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" not in ids

    def test_p1_request_excludes_c_severity_eager(self) -> None:
        """Early phases do not have code review constraints."""
        ctx = get_phase_context(PhaseId.P1_REQUEST)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" not in ids

    def test_p10_code_review_excludes_c_severity_not_plan(self) -> None:
        """P10_CODE_REVIEW is code review, not plan review — no severity-not-plan."""
        ctx = get_phase_context(PhaseId.P10_CODE_REVIEW)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-not-plan" not in ids


# ─── ConstraintContext Field Verification ────────────────────────────────────


class TestConstraintContextFields:
    """Verify all ConstraintContext objects have id, when, then populated."""

    @pytest.mark.parametrize("role", list(RoleId))
    def test_all_role_constraint_contexts_have_id(self, role: RoleId) -> None:
        """Every ConstraintContext returned by get_role_context has a non-empty id."""
        ctx = get_role_context(role)
        for c in ctx.constraints:
            assert c.id, f"Role {role.value}: ConstraintContext has empty 'id'"

    @pytest.mark.parametrize("role", list(RoleId))
    def test_all_role_constraint_contexts_have_when(self, role: RoleId) -> None:
        """Every ConstraintContext returned by get_role_context has a non-empty when."""
        ctx = get_role_context(role)
        for c in ctx.constraints:
            assert c.when, f"Role {role.value}: ConstraintContext {c.id!r} has empty 'when'"

    @pytest.mark.parametrize("role", list(RoleId))
    def test_all_role_constraint_contexts_have_then(self, role: RoleId) -> None:
        """Every ConstraintContext returned by get_role_context has a non-empty then."""
        ctx = get_role_context(role)
        for c in ctx.constraints:
            assert c.then, f"Role {role.value}: ConstraintContext {c.id!r} has empty 'then'"

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phase_constraint_contexts_have_id(self, phase: PhaseId) -> None:
        """Every ConstraintContext returned by get_phase_context has a non-empty id."""
        ctx = get_phase_context(phase)
        for c in ctx.constraints:
            assert c.id, f"Phase {phase.value}: ConstraintContext has empty 'id'"

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phase_constraint_contexts_have_when(self, phase: PhaseId) -> None:
        """Every ConstraintContext returned by get_phase_context has a non-empty when."""
        ctx = get_phase_context(phase)
        for c in ctx.constraints:
            assert c.when, f"Phase {phase.value}: ConstraintContext {c.id!r} has empty 'when'"

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phase_constraint_contexts_have_then(self, phase: PhaseId) -> None:
        """Every ConstraintContext returned by get_phase_context has a non-empty then."""
        ctx = get_phase_context(phase)
        for c in ctx.constraints:
            assert c.then, f"Phase {phase.value}: ConstraintContext {c.id!r} has empty 'then'"

    @pytest.mark.parametrize("role", list(RoleId))
    def test_all_role_constraint_contexts_have_given(self, role: RoleId) -> None:
        """Every ConstraintContext returned by get_role_context has a non-empty given."""
        ctx = get_role_context(role)
        for c in ctx.constraints:
            assert c.given, f"Role {role.value}: ConstraintContext {c.id!r} has empty 'given'"

    @pytest.mark.parametrize("role", list(RoleId))
    def test_all_role_constraint_contexts_have_should_not(self, role: RoleId) -> None:
        """Every ConstraintContext returned by get_role_context has a non-empty should_not."""
        ctx = get_role_context(role)
        for c in ctx.constraints:
            assert c.should_not, (
                f"Role {role.value}: ConstraintContext {c.id!r} has empty 'should_not'"
            )

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phase_constraint_contexts_have_given(self, phase: PhaseId) -> None:
        """Every ConstraintContext returned by get_phase_context has a non-empty given."""
        ctx = get_phase_context(phase)
        for c in ctx.constraints:
            assert c.given, (
                f"Phase {phase.value}: ConstraintContext {c.id!r} has empty 'given'"
            )

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phase_constraint_contexts_have_should_not(self, phase: PhaseId) -> None:
        """Every ConstraintContext returned by get_phase_context has a non-empty should_not."""
        ctx = get_phase_context(phase)
        for c in ctx.constraints:
            assert c.should_not, (
                f"Phase {phase.value}: ConstraintContext {c.id!r} has empty 'should_not'"
            )

    def test_constraint_context_given_matches_spec(self) -> None:
        """ConstraintContext.given must match the originating ConstraintSpec.given."""
        for role in RoleId:
            ctx = get_role_context(role)
            for c in ctx.constraints:
                spec = CONSTRAINT_SPECS[c.id]
                assert c.given == spec.given, (
                    f"Role {role.value}: ConstraintContext {c.id!r} given mismatch: "
                    f"{c.given!r} != {spec.given!r}"
                )

    def test_constraint_context_should_not_matches_spec(self) -> None:
        """ConstraintContext.should_not must match the originating ConstraintSpec.should_not."""
        for role in RoleId:
            ctx = get_role_context(role)
            for c in ctx.constraints:
                spec = CONSTRAINT_SPECS[c.id]
                assert c.should_not == spec.should_not, (
                    f"Role {role.value}: ConstraintContext {c.id!r} should_not mismatch: "
                    f"{c.should_not!r} != {spec.should_not!r}"
                )

    def test_constraint_context_ids_exist_in_constraint_specs(self) -> None:
        """All ConstraintContext ids in role/phase contexts are valid CONSTRAINT_SPECS keys."""
        known_ids = set(CONSTRAINT_SPECS.keys())
        for role in RoleId:
            ctx = get_role_context(role)
            for c in ctx.constraints:
                assert c.id in known_ids, (
                    f"Role {role.value}: ConstraintContext id {c.id!r} not in CONSTRAINT_SPECS"
                )
        for phase in PhaseId:
            if phase == PhaseId.COMPLETE:
                continue
            ctx = get_phase_context(phase)
            for c in ctx.constraints:
                assert c.id in known_ids, (
                    f"Phase {phase.value}: ConstraintContext id {c.id!r} not in CONSTRAINT_SPECS"
                )


# ─── Static Mapping Invariant Tests ───────────────────────────────────────────


class TestStaticMappingInvariants:
    """Verify _ROLE_CONSTRAINTS and _PHASE_CONSTRAINTS map to known constraint IDs."""

    def test_role_constraints_all_ids_known(self) -> None:
        """Every constraint ID in _ROLE_CONSTRAINTS exists in CONSTRAINT_SPECS."""
        known_ids = set(CONSTRAINT_SPECS.keys())
        for role, cids in _ROLE_CONSTRAINTS.items():
            for cid in cids:
                assert cid in known_ids, (
                    f"_ROLE_CONSTRAINTS[{role.value}] contains unknown id {cid!r}"
                )

    def test_phase_constraints_all_ids_known(self) -> None:
        """Every constraint ID in _PHASE_CONSTRAINTS exists in CONSTRAINT_SPECS."""
        known_ids = set(CONSTRAINT_SPECS.keys())
        for phase, cids in _PHASE_CONSTRAINTS.items():
            for cid in cids:
                assert cid in known_ids, (
                    f"_PHASE_CONSTRAINTS[{phase.value}] contains unknown id {cid!r}"
                )

    def test_all_roles_have_entries_in_role_constraints(self) -> None:
        """All RoleId values have entries in _ROLE_CONSTRAINTS."""
        for role in RoleId:
            assert role in _ROLE_CONSTRAINTS, (
                f"RoleId.{role.name} not found in _ROLE_CONSTRAINTS"
            )

    def test_all_12_phases_have_entries_in_phase_constraints(self) -> None:
        """All 12 protocol phases (not COMPLETE) have entries in _PHASE_CONSTRAINTS."""
        for phase in PhaseId:
            if phase == PhaseId.COMPLETE:
                continue
            assert phase in _PHASE_CONSTRAINTS, (
                f"PhaseId.{phase.name} not found in _PHASE_CONSTRAINTS"
            )

    def test_general_constraints_present_in_all_roles(self) -> None:
        """General constraints apply to ALL roles."""
        general = {"C-audit-never-delete", "C-audit-dep-chain", "C-dep-direction",
                   "C-frontmatter-refs", "C-actionable-errors"}
        for role in RoleId:
            cids = _ROLE_CONSTRAINTS[role]
            for gid in general:
                assert gid in cids, (
                    f"General constraint {gid!r} missing from _ROLE_CONSTRAINTS[{role.value}]"
                )

    def test_general_constraints_present_in_all_phases(self) -> None:
        """General constraints apply to ALL phases."""
        general = {"C-audit-never-delete", "C-audit-dep-chain", "C-dep-direction",
                   "C-frontmatter-refs", "C-actionable-errors"}
        for phase in PhaseId:
            if phase == PhaseId.COMPLETE:
                continue
            cids = _PHASE_CONSTRAINTS[phase]
            for gid in general:
                assert gid in cids, (
                    f"General constraint {gid!r} missing from _PHASE_CONSTRAINTS[{phase.value}]"
                )


# ─── Additional Integration Tests ────────────────────────────────────────────


class TestGetRoleContextWorker:
    """Verify WORKER role context is correctly scoped."""

    def test_worker_phases_is_p9_only(self) -> None:
        """WORKER only operates in P9_SLICE."""
        ctx = get_role_context(RoleId.WORKER)
        # WORKER is in P9_SLICE only (per PHASE_SPECS owner_roles).
        # EPOCH is also owner for all phases but that's EPOCH not WORKER.
        assert ctx.phases == frozenset({PhaseId.P9_SLICE})

    def test_worker_includes_c_worker_gates(self) -> None:
        """WORKER must include C-worker-gates — its quality gate constraint."""
        ctx = get_role_context(RoleId.WORKER)
        ids = {c.id for c in ctx.constraints}
        assert "C-worker-gates" in ids

    def test_worker_includes_c_agent_commit(self) -> None:
        """WORKER commits code and must use agent-commit."""
        ctx = get_role_context(RoleId.WORKER)
        ids = {c.id for c in ctx.constraints}
        assert "C-agent-commit" in ids

    def test_worker_constraint_count_is_role_scoped(self) -> None:
        """WORKER role should have 7 role-scoped constraints (not all 23)."""
        ctx = get_role_context(RoleId.WORKER)
        assert len(ctx.constraints) == 7, (
            f"Expected 7 role-scoped constraints for worker, got {len(ctx.constraints)}"
        )

    def test_supervisor_constraint_count_is_role_scoped(self) -> None:
        """SUPERVISOR role should have 18 role-scoped constraints (not all 26)."""
        ctx = get_role_context(RoleId.SUPERVISOR)
        assert len(ctx.constraints) == 18, (
            f"Expected 18 role-scoped constraints for supervisor, got {len(ctx.constraints)}"
        )


class TestGetPhaseContextAllPhases:
    """Smoke test all 12 phases return valid PhaseContext."""

    @pytest.mark.parametrize("phase", [p for p in PhaseId if p != PhaseId.COMPLETE])
    def test_all_phases_return_phase_context(self, phase: PhaseId) -> None:
        """Every protocol phase returns a valid PhaseContext."""
        ctx = get_phase_context(phase)
        assert isinstance(ctx, PhaseContext)
        assert ctx.phase == phase
        assert isinstance(ctx.constraints, frozenset)
        assert isinstance(ctx.labels, tuple)
        assert isinstance(ctx.transitions, tuple)


# ─── Positive Constraint Inclusion Tests for REVIEWER, ARCHITECT, EPOCH ───────


class TestGetRoleContextReviewer:
    """Positive constraint inclusion tests for REVIEWER role."""

    def test_reviewer_includes_c_severity_eager(self) -> None:
        """REVIEWER must include C-severity-eager (p10 code review creates severity tree)."""
        ctx = get_role_context(RoleId.REVIEWER)
        ids = {c.id for c in ctx.constraints}
        assert "C-severity-eager" in ids

    def test_reviewer_includes_c_review_binary(self) -> None:
        """REVIEWER must include C-review-binary (binary ACCEPT/REVISE voting)."""
        ctx = get_role_context(RoleId.REVIEWER)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-binary" in ids

    def test_reviewer_includes_c_review_consensus(self) -> None:
        """REVIEWER must include C-review-consensus (all reviewers must agree)."""
        ctx = get_role_context(RoleId.REVIEWER)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" in ids

    def test_reviewer_includes_c_blocker_dual_parent(self) -> None:
        """REVIEWER must include C-blocker-dual-parent (BLOCKER findings need dual parents)."""
        ctx = get_role_context(RoleId.REVIEWER)
        ids = {c.id for c in ctx.constraints}
        assert "C-blocker-dual-parent" in ids


class TestGetRoleContextArchitect:
    """Positive constraint inclusion tests for ARCHITECT role."""

    def test_architect_includes_c_proposal_naming(self) -> None:
        """ARCHITECT must include C-proposal-naming (creates proposals with naming convention)."""
        ctx = get_role_context(RoleId.ARCHITECT)
        ids = {c.id for c in ctx.constraints}
        assert "C-proposal-naming" in ids


class TestGetRoleContextEpoch:
    """Positive constraint inclusion tests for EPOCH role."""

    def test_epoch_includes_c_review_consensus(self) -> None:
        """EPOCH must include C-review-consensus (gates phase transitions on consensus)."""
        ctx = get_role_context(RoleId.EPOCH)
        ids = {c.id for c in ctx.constraints}
        assert "C-review-consensus" in ids

    def test_epoch_includes_c_handoff_skill_invocation(self) -> None:
        """EPOCH must include C-handoff-skill-invocation (master orchestrator creates handoffs)."""
        ctx = get_role_context(RoleId.EPOCH)
        ids = {c.id for c in ctx.constraints}
        assert "C-handoff-skill-invocation" in ids


# ─── Error Handling: _build_constraint_contexts ────────────────────────────────


class TestBuildConstraintContextsErrorHandling:
    """_build_constraint_contexts raises KeyError on unknown constraint IDs."""

    def test_raises_key_error_on_unknown_constraint_id(self) -> None:
        """Unknown constraint ID must raise KeyError with actionable message."""
        with pytest.raises(KeyError, match="not found in CONSTRAINT_SPECS"):
            _build_constraint_contexts(frozenset({"C-nonexistent-constraint-xyz"}))
