"""Aura Protocol Engine — public API.

This package provides typed Python definitions for the Aura multi-agent protocol.
All definitions are derived from and validated against skills/protocol/schema.xml.

Public API (re-exported from submodules):

Enums:
    PhaseId       — 13 values: p1-p12 + complete
    Domain        — user, plan, impl
    RoleId        — epoch, architect, reviewer, supervisor, worker
    VoteType      — ACCEPT, REVISE
    SeverityLevel — BLOCKER, IMPORTANT, MINOR
    ExecutionMode — sequential, parallel
    ContentLevel  — full-provenance, summary-with-ids
    ReviewAxis    — A, B, C
    SubstepType   — 13 values: classify, research, explore, elicit, urd, propose, review, uat, ratify, handoff, plan, slice, landing
    StepSlug      — nested namespace: StepSlug.Supervisor.* and StepSlug.Worker.* str enums for ProcedureStep.id
    SkillRef      — SUPERVISOR, WORKER str enum for ProcedureStep.command skill invocations

Frozen Dataclasses:
    Transition          — single valid phase transition
    PhaseSpec           — complete phase specification
    ConstraintSpec      — protocol constraint (Given/When/Then)
    HandoffSpec         — actor-change handoff specification
    SubstepSpec         — phase substep specification
    RoleSpec            — agent role specification
    DelegateSpec        — delegation relationship from epoch to role
    CommandSpec         — protocol command (skill) specification
    LabelSpec           — protocol label specification
    ReviewAxisSpec      — code review axis specification
    TitleConvention     — task title naming convention
    ProcedureStep       — single step in a role procedure
    ConstraintContext   — context injection fragment for runtime constraint evaluation

Event Stub Types (frozen dataclasses):
    PhaseTransitionEvent
    ConstraintCheckEvent
    ReviewVoteEvent
    AuditEvent
    ToolPermissionRequest
    PermissionDecision

Canonical Lookup Dicts:
    PHASE_SPECS         — dict[PhaseId, PhaseSpec]        — all 12 phases
    CONSTRAINT_SPECS    — dict[str, ConstraintSpec]       — all C-* constraints
    HANDOFF_SPECS       — dict[str, HandoffSpec]          — all 6 handoffs
    PHASE_DOMAIN        — dict[PhaseId, Domain]           — phase-to-domain mapping
    ROLE_SPECS          — dict[RoleId, RoleSpec]          — all 5 roles
    COMMAND_SPECS       — dict[str, CommandSpec]          — all 35 commands
    LABEL_SPECS         — dict[str, LabelSpec]            — all 21 labels
    REVIEW_AXIS_SPECS   — dict[str, ReviewAxisSpec]       — all 3 review axes
    TITLE_CONVENTIONS   — list[TitleConvention]           — all 16 title conventions
    PROCEDURE_STEPS     — dict[RoleId, tuple[ProcedureStep, ...]] — supervisor+worker steps

Schema Parser (from schema_parser.py):
    SchemaSpec          — root container for all parsed schema entities
    SchemaParseError    — raised when schema.xml is malformed or missing entities
    parse_schema(path)  — parse schema.xml into SchemaSpec

Bootstrap Codegen (from gen_types.py):
    generate_types_source(spec) — generate draft Python source from SchemaSpec (one-time tool)

Schema Generator (from gen_schema.py):
    generate_schema(output, diff=True) — generate schema.xml from Python types with diff output

Context Injection (from context_injection.py):
    RoleContext     — frozen dataclass: role, phases, constraints, commands, handoffs
    PhaseContext    — frozen dataclass: phase, constraints, labels, transitions
    get_role_context(role)   — build RoleContext for a given RoleId
    get_phase_context(phase) — build PhaseContext for a given PhaseId

State Machine (from state_machine.py):
    EpochState          — mutable epoch runtime state
    TransitionRecord    — frozen, immutable audit entry for one transition
    TransitionError     — exception raised when a transition is invalid
    EpochStateMachine   — 12-phase epoch lifecycle state machine

Runtime Constraint Checking (from constraints.py):
    ConstraintViolation     — frozen dataclass: constraint_id, message, context
    RuntimeConstraintChecker — checks all 23 C-* constraints against epoch state
        check_state_constraints(state) — aggregates the 5 state-based checks
        check_transition_constraints(state, to_phase) — combines transition-specific checks

Protocol Interfaces (runtime_checkable, from interfaces.py):
    ConstraintValidatorInterface
    TranscriptRecorder
    SecurityGate
    AuditTrail

A2A Content Types (frozen dataclasses, from interfaces.py):
    TextPart, FilePart, DataPart, Part (union), ToolCall

Model Identifier (from interfaces.py):
    ModelId — models.dev {provider}/{model} composite ID
"""

from aura_protocol.constraints import (
    ConstraintViolation,
    RuntimeConstraintChecker,
)
from aura_protocol.context_injection import (
    PhaseContext,
    RoleContext,
    get_phase_context,
    get_role_context,
    render_role_context_as_text,
    render_role_context_as_xml,
)
from aura_protocol.gen_schema import (
    generate_schema,
)
from aura_protocol.gen_types import (
    generate_types_source,
)
from aura_protocol.schema_parser import (
    SchemaParseError,
    SchemaSpec,
    parse_schema,
)
from aura_protocol.interfaces import (
    AuditTrail,
    ConstraintValidatorInterface,
    DataPart,
    FilePart,
    ModelId,
    Part,
    SecurityGate,
    TextPart,
    ToolCall,
    TranscriptRecorder,
)
from aura_protocol.state_machine import (
    EpochState,
    EpochStateMachine,
    TransitionError,
    TransitionRecord,
)
from aura_protocol.types import (
    COMMAND_SPECS,
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    LABEL_SPECS,
    PHASE_DOMAIN,
    PHASE_SPECS,
    PROCEDURE_STEPS,
    REVIEW_AXIS_SPECS,
    ROLE_SPECS,
    TITLE_CONVENTIONS,
    AuditEvent,
    CommandSpec,
    ConstraintCheckEvent,
    ConstraintContext,
    ConstraintSpec,
    ContentLevel,
    DelegateSpec,
    Domain,
    ExecutionMode,
    HandoffSpec,
    LabelSpec,
    PermissionDecision,
    PhaseId,
    PhaseSpec,
    PhaseTransitionEvent,
    ProcedureStep,
    ReviewAxis,
    ReviewAxisSpec,
    ReviewVoteEvent,
    RoleId,
    RoleSpec,
    SeverityLevel,
    SkillRef,
    StepSlug,
    SubstepSpec,
    SubstepType,
    TitleConvention,
    ToolPermissionRequest,
    Transition,
    VoteType,
)

__all__ = [
    # Constraint types
    "ConstraintViolation",
    "RuntimeConstraintChecker",
    # Enums
    "PhaseId",
    "Domain",
    "RoleId",
    "VoteType",
    "SeverityLevel",
    "ExecutionMode",
    "ContentLevel",
    "ReviewAxis",
    "SubstepType",
    "StepSlug",
    "SkillRef",
    # Frozen dataclasses
    "Transition",
    "PhaseSpec",
    "ConstraintSpec",
    "HandoffSpec",
    "SubstepSpec",
    "RoleSpec",
    "DelegateSpec",
    "CommandSpec",
    "LabelSpec",
    "ReviewAxisSpec",
    "TitleConvention",
    "ProcedureStep",
    "ConstraintContext",
    # Event stub types
    "PhaseTransitionEvent",
    "ConstraintCheckEvent",
    "ReviewVoteEvent",
    "AuditEvent",
    "ToolPermissionRequest",
    "PermissionDecision",
    # Canonical lookup dicts
    "PHASE_SPECS",
    "CONSTRAINT_SPECS",
    "HANDOFF_SPECS",
    "PHASE_DOMAIN",
    "ROLE_SPECS",
    "COMMAND_SPECS",
    "LABEL_SPECS",
    "REVIEW_AXIS_SPECS",
    "TITLE_CONVENTIONS",
    "PROCEDURE_STEPS",
    # Protocol interfaces
    "ConstraintValidatorInterface",
    "TranscriptRecorder",
    "SecurityGate",
    "AuditTrail",
    # A2A content types
    "TextPart",
    "FilePart",
    "DataPart",
    "Part",
    "ToolCall",
    # Model identifier
    "ModelId",
    # State machine
    "EpochState",
    "TransitionRecord",
    "TransitionError",
    "EpochStateMachine",
    # Schema parser
    "SchemaSpec",
    "SchemaParseError",
    "parse_schema",
    # Bootstrap codegen
    "generate_types_source",
    # Schema generator
    "generate_schema",
    # Context injection
    "RoleContext",
    "PhaseContext",
    "get_role_context",
    "get_phase_context",
    "render_role_context_as_text",
    "render_role_context_as_xml",
]
