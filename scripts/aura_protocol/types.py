"""Protocol type definitions for the Aura multi-agent protocol.

All enums are str Enums for JSON/Temporal serialization compatibility.
All spec dataclasses are frozen (immutable) for use as dict keys and safe sharing.

Source of truth: skills/protocol/schema.xml
Integration test: tests/test_schema_types_sync.py verifies Python types match schema.xml.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


# ─── Enums ────────────────────────────────────────────────────────────────────


class PhaseId(str, Enum):
    """12-phase epoch lifecycle + COMPLETE sentinel.

    Values match schema.xml <phase id="..."> elements.
    """

    P1_REQUEST = "p1"
    P2_ELICIT = "p2"
    P3_PROPOSE = "p3"
    P4_REVIEW = "p4"
    P5_UAT = "p5"
    P6_RATIFY = "p6"
    P7_HANDOFF = "p7"
    P8_IMPL_PLAN = "p8"
    P9_SLICE = "p9"
    P10_CODE_REVIEW = "p10"
    P11_IMPL_UAT = "p11"
    P12_LANDING = "p12"
    COMPLETE = "complete"


class Domain(str, Enum):
    """Phase domain classification.

    Values match schema.xml <enum name="DomainType"> entries.
    """

    USER = "user"
    PLAN = "plan"
    IMPL = "impl"


class RoleId(str, Enum):
    """Agent role identifiers.

    Values match schema.xml <role id="..."> elements.
    """

    EPOCH = "epoch"
    ARCHITECT = "architect"
    REVIEWER = "reviewer"
    SUPERVISOR = "supervisor"
    WORKER = "worker"


class VoteType(str, Enum):
    """Binary review vote.

    Values match schema.xml <enum name="VoteType"> entries.
    """

    ACCEPT = "ACCEPT"
    REVISE = "REVISE"


class SeverityLevel(str, Enum):
    """Code review finding severity.

    Values match schema.xml <enum name="SeverityLevel"> entries.
    """

    BLOCKER = "BLOCKER"
    IMPORTANT = "IMPORTANT"
    MINOR = "MINOR"


# ─── Frozen Dataclasses ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Transition:
    """A single valid phase transition.

    Derived from schema.xml <transition> elements within each <phase>.
    """

    to_phase: PhaseId
    condition: str
    action: str | None = None


@dataclass(frozen=True)
class PhaseSpec:
    """Complete specification for a single protocol phase.

    Derived from schema.xml <phase> elements.
    owner_roles uses frozenset for hashability; transitions uses tuple for ordering.
    """

    id: PhaseId
    number: int
    domain: Domain
    name: str
    owner_roles: frozenset[RoleId]
    transitions: tuple[Transition, ...]


@dataclass(frozen=True)
class ConstraintSpec:
    """A single protocol constraint in Given/When/Then/Should-not format.

    Derived from schema.xml <constraint> elements.
    """

    id: str
    given: str
    when: str
    then: str
    should_not: str


@dataclass(frozen=True)
class HandoffSpec:
    """Specification for an actor-change transition handoff document.

    Derived from schema.xml <handoff> elements.
    required_fields uses tuple for ordering.
    """

    id: str
    source_role: RoleId
    target_role: RoleId
    at_phase: PhaseId
    content_level: str
    required_fields: tuple[str, ...]


# ─── Event Stub Types ─────────────────────────────────────────────────────────
# Minimal frozen dataclasses for v1 interface definitions.
# Full event bodies are defined in interfaces.py.


@dataclass(frozen=True)
class PhaseTransitionEvent:
    """Emitted when an epoch advances to a new phase."""

    epoch_id: str
    from_phase: PhaseId
    to_phase: PhaseId
    triggered_by: str
    condition_met: str


@dataclass(frozen=True)
class ConstraintCheckEvent:
    """Emitted when constraint checking runs against epoch state."""

    epoch_id: str
    phase: PhaseId
    constraint_id: str
    passed: bool
    message: str | None = None


@dataclass(frozen=True)
class ReviewVoteEvent:
    """Emitted when a reviewer casts a vote."""

    epoch_id: str
    phase: PhaseId
    axis: str  # "A", "B", or "C"
    vote: VoteType
    reviewer_id: str


@dataclass(frozen=True)
class AuditEvent:
    """Generic audit trail event."""

    epoch_id: str
    event_type: str
    phase: PhaseId
    role: RoleId
    payload: dict[str, Any]  # Structured event details


@dataclass(frozen=True)
class ToolPermissionRequest:
    """Request for tool permission check (for agentfilter integration)."""

    epoch_id: str
    phase: PhaseId
    role: RoleId
    tool_name: str
    tool_input_summary: str


@dataclass(frozen=True)
class PermissionDecision:
    """Decision result from a permission check."""

    allowed: bool
    reason: str | None = None


# ─── Phase-Domain Mapping ─────────────────────────────────────────────────────
# Derived from schema.xml semantic rule _EXPECTED_DOMAINS in validate_schema.py.
# Each phase number maps to its domain; this dict maps PhaseId to Domain.

PHASE_DOMAIN: dict[PhaseId, Domain] = {
    PhaseId.P1_REQUEST:    Domain.USER,
    PhaseId.P2_ELICIT:     Domain.USER,
    PhaseId.P3_PROPOSE:    Domain.PLAN,
    PhaseId.P4_REVIEW:     Domain.PLAN,
    PhaseId.P5_UAT:        Domain.USER,
    PhaseId.P6_RATIFY:     Domain.PLAN,
    PhaseId.P7_HANDOFF:    Domain.PLAN,
    PhaseId.P8_IMPL_PLAN:  Domain.IMPL,
    PhaseId.P9_SLICE:      Domain.IMPL,
    PhaseId.P10_CODE_REVIEW: Domain.IMPL,
    PhaseId.P11_IMPL_UAT:  Domain.USER,
    PhaseId.P12_LANDING:   Domain.IMPL,
}


# ─── Canonical Protocol Definitions ──────────────────────────────────────────
# Transition table derived from schema.xml <phase>/<transitions> elements.
# Integration test (test_schema_types_sync.py) verifies these match schema.xml.

PHASE_SPECS: dict[PhaseId, PhaseSpec] = {
    PhaseId.P1_REQUEST: PhaseSpec(
        id=PhaseId.P1_REQUEST,
        number=1,
        domain=Domain.USER,
        name="Request",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT}),
        transitions=(
            Transition(
                to_phase=PhaseId.P2_ELICIT,
                condition="classification confirmed, research and explore complete",
            ),
        ),
    ),
    PhaseId.P2_ELICIT: PhaseSpec(
        id=PhaseId.P2_ELICIT,
        number=2,
        domain=Domain.USER,
        name="Elicit",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT}),
        transitions=(
            Transition(
                to_phase=PhaseId.P3_PROPOSE,
                condition="URD created with structured requirements",
            ),
        ),
    ),
    PhaseId.P3_PROPOSE: PhaseSpec(
        id=PhaseId.P3_PROPOSE,
        number=3,
        domain=Domain.PLAN,
        name="Propose",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT}),
        transitions=(
            Transition(
                to_phase=PhaseId.P4_REVIEW,
                condition="proposal created",
            ),
        ),
    ),
    PhaseId.P4_REVIEW: PhaseSpec(
        id=PhaseId.P4_REVIEW,
        number=4,
        domain=Domain.PLAN,
        name="Review",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT, RoleId.REVIEWER}),
        transitions=(
            Transition(
                to_phase=PhaseId.P5_UAT,
                condition="all 3 reviewers vote ACCEPT",
            ),
            Transition(
                to_phase=PhaseId.P3_PROPOSE,
                condition="any reviewer votes REVISE",
                action="create PROPOSAL-{N+1}, mark current aura:superseded",
            ),
        ),
    ),
    PhaseId.P5_UAT: PhaseSpec(
        id=PhaseId.P5_UAT,
        number=5,
        domain=Domain.USER,
        name="Plan UAT",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT}),
        transitions=(
            Transition(
                to_phase=PhaseId.P6_RATIFY,
                condition="user accepts plan",
            ),
            Transition(
                to_phase=PhaseId.P3_PROPOSE,
                condition="user requests changes",
                action="create PROPOSAL-{N+1}",
            ),
        ),
    ),
    PhaseId.P6_RATIFY: PhaseSpec(
        id=PhaseId.P6_RATIFY,
        number=6,
        domain=Domain.PLAN,
        name="Ratify",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT}),
        transitions=(
            Transition(
                to_phase=PhaseId.P7_HANDOFF,
                condition="proposal ratified, IMPL_PLAN placeholder created",
            ),
        ),
    ),
    PhaseId.P7_HANDOFF: PhaseSpec(
        id=PhaseId.P7_HANDOFF,
        number=7,
        domain=Domain.PLAN,
        name="Handoff",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.ARCHITECT, RoleId.SUPERVISOR}),
        transitions=(
            Transition(
                to_phase=PhaseId.P8_IMPL_PLAN,
                condition="handoff document stored at .git/.aura/handoff/",
            ),
        ),
    ),
    PhaseId.P8_IMPL_PLAN: PhaseSpec(
        id=PhaseId.P8_IMPL_PLAN,
        number=8,
        domain=Domain.IMPL,
        name="Impl Plan",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.SUPERVISOR}),
        transitions=(
            Transition(
                to_phase=PhaseId.P9_SLICE,
                condition="all slices created with leaf tasks, assigned, and dependency-chained",
            ),
        ),
    ),
    PhaseId.P9_SLICE: PhaseSpec(
        id=PhaseId.P9_SLICE,
        number=9,
        domain=Domain.IMPL,
        name="Worker Slices",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.SUPERVISOR, RoleId.WORKER}),
        transitions=(
            Transition(
                to_phase=PhaseId.P10_CODE_REVIEW,
                condition="all slices complete, quality gates pass",
            ),
        ),
    ),
    PhaseId.P10_CODE_REVIEW: PhaseSpec(
        id=PhaseId.P10_CODE_REVIEW,
        number=10,
        domain=Domain.IMPL,
        name="Code Review",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.SUPERVISOR, RoleId.REVIEWER}),
        transitions=(
            Transition(
                to_phase=PhaseId.P11_IMPL_UAT,
                condition="all 3 reviewers ACCEPT, all BLOCKERs resolved",
            ),
            Transition(
                to_phase=PhaseId.P9_SLICE,
                condition="any reviewer votes REVISE",
                action="fix BLOCKERs in affected slices, then re-review",
            ),
        ),
    ),
    PhaseId.P11_IMPL_UAT: PhaseSpec(
        id=PhaseId.P11_IMPL_UAT,
        number=11,
        domain=Domain.USER,
        name="Impl UAT",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.SUPERVISOR}),
        transitions=(
            Transition(
                to_phase=PhaseId.P12_LANDING,
                condition="user accepts implementation",
            ),
            Transition(
                to_phase=PhaseId.P9_SLICE,
                condition="user requests changes",
                action="create fix tasks in affected slices",
            ),
        ),
    ),
    PhaseId.P12_LANDING: PhaseSpec(
        id=PhaseId.P12_LANDING,
        number=12,
        domain=Domain.IMPL,
        name="Landing",
        owner_roles=frozenset({RoleId.EPOCH, RoleId.SUPERVISOR}),
        transitions=(
            Transition(
                to_phase=PhaseId.COMPLETE,
                condition="git push succeeds, all tasks closed or dependency-resolved",
            ),
        ),
    ),
}


CONSTRAINT_SPECS: dict[str, ConstraintSpec] = {
    "C-audit-never-delete": ConstraintSpec(
        id="C-audit-never-delete",
        given="any task or label",
        when="modifying",
        then="add labels and comments only",
        should_not="delete or close tasks prematurely, remove labels",
    ),
    "C-audit-dep-chain": ConstraintSpec(
        id="C-audit-dep-chain",
        given="any phase transition",
        when="creating new task",
        then="chain dependency: bd dep add parent --blocked-by child",
        should_not="skip dependency chaining or invert direction",
    ),
    "C-review-consensus": ConstraintSpec(
        id="C-review-consensus",
        given="review cycle (p4 or p10)",
        when="evaluating",
        then="all 3 reviewers must ACCEPT before proceeding",
        should_not="proceed with any REVISE vote outstanding",
    ),
    "C-review-binary": ConstraintSpec(
        id="C-review-binary",
        given="a reviewer",
        when="voting",
        then="use ACCEPT or REVISE only",
        should_not="use APPROVE, APPROVE_WITH_COMMENTS, REQUEST_CHANGES, or REJECT",
    ),
    "C-severity-eager": ConstraintSpec(
        id="C-severity-eager",
        given="code review round (p10 only)",
        when="starting review",
        then="ALWAYS create 3 severity group tasks (BLOCKER, IMPORTANT, MINOR) immediately",
        should_not="lazily create severity groups only when findings exist",
    ),
    "C-severity-not-plan": ConstraintSpec(
        id="C-severity-not-plan",
        given="plan review (p4)",
        when="reviewing",
        then="use binary ACCEPT/REVISE only",
        should_not="create severity tree for plan reviews",
    ),
    "C-blocker-dual-parent": ConstraintSpec(
        id="C-blocker-dual-parent",
        given="a BLOCKER finding in code review",
        when="recording",
        then="add as child of BOTH the severity group AND the slice it blocks",
        should_not="add to severity group only",
    ),
    "C-followup-timing": ConstraintSpec(
        id="C-followup-timing",
        given="code review completion with IMPORTANT or MINOR findings",
        when="creating follow-up epic",
        then="create immediately upon review completion",
        should_not="gate follow-up epic on BLOCKER resolution",
    ),
    "C-vertical-slices": ConstraintSpec(
        id="C-vertical-slices",
        given="implementation decomposition",
        when="assigning work",
        then="each production code path owned by exactly ONE worker (full vertical)",
        should_not="assign horizontal layers or same path to multiple workers",
    ),
    "C-supervisor-no-impl": ConstraintSpec(
        id="C-supervisor-no-impl",
        given="supervisor role",
        when="implementation phase",
        then="spawn workers for all code changes",
        should_not="implement code directly",
    ),
    "C-supervisor-explore-team": ConstraintSpec(
        id="C-supervisor-explore-team",
        given="supervisor needs codebase exploration",
        when="starting Phase 8 (IMPL_PLAN)",
        then=(
            "create standing explore team via TeamCreate with minimum 1 scoped explore agent; "
            "delegate all deep exploration to explore agents; "
            "reuse agents for follow-up queries on same domain"
        ),
        should_not="perform deep codebase exploration directly as supervisor",
    ),
    "C-slice-leaf-tasks": ConstraintSpec(
        id="C-slice-leaf-tasks",
        given="vertical slice created",
        when="decomposing slice into implementation units",
        then=(
            "create Beads leaf tasks (L1: types, L2: tests, L3: impl) within each slice "
            "with bd dep add slice-id --blocked-by leaf-task-id"
        ),
        should_not=(
            "create slices without leaf tasks — "
            "a slice with no children is undecomposed and cannot be tracked"
        ),
    ),
    "C-handoff-skill-invocation": ConstraintSpec(
        id="C-handoff-skill-invocation",
        given="an agent is launched for a new phase (especially p7 to p8 handoff)",
        when="composing the launch prompt",
        then=(
            "prompt MUST start with Skill(/aura:{role}) invocation directive "
            "so the agent loads its role instructions"
        ),
        should_not=(
            "launch agents without skill invocation — "
            "they skip role-critical procedures like explore team setup and leaf task creation"
        ),
    ),
    "C-dep-direction": ConstraintSpec(
        id="C-dep-direction",
        given="adding a Beads dependency",
        when="determining direction",
        then="parent blocked-by child: bd dep add stays-open --blocked-by must-finish-first",
        should_not="invert (child blocked-by parent)",
    ),
    "C-frontmatter-refs": ConstraintSpec(
        id="C-frontmatter-refs",
        given="cross-task references (URD, request, etc.)",
        when="linking tasks",
        then="use description frontmatter references: block",
        should_not="use bd dep relate (buggy) or blocking dependencies for reference docs",
    ),
    "C-agent-commit": ConstraintSpec(
        id="C-agent-commit",
        given="code is ready to commit",
        when="committing",
        then="use git agent-commit -m ...",
        should_not="use git commit -m ...",
    ),
    "C-proposal-naming": ConstraintSpec(
        id="C-proposal-naming",
        given="a new or revised proposal",
        when="creating task",
        then="title PROPOSAL-{N} where N increments; mark old as aura:superseded",
        should_not="reuse N or delete old proposals",
    ),
    "C-review-naming": ConstraintSpec(
        id="C-review-naming",
        given="a review task",
        when="creating",
        then="title {SCOPE}-REVIEW-{axis}-{round} where axis=A|B|C, round starts at 1",
        should_not="use numeric reviewer IDs (1/2/3) instead of axis letters",
    ),
    "C-ure-verbatim": ConstraintSpec(
        id="C-ure-verbatim",
        given="user interview (URE or UAT)",
        when="recording in Beads",
        then="capture full question text, ALL option descriptions, AND user's verbatim response",
        should_not="summarize options as (1)/(2)/(3) without option text",
    ),
    "C-followup-lifecycle": ConstraintSpec(
        id="C-followup-lifecycle",
        given="follow-up epic created",
        when="starting follow-up work",
        then=(
            "run same protocol phases with FOLLOWUP_* prefix: "
            "FOLLOWUP_URE → FOLLOWUP_URD → FOLLOWUP_PROPOSAL → FOLLOWUP_IMPL_PLAN → FOLLOWUP_SLICE"
        ),
        should_not="skip the follow-up lifecycle or treat the follow-up epic as a flat task list",
    ),
    "C-followup-leaf-adoption": ConstraintSpec(
        id="C-followup-leaf-adoption",
        given="supervisor creates FOLLOWUP_SLICE-N",
        when="assigning original IMPORTANT/MINOR leaf tasks to follow-up slices",
        then=(
            "add leaf task as child of follow-up slice "
            "(dual-parent: leaf blocks both severity group AND follow-up slice)"
        ),
        should_not="remove the leaf task from its original severity group parent",
    ),
    "C-worker-gates": ConstraintSpec(
        id="C-worker-gates",
        given="worker finishes implementation",
        when="signaling completion",
        then="run quality gates (typecheck + tests) AND verify production code path (no TODOs, real deps)",
        should_not="close with only 'tests pass' as completion gate",
    ),
    "C-actionable-errors": ConstraintSpec(
        id="C-actionable-errors",
        given="an error, exception, or user-facing message",
        when="creating or raising",
        then=(
            "make it actionable: describe (1) what went wrong, (2) why it happened, "
            "(3) where it failed (file location, module, or function), "
            "(4) when it failed (step, operation, or timestamp), "
            "(5) what it means for the caller, and (6) how to fix it"
        ),
        should_not=(
            "raise generic or opaque error messages (e.g. 'invalid input', 'operation failed') "
            "that don't guide the user toward resolution"
        ),
    ),
}


HANDOFF_SPECS: dict[str, HandoffSpec] = {
    "h1": HandoffSpec(
        id="h1",
        source_role=RoleId.ARCHITECT,
        target_role=RoleId.SUPERVISOR,
        at_phase=PhaseId.P7_HANDOFF,
        content_level="full-provenance",
        required_fields=(
            "request", "urd", "proposal", "ratified-plan",
            "context", "key-decisions", "open-items", "acceptance-criteria",
        ),
    ),
    "h2": HandoffSpec(
        id="h2",
        source_role=RoleId.SUPERVISOR,
        target_role=RoleId.WORKER,
        at_phase=PhaseId.P9_SLICE,
        content_level="summary-with-ids",
        required_fields=(
            "request", "urd", "proposal", "ratified-plan", "impl-plan",
            "slice", "context", "key-decisions", "open-items", "acceptance-criteria",
        ),
    ),
    "h3": HandoffSpec(
        id="h3",
        source_role=RoleId.SUPERVISOR,
        target_role=RoleId.REVIEWER,
        at_phase=PhaseId.P10_CODE_REVIEW,
        content_level="summary-with-ids",
        required_fields=(
            "request", "urd", "proposal", "ratified-plan", "impl-plan",
            "context", "key-decisions", "acceptance-criteria",
        ),
    ),
    "h4": HandoffSpec(
        id="h4",
        source_role=RoleId.WORKER,
        target_role=RoleId.REVIEWER,
        at_phase=PhaseId.P10_CODE_REVIEW,
        content_level="summary-with-ids",
        required_fields=(
            "request", "urd", "impl-plan", "slice",
            "context", "key-decisions", "open-items",
        ),
    ),
    "h5": HandoffSpec(
        id="h5",
        source_role=RoleId.REVIEWER,
        target_role=RoleId.SUPERVISOR,
        at_phase=PhaseId.P10_CODE_REVIEW,
        content_level="summary-with-ids",
        required_fields=(
            "request", "urd", "proposal",
            "context", "key-decisions", "open-items", "acceptance-criteria",
        ),
    ),
    "h6": HandoffSpec(
        id="h6",
        source_role=RoleId.SUPERVISOR,
        target_role=RoleId.ARCHITECT,
        at_phase=PhaseId.P3_PROPOSE,
        content_level="summary-with-ids",
        required_fields=(
            "request", "urd", "followup-epic", "followup-ure", "followup-urd",
            "context", "key-decisions", "findings-summary", "acceptance-criteria",
        ),
    ),
}
