"""Protocol type definitions for the Aura multi-agent protocol.

All enums are str Enums for JSON/Temporal serialization compatibility.
All spec dataclasses are frozen (immutable) for use as dict keys and safe sharing.

Source of truth: this file (types.py). schema.xml is generated from Python via gen_schema.py.
Integration test: tests/test_schema_types_sync.py verifies Python types match schema.xml.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


# ─── Enums ────────────────────────────────────────────────────────────────────


class PhaseId(StrEnum):
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


class Domain(StrEnum):
    """Phase domain classification.

    Values match schema.xml <enum name="DomainType"> entries.
    """

    USER = "user"
    PLAN = "plan"
    IMPL = "impl"


class RoleId(StrEnum):
    """Agent role identifiers.

    Values match schema.xml <role id="..."> elements.
    """

    EPOCH = "epoch"
    ARCHITECT = "architect"
    REVIEWER = "reviewer"
    SUPERVISOR = "supervisor"
    WORKER = "worker"


class VoteType(StrEnum):
    """Binary review vote.

    Values match schema.xml <enum name="VoteType"> entries.
    """

    ACCEPT = "ACCEPT"
    REVISE = "REVISE"


class SeverityLevel(StrEnum):
    """Code review finding severity.

    Values match schema.xml <enum name="SeverityLevel"> entries.
    """

    BLOCKER = "BLOCKER"
    IMPORTANT = "IMPORTANT"
    MINOR = "MINOR"


class ExecutionMode(StrEnum):
    """Substep execution mode within a phase.

    Values match schema.xml <enum name="ExecutionMode"> entries.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ContentLevel(StrEnum):
    """Handoff document content level.

    Values match schema.xml <enum name="ContentLevel"> entries.
    """

    FULL_PROVENANCE = "full-provenance"
    SUMMARY_WITH_IDS = "summary-with-ids"


class ReviewAxis(StrEnum):
    """Review axis semantic identifiers used in review votes.

    Values are lowercase wire-format strings used in JSON/Temporal serialization.
    Previously: A="A", B="B", C="C" (single-letter). Now semantic names for clarity.
    """

    CORRECTNESS = "correctness"
    TEST_QUALITY = "test_quality"
    ELEGANCE = "elegance"


class SubstepType(StrEnum):
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


class ExampleLabel(StrEnum):
    """Label type for a code example.

    Values match schema.xml <example label="..."> attributes.
    """

    CORRECT = "correct"
    ANTI_PATTERN = "anti-pattern"
    CONTEXT = "context"
    TEMPLATE = "template"


class ExampleLang(StrEnum):
    """Programming language / format for a code example.

    Values match schema.xml <example lang="..."> attributes.
    """

    BASH = "bash"
    GO = "go"
    PYTHON = "python"
    PSEUDO = "pseudo"
    XML = "xml"
    JSON = "json"
    MARKDOWN = "markdown"


class GateType(StrEnum):
    """Quality gate type for a completion checklist.

    Values match schema.xml <checklist gate="..."> attributes.
    """

    COMPLETION = "completion"
    SLICE_CLOSURE = "slice-closure"
    REVIEW_READY = "review-ready"
    LANDING = "landing"


class WorkflowExecution(StrEnum):
    """Execution mode for a workflow stage.

    Values match schema.xml <stage execution="..."> attributes.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL_LOOP = "conditional-loop"


class ExitConditionType(StrEnum):
    """Exit condition outcome classification for a workflow stage.

    Values match schema.xml <exit-condition type="..."> attributes.
    Closed enum — known set of exit outcomes; use ExitConditionType not str.
    """

    SUCCESS = "success"
    CONTINUE = "continue"
    ESCALATE = "escalate"
    PROCEED = "proceed"


class FigureId(StrEnum):
    """Unique identifier for each figure.

    Values match schema.xml <figure id='...'> attributes.
    Keyed in FIGURE_SPECS.
    """

    LAYER_CAKE = "layer-cake"
    RIDE_THE_WAVE = "ride-the-wave"
    ARCHITECT_STATE_FLOW = "architect-state-flow"


class FigureType(StrEnum):
    """Type of figure content.

    Values match schema.xml <figure type='...'> attributes.
    """

    ASCII_DIAGRAM = "ascii-diagram"


class SectionRef(StrEnum):
    """Section in which a figure can be placed.

    Values match schema.xml <figure section-ref='...'> attributes.
    """

    WORKFLOWS = "workflows"


class CommandId(StrEnum):
    """Unique identifier for each protocol command (skill).

    Values match schema.xml <command id='...'> attributes.
    Keyed in COMMAND_SPECS.
    Member names are UPPER_SNAKE_CASE of the id with 'cmd-' prefix stripped.
    """

    EPOCH = "cmd-epoch"
    PLAN = "cmd-plan"
    STATUS = "cmd-status"
    USER_REQUEST = "cmd-user-request"
    USER_ELICIT = "cmd-user-elicit"
    USER_UAT = "cmd-user-uat"
    ARCHITECT = "cmd-architect"
    ARCH_PROPOSE = "cmd-arch-propose"
    ARCH_REVIEW = "cmd-arch-review"
    ARCH_RATIFY = "cmd-arch-ratify"
    ARCH_HANDOFF = "cmd-arch-handoff"
    SUPERVISOR = "cmd-supervisor"
    SUP_PLAN = "cmd-sup-plan"
    SUP_SPAWN = "cmd-sup-spawn"
    SUP_TRACK = "cmd-sup-track"
    SUP_COMMIT = "cmd-sup-commit"
    WORKER = "cmd-worker"
    WORK_IMPL = "cmd-work-impl"
    WORK_COMPLETE = "cmd-work-complete"
    WORK_BLOCKED = "cmd-work-blocked"
    REVIEWER = "cmd-reviewer"
    REV_PLAN = "cmd-rev-plan"
    REV_CODE = "cmd-rev-code"
    REV_COMMENT = "cmd-rev-comment"
    REV_VOTE = "cmd-rev-vote"
    IMPL_SLICE = "cmd-impl-slice"
    IMPL_REVIEW = "cmd-impl-review"
    MSG_SEND = "cmd-msg-send"
    MSG_RECEIVE = "cmd-msg-receive"
    MSG_BROADCAST = "cmd-msg-broadcast"
    MSG_ACK = "cmd-msg-ack"
    EXPLORE = "cmd-explore"
    RESEARCH = "cmd-research"
    TEST = "cmd-test"
    FEEDBACK = "cmd-feedback"


# ─── Step Slug + Skill Ref Namespaces ─────────────────────────────────────────


class StepSlug:
    """Typed namespace for ProcedureStep.id slug constants.

    Nested StrEnums allow typed references in PROCEDURE_STEPS and tests
    while remaining transparently interoperable with str (comparison,
    XML attribute assignment, etc. all work without conversion).
    """

    class Supervisor(StrEnum):
        """Slug constants for supervisor procedure step IDs."""

        CallSkill = "S-supervisor-call-skill"
        ReadPlan = "S-supervisor-read-plan"
        ExploreEphemeral = "S-supervisor-explore-ephemeral"
        DecomposeSlices = "S-supervisor-decompose-slices"
        CreateLeafTasks = "S-supervisor-create-leaf-tasks"
        SpawnWorkers = "S-supervisor-spawn-workers"

    class Worker(StrEnum):
        """Slug constants for worker procedure step IDs."""

        Types = "S-worker-types"
        Tests = "S-worker-tests"
        Impl = "S-worker-impl"


class SkillRef(StrEnum):
    """Skill invocation strings for ProcedureStep.command.

    Values match the Skill(/aura:<role>) directive format.
    """

    SUPERVISOR = "Skill(/aura:supervisor)"
    WORKER = "Skill(/aura:worker)"


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
class SerializableTransition:
    """A single phase transition that is fully JSON-serializable.

    Mirrors Transition but uses only StrEnum/str fields (no frozenset/tuple)
    for safe round-tripping through Temporal DataConverter.
    """

    to_phase: PhaseId
    condition: str
    action: str | None = None


@dataclass(frozen=True)
class SerializablePhaseSpec:
    """JSON-serializable frozen snapshot of a PhaseSpec.

    Replaces frozenset[RoleId] with list[RoleId] (sorted by .value) and
    tuple[Transition, ...] with list[SerializableTransition] so that
    Temporal's JSON DataConverter can encode/decode the type without error.
    """

    id: PhaseId
    number: int
    domain: Domain
    name: str
    owner_roles: list[RoleId]
    transitions: list[SerializableTransition]

    @staticmethod
    def from_spec(spec: "PhaseSpec") -> "SerializablePhaseSpec":
        """Convert a frozen PhaseSpec into a SerializablePhaseSpec.

        owner_roles preserves frozenset iteration order (which is the declaration
        order from PHASE_SPECS) rather than sorting alphabetically.
        """
        return SerializablePhaseSpec(
            id=spec.id,
            number=spec.number,
            domain=spec.domain,
            name=spec.name,
            owner_roles=list(spec.owner_roles),
            transitions=[
                SerializableTransition(
                    to_phase=t.to_phase,
                    condition=t.condition,
                    action=t.action,
                )
                for t in spec.transitions
            ],
        )


@dataclass(frozen=True)
class PhaseInput:
    """Input payload passed to a phase child workflow.

    Contains the epoch identity and a serializable snapshot of the phase spec.
    All fields are Temporal DataConverter-safe (StrEnum, str, frozen dataclass).
    """

    epoch_id: str
    phase_spec: SerializablePhaseSpec


@dataclass(frozen=True)
class PhaseResult:
    """Result payload returned by a phase child workflow.

    Contains the phase identity, success flag, number of open blockers, and
    the optional vote result (only present for review phases).
    """

    phase_id: PhaseId
    success: bool
    blocker_count: int = 0
    vote_result: VoteType | None = None


@dataclass(frozen=True)
class ConstraintSpec:
    """A single protocol constraint in Given/When/Then/Should-not format.

    Derived from schema.xml <constraint> elements.
    command: optional primary command to run for this constraint (e.g. 'git agent-commit -m ...').
    examples: optional code examples illustrating correct / anti-pattern usage.
    """

    id: str
    given: str
    when: str
    then: str
    should_not: str
    command: str | None = None
    examples: tuple[CodeExample, ...] = ()


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
    introduction: 1-2 sentence opener describing the role's purpose.
    ownership_narrative: prose description of what the role owns (the "What You Own" section).
    behaviors: tactical Given/When/Then guidance specific to this role (not formal protocol constraints).
    """

    id: RoleId
    name: str
    description: str
    owned_phases: frozenset[PhaseId]
    introduction: str | None = None
    ownership_narrative: str | None = None
    behaviors: tuple[BehaviorSpec, ...] = ()
    tools: tuple[str, ...] = ()
    model: str | None = None
    thinking: str | None = None


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

    id: CommandId
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
        examples:    Optional code examples illustrating how to execute this step.
    """

    id: str
    order: int
    instruction: str
    command: str | None = None
    context: str | None = None
    next_state: PhaseId | None = None
    examples: tuple[CodeExample, ...] = ()


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


# ─── Schema Extension Dataclasses ─────────────────────────────────────────────
# New types for R1-R7: code examples on constraints/steps, role behaviors,
# completion checklists, coordination commands, and workflow specifications.
# Placement: before canonical dicts so instances can be created in dict literals.


@dataclass(frozen=True)
class CodeExample:
    """A labeled code example for a constraint or procedure step.

    Derived from schema.xml <example> child elements under <constraint> or <step>.
    also_illustrates: optional cross-reference to another constraint or concept.
    """

    id: str
    lang: ExampleLang
    label: ExampleLabel
    code: str
    also_illustrates: str | None = None


@dataclass(frozen=True)
class BehaviorSpec:
    """A role-tactical behavior in Given/When/Then/Should-not format.

    Distinct from ConstraintSpec: behaviors are role-specific guidance that are NOT
    formal protocol constraints — they are best-practice patterns captured from
    hand-written SKILL.md sections.
    Derived from schema.xml <behavior> child elements under <role>.
    """

    id: str
    given: str
    when: str
    then: str
    should_not: str


@dataclass(frozen=True)
class ChecklistItem:
    """A single item in a completion checklist.

    Derived from schema.xml <item> child elements under <checklist>.
    required: whether this item is mandatory (True) or optional (False).
    """

    id: str
    text: str
    required: bool = True


@dataclass(frozen=True)
class Checklist:
    """A completion checklist for a role at a specific quality gate.

    Derived from schema.xml <checklist> elements within <checklists>.
    Keyed in CHECKLIST_SPECS by "{role}-{gate}".
    """

    role_ref: RoleId
    gate: GateType
    items: tuple[ChecklistItem, ...]


@dataclass(frozen=True)
class CoordinationCommand:
    """A coordination command for inter-agent communication via Beads.

    Derived from schema.xml <coordination-command> elements.
    role_ref: None means the command is shared across all roles.
    shared: True when the command appears in every role's coordination table.
    """

    id: str
    action: str
    template: str
    role_ref: RoleId | None = None
    shared: bool = False


@dataclass(frozen=True)
class WorkflowAction:
    """A single action within a workflow stage.

    Derived from schema.xml <action> child elements under <stage>.
    command: optional concrete shell/tool command to run for this action.
    """

    id: str
    instruction: str
    command: str | None = None


@dataclass(frozen=True)
class ExitCondition:
    """An exit condition for a workflow stage.

    Derived from schema.xml <exit-condition> child elements under <stage>.
    type: MUST be ExitConditionType (closed enum), NOT str.
    """

    type: ExitConditionType
    condition: str


@dataclass(frozen=True)
class WorkflowStage:
    """A single stage in an agent workflow.

    Derived from schema.xml <stage> child elements under <workflow>.
    phase_ref: optional phase this stage maps to in the 12-phase lifecycle.
    """

    id: str
    name: str
    order: int
    execution: WorkflowExecution
    phase_ref: PhaseId | None = None
    actions: tuple[WorkflowAction, ...] = ()
    exit_conditions: tuple[ExitCondition, ...] = ()


@dataclass(frozen=True)
class Workflow:
    """A complete workflow specification for an agent role.

    Derived from schema.xml <workflow> elements within <workflows>.
    Keyed in WORKFLOW_SPECS by workflow id.
    """

    id: str
    name: str
    role_ref: RoleId
    description: str
    stages: tuple[WorkflowStage, ...]


@dataclass(frozen=True)
class Figure:
    """A figure specification (ASCII diagram or other visual).

    Derived from YAML files in skills/protocol/figures/.
    Keyed in FIGURE_SPECS by FigureId.
    M:N relationship with roles (role_refs), workflows (workflow_refs),
    and commands (command_refs).
    """

    id: FigureId
    title: str
    type: FigureType
    role_refs: frozenset[RoleId]
    section_ref: SectionRef
    workflow_refs: frozenset[str]
    command_refs: frozenset[CommandId] = frozenset()
    content: str = ""


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
        command="bd dep add <parent> --blocked-by <child>",
        examples=(
            CodeExample(
                id="C-audit-dep-chain-full",
                lang=ExampleLang.BASH,
                label=ExampleLabel.CORRECT,
                code=(
                    "# Full dependency chain: work flows bottom-up, closure flows top-down\n"
                    "bd dep add request-id --blocked-by ure-id\n"
                    "bd dep add ure-id --blocked-by proposal-id\n"
                    "bd dep add proposal-id --blocked-by impl-plan-id\n"
                    "bd dep add impl-plan-id --blocked-by slice-1-id\n"
                    "bd dep add slice-1-id --blocked-by leaf-task-a-id"
                ),
            ),
        ),
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
        examples=(
            CodeExample(
                id="C-severity-eager-create",
                lang=ExampleLang.BASH,
                label=ExampleLabel.CORRECT,
                code=(
                    "# Create all 3 severity groups immediately (even if empty)\n"
                    'bd create --title "SLICE-1-REVIEW-A-1 BLOCKER" \\\n'
                    '  --labels "aura:severity:blocker,aura:p10-impl:s10-review"\n'
                    'bd create --title "SLICE-1-REVIEW-A-1 IMPORTANT" \\\n'
                    '  --labels "aura:severity:important,aura:p10-impl:s10-review"\n'
                    'bd create --title "SLICE-1-REVIEW-A-1 MINOR" \\\n'
                    '  --labels "aura:severity:minor,aura:p10-impl:s10-review"\n'
                    "\n"
                    "# Close empty groups immediately\n"
                    "bd close <empty-important-id>\n"
                    "bd close <empty-minor-id>"
                ),
            ),
            CodeExample(
                id="C-severity-eager-anti",
                lang=ExampleLang.BASH,
                label=ExampleLabel.ANTI_PATTERN,
                code=(
                    "# WRONG: only creating groups when findings exist\n"
                    "# This skips empty groups and breaks the audit trail\n"
                    'if blocker_findings:\n'
                    '    bd create --title "BLOCKER" ...'
                ),
            ),
        ),
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
    "C-supervisor-explore-ephemeral": ConstraintSpec(
        id="C-supervisor-explore-ephemeral",
        given="supervisor needs codebase exploration",
        when="starting Phase 8 (IMPL_PLAN)",
        then=(
            "spawn ephemeral Explore subagents via Task tool for scoped codebase queries; "
            "each subagent is short-lived and returns findings; no standing team overhead"
        ),
        should_not=(
            "explore the codebase directly as supervisor; "
            "maintain a standing explore team"
        ),
    ),
    "C-clean-review-exit": ConstraintSpec(
        id="C-clean-review-exit",
        given="per-slice code review",
        when="evaluating review results",
        then=(
            "clean review exit requires 0 BLOCKERs AND 0 IMPORTANTs; "
            "MINORs are acceptable and tracked in FOLLOWUP epic; "
            "each slice has its own independent review cycle counter (max 3 cycles); "
            "after 3 failed cycles, escalate to architect for re-planning"
        ),
        should_not=(
            "accept review with open BLOCKERs or IMPORTANTs; "
            "batch review across multiple slices; "
            "exceed 3 cycles without escalating; "
            "escalate to user instead of architect"
        ),
    ),
    "C-autonomous-progression": ConstraintSpec(
        id="C-autonomous-progression",
        given="supervisor orchestrating phases",
        when="deciding whether to proceed",
        then=(
            "4 user-gated phases only: (1) research depth decision, (2) URE survey, "
            "(3) Plan UAT, (4) Impl UAT; all other phase transitions are auto-ratified "
            "by the supervisor; after Plan UAT ACCEPT, proceed directly to ratification "
            "without user gate"
        ),
        should_not=(
            "add additional user gates beyond the 4 defined; "
            "require user approval for ratification after UAT ACCEPT"
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
            "slices must be reviewed at least once by ephemeral reviewers before closure; "
            "only the supervisor closes slices, after review passes"
        ),
        should_not=(
            "close slices immediately upon worker completion; "
            "allow workers to close their own slices"
        ),
    ),
    "C-max-review-cycles": ConstraintSpec(
        id="C-max-review-cycles",
        given="per-slice review-fix cycles are ongoing",
        when="counting review-fix iterations per slice",
        then=(
            "limit to a maximum of 3 cycles per slice; "
            "clean review exit = 0 BLOCKERs + 0 IMPORTANTs; "
            "after cycle 3, escalate to architect for re-planning if BLOCKERs or IMPORTANTs remain; "
            "remaining IMPORTANT findings move to FOLLOWUP epic"
        ),
        should_not=(
            "exceed 3 review cycles per slice; "
            "escalate to user instead of architect; "
            "batch review across multiple slices"
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
        command="bd dep add <slice-id> --blocked-by <leaf-task-id>",
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
            "they skip role-critical procedures like ephemeral exploration and leaf task creation"
        ),
    ),
    "C-dep-direction": ConstraintSpec(
        id="C-dep-direction",
        given="adding a Beads dependency",
        when="determining direction",
        then="parent blocked-by child: bd dep add stays-open --blocked-by must-finish-first",
        should_not="invert (child blocked-by parent)",
        command="bd dep add <stays-open> --blocked-by <must-finish-first>",
        examples=(
            CodeExample(
                id="C-dep-direction-correct",
                lang=ExampleLang.BASH,
                label=ExampleLabel.CORRECT,
                code='bd dep add request-id --blocked-by ure-id',
                also_illustrates="C-audit-dep-chain",
            ),
            CodeExample(
                id="C-dep-direction-anti",
                lang=ExampleLang.BASH,
                label=ExampleLabel.ANTI_PATTERN,
                code='bd dep add ure-id --blocked-by request-id',
            ),
        ),
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
        command="git agent-commit -m ...",
        examples=(
            CodeExample(
                id="C-agent-commit-correct",
                lang=ExampleLang.BASH,
                label=ExampleLabel.CORRECT,
                code='git agent-commit -m "feat: add login"',
            ),
            CodeExample(
                id="C-agent-commit-anti",
                lang=ExampleLang.BASH,
                label=ExampleLabel.ANTI_PATTERN,
                code='git commit -m "feat: add login"',
            ),
        ),
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
        given="user interview (Request, URE, or UAT), URD update, or mid-implementation design decision",
        when="recording in Beads",
        then="capture full question text, ALL option descriptions, AND user's verbatim response; the URD is the living document of ALL user requests, URE, UAT, and mid-implementation design decisions and feedback — update it via bd comments add whenever user intent is captured",
        should_not="summarize options as (1)/(2)/(3) without option text, or paraphrase user responses",
        examples=(
            CodeExample(
                id="C-ure-verbatim-correct",
                lang=ExampleLang.BASH,
                label=ExampleLabel.CORRECT,
                code=(
                    "# Full question, all options with descriptions, verbatim response\n"
                    'bd create --title "UAT: Plan acceptance for feature-X" \\\n'
                    '  --description "## Component: Verbose fields\n'
                    "**Question:** Which verbose fields are useful?\n"
                    "**Options:**\n"
                    "- backupDir (full path): Shows where the backup landed\n"
                    "- session ID: Enables log correlation across events\n"
                    "- repo path + hash: Confirms which git repo was detected\n"
                    "**User response:** backupDir (full path), session ID\n"
                    '**Decision:** ACCEPT"'
                ),
            ),
            CodeExample(
                id="C-ure-verbatim-anti",
                lang=ExampleLang.BASH,
                label=ExampleLabel.ANTI_PATTERN,
                code=(
                    "# WRONG: options summarized as numbers, response paraphrased\n"
                    'bd create --title "UAT: Plan acceptance" \\\n'
                    '  --description "Asked about verbose fields (1-4). '
                    'User picked 1 and 2. Accepted."'
                ),
            ),
        ),
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
        introduction=(
            "You are the master orchestrator for the full 12-phase epoch lifecycle. "
            "You delegate planning phases (1-7) to the architect and implementation phases (7-12) "
            "to the supervisor."
        ),
        ownership_narrative=(
            "You own the full 12-phase lifecycle from Request to Landing. "
            "You delegate phases 1-7 to the architect and phases 7-12 to the supervisor. "
            "The epoch role coordinates the complete workflow end-to-end and is the only role "
            "that spans all phases."
        ),
        tools=("Read", "Glob", "Grep", "Bash", "Skill", "Agent", "Task"),
        model="opus",
        thinking="medium",
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
        introduction=(
            "You design specifications and coordinate the planning phases of epochs. "
            "See the project's AGENTS.md and ~/.claude/CLAUDE.md for coding standards and constraints."
        ),
        ownership_narrative=(
            "You own Phases 1-7 of the epoch: "
            "capture and classify user request (p1), "
            "run requirements elicitation URE survey (p2), "
            "create PROPOSAL-N with full technical plan (p3), "
            "spawn 3 axis-specific reviewers and loop until consensus (p4), "
            "present plan to user for acceptance test (p5), "
            "add ratify label to accepted PROPOSAL-N (p6), "
            "create handoff document and transfer to supervisor (p7)."
        ),
        behaviors=(
            BehaviorSpec(
                id="B-arch-elicit",
                given="user request captured",
                when="starting",
                then="run /aura:user-elicit for URE survey",
                should_not="skip elicitation phase",
            ),
            BehaviorSpec(
                id="B-arch-bdd",
                given="a feature request",
                when="writing plan",
                then="use BDD Given/When/Then format with acceptance criteria",
                should_not="write vague requirements",
            ),
            BehaviorSpec(
                id="B-arch-reviewers",
                given="plan ready",
                when="requesting review",
                then="spawn 3 axis-specific reviewers (A=Correctness, B=Test quality, C=Elegance)",
                should_not="spawn reviewers without axis assignment",
            ),
            BehaviorSpec(
                id="B-arch-uat",
                given="consensus reached (all 3 ACCEPT)",
                when="proceeding",
                then="run /aura:user-uat before ratifying",
                should_not="skip user acceptance test",
            ),
            BehaviorSpec(
                id="B-arch-ratify",
                given="UAT passed",
                when="ratifying",
                then="add aura:p6-plan:s6-ratify label to PROPOSAL-N",
                should_not="close or delete the proposal task",
            ),
        ),
        tools=("Read", "Glob", "Grep", "Bash", "Skill", "Agent", "Task"),
        model="opus",
        thinking="medium",
    ),
    RoleId.REVIEWER: RoleSpec(
        id=RoleId.REVIEWER,
        name="Reviewer",
        description="End-user alignment reviewer for plans and code",
        owned_phases=frozenset({PhaseId.P4_REVIEW, PhaseId.P10_CODE_REVIEW}),
        introduction=(
            "You review from an end-user alignment perspective. "
            "See the project's protocol/CONSTRAINTS.md for coding standards."
        ),
        ownership_narrative=(
            "You participate in two phases: "
            "Phase 4 (plan review) — evaluate PROPOSAL-N against one axis using binary ACCEPT/REVISE, "
            "NO severity tree; "
            "Phase 10 (code review) — review ALL implementation slices against your axis using "
            "full severity tree (BLOCKER/IMPORTANT/MINOR), EAGER creation of all 3 severity groups."
        ),
        behaviors=(
            BehaviorSpec(
                id="B-rev-end-user",
                given="a review assignment",
                when="reviewing",
                then="apply end-user alignment criteria",
                should_not="focus only on technical details",
            ),
            BehaviorSpec(
                id="B-rev-revise-feedback",
                given="issues found",
                when="voting",
                then="vote REVISE with specific actionable feedback",
                should_not="vote REVISE without suggestions",
            ),
            BehaviorSpec(
                id="B-rev-accept",
                given="all criteria met",
                when="voting",
                then="vote ACCEPT with brief rationale",
                should_not="delay consensus unnecessarily",
            ),
            BehaviorSpec(
                id="B-rev-all-slices",

                given="impl review (Phase 10)",
                when="assigned",
                then="review ALL slices (not just one)",
                should_not="skip any slice",
            ),
        ),
        tools=("Read", "Glob", "Grep", "Bash", "Skill"),
        model="sonnet",
    ),
    RoleId.SUPERVISOR: RoleSpec(
        id=RoleId.SUPERVISOR,
        name="Supervisor",
        description="Task coordinator, spawns workers, manages parallel execution",
        owned_phases=frozenset({
            PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT, PhaseId.P12_LANDING,
        }),
        introduction=(
            "You coordinate parallel task execution. "
            "See the project's AGENTS.md and ~/.claude/CLAUDE.md for coding standards and constraints."
        ),
        ownership_narrative=(
            "You own Phases 7-12 of the epoch: "
            "receive handoff from architect (p7), "
            "create vertical slice decomposition IMPL_PLAN (p8), "
            "spawn workers for parallel implementation SLICE-N (p9), "
            "spawn ephemeral reviewers for per-slice code review with severity tree (p10), "
            "coordinate user acceptance test (p11), "
            "commit, push, and hand off (p12). "
            "You NEVER implement code directly — all implementation is delegated to workers."
        ),
        behaviors=(
            BehaviorSpec(
                id="B-sup-read-context",
                given="handoff received",
                when="starting",
                then="read ratified plan, URD, UAT, and elicit tasks for full context",
                should_not="start without reading all four",
            ),
            BehaviorSpec(
                id="B-sup-model-trivial",
                given="trivial changes (single-file edits, config tweaks, typo fixes)",
                when="spawning a worker",
                then="use model: haiku to minimize cost and latency",
                should_not="use a heavyweight model for trivial work",
            ),
            BehaviorSpec(
                id="B-sup-model-nontrivial",
                given="non-trivial changes (multi-file, architectural, logic-heavy)",
                when="spawning a worker",
                then="prefer model: sonnet for the Task tool to ensure quality",
                should_not="default to haiku for complex work",
            ),
            BehaviorSpec(
                id="B-sup-explore-ephemeral",
                given="codebase exploration needed",
                when="needing to understand a codebase area",
                then=(
                    "spawn an ephemeral Explore subagent via Task tool with a scoped query; "
                    "each subagent is short-lived and returns findings"
                ),
                should_not="explore the codebase directly as supervisor or maintain a standing explore team",
            ),
            BehaviorSpec(
                id="B-sup-ride-the-wave",
                given="Phase 8-10 execution",
                when="starting implementation",
                then=(
                    "follow the Ride the Wave cycle: plan tasks with integration points, "
                    "launch the wave of workers, spawn ephemeral reviewers for per-slice review "
                    "(clean exit = 0 BLOCKERs + 0 IMPORTANTs), workers fix per-slice with atomic commits, "
                    "max 3 cycles per slice, escalate to architect after cycle 3"
                ),
                should_not="skip any stage; batch review across slices; exceed 3 review cycles per slice",
            ),
        ),
        tools=("Read", "Glob", "Grep", "Bash", "Skill", "Agent", "Task"),
        model="opus",
        thinking="medium",
    ),
    RoleId.WORKER: RoleSpec(
        id=RoleId.WORKER,
        name="Worker",
        description="Vertical slice implementer (full production code path)",
        owned_phases=frozenset({PhaseId.P9_SLICE}),
        introduction=(
            "You own a vertical slice (full production code path from CLI/API entry point "
            "→ service → types). "
            "See the project's AGENTS.md and ~/.claude/CLAUDE.md for coding standards and constraints."
        ),
        ownership_narrative=(
            "NOT: A single file or horizontal layer (e.g., 'all types' or 'all tests'). "
            "YES: A full vertical slice (complete production code path end-to-end). "
            "You own the FEATURE end-to-end, not a layer or file. "
            "Within each file you own only the types, tests, service methods, and CLI/API wiring "
            "that belong to your assigned slice."
        ),
        behaviors=(
            BehaviorSpec(
                id="B-worker-vertical-ownership",
                given="vertical slice assignment",
                when="implementing",
                then="own full production code path (types → tests → impl → wiring)",
                should_not="implement only horizontal layer",
            ),
            BehaviorSpec(
                id="B-worker-plan-backwards",
                given="production code path",
                when="planning",
                then="plan backwards from end point to types",
                should_not="start with types without knowing the end",
            ),
            BehaviorSpec(
                id="B-worker-test-production-code",
                given="tests",
                when="writing",
                then="import actual production code (CLI/API users will run)",
                should_not="create test-only export or dual code paths",
            ),
            BehaviorSpec(
                id="B-worker-verify-production",
                given="implementation complete",
                when="verifying",
                then="run actual production code path manually",
                should_not="rely only on unit tests passing",
            ),
            BehaviorSpec(
                id="B-worker-blocker",
                given="a blocker",
                when="unable to proceed",
                then="use /aura:worker-blocked with details",
                should_not="guess or work around",
            ),
        ),
        tools=("Read", "Glob", "Grep", "Bash", "Skill", "Edit", "Write"),
        model="sonnet",
    ),
}


COMMAND_SPECS: dict[CommandId, CommandSpec] = {
    CommandId.EPOCH: CommandSpec(
        id=CommandId.EPOCH,
        name="aura:epoch",
        description="Master orchestrator for full 12-phase workflow",
        role_ref=RoleId.EPOCH,
        phases=("p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12"),
        file="skills/epoch/SKILL.md",
        creates_labels=(),
    ),
    CommandId.PLAN: CommandSpec(
        id=CommandId.PLAN,
        name="aura:plan",
        description="Plan coordination across phases 1-6",
        role_ref=RoleId.ARCHITECT,
        phases=("p1", "p2", "p3", "p4", "p5", "p6"),
        file="skills/plan/SKILL.md",
        creates_labels=(),
    ),
    CommandId.STATUS: CommandSpec(
        id=CommandId.STATUS,
        name="aura:status",
        description="Project status and monitoring via Beads queries",
        role_ref=None,
        phases=(),
        file="skills/status/SKILL.md",
        creates_labels=(),
    ),
    CommandId.USER_REQUEST: CommandSpec(
        id=CommandId.USER_REQUEST,
        name="aura:user:request",
        description="Capture user feature request verbatim (Phase 1)",
        role_ref=RoleId.ARCHITECT,
        phases=("p1",),
        file="skills/user-request/SKILL.md",
        creates_labels=("L-p1s1_1",),
    ),
    CommandId.USER_ELICIT: CommandSpec(
        id=CommandId.USER_ELICIT,
        name="aura:user:elicit",
        description="User Requirements Elicitation survey (Phase 2)",
        role_ref=RoleId.ARCHITECT,
        phases=("p2",),
        file="skills/user-elicit/SKILL.md",
        creates_labels=("L-p2s2_1", "L-p2s2_2", "L-urd"),
    ),
    CommandId.USER_UAT: CommandSpec(
        id=CommandId.USER_UAT,
        name="aura:user:uat",
        description="User Acceptance Testing with demonstrative examples",
        role_ref=None,
        phases=("p5", "p11"),
        file="skills/user-uat/SKILL.md",
        creates_labels=("L-p5s5", "L-p11s11"),
    ),
    CommandId.ARCHITECT: CommandSpec(
        id=CommandId.ARCHITECT,
        name="aura:architect",
        description="Specification writer and implementation designer",
        role_ref=RoleId.ARCHITECT,
        phases=("p1", "p2", "p3", "p4", "p5", "p6", "p7"),
        file="skills/architect/SKILL.md",
        creates_labels=(),
    ),
    CommandId.ARCH_PROPOSE: CommandSpec(
        id=CommandId.ARCH_PROPOSE,
        name="aura:architect:propose-plan",
        description="Create PROPOSAL-N task with full technical plan",
        role_ref=RoleId.ARCHITECT,
        phases=("p3",),
        file="skills/architect-propose-plan/SKILL.md",
        creates_labels=("L-p3s3",),
    ),
    CommandId.ARCH_REVIEW: CommandSpec(
        id=CommandId.ARCH_REVIEW,
        name="aura:architect:request-review",
        description="Spawn 3 axis-specific reviewers (A/B/C)",
        role_ref=RoleId.ARCHITECT,
        phases=("p4",),
        file="skills/architect-request-review/SKILL.md",
        creates_labels=("L-p4s4",),
    ),
    CommandId.ARCH_RATIFY: CommandSpec(
        id=CommandId.ARCH_RATIFY,
        name="aura:architect:ratify",
        description="Ratify proposal, mark old proposals aura:superseded",
        role_ref=RoleId.ARCHITECT,
        phases=("p6",),
        file="skills/architect-ratify/SKILL.md",
        creates_labels=("L-p6s6", "L-superseded"),
    ),
    CommandId.ARCH_HANDOFF: CommandSpec(
        id=CommandId.ARCH_HANDOFF,
        name="aura:architect:handoff",
        description="Create handoff document and transfer to supervisor",
        role_ref=RoleId.ARCHITECT,
        phases=("p7",),
        file="skills/architect-handoff/SKILL.md",
        creates_labels=("L-p7s7",),
    ),
    CommandId.SUPERVISOR: CommandSpec(
        id=CommandId.SUPERVISOR,
        name="aura:supervisor",
        description="Task coordinator, spawns workers, manages parallel execution",
        role_ref=RoleId.SUPERVISOR,
        phases=("p7", "p8", "p9", "p10", "p11", "p12"),
        file="skills/supervisor/SKILL.md",
        creates_labels=(),
    ),
    CommandId.SUP_PLAN: CommandSpec(
        id=CommandId.SUP_PLAN,
        name="aura:supervisor:plan-tasks",
        description="Decompose ratified plan into vertical slices (SLICE-N)",
        role_ref=RoleId.SUPERVISOR,
        phases=("p8",),
        file="skills/supervisor-plan-tasks/SKILL.md",
        creates_labels=("L-p8s8", "L-p9s9"),
    ),
    CommandId.SUP_SPAWN: CommandSpec(
        id=CommandId.SUP_SPAWN,
        name="aura:supervisor:spawn-worker",
        description="Launch a worker agent for an assigned slice",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9",),
        file="skills/supervisor-spawn-worker/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    CommandId.SUP_TRACK: CommandSpec(
        id=CommandId.SUP_TRACK,
        name="aura:supervisor:track-progress",
        description="Monitor worker status via Beads",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9", "p10"),
        file="skills/supervisor-track-progress/SKILL.md",
        creates_labels=(),
    ),
    CommandId.SUP_COMMIT: CommandSpec(
        id=CommandId.SUP_COMMIT,
        name="aura:supervisor:commit",
        description="Atomic commit per completed layer/slice",
        role_ref=RoleId.SUPERVISOR,
        phases=("p12",),
        file="skills/supervisor-commit/SKILL.md",
        creates_labels=("L-p12s12",),
    ),
    CommandId.WORKER: CommandSpec(
        id=CommandId.WORKER,
        name="aura:worker",
        description="Vertical slice implementer (full production code path)",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker/SKILL.md",
        creates_labels=(),
    ),
    CommandId.WORK_IMPL: CommandSpec(
        id=CommandId.WORK_IMPL,
        name="aura:worker:implement",
        description="Implement assigned vertical slice following TDD layers",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-implement/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    CommandId.WORK_COMPLETE: CommandSpec(
        id=CommandId.WORK_COMPLETE,
        name="aura:worker:complete",
        description="Signal slice completion after quality gates pass",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-complete/SKILL.md",
        creates_labels=(),
    ),
    CommandId.WORK_BLOCKED: CommandSpec(
        id=CommandId.WORK_BLOCKED,
        name="aura:worker:blocked",
        description="Report a blocker to supervisor via Beads",
        role_ref=RoleId.WORKER,
        phases=("p9",),
        file="skills/worker-blocked/SKILL.md",
        creates_labels=(),
    ),
    CommandId.REVIEWER: CommandSpec(
        id=CommandId.REVIEWER,
        name="aura:reviewer",
        description="End-user alignment reviewer for plans and code",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer/SKILL.md",
        creates_labels=(),
    ),
    CommandId.REV_PLAN: CommandSpec(
        id=CommandId.REV_PLAN,
        name="aura:reviewer:review-plan",
        description="Evaluate proposal against one axis (binary ACCEPT/REVISE)",
        role_ref=RoleId.REVIEWER,
        phases=("p4",),
        file="skills/reviewer-review-plan/SKILL.md",
        creates_labels=("L-p4s4",),
    ),
    CommandId.REV_CODE: CommandSpec(
        id=CommandId.REV_CODE,
        name="aura:reviewer:review-code",
        description="Review implementation slices with EAGER severity tree",
        role_ref=RoleId.REVIEWER,
        phases=("p10",),
        file="skills/reviewer-review-code/SKILL.md",
        creates_labels=("L-p10s10", "L-sev-blocker", "L-sev-import", "L-sev-minor"),
    ),
    CommandId.REV_COMMENT: CommandSpec(
        id=CommandId.REV_COMMENT,
        name="aura:reviewer:comment",
        description="Leave structured review comment via Beads",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer-comment/SKILL.md",
        creates_labels=(),
    ),
    CommandId.REV_VOTE: CommandSpec(
        id=CommandId.REV_VOTE,
        name="aura:reviewer:vote",
        description="Cast ACCEPT or REVISE vote (binary only)",
        role_ref=RoleId.REVIEWER,
        phases=("p4", "p10"),
        file="skills/reviewer-vote/SKILL.md",
        creates_labels=(),
    ),
    CommandId.IMPL_SLICE: CommandSpec(
        id=CommandId.IMPL_SLICE,
        name="aura:impl:slice",
        description="Vertical slice assignment and tracking",
        role_ref=RoleId.SUPERVISOR,
        phases=("p9",),
        file="skills/impl-slice/SKILL.md",
        creates_labels=("L-p9s9",),
    ),
    CommandId.IMPL_REVIEW: CommandSpec(
        id=CommandId.IMPL_REVIEW,
        name="aura:impl:review",
        description="Code review coordination across all slices (Phase 10)",
        role_ref=RoleId.SUPERVISOR,
        phases=("p10",),
        file="skills/impl-review/SKILL.md",
        creates_labels=("L-p10s10", "L-sev-blocker", "L-sev-import", "L-sev-minor"),
    ),
    CommandId.MSG_SEND: CommandSpec(
        id=CommandId.MSG_SEND,
        name="aura:msg:send",
        description="Send a message to another agent via Beads comment",
        role_ref=None,
        phases=(),
        file="skills/msg-send/SKILL.md",
        creates_labels=(),
    ),
    CommandId.MSG_RECEIVE: CommandSpec(
        id=CommandId.MSG_RECEIVE,
        name="aura:msg:receive",
        description="Check inbox for messages from other agents",
        role_ref=None,
        phases=(),
        file="skills/msg-receive/SKILL.md",
        creates_labels=(),
    ),
    CommandId.MSG_BROADCAST: CommandSpec(
        id=CommandId.MSG_BROADCAST,
        name="aura:msg:broadcast",
        description="Broadcast a message to multiple agents",
        role_ref=None,
        phases=(),
        file="skills/msg-broadcast/SKILL.md",
        creates_labels=(),
    ),
    CommandId.MSG_ACK: CommandSpec(
        id=CommandId.MSG_ACK,
        name="aura:msg:ack",
        description="Acknowledge received messages",
        role_ref=None,
        phases=(),
        file="skills/msg-ack/SKILL.md",
        creates_labels=(),
    ),
    CommandId.EXPLORE: CommandSpec(
        id=CommandId.EXPLORE,
        name="aura:explore",
        description=(
            "Codebase exploration — find integration points, existing patterns, and related code"
        ),
        role_ref=None,
        phases=("p1", "p8"),
        file="skills/explore/SKILL.md",
        creates_labels=("L-p1s1_3",),
    ),
    CommandId.RESEARCH: CommandSpec(
        id=CommandId.RESEARCH,
        name="aura:research",
        description="Domain research — find standards, prior art, and competing approaches",
        role_ref=None,
        phases=("p1",),
        file="skills/research/SKILL.md",
        creates_labels=("L-p1s1_2",),
    ),
    CommandId.TEST: CommandSpec(
        id=CommandId.TEST,
        name="aura:test",
        description="Run tests using BDD patterns",
        role_ref=None,
        phases=(),
        file="skills/test/SKILL.md",
        creates_labels=(),
    ),
    CommandId.FEEDBACK: CommandSpec(
        id=CommandId.FEEDBACK,
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
    "axis-correctness": ReviewAxisSpec(
        id="axis-correctness",
        letter=ReviewAxis.CORRECTNESS,
        name="Correctness",
        short="Spirit and technicality",
        key_questions=(
            "Does the implementation faithfully serve the user's original request?",
            "Are technical decisions consistent with the rationale in the proposal?",
            "Are there gaps where the proposal says one thing but the code does another?",
        ),
    ),
    "axis-test_quality": ReviewAxisSpec(
        id="axis-test_quality",
        letter=ReviewAxis.TEST_QUALITY,
        name="Test quality",
        short="Test strategy adequacy",
        key_questions=(
            "Favour integration tests over brittle unit tests?",
            "System under test NOT mocked — mock dependencies only?",
            "Shared fixtures for common test values?",
            "Assert observable outcomes, not internal state?",
        ),
    ),
    "axis-elegance": ReviewAxisSpec(
        id="axis-elegance",
        letter=ReviewAxis.ELEGANCE,
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
            id=StepSlug.Supervisor.CallSkill,
            order=1,
            instruction="Call Skill(/aura:supervisor) to load role instructions",
            command=SkillRef.SUPERVISOR,
        ),
        ProcedureStep(
            id=StepSlug.Supervisor.ReadPlan,
            order=2,
            instruction="Read RATIFIED_PLAN and URD via bd show",
            command="bd show <ratified-plan-id> && bd show <urd-id>",
        ),
        ProcedureStep(
            id=StepSlug.Supervisor.ExploreEphemeral,
            order=3,
            instruction="Spawn ephemeral Explore subagents via Task tool for scoped codebase queries",
            context="Each subagent is short-lived and returns findings; no standing team overhead",
        ),
        ProcedureStep(
            id=StepSlug.Supervisor.DecomposeSlices,
            order=4,
            instruction="Decompose into vertical slices",
            context=(
                "Vertical slices give one worker end-to-end ownership of a feature path "
                "(types → tests → impl → wiring) with clear file boundaries"
            ),
            next_state=PhaseId.P8_IMPL_PLAN,
        ),
        ProcedureStep(
            id=StepSlug.Supervisor.CreateLeafTasks,
            order=5,
            instruction="Create leaf tasks (L1/L2/L3) for every slice",
            command=(
                'bd create --labels aura:p9-impl:s9-slice --title '
                '"SLICE-{K}-L{1,2,3}: <description>" ...'
            ),
            examples=(
                CodeExample(
                    id="S-supervisor-create-leaf-tasks-frontmatter",
                    lang=ExampleLang.BASH,
                    label=ExampleLabel.TEMPLATE,
                    code=(
                        'bd create --labels aura:p9-impl:s9-slice \\\n'
                        '  --title "SLICE-1-L1: Types -- <slice name>" \\\n'
                        '  --description "---\n'
                        'references:\n'
                        '  slice: <slice-1-id>\n'
                        '  impl_plan: <impl-plan-task-id>\n'
                        '  urd: <urd-task-id>\n'
                        '---\n'
                        'Layer 1: types and interfaces for <slice name>."'
                    ),
                    also_illustrates="C-frontmatter-refs",
                ),
            ),
        ),
        ProcedureStep(
            id=StepSlug.Supervisor.SpawnWorkers,
            order=6,
            instruction="Spawn workers for leaf tasks",
            command="aura-swarm start --epic <epic-id>",
            next_state=PhaseId.P9_SLICE,
        ),
    ),
    RoleId.WORKER: (
        ProcedureStep(
            id=StepSlug.Worker.Types,
            order=1,
            instruction="Types, interfaces, schemas (no deps)",
        ),
        ProcedureStep(
            id=StepSlug.Worker.Tests,
            order=2,
            instruction="Tests importing production code (will fail initially)",
        ),
        ProcedureStep(
            id=StepSlug.Worker.Impl,
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


# ─── Checklist Specs ──────────────────────────────────────────────────────────
# Completion checklists keyed by "{role}-{gate}".
# Integration test (test_schema_types_sync.py) verifies these match schema.xml.

CHECKLIST_SPECS: dict[str, Checklist] = {
    "worker-completion": Checklist(
        role_ref=RoleId.WORKER,
        gate=GateType.COMPLETION,
        items=(
            ChecklistItem(
                id="CL-worker-no-todos",
                text="No TODO placeholders in CLI/API actions",
            ),
            ChecklistItem(
                id="CL-worker-real-deps",
                text="Real dependencies wired (not mocks in production code)",
            ),
            ChecklistItem(
                id="CL-worker-test-import",
                text="Tests import production code (not test-only export)",
            ),
            ChecklistItem(
                id="CL-worker-no-dual-export",
                text="No dual-export anti-pattern (one code path for tests and production)",
            ),
            ChecklistItem(
                id="CL-worker-quality-gates",
                text="Quality gates pass (typecheck + tests)",
            ),
            ChecklistItem(
                id="CL-worker-production-path",
                text="Production code path verified end-to-end via code inspection",
            ),
        ),
    ),
    "worker-slice-closure": Checklist(
        role_ref=RoleId.WORKER,
        gate=GateType.SLICE_CLOSURE,
        items=(
            ChecklistItem(
                id="CL-worker-notified-supervisor",
                text="Supervisor notified via bd comments add (not bd close)",
            ),
            ChecklistItem(
                id="CL-worker-completion-done",
                text="All completion-gate items passed",
            ),
            ChecklistItem(
                id="CL-worker-close-on-review-wave",
                text="Can only close on a review wave, not a worker wave",
            ),
            ChecklistItem(
                id="CL-worker-review-eligible",
                text="Eligible to close only after review by independent agents with no BLOCKERS or IMPORTANT findings",
            ),
        ),
    ),
    "supervisor-review-ready": Checklist(
        role_ref=RoleId.SUPERVISOR,
        gate=GateType.REVIEW_READY,
        items=(
            ChecklistItem(
                id="CL-sup-all-slices-notified",
                text="All workers have notified completion via bd comments add",
            ),
            ChecklistItem(
                id="CL-sup-reviewers-assigned",
                text="Ephemeral reviewers spawned for all slices",
            ),
            ChecklistItem(
                id="CL-sup-severity-groups-created",
                text="Severity groups (BLOCKER/IMPORTANT/MINOR) eagerly created per slice",
            ),
        ),
    ),
    "supervisor-landing": Checklist(
        role_ref=RoleId.SUPERVISOR,
        gate=GateType.LANDING,
        items=(
            ChecklistItem(
                id="CL-sup-all-accept",
                text="All 3 reviewers ACCEPT, no open BLOCKERs",
            ),
            ChecklistItem(
                id="CL-sup-followup-created",
                text="FOLLOWUP epic created if any IMPORTANT/MINOR findings exist",
            ),
            ChecklistItem(
                id="CL-sup-agent-commit",
                text="git agent-commit used (not git commit -m)",
            ),
            ChecklistItem(
                id="CL-sup-tasks-closed",
                text="All upstream tasks closed or dependency-resolved",
            ),
            ChecklistItem(
                id="CL-sup-close-on-review-wave",
                text="Can only close on a review wave, not a worker wave",
            ),
            ChecklistItem(
                id="CL-sup-review-eligible",
                text="Eligible to close only after review by independent agents with no BLOCKERS or IMPORTANT findings",
            ),
        ),
    ),
}


# ─── Coordination Commands ────────────────────────────────────────────────────
# Shared and role-specific Beads coordination commands.
# role_ref=None means the command is available to all roles (shared=True).

COORDINATION_COMMANDS: dict[str, CoordinationCommand] = {
    # Shared commands (all roles)
    "cmd-coord-show": CoordinationCommand(
        id="cmd-coord-show",
        action="Check task details",
        template="bd show <task-id>",
        role_ref=None,
        shared=True,
    ),
    "cmd-coord-status": CoordinationCommand(
        id="cmd-coord-status",
        action="Update status",
        template="bd update <task-id> --status=in_progress",
        role_ref=None,
        shared=True,
    ),
    "cmd-coord-comment": CoordinationCommand(
        id="cmd-coord-comment",
        action="Add progress note",
        template="bd comments add <task-id> \"Progress: ...\"",
        role_ref=None,
        shared=True,
    ),
    "cmd-coord-list": CoordinationCommand(
        id="cmd-coord-list",
        action="List in-progress",
        template="bd list --pretty --status=in_progress",
        role_ref=None,
        shared=True,
    ),
    "cmd-coord-blocked": CoordinationCommand(
        id="cmd-coord-blocked",
        action="List blocked",
        template="bd blocked",
        role_ref=None,
        shared=True,
    ),
    # Supervisor-specific commands
    "cmd-coord-assign": CoordinationCommand(
        id="cmd-coord-assign",
        action="Assign task",
        template="bd update <task-id> --assignee \"<worker-name>\"",
        role_ref=RoleId.SUPERVISOR,
    ),
    "cmd-coord-label": CoordinationCommand(
        id="cmd-coord-label",
        action="Label completed slice",
        template="bd label add <slice-id> aura:p9-impl:slice-complete",
        role_ref=RoleId.SUPERVISOR,
    ),
    "cmd-coord-dep-add": CoordinationCommand(
        id="cmd-coord-dep-add",
        action="Chain dependency",
        template="bd dep add <parent> --blocked-by <child>",
        role_ref=RoleId.SUPERVISOR,
    ),
    # Worker-specific commands
    "cmd-coord-close": CoordinationCommand(
        id="cmd-coord-close",
        action="Report completion",
        template="bd close <task-id>",
        role_ref=RoleId.WORKER,
    ),
    "cmd-coord-worker-notes": CoordinationCommand(
        id="cmd-coord-worker-notes",
        action="Add completion notes",
        template="bd update <task-id> --notes=\"Implementation complete. Production code verified.\"",
        role_ref=RoleId.WORKER,
    ),
}


# ─── Workflow Specs ───────────────────────────────────────────────────────────
# Three named workflows covering supervisor (Ride the Wave), worker (Layer Cake),
# and architect (Architect State Flow).

WORKFLOW_SPECS: dict[str, Workflow] = {
    "ride-the-wave": Workflow(
        id="ride-the-wave",
        name="Ride the Wave",
        role_ref=RoleId.SUPERVISOR,
        description=(
            "Coordinated Phase 8-10 execution pattern. The supervisor orchestrates "
            "the full cycle: plan slices, launch workers, "
            "spawn ephemeral reviewers for per-slice review, workers fix, repeat max 3 cycles per slice."
        ),
        stages=(
            WorkflowStage(
                id="rtw-plan",
                name="Plan",
                order=1,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P8_IMPL_PLAN,
                actions=(
                    WorkflowAction(
                        id="rtw-plan-read",
                        instruction="Read RATIFIED_PLAN and URD via bd show",
                        command="bd show <ratified-plan-id> && bd show <urd-id>",
                    ),
                    WorkflowAction(
                        id="rtw-plan-explore",
                        instruction="Spawn ephemeral Explore subagents via Task tool to map codebase areas",
                    ),
                    WorkflowAction(
                        id="rtw-plan-decompose",
                        instruction="Use Explore findings to decompose into vertical slices with integration points",
                    ),
                    WorkflowAction(
                        id="rtw-plan-leaf-tasks",
                        instruction="Create leaf tasks (L1/L2/L3) for every slice",
                        command="bd dep add <slice-id> --blocked-by <leaf-task-id>",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="All slices created with leaf tasks, dependency-chained, assigned",
                    ),
                ),
            ),
            WorkflowStage(
                id="rtw-build",
                name="Build",
                order=2,
                execution=WorkflowExecution.PARALLEL,
                phase_ref=PhaseId.P9_SLICE,
                actions=(
                    WorkflowAction(
                        id="rtw-build-spawn",
                        instruction="Spawn N workers for parallel slice implementation",
                        command="aura-swarm start --epic <epic-id>",
                    ),
                    WorkflowAction(
                        id="rtw-build-monitor",
                        instruction="Monitor worker progress via bd list and bd show",
                        command="bd list --labels=\"aura:p9-impl:s9-slice\" --status=in_progress",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="All workers have notified completion via bd comments add",
                    ),
                ),
            ),
            WorkflowStage(
                id="rtw-review-fix",
                name="Review + Fix Cycles",
                order=3,
                execution=WorkflowExecution.CONDITIONAL_LOOP,
                phase_ref=PhaseId.P10_CODE_REVIEW,
                actions=(
                    WorkflowAction(
                        id="rtw-review-spawn",
                        instruction="Spawn ephemeral reviewers via Task tool for per-slice code review",
                    ),
                    WorkflowAction(
                        id="rtw-review-severity",
                        instruction="Reviewers create severity groups (BLOCKER/IMPORTANT/MINOR) per slice",
                    ),
                    WorkflowAction(
                        id="rtw-review-followup",
                        instruction="Create FOLLOWUP epic if any IMPORTANT/MINOR findings exist",
                    ),
                    WorkflowAction(
                        id="rtw-review-fix",
                        instruction="Workers fix BLOCKERs and IMPORTANT findings",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.SUCCESS,
                        condition="All reviewers ACCEPT, no open BLOCKERs — proceed to Phase 11 UAT",
                    ),
                    ExitCondition(
                        type=ExitConditionType.CONTINUE,
                        condition="BLOCKERs or IMPORTANTs remain, cycles < 3 per slice — workers fix, spawn new ephemeral reviewers",
                    ),
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="3 cycles exhausted, IMPORTANT remain — track in FOLLOWUP, proceed to Phase 11",
                    ),
                    ExitCondition(
                        type=ExitConditionType.ESCALATE,
                        condition="3 cycles exhausted per slice, BLOCKERs remain — escalate to architect for re-planning",
                    ),
                ),
            ),
        ),
    ),
    "layer-cake": Workflow(
        id="layer-cake",
        name="Layer Cake",
        role_ref=RoleId.WORKER,
        description=(
            "TDD layer-by-layer implementation within a vertical slice. "
            "Worker implements types first, then tests (will fail), "
            "then production code to make tests pass."
        ),
        stages=(
            WorkflowStage(
                id="lc-types",
                name="Types",
                order=1,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P9_SLICE,
                actions=(
                    WorkflowAction(
                        id="lc-types-read",
                        instruction="Read slice task and identify required types",
                        command="bd show <slice-task-id>",
                    ),
                    WorkflowAction(
                        id="lc-types-define",
                        instruction="Define types, interfaces, and schemas (no deps) — only types for YOUR slice",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="All required types defined; file imports without error",
                    ),
                ),
            ),
            WorkflowStage(
                id="lc-tests",
                name="Tests",
                order=2,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P9_SLICE,
                actions=(
                    WorkflowAction(
                        id="lc-tests-write",
                        instruction="Write tests importing production code (CLI/API users will run) — tests WILL fail",
                    ),
                    WorkflowAction(
                        id="lc-tests-verify-import",
                        instruction="Verify tests import actual production code, not test-only export",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="Tests written and import production code; typecheck passes; tests fail (expected)",
                    ),
                ),
            ),
            WorkflowStage(
                id="lc-impl",
                name="Implementation + Wiring",
                order=3,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P9_SLICE,
                actions=(
                    WorkflowAction(
                        id="lc-impl-code",
                        instruction="Implement production code to make Layer 2 tests pass",
                    ),
                    WorkflowAction(
                        id="lc-impl-wire",
                        instruction="Wire with real dependencies (not mocks in production code)",
                    ),
                    WorkflowAction(
                        id="lc-impl-run-tests",
                        instruction="Run tests — all Layer 2 tests must pass",
                    ),
                    WorkflowAction(
                        id="lc-impl-commit",
                        instruction="Commit completed work",
                        command="git agent-commit -m ...",
                    ),
                    WorkflowAction(
                        id="lc-impl-notify",
                        instruction="Notify supervisor of completion via bd comments add",
                        command="bd comments add <slice-id> \"Implementation complete\"",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.SUCCESS,
                        condition=(
                            "All tests pass; no TODO placeholders; real deps wired; "
                            "production code path verified via code inspection"
                        ),
                    ),
                    ExitCondition(
                        type=ExitConditionType.ESCALATE,
                        condition="Blocker encountered — use /aura:worker-blocked with details",
                    ),
                ),
            ),
        ),
    ),
    "architect-state-flow": Workflow(
        id="architect-state-flow",
        name="Architect State Flow",
        role_ref=RoleId.ARCHITECT,
        description=(
            "Sequential planning phases 1-7. The architect captures requirements, "
            "writes proposals, coordinates review consensus, and hands off to supervisor."
        ),
        stages=(
            WorkflowStage(
                id="asf-request",
                name="Request",
                order=1,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P1_REQUEST,
                actions=(
                    WorkflowAction(
                        id="asf-request-capture",
                        instruction="Capture user request verbatim via /aura:user-request",
                    ),
                    WorkflowAction(
                        id="asf-request-classify",
                        instruction="Classify request along 4 axes: scope, complexity, risk, domain novelty",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="Classification confirmed, research and explore complete",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-elicit",
                name="Elicit",
                order=2,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P2_ELICIT,
                actions=(
                    WorkflowAction(
                        id="asf-elicit-ure",
                        instruction="Run URE survey with user via /aura:user-elicit",
                    ),
                    WorkflowAction(
                        id="asf-elicit-urd",
                        instruction="Create URD as single source of truth for requirements",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="URD created with structured requirements",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-propose",
                name="Propose",
                order=3,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P3_PROPOSE,
                actions=(
                    WorkflowAction(
                        id="asf-propose-write",
                        instruction="Write full technical proposal: interfaces, approach, validation checklist, BDD criteria",
                    ),
                    WorkflowAction(
                        id="asf-propose-create",
                        instruction="Create PROPOSAL-N task via /aura:architect:propose-plan",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="Proposal created",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-review",
                name="Review",
                order=4,
                execution=WorkflowExecution.CONDITIONAL_LOOP,
                phase_ref=PhaseId.P4_REVIEW,
                actions=(
                    WorkflowAction(
                        id="asf-review-spawn",
                        instruction="Spawn 3 axis-specific reviewers (A=Correctness, B=Test quality, C=Elegance)",
                    ),
                    WorkflowAction(
                        id="asf-review-wait",
                        instruction="Wait for all 3 reviewers to vote",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="All 3 reviewers vote ACCEPT",
                    ),
                    ExitCondition(
                        type=ExitConditionType.CONTINUE,
                        condition="Any reviewer votes REVISE — create PROPOSAL-N+1, mark old as superseded, re-spawn reviewers",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-uat",
                name="Plan UAT",
                order=5,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P5_UAT,
                actions=(
                    WorkflowAction(
                        id="asf-uat-present",
                        instruction="Present plan to user with demonstrative examples via /aura:user-uat",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="User accepts plan",
                    ),
                    ExitCondition(
                        type=ExitConditionType.CONTINUE,
                        condition="User requests changes — create PROPOSAL-N+1",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-ratify",
                name="Ratify",
                order=6,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P6_RATIFY,
                actions=(
                    WorkflowAction(
                        id="asf-ratify-label",
                        instruction="Add ratify label to accepted PROPOSAL-N",
                    ),
                    WorkflowAction(
                        id="asf-ratify-supersede",
                        instruction="Mark all prior proposals aura:superseded",
                    ),
                    WorkflowAction(
                        id="asf-ratify-placeholder",
                        instruction="Create placeholder IMPL_PLAN task",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.PROCEED,
                        condition="Proposal ratified, IMPL_PLAN placeholder created",
                    ),
                ),
            ),
            WorkflowStage(
                id="asf-handoff",
                name="Handoff",
                order=7,
                execution=WorkflowExecution.SEQUENTIAL,
                phase_ref=PhaseId.P7_HANDOFF,
                actions=(
                    WorkflowAction(
                        id="asf-handoff-doc",
                        instruction="Create handoff document with full inline provenance at .git/.aura/handoff/",
                    ),
                    WorkflowAction(
                        id="asf-handoff-transfer",
                        instruction="Transfer to supervisor via /aura:architect:handoff",
                    ),
                ),
                exit_conditions=(
                    ExitCondition(
                        type=ExitConditionType.SUCCESS,
                        condition="Handoff document stored at .git/.aura/handoff/, supervisor notified",
                    ),
                ),
            ),
        ),
    ),
}


# ─── Figure Specs ─────────────────────────────────────────────────────────────
# Keyed by FigureId. Content is loaded from YAML files at generation time;
# these specs carry structural metadata only (content defaults to '').

FIGURE_SPECS: dict[FigureId, Figure] = {
    FigureId.LAYER_CAKE: Figure(
        id=FigureId.LAYER_CAKE,
        title="Layer Cake — TDD Parallelism Within Vertical Slices",
        type=FigureType.ASCII_DIAGRAM,
        role_refs=frozenset({RoleId.WORKER}),
        section_ref=SectionRef.WORKFLOWS,
        workflow_refs=frozenset({"layer-cake"}),
        command_refs=frozenset({CommandId.SUP_PLAN}),
    ),
    FigureId.RIDE_THE_WAVE: Figure(
        id=FigureId.RIDE_THE_WAVE,
        title="Ride the Wave — Coordinated Phase 8-10 Execution",
        type=FigureType.ASCII_DIAGRAM,
        role_refs=frozenset({RoleId.SUPERVISOR}),
        section_ref=SectionRef.WORKFLOWS,
        workflow_refs=frozenset({"ride-the-wave"}),
        command_refs=frozenset({CommandId.SUP_SPAWN}),
    ),
    FigureId.ARCHITECT_STATE_FLOW: Figure(
        id=FigureId.ARCHITECT_STATE_FLOW,
        title="Architect State Flow — Sequential Planning Phases 1-7",
        type=FigureType.ASCII_DIAGRAM,
        role_refs=frozenset({RoleId.ARCHITECT}),
        section_ref=SectionRef.WORKFLOWS,
        workflow_refs=frozenset({"architect-state-flow"}),
    ),
}
