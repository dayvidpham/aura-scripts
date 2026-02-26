"""Protocol type definitions for the Aura multi-agent protocol.

All enums are str Enums for JSON/Temporal serialization compatibility.
All spec dataclasses are frozen (immutable) for use as dict keys and safe sharing.

Source of truth: this file (types.py). schema.xml is generated from Python via gen_schema.py.
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


class ExecutionMode(str, Enum):
    """Substep execution mode within a phase.

    Values match schema.xml <enum name="ExecutionMode"> entries.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ContentLevel(str, Enum):
    """Handoff document content level.

    Values match schema.xml <enum name="ContentLevel"> entries.
    """

    FULL_PROVENANCE = "full-provenance"
    SUMMARY_WITH_IDS = "summary-with-ids"


class ReviewAxis(str, Enum):
    """Review axis identifier letters used in review votes.

    Values match schema.xml <axis letter="..."> elements.
    """

    A = "A"
    B = "B"
    C = "C"


class SubstepType(str, Enum):
    """Substep type classification within a phase.

    Values match schema.xml <substep type="..."> attributes.
    """

    CLASSIFY = "classify"
    RESEARCH = "research"
    EXPLORE = "explore"
    ELICIT = "elicit"
    URD = "urd"
    PROPOSE = "propose"
    REVIEW = "review"
    UAT = "uat"
    RATIFY = "ratify"
    HANDOFF = "handoff"
    PLAN = "plan"
    SLICE = "slice"
    LANDING = "landing"


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
    content_level: ContentLevel
    required_fields: tuple[str, ...]


@dataclass(frozen=True)
class SubstepSpec:
    """Complete specification for a single phase substep.

    Derived from schema.xml <substep> elements within each <phase>.
    """

    id: str
    type: SubstepType
    execution: ExecutionMode
    order: int
    label_ref: str
    parallel_group: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class RoleSpec:
    """Complete specification for an agent role.

    Derived from schema.xml <role> elements.
    owned_phases uses frozenset for hashability.
    """

    id: RoleId
    name: str
    description: str
    owned_phases: frozenset[PhaseId]


@dataclass(frozen=True)
class DelegateSpec:
    """Delegation relationship from epoch role to another role.

    Derived from schema.xml <delegate> elements within <role>.
    """

    to_role: RoleId
    phases: tuple[str, ...]


@dataclass(frozen=True)
class CommandSpec:
    """Complete specification for a protocol command (skill).

    Derived from schema.xml <command> elements within <commands>.
    phases uses tuple for ordering; creates_labels uses tuple for ordering.
    """

    id: str
    name: str
    description: str
    role_ref: RoleId | None
    phases: tuple[str, ...]
    file: str
    creates_labels: tuple[str, ...]


@dataclass(frozen=True)
class LabelSpec:
    """Complete specification for a protocol label.

    Derived from schema.xml <label> elements within <labels>.
    """

    id: str
    value: str
    special: bool
    phase_ref: str | None = None
    substep_ref: str | None = None
    severity_ref: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ReviewAxisSpec:
    """Complete specification for a code review axis.

    Derived from schema.xml <axis> elements within <review-axes>.
    key_questions uses tuple for ordering.
    """

    id: str
    letter: ReviewAxis
    name: str
    short: str
    key_questions: tuple[str, ...]


@dataclass(frozen=True)
class TitleConvention:
    """Task title naming convention for a phase/substep type.

    Derived from schema.xml <title-convention> elements within <task-titles>.
    """

    pattern: str
    label_ref: str
    created_by: str
    phase_ref: str | None = None
    extra_label_ref: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ProcedureStep:
    """A single step in a role's startup or operational procedure.

    Fields:
        id:          Unique step identifier, e.g. 'S-supervisor-call-skill'.
        order:       Step number (1-based).
        instruction: Human-readable description of what to do.
        command:     Optional exact shell/bd command to run (e.g. 'bd dep add ...').
        context:     Optional situational context (e.g. 'only if working on a follow-up').
        next_state:  Phase this step transitions to, if any.
    """

    id: str
    order: int
    instruction: str
    command: str | None = None
    context: str | None = None
    next_state: PhaseId | None = None


@dataclass(frozen=True)
class ConstraintContext:
    """Context injection fragment for runtime constraint evaluation.

    Used by SLICE-4 context injection to embed constraint facts into agent prompts.
    Fields align with schema.xml <constraint> attribute structure.
    """

    id: str
    given: str
    when: str
    then: str
    should_not: str


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
    axis: ReviewAxis
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
    "C-supervisor-cartographers": ConstraintSpec(
        id="C-supervisor-cartographers",
        given="supervisor needs codebase exploration and code review",
        when="starting Phase 8 (IMPL_PLAN) and Phase 10 (Code Review)",
        then=(
            "create exactly 3 Cartographers via TeamCreate with /aura:explore before any exploration; "
            "Cartographers are dual-role: explore codebase in Phase 8, switch to /aura:reviewer in Phase 10; "
            "Cartographers NEVER shut down between phases — persist for full Ride the Wave cycle; "
            "max 3 worker-reviewer cycles; supervisor shuts down Cartographers after cycle 3 or all-ACCEPT"
        ),
        should_not=(
            "perform deep codebase exploration directly as supervisor; "
            "shut down Cartographers between Phase 8 and Phase 10; "
            "exceed 3 worker-reviewer cycles"
        ),
    ),
    "C-integration-points": ConstraintSpec(
        id="C-integration-points",
        given="multiple vertical slices share types, interfaces, or data flows",
        when="decomposing IMPL_PLAN in Phase 8",
        then=(
            "identify horizontal Layer Integration Points and document them in IMPL_PLAN; "
            "each integration point specifies: owning slice, consuming slices, shared contract, merge timing; "
            "include integration points in slice descriptions so workers know what to export and import"
        ),
        should_not=(
            "leave cross-slice dependencies implicit; "
            "assume workers will discover contracts on their own"
        ),
    ),
    "C-slice-review-before-close": ConstraintSpec(
        id="C-slice-review-before-close",
        given="workers complete their implementation slices",
        when="slice implementation is done",
        then=(
            "workers notify supervisor with bd comments add (not bd close); "
            "slices must be reviewed at least once by Cartographers before closure; "
            "only the supervisor closes slices, after review passes"
        ),
        should_not=(
            "close slices immediately upon worker completion; "
            "allow workers to close their own slices"
        ),
    ),
    "C-max-review-cycles": ConstraintSpec(
        id="C-max-review-cycles",
        given="worker-Cartographer review-fix cycles are ongoing",
        when="counting review-fix iterations",
        then=(
            "limit to a maximum of 3 cycles total; "
            "after cycle 3, remaining IMPORTANT findings move to FOLLOWUP epic; "
            "proceed to Phase 11 (UAT) regardless of remaining IMPORTANTs after cycle 3"
        ),
        should_not=(
            "exceed 3 worker-reviewer cycles; "
            "block UAT on non-BLOCKER findings after 3 cycles"
        ),
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
        content_level=ContentLevel.FULL_PROVENANCE,
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
        content_level=ContentLevel.SUMMARY_WITH_IDS,
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
        content_level=ContentLevel.SUMMARY_WITH_IDS,
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
        content_level=ContentLevel.SUMMARY_WITH_IDS,
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
        content_level=ContentLevel.SUMMARY_WITH_IDS,
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
        content_level=ContentLevel.SUMMARY_WITH_IDS,
        required_fields=(
            "request", "urd", "followup-epic", "followup-ure", "followup-urd",
            "context", "key-decisions", "findings-summary", "acceptance-criteria",
        ),
    ),
}


# ─── New Canonical Dicts (schema-driven) ─────────────────────────────────────
# Derived from schema.xml. Integration tests in test_schema_types_sync.py verify
# these match schema.xml entities.


ROLE_SPECS: dict[RoleId, RoleSpec] = {
    RoleId.EPOCH: RoleSpec(
        id=RoleId.EPOCH,
        name="Epoch",
        description="Master orchestrator for full 12-phase workflow",
        owned_phases=frozenset({
            PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P3_PROPOSE,
            PhaseId.P4_REVIEW, PhaseId.P5_UAT, PhaseId.P6_RATIFY,
            PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT, PhaseId.P12_LANDING,
        }),
    ),
    RoleId.ARCHITECT: RoleSpec(
        id=RoleId.ARCHITECT,
        name="Architect",
        description="Specification writer and implementation designer",
        owned_phases=frozenset({
            PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P3_PROPOSE,
            PhaseId.P4_REVIEW, PhaseId.P5_UAT, PhaseId.P6_RATIFY,
            PhaseId.P7_HANDOFF,
        }),
    ),
    RoleId.REVIEWER: RoleSpec(
        id=RoleId.REVIEWER,
        name="Reviewer",
        description="End-user alignment reviewer for plans and code",
        owned_phases=frozenset({PhaseId.P4_REVIEW, PhaseId.P10_CODE_REVIEW}),
    ),
    RoleId.SUPERVISOR: RoleSpec(
        id=RoleId.SUPERVISOR,
        name="Supervisor",
        description="Task coordinator, spawns workers, manages parallel execution",
        owned_phases=frozenset({
            PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT, PhaseId.P12_LANDING,
        }),
    ),
    RoleId.WORKER: RoleSpec(
        id=RoleId.WORKER,
        name="Worker",
        description="Vertical slice implementer (full production code path)",
        owned_phases=frozenset({PhaseId.P9_SLICE}),
    ),
}


COMMAND_SPECS: dict[str, CommandSpec] = {
    "cmd-epoch": CommandSpec(
        id="cmd-epoch",
        name="aura:epoch",
        description="Master orchestrator for full 12-phase workflow",
        role_ref=RoleId.EPOCH,
        phases=("p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12"),
        file="skills/epoch/SKILL.md",
        creates_labels=(),
    ),
    "cmd-plan": CommandSpec(
        id="cmd-plan",
        name="aura:plan",
        description="Plan coordination across phases 1-6",
        role_ref=RoleId.ARCHITECT,
        phases=("p1", "p2", "p3", "p4", "p5", "p6"),
        file="skills/plan/SKILL.md",
        creates_labels=(),
    ),
    "cmd-status": CommandSpec(
        id="cmd-status",
        name="aura:status",
        description="Project status and monitoring via Beads queries",
        role_ref=None,
        phases=(),
        file="skills/status/SKILL.md",
        creates_labels=(),
    ),
    "cmd-user-request": CommandSpec(
        id="cmd-user-request",
        name="aura:user:request",
        description="Capture user feature request verbatim (Phase 1)",
        role_ref=RoleId.ARCHITECT,
        phases=("p1",),
        file="skills/user-request/SKILL.md",
        creates_labels=("L-p1s1_1",),
    ),
    "cmd-user-elicit": CommandSpec(
        id="cmd-user-elicit",
        name="aura:user:elicit",
        description="User Requirements Elicitation survey (Phase 2)",
        role_ref=RoleId.ARCHITECT,
        phases=("p2",),
        file="skills/user-elicit/SKILL.md",
        creates_labels=("L-p2s2_1", "L-p2s2_2", "L-urd"),
    ),
    "cmd-user-uat": CommandSpec(
        id="cmd-user-uat",
        name="aura:user:uat",
        description="User Acceptance Testing with demonstrative examples",
        role_ref=None,
        phases=("p5", "p11"),
        file="skills/user-uat/SKILL.md",
        creates_labels=("L-p5s5", "L-p11s11"),
    ),
    "cmd-architect": CommandSpec(
        id="cmd-architect",
        name="aura:architect",
        description="Specification writer and implementation designer",
        role_ref=RoleId.ARCHITECT,
        phases=("p1", "p2", "p3", "p4", "p5", "p6", "p7"),
        file="skills/architect/SKILL.md",
        creates_labels=(),
    ),
    "cmd-arch-propose": CommandSpec(
        id="cmd-arch-propose",
        name="aura:architect:propose-plan",
        description="Create PROPOSAL-N task with full technical plan",
        role_ref=RoleId.ARCHITECT,
        phases=("p3",),
        file="skills/architect-propose-plan/SKILL.md",
        creates_labels=("L-p3s3",),
    ),
    "cmd-arch-review": CommandSpec(
        id="cmd-arch-review",
        name="aura:architect:request-review",
        description="Spawn 3 axis-specific reviewers (A/B/C)",
        role_ref=RoleId.ARCHITECT,
        phases=("p4",),
        file="skills/architect-request-review/SKILL.md",
        creates_labels=("L-p4s4",),
    ),
    "cmd-arch-ratify": CommandSpec(
        id="cmd-arch-ratify",
        name="aura:architect:ratify",
        description="Ratify proposal, mark old proposals aura:superseded",
        role_ref=RoleId.ARCHITECT,
        phases=("p6",),
        file="skills/architect-ratify/SKILL.md",
        creates_labels=("L-p6s6", "L-superseded"),
    ),
    "cmd-arch-handoff": CommandSpec(
        id="cmd-arch-handoff",
        name="aura:architect:handoff",
        description="Create handoff document and transfer to supervisor",
        role_ref=RoleId.ARCHITECT,
        phases=("p7",),
        file="skills/architect-handoff/SKILL.md",
        creates_labels=("L-p7s7",),
    ),
    "cmd-supervisor": CommandSpec(
        id="cmd-supervisor",
        name="aura:supervisor",
        description="Task coordinator, spawns workers, manages parallel execution",
        role_ref=RoleId.SUPERVISOR,
        phases=("p7", "p8", "p9", "p10", "p11", "p12"),
        file="skills/supervisor/SKILL.md",
        creates_labels=(),
    ),
    "cmd-sup-plan": CommandSpec(
        id="cmd-sup-plan",
        name="aura:supervisor:plan-tasks",
        description="Decompose ratified plan into vertical slices (SLICE-N)",
        role_ref=RoleId.SUPERVISOR,
        phases=("p8",),
        file="skills/supervisor-plan-tasks/SKILL.md",
        creates_labels=("L-p8s8", "L-p9s9"),
    ),
    "cmd-sup-spawn": CommandSpec(
        id="cmd-sup-spawn",
        name="aura:supervisor:spawn-worker",
        description="Launch a worker agent for an assigned slice",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9",),
        file="skills/supervisor-spawn-worker/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    "cmd-sup-track": CommandSpec(
        id="cmd-sup-track",
        name="aura:supervisor:track-progress",
        description="Monitor worker status via Beads",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9", "p10"),
        file="skills/supervisor-track-progress/SKILL.md",
        creates_labels=(),
    ),
    "cmd-sup-commit": CommandSpec(
        id="cmd-sup-commit",
        name="aura:supervisor:commit",
        description="Atomic commit per completed layer/slice",
        role_ref=RoleId.SUPERVISOR,
        phases=("p12",),
        file="skills/supervisor-commit/SKILL.md",
        creates_labels=("L-p12s12",),
    ),
    "cmd-worker": CommandSpec(
        id="cmd-worker",
        name="aura:worker",
        description="Vertical slice implementer (full production code path)",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker/SKILL.md",
        creates_labels=(),
    ),
    "cmd-work-impl": CommandSpec(
        id="cmd-work-impl",
        name="aura:worker:implement",
        description="Implement assigned vertical slice following TDD layers",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-implement/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    "cmd-work-complete": CommandSpec(
        id="cmd-work-complete",
        name="aura:worker:complete",
        description="Signal slice completion after quality gates pass",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-complete/SKILL.md",
        creates_labels=(),
    ),
    "cmd-work-blocked": CommandSpec(
        id="cmd-work-blocked",
        name="aura:worker:blocked",
        description="Report a blocker to supervisor via Beads",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-blocked/SKILL.md",
        creates_labels=(),
    ),
    "cmd-reviewer": CommandSpec(
        id="cmd-reviewer",
        name="aura:reviewer",
        description="End-user alignment reviewer for plans and code",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer/SKILL.md",
        creates_labels=(),
    ),
    "cmd-rev-plan": CommandSpec(
        id="cmd-rev-plan",
        name="aura:reviewer:review-plan",
        description="Evaluate proposal against one axis (binary ACCEPT/REVISE)",
        role_ref=RoleId.REVIEWER,
        phases=("p4",),
        file="skills/reviewer-review-plan/SKILL.md",
        creates_labels=("L-p4s4",),
    ),
    "cmd-rev-code": CommandSpec(
        id="cmd-rev-code",
        name="aura:reviewer:review-code",
        description="Review implementation slices with EAGER severity tree",
        role_ref=RoleId.REVIEWER,
        phases=("p10",),
        file="skills/reviewer-review-code/SKILL.md",
        creates_labels=("L-p10s10", "L-sev-blocker", "L-sev-import", "L-sev-minor"),
    ),
    "cmd-rev-comment": CommandSpec(
        id="cmd-rev-comment",
        name="aura:reviewer:comment",
        description="Leave structured review comment via Beads",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer-comment/SKILL.md",
        creates_labels=(),
    ),
    "cmd-rev-vote": CommandSpec(
        id="cmd-rev-vote",
        name="aura:reviewer:vote",
        description="Cast ACCEPT or REVISE vote (binary only)",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer-vote/SKILL.md",
        creates_labels=(),
    ),
    "cmd-impl-slice": CommandSpec(
        id="cmd-impl-slice",
        name="aura:impl:slice",
        description="Vertical slice assignment and tracking",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9",),
        file="skills/impl-slice/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    "cmd-impl-review": CommandSpec(
        id="cmd-impl-review",
        name="aura:impl:review",
        description="Code review coordination across all slices (Phase 10)",
        role_ref=RoleId.SUPERVISOR,
        phases=("p10",),
        file="skills/impl-review/SKILL.md",
        creates_labels=("L-p10s10", "L-sev-blocker", "L-sev-import", "L-sev-minor"),
    ),
    "cmd-msg-send": CommandSpec(
        id="cmd-msg-send",
        name="aura:msg:send",
        description="Send a message to another agent via Beads comment",
        role_ref=None,
        phases=(),
        file="skills/msg-send/SKILL.md",
        creates_labels=(),
    ),
    "cmd-msg-receive": CommandSpec(
        id="cmd-msg-receive",
        name="aura:msg:receive",
        description="Check inbox for messages from other agents",
        role_ref=None,
        phases=(),
        file="skills/msg-receive/SKILL.md",
        creates_labels=(),
    ),
    "cmd-msg-broadcast": CommandSpec(
        id="cmd-msg-broadcast",
        name="aura:msg:broadcast",
        description="Broadcast a message to multiple agents",
        role_ref=None,
        phases=(),
        file="skills/msg-broadcast/SKILL.md",
        creates_labels=(),
    ),
    "cmd-msg-ack": CommandSpec(
        id="cmd-msg-ack",
        name="aura:msg:ack",
        description="Acknowledge received messages",
        role_ref=None,
        phases=(),
        file="skills/msg-ack/SKILL.md",
        creates_labels=(),
    ),
    "cmd-explore": CommandSpec(
        id="cmd-explore",
        name="aura:explore",
        description=(
            "Codebase exploration — find integration points, existing patterns, and related code"
        ),
        role_ref=None,
        phases=("p1", "p8"),
        file="skills/explore/SKILL.md",
        creates_labels=("L-p1s1_3",),
    ),
    "cmd-research": CommandSpec(
        id="cmd-research",
        name="aura:research",
        description="Domain research — find standards, prior art, and competing approaches",
        role_ref=None,
        phases=("p1",),
        file="skills/research/SKILL.md",
        creates_labels=("L-p1s1_2",),
    ),
    "cmd-test": CommandSpec(
        id="cmd-test",
        name="aura:test",
        description="Run tests using BDD patterns",
        role_ref=None,
        phases=(),
        file="skills/test/SKILL.md",
        creates_labels=(),
    ),
    "cmd-feedback": CommandSpec(
        id="cmd-feedback",
        name="aura:feedback",
        description="Leave structured feedback on any Beads task",
        role_ref=None,
        phases=(),
        file="skills/feedback/SKILL.md",
        creates_labels=(),
    ),
}


LABEL_SPECS: dict[str, LabelSpec] = {
    "L-p1s1_1": LabelSpec(
        id="L-p1s1_1",
        value="aura:p1-user:s1_1-classify",
        special=False,
        phase_ref="p1",
        substep_ref="s1_1",
    ),
    "L-p1s1_2": LabelSpec(
        id="L-p1s1_2",
        value="aura:p1-user:s1_2-research",
        special=False,
        phase_ref="p1",
        substep_ref="s1_2",
    ),
    "L-p1s1_3": LabelSpec(
        id="L-p1s1_3",
        value="aura:p1-user:s1_3-explore",
        special=False,
        phase_ref="p1",
        substep_ref="s1_3",
    ),
    "L-p2s2_1": LabelSpec(
        id="L-p2s2_1",
        value="aura:p2-user:s2_1-elicit",
        special=False,
        phase_ref="p2",
        substep_ref="s2_1",
    ),
    "L-p2s2_2": LabelSpec(
        id="L-p2s2_2",
        value="aura:p2-user:s2_2-urd",
        special=False,
        phase_ref="p2",
        substep_ref="s2_2",
    ),
    "L-p3s3": LabelSpec(
        id="L-p3s3",
        value="aura:p3-plan:s3-propose",
        special=False,
        phase_ref="p3",
        substep_ref="s3",
    ),
    "L-p4s4": LabelSpec(
        id="L-p4s4",
        value="aura:p4-plan:s4-review",
        special=False,
        phase_ref="p4",
        substep_ref="s4",
    ),
    "L-p5s5": LabelSpec(
        id="L-p5s5",
        value="aura:p5-user:s5-uat",
        special=False,
        phase_ref="p5",
        substep_ref="s5",
    ),
    "L-p6s6": LabelSpec(
        id="L-p6s6",
        value="aura:p6-plan:s6-ratify",
        special=False,
        phase_ref="p6",
        substep_ref="s6",
    ),
    "L-p7s7": LabelSpec(
        id="L-p7s7",
        value="aura:p7-plan:s7-handoff",
        special=False,
        phase_ref="p7",
        substep_ref="s7",
    ),
    "L-p8s8": LabelSpec(
        id="L-p8s8",
        value="aura:p8-impl:s8-plan",
        special=False,
        phase_ref="p8",
        substep_ref="s8",
    ),
    "L-p9s9": LabelSpec(
        id="L-p9s9",
        value="aura:p9-impl:s9-slice",
        special=False,
        phase_ref="p9",
        substep_ref="s9",
    ),
    "L-p10s10": LabelSpec(
        id="L-p10s10",
        value="aura:p10-impl:s10-review",
        special=False,
        phase_ref="p10",
        substep_ref="s10",
    ),
    "L-p11s11": LabelSpec(
        id="L-p11s11",
        value="aura:p11-user:s11-uat",
        special=False,
        phase_ref="p11",
        substep_ref="s11",
    ),
    "L-p12s12": LabelSpec(
        id="L-p12s12",
        value="aura:p12-impl:s12-landing",
        special=False,
        phase_ref="p12",
        substep_ref="s12",
    ),
    "L-urd": LabelSpec(
        id="L-urd",
        value="aura:urd",
        special=True,
        description="User Requirements Document",
    ),
    "L-superseded": LabelSpec(
        id="L-superseded",
        value="aura:superseded",
        special=True,
        description="Superseded proposal or plan",
    ),
    "L-sev-blocker": LabelSpec(
        id="L-sev-blocker",
        value="aura:severity:blocker",
        special=True,
        severity_ref="BLOCKER",
    ),
    "L-sev-import": LabelSpec(
        id="L-sev-import",
        value="aura:severity:important",
        special=True,
        severity_ref="IMPORTANT",
    ),
    "L-sev-minor": LabelSpec(
        id="L-sev-minor",
        value="aura:severity:minor",
        special=True,
        severity_ref="MINOR",
    ),
    "L-followup": LabelSpec(
        id="L-followup",
        value="aura:epic-followup",
        special=True,
        description="Follow-up epic for non-blocking findings",
    ),
}


REVIEW_AXIS_SPECS: dict[str, ReviewAxisSpec] = {
    "axis-A": ReviewAxisSpec(
        id="axis-A",
        letter=ReviewAxis.A,
        name="Correctness",
        short="Spirit and technicality",
        key_questions=(
            "Does the implementation faithfully serve the user's original request?",
            "Are technical decisions consistent with the rationale in the proposal?",
            "Are there gaps where the proposal says one thing but the code does another?",
        ),
    ),
    "axis-B": ReviewAxisSpec(
        id="axis-B",
        letter=ReviewAxis.B,
        name="Test quality",
        short="Test strategy adequacy",
        key_questions=(
            "Favour integration tests over brittle unit tests?",
            "System under test NOT mocked — mock dependencies only?",
            "Shared fixtures for common test values?",
            "Assert observable outcomes, not internal state?",
        ),
    ),
    "axis-C": ReviewAxisSpec(
        id="axis-C",
        letter=ReviewAxis.C,
        name="Elegance",
        short="Complexity matching",
        key_questions=(
            "Design the API you know you will need?",
            "No over-engineering (premature abstractions, plugin systems)?",
            "No under-engineering (cutting corners on security or correctness)?",
            "Complexity proportional to innate problem complexity?",
        ),
    ),
}


TITLE_CONVENTIONS: list[TitleConvention] = [
    TitleConvention(
        pattern="REQUEST: {description}",
        label_ref="L-p1s1_1",
        created_by="epoch,architect",
        phase_ref="p1",
    ),
    TitleConvention(
        pattern="ELICIT: {description}",
        label_ref="L-p2s2_1",
        created_by="architect",
        phase_ref="p2",
    ),
    TitleConvention(
        pattern="URD: {description}",
        label_ref="L-p2s2_2",
        created_by="architect",
        phase_ref="p2",
        extra_label_ref="L-urd",
    ),
    TitleConvention(
        pattern="PROPOSAL-{N}: {description}",
        label_ref="L-p3s3",
        created_by="architect",
        phase_ref="p3",
        note="N increments per revision. Old proposals marked aura:superseded.",
    ),
    TitleConvention(
        pattern="PROPOSAL-{N}-REVIEW-{axis}-{round}: {description}",
        label_ref="L-p4s4",
        created_by="reviewer",
        phase_ref="p4",
        note="axis=A|B|C, round starts at 1",
    ),
    TitleConvention(
        pattern="UAT-{N}: {description}",
        label_ref="L-p5s5",
        created_by="architect",
        phase_ref="p5",
    ),
    TitleConvention(
        pattern="IMPL_PLAN: {description}",
        label_ref="L-p8s8",
        created_by="supervisor",
        phase_ref="p8",
    ),
    TitleConvention(
        pattern="SLICE-{N}: {description}",
        label_ref="L-p9s9",
        created_by="supervisor",
        phase_ref="p9",
        note="N identifies slice within the implementation plan",
    ),
    TitleConvention(
        pattern="SLICE-{N}-REVIEW-{axis}-{round}: {description}",
        label_ref="L-p10s10",
        created_by="reviewer",
        phase_ref="p10",
        note="axis=A|B|C, round starts at 1",
    ),
    TitleConvention(
        pattern="IMPL-REVIEW-{axis}-{round}: {description}",
        label_ref="L-p10s10",
        created_by="supervisor",
        phase_ref="p10",
        note="When reviewing all slices collectively",
    ),
    TitleConvention(
        pattern="FOLLOWUP: {description}",
        label_ref="L-followup",
        created_by="supervisor",
        note=(
            "Follow-up epic created after code review with IMPORTANT/MINOR findings. "
            "Single-parent epic relationship — no followup-of-followup."
        ),
    ),
    TitleConvention(
        pattern="FOLLOWUP_URE: {description}",
        label_ref="L-p2s2_1",
        created_by="supervisor",
        phase_ref="p2",
        note="Scoping URE to determine which IMPORTANT/MINOR findings to address",
    ),
    TitleConvention(
        pattern="FOLLOWUP_URD: {description}",
        label_ref="L-p2s2_2",
        created_by="supervisor",
        phase_ref="p2",
        extra_label_ref="L-urd",
        note="Requirements doc for follow-up scope. References original URD.",
    ),
    TitleConvention(
        pattern="FOLLOWUP_PROPOSAL-{N}: {description}",
        label_ref="L-p3s3",
        created_by="architect",
        phase_ref="p3",
        note="Proposal accounting for original URD + FOLLOWUP_URD + outstanding findings",
    ),
    TitleConvention(
        pattern="FOLLOWUP_IMPL_PLAN: {description}",
        label_ref="L-p8s8",
        created_by="supervisor",
        phase_ref="p8",
        note="Implementation plan for follow-up slices",
    ),
    TitleConvention(
        pattern="FOLLOWUP_SLICE-{N}: {description}",
        label_ref="L-p9s9",
        created_by="supervisor",
        phase_ref="p9",
        note=(
            "Follow-up slice. Adopts IMPORTANT/MINOR leaf tasks from original review as children "
            "(dual-parent: leaf blocks both original severity group AND follow-up slice)."
        ),
    ),
]


# PROCEDURE_STEPS: populated for supervisor + worker as POC (UAT-6).
# Derived from schema.xml <startup-sequence> elements within <substep> of Phase 8 (supervisor)
# and TDD layer descriptions from Phase 9 (worker).
# Other roles have empty tuples — they have no structured procedure steps in schema.xml v2.

PROCEDURE_STEPS: dict[RoleId, tuple[ProcedureStep, ...]] = {
    RoleId.EPOCH: (),
    RoleId.ARCHITECT: (),
    RoleId.REVIEWER: (),
    RoleId.SUPERVISOR: (
        ProcedureStep(
            id="S-supervisor-call-skill",
            order=1,
            instruction="Call Skill(/aura:supervisor) to load role instructions",
            command="Skill(/aura:supervisor)",
        ),
        ProcedureStep(
            id="S-supervisor-read-plan",
            order=2,
            instruction="Read RATIFIED_PLAN and URD via bd show",
            command="bd show <ratified-plan-id> && bd show <urd-id>",
        ),
        ProcedureStep(
            id="S-supervisor-cartographers",
            order=3,
            instruction="Create standing explore team via TeamCreate before any codebase exploration",
            context="TeamCreate with /aura:explore role; minimum 3 agents",
        ),
        ProcedureStep(
            id="S-supervisor-decompose-slices",
            order=4,
            instruction="Decompose into vertical slices",
            context=(
                "Vertical slices give one worker end-to-end ownership of a feature path "
                "(types → tests → impl → wiring) with clear file boundaries"
            ),
            next_state=PhaseId.P8_IMPL_PLAN,
        ),
        ProcedureStep(
            id="S-supervisor-create-leaf-tasks",
            order=5,
            instruction="Create leaf tasks (L1/L2/L3) for every slice",
            command=(
                'bd create --labels aura:p9-impl:s9-slice --title '
                '"SLICE-{K}-L{1,2,3}: <description>" ...'
            ),
        ),
        ProcedureStep(
            id="S-supervisor-spawn-workers",
            order=6,
            instruction="Spawn workers for leaf tasks",
            command="aura-swarm start --epic <epic-id>",
            next_state=PhaseId.P9_SLICE,
        ),
    ),
    RoleId.WORKER: (
        ProcedureStep(
            id="S-worker-types",
            order=1,
            instruction="Types, interfaces, schemas (no deps)",
        ),
        ProcedureStep(
            id="S-worker-tests",
            order=2,
            instruction="Tests importing production code (will fail initially)",
        ),
        ProcedureStep(
            id="S-worker-impl",
            order=3,
            instruction="Make tests pass. Wire with real dependencies. No TODOs.",
            next_state=PhaseId.P9_SLICE,
        ),
    ),
}


# ─── Substep Data (canonical per-phase substep specifications) ────────────────
# Moved from gen_schema.py (mk16) — types.py is the single source of truth.
# Format: phase_id_str → list of substep attribute dicts for XML generation.
# Keys match schema.xml <substep> attributes; special keys:
#   "extra-label"     — adds <extra-label ref="..."/> child element
#   "instances"       — adds <instances count="..." per="..."/> child element
#   "startup-sequence"— adds <startup-sequence> from PROCEDURE_STEPS[SUPERVISOR]

SUBSTEP_DATA: dict[str, list[dict]] = {
    "p1": [
        {
            "id": "s1_1", "type": "classify", "execution": "sequential", "order": "1",
            "label-ref": "L-p1s1_1",
            "description": "Classify request along 4 axes: scope, complexity, risk, domain novelty",
        },
        {
            "id": "s1_2", "type": "research", "execution": "parallel", "order": "2",
            "parallel-group": "p1-discovery", "label-ref": "L-p1s1_2",
            "description": "Find domain standards, prior art, relevant documentation",
        },
        {
            "id": "s1_3", "type": "explore", "execution": "parallel", "order": "2",
            "parallel-group": "p1-discovery", "label-ref": "L-p1s1_3",
            "description": "Codebase exploration for integration points",
        },
    ],
    "p2": [
        {
            "id": "s2_1", "type": "elicit", "execution": "sequential", "order": "1",
            "label-ref": "L-p2s2_1",
            "description": "URE survey: structured Q&A with user to capture requirements",
        },
        {
            "id": "s2_2", "type": "urd", "execution": "sequential", "order": "2",
            "label-ref": "L-p2s2_2",
            "description": "Create URD as single source of truth for requirements",
            "extra-label": "L-urd",
        },
    ],
    "p3": [
        {
            "id": "s3", "type": "propose", "execution": "sequential", "order": "1",
            "label-ref": "L-p3s3",
            "description": (
                "Full technical proposal: interfaces, approach, validation checklist, BDD criteria"
            ),
        },
    ],
    "p4": [
        {
            "id": "s4", "type": "review", "execution": "parallel", "order": "1",
            "label-ref": "L-p4s4",
            "description": "Each reviewer assesses one axis (A/B/C). All 3 must ACCEPT.",
            "instances": {"count": "3", "per": "review-axis"},
        },
    ],
    "p5": [
        {
            "id": "s5", "type": "uat", "execution": "sequential", "order": "1",
            "label-ref": "L-p5s5",
            "description": (
                "Present plan to user with demonstrative examples. "
                "User approves or requests changes."
            ),
        },
    ],
    "p6": [
        {
            "id": "s6", "type": "ratify", "execution": "sequential", "order": "1",
            "label-ref": "L-p6s6",
            "description": (
                "Add ratify label. Mark prior proposals aura:superseded. "
                "Create placeholder IMPL_PLAN."
            ),
        },
    ],
    "p7": [
        {
            "id": "s7", "type": "handoff", "execution": "sequential", "order": "1",
            "label-ref": "L-p7s7",
            "description": (
                "Create handoff document with full inline provenance. Transfer to supervisor."
            ),
        },
    ],
    "p8": [
        {
            "id": "s8", "type": "plan", "execution": "sequential", "order": "1",
            "label-ref": "L-p8s8",
            "description": (
                "Identify production code paths. Create SLICE-N tasks with leaf tasks. "
                "Assign workers."
            ),
            "startup-sequence": True,  # Signal to add startup-sequence from PROCEDURE_STEPS
        },
    ],
    "p9": [
        {
            "id": "s9", "type": "slice", "execution": "parallel", "order": "1",
            "label-ref": "L-p9s9",
            "description": (
                "Each worker owns full vertical: types, tests, implementation, wiring"
            ),
            "instances": {"count": "N", "per": "production-code-path"},
        },
    ],
    "p10": [
        {
            "id": "s10", "type": "review", "execution": "parallel", "order": "1",
            "label-ref": "L-p10s10",
            "description": (
                "Each reviewer reviews ALL slices against their axis. EAGER severity tree."
            ),
            "instances": {"count": "3", "per": "review-axis"},
        },
    ],
    "p11": [
        {
            "id": "s11", "type": "uat", "execution": "sequential", "order": "1",
            "label-ref": "L-p11s11",
            "description": (
                "Present implementation to user. User approves or requests fixes."
            ),
        },
    ],
    "p12": [
        {
            "id": "s12", "type": "landing", "execution": "sequential", "order": "1",
            "label-ref": "L-p12s12",
            "description": "git agent-commit, bd sync, git push. Close upstream tasks.",
        },
    ],
}
