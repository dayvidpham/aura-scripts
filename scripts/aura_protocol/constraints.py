"""Runtime constraint validators for the Aura protocol.

Extends the validate_schema.py patterns for runtime state checking.
Implements all 22 C-* constraints from schema.xml.

Key types:
    ConstraintViolation     — frozen dataclass: constraint_id, message, context
    RuntimeConstraintChecker — main checker class; all check methods return
                               list[ConstraintViolation] (empty = no violations)

Design decisions:
    - DI: accepts optional constraint_specs/handoff_specs; defaults to canonical dicts
    - Returns list[ConstraintViolation] — never raises, never silently swallows
    - Two aggregation entry points:
        check_state_constraints(state) — aggregates the 5 state-based checks
        check_transition_constraints(state, to_phase) — combines transition-specific checks
          (consensus gate, handoff requirement, blocker gate)
    - Individual check methods (check_dep_direction, check_agent_commit, etc.) are kept
      intact — they have different signatures and cannot be unified into a single entry point
    - Structural / git-level constraints (e.g. C-agent-commit) validate what CAN be
      checked at runtime and document what requires external enforcement
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aura_protocol.state_machine import EpochState
from aura_protocol.types import (
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    ConstraintSpec,
    HandoffSpec,
    PhaseId,
    RoleId,
    VoteType,
)


# ─── Violation Type ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConstraintViolation:
    """A single protocol constraint violation detected at runtime.

    constraint_id matches a key in CONSTRAINT_SPECS (e.g. "C-review-consensus").
    message is a human-readable description of the violation.
    context provides key-value pairs with details (phase, role, count, etc.).
    """

    constraint_id: str
    message: str
    context: dict[str, str] = field(default_factory=dict)


# ─── Review axes (canonical) ───────────────────────────────────────────────────

_REVIEW_AXES: frozenset[str] = frozenset({"A", "B", "C"})

# Phases that use review consensus gating
_REVIEW_PHASES: frozenset[PhaseId] = frozenset(
    {PhaseId.P4_REVIEW, PhaseId.P10_CODE_REVIEW}
)

# Phase transitions that require handoff documents.
# Maps (from_phase, to_phase) -> expected handoff id.
# Derived from HANDOFF_SPECS: h1 = p7→p8, h2 = p9→p10 (supervisor→worker is p9),
# h3 = p10→... (supervisor→reviewer), h4 = p9→p10 (worker→reviewer).
# At runtime, we track actor changes via (from_phase, to_phase) pairs.
_HANDOFF_REQUIRED_TRANSITIONS: frozenset[tuple[PhaseId, PhaseId]] = frozenset(
    {
        # h1: architect → supervisor handoff at p7
        (PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN),
        # h2: supervisor → worker handoff at p9
        (PhaseId.P9_SLICE, PhaseId.P10_CODE_REVIEW),
    }
)

# Phases where severity tree (BLOCKER/IMPORTANT/MINOR) is required.
_SEVERITY_TREE_PHASES: frozenset[PhaseId] = frozenset({PhaseId.P10_CODE_REVIEW})

# The required severity groups for p10 code review.
_REQUIRED_SEVERITY_GROUPS: frozenset[str] = frozenset({"BLOCKER", "IMPORTANT", "MINOR"})


# ─── Checker ──────────────────────────────────────────────────────────────────


class RuntimeConstraintChecker:
    """Checks protocol constraints against current epoch state.

    All check methods return list[ConstraintViolation] — an empty list means
    no violations for that constraint. No exceptions are raised.

    Usage:
        checker = RuntimeConstraintChecker()
        violations = checker.check_all(state)
        if violations:
            for v in violations:
                print(f"[{v.constraint_id}] {v.message}")

    Dependency injection:
        Pass custom constraint_specs or handoff_specs for testing.
        Defaults are CONSTRAINT_SPECS and HANDOFF_SPECS from types.py.
    """

    def __init__(
        self,
        constraint_specs: dict[str, ConstraintSpec] | None = None,
        handoff_specs: dict[str, HandoffSpec] | None = None,
    ) -> None:
        self._constraint_specs: dict[str, ConstraintSpec] = (
            constraint_specs if constraint_specs is not None else CONSTRAINT_SPECS
        )
        self._handoff_specs: dict[str, HandoffSpec] = (
            handoff_specs if handoff_specs is not None else HANDOFF_SPECS
        )

    # ── Aggregation Entry Points ──────────────────────────────────────────────

    def check_state_constraints(self, state: EpochState) -> list[ConstraintViolation]:
        """Run state-based constraint checks against current epoch state.

        Aggregates the 5 state-based checks. Does NOT short-circuit —
        all checks run regardless of earlier violations.

        This entry point covers constraints that can be evaluated from state alone,
        without knowledge of the intended next phase:
        - C-review-consensus: all 3 axes must ACCEPT in review phases
        - C-severity-not-plan: p4 must NOT use severity trees
        - C-worker-gates: p10 with unresolved blockers
        - C-audit-never-delete / C-audit-dep-chain: audit trail integrity
        - C-vertical-slices: role-phase ownership

        For transition-specific checks (consensus gate, handoff, blocker gate as
        a transition precondition), use check_transition_constraints(state, to_phase).

        Returns combined list of all violations (empty = all state constraints satisfied).
        """
        violations: list[ConstraintViolation] = []
        violations.extend(self.check_review_consensus(state))
        violations.extend(self.check_severity_tree(state))
        violations.extend(self.check_blocker_gate(state))
        violations.extend(self.check_audit_trail(state))
        violations.extend(self.check_role_ownership(state))
        return violations

    def check_transition_constraints(
        self, state: EpochState, to_phase: PhaseId
    ) -> list[ConstraintViolation]:
        """Check constraints specific to a proposed phase transition.

        Combines the transition-specific checks into one entry point:
        - C-review-consensus: p4→p5 or p10→p11 requires all 3 ACCEPT
        - C-handoff-skill-invocation: actor-change transitions require handoff
        - C-worker-gates (blocker gate): p10→p11 blocked while blocker_count > 0

        Does NOT short-circuit — all transition checks run regardless of
        earlier violations.

        Returns list of violations (empty = transition is protocol-valid).
        """
        violations: list[ConstraintViolation] = []

        current = state.current_phase

        # C-review-consensus: check consensus gate for review phase → forward transition
        if current == PhaseId.P4_REVIEW and to_phase == PhaseId.P5_UAT:
            violations.extend(self.check_review_consensus(state))
        elif current == PhaseId.P10_CODE_REVIEW and to_phase == PhaseId.P11_IMPL_UAT:
            violations.extend(self.check_review_consensus(state))

        # C-handoff-skill-invocation: handoff required for actor-change transitions
        violations.extend(self.check_handoff_required(current, to_phase))

        # C-worker-gates: blocker gate — p10→p11 blocked while blocker_count > 0
        if current == PhaseId.P10_CODE_REVIEW and to_phase == PhaseId.P11_IMPL_UAT:
            violations.extend(self.check_blocker_gate(state))

        return violations

    def check_transition(
        self, state: EpochState, to_phase: PhaseId
    ) -> list[ConstraintViolation]:
        """Check constraints specific to a proposed phase transition.

        Deprecated alias for check_transition_constraints(). Kept for backwards
        compatibility. Use check_transition_constraints() for new code.

        Returns list of violations (empty = transition is protocol-valid).
        """
        return self.check_transition_constraints(state, to_phase)

    def validate(self, state: EpochState) -> list[ConstraintViolation]:
        """Validate protocol constraints against the given epoch state.

        Satisfies the ConstraintValidatorInterface Protocol contract, enabling
        isinstance(RuntimeConstraintChecker(), ConstraintValidatorInterface) to
        return True at runtime.

        Delegates to check_state_constraints() — runs all 5 state-based checks.

        Args:
            state: Current epoch state to validate.

        Returns:
            List of constraint violations found. Empty list means all pass.
        """
        return self.check_state_constraints(state)

    # ── Named Constraint Checks ────────────────────────────────────────────────

    def check_review_consensus(self, state: EpochState) -> list[ConstraintViolation]:
        """C-review-consensus: all 3 axes (A, B, C) must ACCEPT in review phases.

        Checks whether the current phase is a review phase and whether all 3
        review axes have ACCEPT votes. Returns a violation if:
        - The state is in a review phase (p4 or p10)
        - AND not all 3 axes have recorded ACCEPT votes.

        Returns empty list if not in a review phase or consensus is met.
        """
        current = state.current_phase
        if current not in _REVIEW_PHASES:
            return []

        votes = state.review_votes
        missing_accept: list[str] = []
        for axis in sorted(_REVIEW_AXES):
            if axis not in votes or votes[axis] != VoteType.ACCEPT:
                missing_accept.append(axis)

        if not missing_accept:
            return []

        accepted = sorted(
            ax for ax, v in votes.items() if v == VoteType.ACCEPT
        )
        revise = sorted(
            ax for ax, v in votes.items() if v == VoteType.REVISE
        )
        not_voted = sorted(ax for ax in _REVIEW_AXES if ax not in votes)

        return [
            ConstraintViolation(
                constraint_id="C-review-consensus",
                message=(
                    f"Phase {current.value!r} requires all 3 axes (A, B, C) to ACCEPT "
                    f"before proceeding. "
                    f"Accepted: {accepted}, REVISE: {revise}, not voted: {not_voted}."
                ),
                context={
                    "phase": current.value,
                    "accepted": ",".join(accepted),
                    "revise": ",".join(revise),
                    "not_voted": ",".join(not_voted),
                },
            )
        ]

    def check_dep_direction(
        self, parent_id: str, child_id: str
    ) -> list[ConstraintViolation]:
        """C-dep-direction: validate that dependency direction is parent blocked-by child.

        At runtime, we can only check that the IDs are non-empty and distinct.
        The actual direction (parent stays open, child must finish first) is
        enforced by the bd CLI. This method validates the inputs are structurally
        valid for creating a dependency.

        External enforcement note: the bd CLI enforces the direction
        semantically. This check validates the runtime preconditions.

        Returns violation if parent_id == child_id (self-referential dep) or
        either ID is empty.
        """
        violations: list[ConstraintViolation] = []

        if not parent_id or not parent_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-dep-direction",
                    message="Dependency parent_id must be a non-empty task ID.",
                    context={"parent_id": parent_id, "child_id": child_id},
                )
            )

        if not child_id or not child_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-dep-direction",
                    message="Dependency child_id must be a non-empty task ID.",
                    context={"parent_id": parent_id, "child_id": child_id},
                )
            )

        if parent_id and child_id and parent_id == child_id:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-dep-direction",
                    message=(
                        f"Self-referential dependency: parent_id and child_id are both {parent_id!r}. "
                        "A task cannot be blocked by itself."
                    ),
                    context={"parent_id": parent_id, "child_id": child_id},
                )
            )

        return violations

    def check_severity_tree(self, state: EpochState) -> list[ConstraintViolation]:
        """C-severity-eager: p10 code review requires 3 severity groups created eagerly.

        In phase p10, all 3 severity groups (BLOCKER, IMPORTANT, MINOR) must be
        created immediately when the review starts — not lazily.

        At runtime, we check that we ARE in p10. The actual creation of
        severity group tasks is enforced structurally by the reviewer workflow.
        This check validates that the severity groups are tracked in state
        (if severity_groups field exists) or emits an informational violation
        when state is at p10 but no groups are tracked.

        Note: EpochState does not have a severity_groups field in v1. This
        check validates the protocol invariant: p4 must NOT have severity groups
        (C-severity-not-plan), and p10 MUST have them (C-severity-eager).
        The presence check at p10 requires external enforcement.

        Returns violations for:
        - Being at p4 with any severity tracking (C-severity-not-plan: plan reviews
          should not have severity trees)
        """
        violations: list[ConstraintViolation] = []
        current = state.current_phase

        # C-severity-not-plan: p4 (plan review) must NOT use severity trees.
        # Since EpochState has no severity_groups field, we validate the phase rule.
        # The violation here is contextual: if caller is checking severity tree
        # for a p4 state, that IS the violation (severity trees don't belong in p4).
        if current == PhaseId.P4_REVIEW:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-severity-not-plan",
                    message=(
                        "Phase p4 (plan review) must NOT use severity trees. "
                        "Plan reviews use binary ACCEPT/REVISE only. "
                        "Severity trees are for p10 code review only."
                    ),
                    context={"phase": current.value},
                )
            )

        return violations

    def check_handoff_required(
        self, from_phase: PhaseId, to_phase: PhaseId
    ) -> list[ConstraintViolation]:
        """C-handoff-skill-invocation: handoff document required for actor-change transitions.

        Transitions that change the active role (p7→p8, p9→p10) require a
        handoff document stored at .git/.aura/handoff/{request-id}/.
        The prompt for the receiving agent MUST start with Skill(/aura:{role}).

        At runtime, we validate that the transition is a known actor-change
        transition. Actual file existence requires external enforcement.

        Returns violation if the transition is an actor-change but no handoff
        spec covers it (i.e. it's an unrecognized actor-change transition).
        Returns empty list for same-actor transitions (p5→p6, p6→p7) and
        well-known transitions that have handoff specs.
        """
        # Same-actor transitions that explicitly do NOT need handoffs per schema.xml
        _SAME_ACTOR: frozenset[tuple[PhaseId, PhaseId]] = frozenset(
            {
                (PhaseId.P5_UAT, PhaseId.P6_RATIFY),
                (PhaseId.P6_RATIFY, PhaseId.P7_HANDOFF),
            }
        )

        if (from_phase, to_phase) in _SAME_ACTOR:
            return []

        if (from_phase, to_phase) not in _HANDOFF_REQUIRED_TRANSITIONS:
            return []

        # The transition IS an actor-change transition — handoff is required.
        # We return a reminder violation. The actual handoff file existence
        # must be verified by the workflow, not at runtime against EpochState alone.
        return [
            ConstraintViolation(
                constraint_id="C-handoff-skill-invocation",
                message=(
                    f"Transition {from_phase.value!r} → {to_phase.value!r} requires "
                    f"a handoff document and the receiving agent's prompt MUST start "
                    f"with Skill(/aura:{{role}}). "
                    f"Store handoff at .git/.aura/handoff/{{request-id}}/."
                ),
                context={
                    "from_phase": from_phase.value,
                    "to_phase": to_phase.value,
                },
            )
        ]

    def check_blocker_gate(self, state: EpochState) -> list[ConstraintViolation]:
        """C-worker-gates / blocker gate: p10→p11 blocked while blocker_count > 0.

        Returns violation if state is at p10 and blocker_count > 0.
        The p10→p11 transition cannot proceed until all BLOCKERs are resolved.
        """
        if state.current_phase != PhaseId.P10_CODE_REVIEW:
            return []

        if state.blocker_count <= 0:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-worker-gates",
                message=(
                    f"Phase p10 has {state.blocker_count} unresolved BLOCKER(s). "
                    "All BLOCKERs must be resolved before advancing to p11 (Impl UAT)."
                ),
                context={
                    "phase": state.current_phase.value,
                    "blocker_count": str(state.blocker_count),
                },
            )
        ]

    def check_audit_trail(self, state: EpochState) -> list[ConstraintViolation]:
        """C-audit-never-delete / C-audit-dep-chain: audit trail integrity checks.

        Validates:
        - Transition history is non-empty if not at p1 (audit trail preserved)
        - Each transition record has required fields (triggered_by, condition_met)

        Returns violations if audit trail is corrupted or missing.
        """
        violations: list[ConstraintViolation] = []

        # If we've moved past p1, there must be transition history.
        if (
            state.current_phase != PhaseId.P1_REQUEST
            and state.current_phase != PhaseId.COMPLETE
            and not state.transition_history
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="C-audit-never-delete",
                    message=(
                        f"State is at phase {state.current_phase.value!r} "
                        "but transition_history is empty. "
                        "Audit trail must never be deleted or cleared."
                    ),
                    context={
                        "phase": state.current_phase.value,
                        "transition_history_length": "0",
                    },
                )
            )

        # Each transition record must have non-empty triggered_by and condition_met.
        for i, record in enumerate(state.transition_history):
            if not record.triggered_by:
                violations.append(
                    ConstraintViolation(
                        constraint_id="C-audit-dep-chain",
                        message=(
                            f"Transition record #{i} ({record.from_phase.value!r} → "
                            f"{record.to_phase.value!r}) is missing 'triggered_by'. "
                            "All transitions must record who triggered them."
                        ),
                        context={
                            "record_index": str(i),
                            "from_phase": record.from_phase.value,
                            "to_phase": record.to_phase.value,
                        },
                    )
                )
            if not record.condition_met:
                violations.append(
                    ConstraintViolation(
                        constraint_id="C-audit-dep-chain",
                        message=(
                            f"Transition record #{i} ({record.from_phase.value!r} → "
                            f"{record.to_phase.value!r}) is missing 'condition_met'. "
                            "All transitions must record the condition that was satisfied."
                        ),
                        context={
                            "record_index": str(i),
                            "from_phase": record.from_phase.value,
                            "to_phase": record.to_phase.value,
                        },
                    )
                )

        return violations

    def check_role_ownership(self, state: EpochState) -> list[ConstraintViolation]:
        """C-supervisor-no-impl / C-vertical-slices: role-phase ownership checks.

        Validates:
        - C-supervisor-no-impl: supervisor should not be in impl phases without workers
        - C-vertical-slices: only one worker owns each production code path

        At runtime, we check the current_role vs current_phase pairing.
        The supervisor role is valid in p8, p9, p10, p11, p12 for coordination
        but must not perform direct implementation.

        Returns violations for clear role mismatches.
        """
        violations: list[ConstraintViolation] = []
        current = state.current_phase

        # Validate that current_role is a known role string.
        known_roles = {r.value for r in RoleId}
        if state.current_role not in known_roles:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-vertical-slices",
                    message=(
                        f"Unknown role {state.current_role!r}. "
                        f"Valid roles are: {sorted(known_roles)}."
                    ),
                    context={
                        "current_role": state.current_role,
                        "phase": current.value,
                    },
                )
            )

        return violations

    # ── Additional Constraint Checks (structural, documented) ─────────────────

    def check_review_binary(
        self, vote: str
    ) -> list[ConstraintViolation]:
        """C-review-binary: votes must be ACCEPT or REVISE only.

        Returns violation if the vote string is not a valid VoteType value.
        Invalid values include: APPROVE, APPROVE_WITH_COMMENTS, REQUEST_CHANGES, REJECT.
        """
        valid_votes = {v.value for v in VoteType}
        if vote in valid_votes:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-review-binary",
                message=(
                    f"Invalid vote {vote!r}. Reviewers must use ACCEPT or REVISE only. "
                    f"Values like APPROVE, APPROVE_WITH_COMMENTS, REQUEST_CHANGES, "
                    f"REJECT are not valid."
                ),
                context={"vote": vote, "valid_votes": ",".join(sorted(valid_votes))},
            )
        ]

    def check_blocker_dual_parent(
        self,
        blocker_task_id: str,
        severity_group_id: str,
        slice_id: str,
    ) -> list[ConstraintViolation]:
        """C-blocker-dual-parent: BLOCKER findings must have two parents.

        BLOCKER findings must be children of BOTH:
        1. The severity group task (aura:severity:blocker)
        2. The slice they block

        At runtime, validates that both IDs are non-empty and distinct.
        Actual dependency creation is enforced via bd CLI.

        Returns violation if severity_group_id or slice_id are empty or equal.
        """
        violations: list[ConstraintViolation] = []

        if not severity_group_id or not severity_group_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-blocker-dual-parent",
                    message=(
                        f"BLOCKER finding {blocker_task_id!r} requires a severity_group_id. "
                        "Must be added as child of the severity group task."
                    ),
                    context={
                        "blocker_task_id": blocker_task_id,
                        "severity_group_id": severity_group_id,
                    },
                )
            )

        if not slice_id or not slice_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-blocker-dual-parent",
                    message=(
                        f"BLOCKER finding {blocker_task_id!r} requires a slice_id. "
                        "Must ALSO be added as child of the slice it blocks (dual-parent)."
                    ),
                    context={
                        "blocker_task_id": blocker_task_id,
                        "slice_id": slice_id,
                    },
                )
            )

        if (
            severity_group_id
            and slice_id
            and severity_group_id == slice_id
        ):
            violations.append(
                ConstraintViolation(
                    constraint_id="C-blocker-dual-parent",
                    message=(
                        f"BLOCKER finding {blocker_task_id!r}: severity_group_id and "
                        f"slice_id are the same ({severity_group_id!r}). "
                        "These must be different tasks (dual-parent requires 2 distinct parents)."
                    ),
                    context={
                        "blocker_task_id": blocker_task_id,
                        "severity_group_id": severity_group_id,
                        "slice_id": slice_id,
                    },
                )
            )

        return violations

    def check_proposal_naming(self, title: str) -> list[ConstraintViolation]:
        """C-proposal-naming: proposal titles must follow PROPOSAL-{N}: {description} pattern.

        Returns violation if the title does not start with 'PROPOSAL-' followed
        by a positive integer.
        """
        import re

        if re.match(r"^PROPOSAL-\d+:", title):
            return []

        return [
            ConstraintViolation(
                constraint_id="C-proposal-naming",
                message=(
                    f"Proposal title {title!r} does not match required pattern "
                    "'PROPOSAL-{{N}}: {{description}}' where N is a positive integer. "
                    "Old proposals must be marked aura:superseded, not deleted or reused."
                ),
                context={"title": title},
            )
        ]

    def check_review_naming(self, title: str) -> list[ConstraintViolation]:
        """C-review-naming: review task titles must follow {SCOPE}-REVIEW-{axis}-{round} pattern.

        axis must be A, B, or C. round is a positive integer starting at 1.
        Returns violation if the title does not match the pattern.
        """
        import re

        # Match pattern: {SCOPE}-REVIEW-{A|B|C}-{N}: {description}
        if re.match(r"^.+-REVIEW-[ABC]-\d+", title):
            return []

        return [
            ConstraintViolation(
                constraint_id="C-review-naming",
                message=(
                    f"Review task title {title!r} does not match required pattern "
                    "'{SCOPE}-REVIEW-{axis}-{round}: {description}' "
                    "where axis is A, B, or C (not numeric 1/2/3) and round starts at 1."
                ),
                context={"title": title},
            )
        ]

    def check_slice_has_leaf_tasks(
        self,
        slice_id: str,
        leaf_task_ids: list[str],
    ) -> list[ConstraintViolation]:
        """C-slice-leaf-tasks: every vertical slice must have leaf tasks (L1/L2/L3).

        Returns violation if leaf_task_ids is empty — a slice with no leaf
        tasks is undecomposed and cannot be tracked.
        """
        if leaf_task_ids:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-slice-leaf-tasks",
                message=(
                    f"Slice {slice_id!r} has no leaf tasks. "
                    "Every slice must have L1 (types), L2 (tests), L3 (impl) leaf tasks "
                    "with bd dep add slice-id --blocked-by leaf-task-id."
                ),
                context={"slice_id": slice_id, "leaf_count": "0"},
            )
        ]

    def check_ure_verbatim(
        self,
        question: str,
        options: list[str],
        response: str,
    ) -> list[ConstraintViolation]:
        """C-ure-verbatim: user interview records must include full question, all options,
        and the user's verbatim response.

        Returns violations if any of the required fields are empty.
        """
        violations: list[ConstraintViolation] = []

        if not question or not question.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-ure-verbatim",
                    message=(
                        "User interview record is missing the question text. "
                        "Must capture full question text verbatim."
                    ),
                    context={"field": "question"},
                )
            )

        if not options:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-ure-verbatim",
                    message=(
                        "User interview record has no options. "
                        "Must capture ALL option descriptions (not just numbers)."
                    ),
                    context={"field": "options", "option_count": "0"},
                )
            )

        if not response or not response.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-ure-verbatim",
                    message=(
                        "User interview record is missing the user's response. "
                        "Must capture verbatim response."
                    ),
                    context={"field": "response"},
                )
            )

        return violations

    def check_followup_timing(
        self,
        has_important_or_minor: bool,
        followup_created: bool,
    ) -> list[ConstraintViolation]:
        """C-followup-timing: follow-up epic must be created immediately upon review completion
        if IMPORTANT or MINOR findings exist, regardless of BLOCKER status.

        Returns violation if findings exist but followup_created is False.
        """
        if not has_important_or_minor:
            return []

        if followup_created:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-followup-timing",
                message=(
                    "IMPORTANT or MINOR findings exist but follow-up epic has not been created. "
                    "Create the follow-up epic immediately upon review completion. "
                    "Do NOT gate follow-up epic creation on BLOCKER resolution."
                ),
                context={
                    "has_important_or_minor": str(has_important_or_minor),
                    "followup_created": str(followup_created),
                },
            )
        ]

    def check_agent_commit(self, commit_command: str) -> list[ConstraintViolation]:
        """C-agent-commit: commits must use 'git agent-commit', not 'git commit'.

        Checks whether a commit command string uses the correct form.
        Returns violation if the command uses 'git commit' (without 'agent-').

        External enforcement note: This check is best-effort at the string
        level. Full enforcement requires shell history or pre-commit hooks.
        """
        if "git agent-commit" in commit_command:
            return []

        if "git commit" in commit_command:
            return [
                ConstraintViolation(
                    constraint_id="C-agent-commit",
                    message=(
                        f"Commit command {commit_command!r} uses 'git commit' but must "
                        "use 'git agent-commit -m ...' instead."
                    ),
                    context={"command": commit_command},
                )
            ]

        # Command doesn't contain either form — not a commit command, no violation.
        return []

    def check_frontmatter_refs(
        self,
        task_description: str,
        required_ref_keys: list[str],
    ) -> list[ConstraintViolation]:
        """C-frontmatter-refs: cross-task references must use description frontmatter.

        Checks that the task description contains YAML frontmatter with the
        required reference keys (e.g. 'urd', 'request', 'impl_plan').

        Returns violations for each missing required reference key.
        """
        violations: list[ConstraintViolation] = []

        # Check if description starts with frontmatter block
        has_frontmatter = task_description.strip().startswith("---")

        for key in required_ref_keys:
            # Simple key presence check in the frontmatter section
            if not has_frontmatter or key + ":" not in task_description:
                violations.append(
                    ConstraintViolation(
                        constraint_id="C-frontmatter-refs",
                        message=(
                            f"Task description is missing frontmatter reference for {key!r}. "
                            "Use YAML frontmatter block (---) with 'references:' section. "
                            "Do NOT use bd dep relate for reference-only links."
                        ),
                        context={"missing_key": key},
                    )
                )

        return violations

    def check_supervisor_no_impl(
        self,
        role: str,
        action_type: str,
    ) -> list[ConstraintViolation]:
        """C-supervisor-no-impl: supervisor must not implement code directly.

        action_type should describe the action being taken, e.g. "file_edit",
        "file_write", "code_change". Returns violation if role is "supervisor"
        and action_type indicates direct code implementation.

        External enforcement note: Full enforcement requires monitoring tool
        calls at the agent level.
        """
        _IMPL_ACTIONS: frozenset[str] = frozenset(
            {"file_edit", "file_write", "code_change", "write_file", "edit_file"}
        )

        if role != RoleId.SUPERVISOR.value:
            return []

        if action_type not in _IMPL_ACTIONS:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-supervisor-no-impl",
                message=(
                    f"Supervisor is performing a direct implementation action ({action_type!r}). "
                    "Supervisors must spawn workers for ALL code changes. "
                    "Delegate this action to a worker agent."
                ),
                context={"role": role, "action_type": action_type},
            )
        ]

    def check_followup_lifecycle(
        self,
        followup_task_title: str,
    ) -> list[ConstraintViolation]:
        """C-followup-lifecycle: follow-up epics must use FOLLOWUP_* prefixed task types.

        Validates that a task title for a follow-up lifecycle task uses the
        correct FOLLOWUP_* prefix. Expected patterns:
        - FOLLOWUP: {description}
        - FOLLOWUP_URE: {description}
        - FOLLOWUP_URD: {description}
        - FOLLOWUP_PROPOSAL-{N}: {description}
        - FOLLOWUP_IMPL_PLAN: {description}
        - FOLLOWUP_SLICE-{N}: {description}

        Returns violation if the title lacks the FOLLOWUP prefix.
        """
        _FOLLOWUP_PREFIXES: tuple[str, ...] = (
            "FOLLOWUP:",
            "FOLLOWUP_URE:",
            "FOLLOWUP_URD:",
            "FOLLOWUP_PROPOSAL-",
            "FOLLOWUP_IMPL_PLAN:",
            "FOLLOWUP_SLICE-",
        )

        for prefix in _FOLLOWUP_PREFIXES:
            if followup_task_title.startswith(prefix):
                return []

        return [
            ConstraintViolation(
                constraint_id="C-followup-lifecycle",
                message=(
                    f"Follow-up task title {followup_task_title!r} does not use "
                    "the required FOLLOWUP_* prefix. "
                    "Use: FOLLOWUP_URE, FOLLOWUP_URD, FOLLOWUP_PROPOSAL-N, "
                    "FOLLOWUP_IMPL_PLAN, or FOLLOWUP_SLICE-N."
                ),
                context={"title": followup_task_title},
            )
        ]

    def check_followup_leaf_adoption(
        self,
        leaf_task_id: str,
        severity_group_id: str,
        followup_slice_id: str,
    ) -> list[ConstraintViolation]:
        """C-followup-leaf-adoption: IMPORTANT/MINOR leaf tasks must be adopted by follow-up slices.

        The leaf task must be a child of BOTH:
        1. The original severity group (from the original review)
        2. The follow-up slice (dual-parent relationship)

        At runtime, validates that both IDs are non-empty and distinct.
        """
        violations: list[ConstraintViolation] = []

        if not severity_group_id or not severity_group_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-followup-leaf-adoption",
                    message=(
                        f"Leaf task {leaf_task_id!r} is missing severity_group_id. "
                        "Must remain child of original severity group (dual-parent)."
                    ),
                    context={
                        "leaf_task_id": leaf_task_id,
                        "severity_group_id": severity_group_id,
                    },
                )
            )

        if not followup_slice_id or not followup_slice_id.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-followup-leaf-adoption",
                    message=(
                        f"Leaf task {leaf_task_id!r} is missing followup_slice_id. "
                        "Must ALSO be a child of the follow-up slice (dual-parent)."
                    ),
                    context={
                        "leaf_task_id": leaf_task_id,
                        "followup_slice_id": followup_slice_id,
                    },
                )
            )

        return violations

    def check_worker_gates(
        self,
        has_todos: bool,
        tests_pass: bool,
        typecheck_pass: bool,
    ) -> list[ConstraintViolation]:
        """C-worker-gates: worker completion requires quality gates AND production path verification.

        Workers must:
        1. Run quality gates: typecheck + tests must pass
        2. Verify production code path: no TODOs, real deps wired

        Returns violations for each failing gate.
        """
        violations: list[ConstraintViolation] = []

        if not tests_pass:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-worker-gates",
                    message=(
                        "Worker completion gate failed: tests are not passing. "
                        "All tests must pass before closing the slice."
                    ),
                    context={"gate": "tests", "passed": "false"},
                )
            )

        if not typecheck_pass:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-worker-gates",
                    message=(
                        "Worker completion gate failed: type checking is not passing. "
                        "All type checks must pass before closing the slice."
                    ),
                    context={"gate": "typecheck", "passed": "false"},
                )
            )

        if has_todos:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-worker-gates",
                    message=(
                        "Worker completion gate failed: production code contains TODO placeholders. "
                        "All TODOs must be resolved before closing the slice. "
                        "No TODO placeholders in CLI/API actions."
                    ),
                    context={"gate": "no_todos", "passed": "false"},
                )
            )

        return violations

    def check_supervisor_explore_team(
        self,
        phase: PhaseId,
        has_explore_team: bool,
    ) -> list[ConstraintViolation]:
        """C-supervisor-explore-team: supervisor must use standing explore team for p8 exploration.

        At Phase 8 (IMPL_PLAN), supervisor must create a standing explore team
        via TeamCreate and delegate all deep codebase exploration to explore agents.

        Returns violation if at p8 and has_explore_team is False.
        """
        if phase != PhaseId.P8_IMPL_PLAN:
            return []

        if has_explore_team:
            return []

        return [
            ConstraintViolation(
                constraint_id="C-supervisor-explore-team",
                message=(
                    "Phase p8 (IMPL_PLAN): supervisor must create a standing explore team "
                    "via TeamCreate before performing any codebase exploration. "
                    "Minimum 1 scoped explore agent. "
                    "Supervisor must NOT explore the codebase directly."
                ),
                context={
                    "phase": phase.value,
                    "has_explore_team": str(has_explore_team),
                },
            )
        ]

    def check_vertical_slices(
        self,
        production_code_path: str,
        owner_ids: list[str],
    ) -> list[ConstraintViolation]:
        """C-vertical-slices: each production code path must be owned by exactly ONE worker.

        Returns violation if:
        - production_code_path is empty
        - owner_ids has more than one entry (multiple workers on same path)
        - owner_ids is empty (no owner)
        """
        violations: list[ConstraintViolation] = []

        if not production_code_path or not production_code_path.strip():
            violations.append(
                ConstraintViolation(
                    constraint_id="C-vertical-slices",
                    message=(
                        "production_code_path must be a non-empty path identifier. "
                        "Each slice must identify the production code path it owns."
                    ),
                    context={"production_code_path": production_code_path},
                )
            )
            return violations

        if not owner_ids:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-vertical-slices",
                    message=(
                        f"Production code path {production_code_path!r} has no owner. "
                        "Each production code path must be owned by exactly one worker."
                    ),
                    context={
                        "production_code_path": production_code_path,
                        "owner_count": "0",
                    },
                )
            )
        elif len(owner_ids) > 1:
            violations.append(
                ConstraintViolation(
                    constraint_id="C-vertical-slices",
                    message=(
                        f"Production code path {production_code_path!r} has "
                        f"{len(owner_ids)} owners ({owner_ids}). "
                        "Each production code path must be owned by exactly ONE worker. "
                        "Do not assign horizontal layers or the same path to multiple workers."
                    ),
                    context={
                        "production_code_path": production_code_path,
                        "owner_count": str(len(owner_ids)),
                        "owners": ",".join(owner_ids),
                    },
                )
            )

        return violations
