"""Runtime context injection for role- and phase-specific constraint prompting.

Pure lookup module — no side effects, no Temporal dependency.
Called at skill invocation time (role-level baseline) and at phase transition
time (phase-level enrichment) to embed constraint facts into agent prompts.

Key types:
    RoleContext  — frozen dataclass: role, phases, constraints, commands, handoffs
    PhaseContext — frozen dataclass: phase, constraints, labels, transitions

Key functions:
    get_role_context(role: RoleId) -> RoleContext
    get_phase_context(phase: PhaseId) -> PhaseContext

Static dicts:
    _ROLE_CONSTRAINTS  — hand-authored mapping: RoleId → frozenset of constraint IDs
    _PHASE_CONSTRAINTS — hand-authored mapping: PhaseId → frozenset of constraint IDs

Design:
    - _ROLE_CONSTRAINTS is hand-authored from constraint given/when text in CONSTRAINT_SPECS.
      Each constraint's "given" and "when" fields determine which role it is relevant to.
    - _PHASE_CONSTRAINTS is hand-authored from constraint given/when text.
      Each constraint's "given" text specifies which phase(s) it applies to.
    - General constraints (audit, dep-direction, frontmatter-refs, actionable-errors)
      apply to ALL roles and ALL phases.
    - Role-specific constraints apply only to the role described in the given/when text.
    - Phase-specific constraints apply only to the phase described in the given text.
    - gen_schema.py (SLICE-2) reads _ROLE_CONSTRAINTS and _PHASE_CONSTRAINTS to emit
      role-ref and phase-ref attributes into schema.xml (UAT-3).
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape as xml_escape

from aura_protocol.types import (
    COMMAND_SPECS,
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    LABEL_SPECS,
    PHASE_SPECS,
    ConstraintContext,
    PhaseId,
    RoleId,
    Transition,
)


# ─── Runtime Context Dataclasses ──────────────────────────────────────────────


@dataclass(frozen=True)
class RoleContext:
    """Context injection fragment for a specific agent role.

    Populated by get_role_context(role) and used by prompt construction
    to embed role-appropriate constraints, phases, commands, and handoffs.

    Fields:
        role:        The agent role this context describes.
        phases:      Phases this role operates in (from PHASE_SPECS owner_roles, inverted).
        constraints: ConstraintContext objects relevant to this role.
        commands:    Command names (aura:*) applicable to this role.
        handoffs:    Handoff IDs where this role is source or target.
    """

    role: RoleId
    phases: frozenset[PhaseId]
    constraints: frozenset[ConstraintContext]
    commands: tuple[str, ...]
    handoffs: tuple[str, ...]


@dataclass(frozen=True)
class PhaseContext:
    """Context injection fragment for a specific protocol phase.

    Populated by get_phase_context(phase) and used by prompt construction
    to embed phase-appropriate constraints, labels, and valid transitions.

    Fields:
        phase:       The protocol phase this context describes.
        constraints: ConstraintContext objects relevant to this phase.
        labels:      Label values associated with this phase.
        transitions: Valid transitions out of this phase.
    """

    phase: PhaseId
    constraints: frozenset[ConstraintContext]
    labels: tuple[str, ...]
    transitions: tuple[Transition, ...]


# ─── General Constraints (apply to ALL roles and ALL phases) ──────────────────
# These constraints govern universal protocol rules regardless of role/phase.

_GENERAL_CONSTRAINTS: frozenset[str] = frozenset({
    # C-audit-never-delete: "any task or label" when modifying → universal
    "C-audit-never-delete",
    # C-audit-dep-chain: "any phase transition" when creating new task → universal
    "C-audit-dep-chain",
    # C-dep-direction: "adding a Beads dependency" → universal
    "C-dep-direction",
    # C-frontmatter-refs: "cross-task references" → universal
    "C-frontmatter-refs",
    # C-actionable-errors: "an error, exception, or user-facing message" → universal
    "C-actionable-errors",
})


# ─── Static Role → Constraint ID Mapping ─────────────────────────────────────
# Hand-authored from CONSTRAINT_SPECS given/when text.
# Each entry maps a RoleId to the frozenset of constraint IDs relevant to that role.
#
# Authoring rationale per constraint:
#   C-audit-never-delete      → ALL (see _GENERAL_CONSTRAINTS)
#   C-audit-dep-chain         → ALL (see _GENERAL_CONSTRAINTS)
#   C-review-consensus        → REVIEWER (does the reviewing), SUPERVISOR (gates the transition)
#   C-review-binary           → REVIEWER (given: "a reviewer" when: "voting")
#   C-severity-eager          → REVIEWER (given: "code review round (p10 only)" — reviewer must create eagerly)
#   C-severity-not-plan       → REVIEWER (given: "plan review (p4)" — reviewer must not use severity in p4)
#   C-blocker-dual-parent     → REVIEWER (given: "a BLOCKER finding in code review" — reviewer creates the finding)
#   C-followup-timing         → SUPERVISOR (given: "code review completion" — supervisor orchestrates followup)
#   C-vertical-slices         → SUPERVISOR (given: "implementation decomposition" when: "assigning work")
#   C-supervisor-no-impl      → SUPERVISOR (given: "supervisor role")
#   C-supervisor-cartographers → SUPERVISOR (given: "supervisor needs codebase exploration and code review")
#   C-integration-points      → SUPERVISOR (given: "multiple vertical slices share types" when: "decomposing IMPL_PLAN")
#   C-slice-review-before-close → SUPERVISOR (given: "workers complete their implementation slices")
#   C-max-review-cycles       → SUPERVISOR (given: "worker-Cartographer review-fix cycles are ongoing")
#   C-slice-leaf-tasks        → SUPERVISOR (given: "vertical slice created" — supervisor creates slices)
#   C-handoff-skill-invocation→ ARCHITECT + SUPERVISOR (both are sources of handoffs h1 and h2/h3)
#   C-dep-direction           → ALL (see _GENERAL_CONSTRAINTS)
#   C-frontmatter-refs        → ALL (see _GENERAL_CONSTRAINTS)
#   C-agent-commit            → WORKER + SUPERVISOR (roles that commit code)
#   C-proposal-naming         → ARCHITECT (given: "a new or revised proposal" — architect creates proposals)
#   C-review-naming           → REVIEWER (given: "a review task" when: "creating")
#   C-ure-verbatim            → ARCHITECT (given: "user interview (URE or UAT)" — architect runs interviews)
#   C-followup-lifecycle      → SUPERVISOR (given: "follow-up epic created" when: "starting follow-up work")
#   C-followup-leaf-adoption  → SUPERVISOR (given: "supervisor creates FOLLOWUP_SLICE-N")
#   C-worker-gates            → WORKER (given: "worker finishes implementation")
#   C-actionable-errors       → ALL (see _GENERAL_CONSTRAINTS)

_ROLE_CONSTRAINTS: dict[RoleId, frozenset[str]] = {
    RoleId.EPOCH: frozenset(_GENERAL_CONSTRAINTS | {
        # Epoch orchestrates all phases — review consensus gating applies to advance
        "C-review-consensus",
        # Epoch creates handoffs as master orchestrator
        "C-handoff-skill-invocation",
        # Epoch delegates p8/p10 exploration+review to 3 Cartographers (Ride the Wave)
        "C-supervisor-cartographers",
        # Epoch ensures supervisor documents integration points between slices
        "C-integration-points",
        # Epoch enforces: slices reviewed before closure; supervisor closes, not workers
        "C-slice-review-before-close",
        # Epoch enforces: max 3 worker-reviewer cycles; remaining IMPORTANT → FOLLOWUP
        "C-max-review-cycles",
    }),
    RoleId.ARCHITECT: frozenset(_GENERAL_CONSTRAINTS | {
        # Architect creates proposals → must follow naming convention
        "C-proposal-naming",
        # Architect runs user interviews (URE/UAT) → must capture verbatim
        "C-ure-verbatim",
        # Architect is source of h1 handoff (architect → supervisor at p7)
        "C-handoff-skill-invocation",
        # Architect commits code outputs occasionally (ratified docs)
        "C-agent-commit",
    }),
    RoleId.REVIEWER: frozenset(_GENERAL_CONSTRAINTS | {
        # Reviewer checks consensus in review phases
        "C-review-consensus",
        # Reviewer must use binary ACCEPT/REVISE
        "C-review-binary",
        # Reviewer must create severity tree eagerly in p10
        "C-severity-eager",
        # Reviewer must NOT use severity tree in p4
        "C-severity-not-plan",
        # Reviewer records BLOCKER findings with dual parents
        "C-blocker-dual-parent",
        # Reviewer creates review task names
        "C-review-naming",
    }),
    RoleId.SUPERVISOR: frozenset(_GENERAL_CONSTRAINTS | {
        # Supervisor gates transition on consensus
        "C-review-consensus",
        # Supervisor must not implement code directly
        "C-supervisor-no-impl",
        # Supervisor must use Cartographers for p8/p10 exploration and review
        "C-supervisor-cartographers",
        # Supervisor must document integration points between slices
        "C-integration-points",
        # Slices must be reviewed before closure
        "C-slice-review-before-close",
        # Worker-reviewer cycles capped at 3
        "C-max-review-cycles",
        # Supervisor assigns vertical slices to workers
        "C-vertical-slices",
        # Supervisor creates slices and must add leaf tasks
        "C-slice-leaf-tasks",
        # Supervisor is source of h2/h3 handoffs
        "C-handoff-skill-invocation",
        # Supervisor commits merged code (landing phase)
        "C-agent-commit",
        # Supervisor creates follow-up timing after review
        "C-followup-timing",
        # Supervisor manages follow-up lifecycle
        "C-followup-lifecycle",
        # Supervisor adopts leaf tasks into follow-up slices
        "C-followup-leaf-adoption",
    }),
    RoleId.WORKER: frozenset(_GENERAL_CONSTRAINTS | {
        # Worker must pass quality gates before closing slice
        "C-worker-gates",
        # Worker commits code with agent-commit
        "C-agent-commit",
    }),
}


# ─── Static Phase → Constraint ID Mapping ─────────────────────────────────────
# Hand-authored from CONSTRAINT_SPECS given/when text.
# Each entry maps a PhaseId to the frozenset of constraint IDs relevant to that phase.
#
# Authoring rationale per constraint:
#   C-audit-never-delete      → ALL phases (see _GENERAL_CONSTRAINTS)
#   C-audit-dep-chain         → ALL phases (new tasks created in any phase)
#   C-review-consensus        → P4_REVIEW, P10_CODE_REVIEW (given: "review cycle (p4 or p10)")
#   C-review-binary           → P4_REVIEW, P10_CODE_REVIEW (given: reviewer voting)
#   C-severity-eager          → P10_CODE_REVIEW ONLY (given: "code review round (p10 only)")
#   C-severity-not-plan       → P4_REVIEW ONLY (given: "plan review (p4)")
#   C-blocker-dual-parent     → P10_CODE_REVIEW (given: "a BLOCKER finding in code review")
#   C-followup-timing         → P10_CODE_REVIEW (given: "code review completion")
#   C-vertical-slices         → P8_IMPL_PLAN, P9_SLICE (given: "implementation decomposition")
#   C-supervisor-no-impl      → P8_IMPL_PLAN, P9_SLICE (given: "implementation phase")
#   C-supervisor-cartographers → P8_IMPL_PLAN, P9_SLICE, P10_CODE_REVIEW (dual-role: explore then review)
#   C-integration-points      → P8_IMPL_PLAN (given: "decomposing IMPL_PLAN in Phase 8")
#   C-slice-review-before-close → P9_SLICE, P10_CODE_REVIEW (given: "slice implementation is done")
#   C-max-review-cycles       → P10_CODE_REVIEW (given: "counting review-fix iterations")
#   C-slice-leaf-tasks        → P8_IMPL_PLAN, P9_SLICE (vertical slices created in p8, tracked in p9)
#   C-handoff-skill-invocation→ P7_HANDOFF (given: "new phase (especially p7 to p8 handoff)")
#   C-dep-direction           → ALL phases
#   C-frontmatter-refs        → ALL phases
#   C-agent-commit            → P9_SLICE, P12_LANDING (code committed in worker and landing)
#   C-proposal-naming         → P3_PROPOSE (given: "a new or revised proposal")
#   C-review-naming           → P4_REVIEW, P10_CODE_REVIEW (given: "a review task" when: "creating")
#   C-ure-verbatim            → P2_ELICIT, P5_UAT (given: "user interview (URE or UAT)")
#   C-followup-lifecycle      → P10_CODE_REVIEW (given: follow-up epic from code review)
#   C-followup-leaf-adoption  → P10_CODE_REVIEW (given: "supervisor creates FOLLOWUP_SLICE-N" in review context)
#   C-worker-gates            → P9_SLICE (given: "worker finishes implementation")
#   C-actionable-errors       → ALL phases

_PHASE_CONSTRAINTS: dict[PhaseId, frozenset[str]] = {
    PhaseId.P1_REQUEST: frozenset(_GENERAL_CONSTRAINTS),
    PhaseId.P2_ELICIT: frozenset(_GENERAL_CONSTRAINTS | {
        # User interviews happen in elicitation
        "C-ure-verbatim",
        # Proposals may begin forming here → naming awareness
    }),
    PhaseId.P3_PROPOSE: frozenset(_GENERAL_CONSTRAINTS | {
        # Proposals created in p3
        "C-proposal-naming",
    }),
    PhaseId.P4_REVIEW: frozenset(_GENERAL_CONSTRAINTS | {
        # Plan review → consensus required
        "C-review-consensus",
        # Plan review → binary voting only
        "C-review-binary",
        # Plan review → must NOT create severity tree
        "C-severity-not-plan",
        # Review tasks created in p4
        "C-review-naming",
    }),
    PhaseId.P5_UAT: frozenset(_GENERAL_CONSTRAINTS | {
        # User acceptance test → verbatim capture
        "C-ure-verbatim",
    }),
    PhaseId.P6_RATIFY: frozenset(_GENERAL_CONSTRAINTS),
    PhaseId.P7_HANDOFF: frozenset(_GENERAL_CONSTRAINTS | {
        # Handoff document required at p7 transition
        "C-handoff-skill-invocation",
    }),
    PhaseId.P8_IMPL_PLAN: frozenset(_GENERAL_CONSTRAINTS | {
        # Implementation decomposition into vertical slices
        "C-vertical-slices",
        # Supervisor must not implement directly
        "C-supervisor-no-impl",
        # Supervisor must use Cartographers for p8 exploration
        "C-supervisor-cartographers",
        # Supervisor must document integration points in p8
        "C-integration-points",
        # Each slice must have leaf tasks
        "C-slice-leaf-tasks",
    }),
    PhaseId.P9_SLICE: frozenset(_GENERAL_CONSTRAINTS | {
        # Worker quality gates before slice completion
        "C-worker-gates",
        # Commits happen in slice phase
        "C-agent-commit",
        # Supervisor still manages vertical slice ownership
        "C-vertical-slices",
        # Supervisor must not implement directly even in p9
        "C-supervisor-no-impl",
        # Slice tasks still need leaf tasks tracked
        "C-slice-leaf-tasks",
        # Cartographers persist from p8 into p9/p10 — no shutdown between phases
        "C-supervisor-cartographers",
        # Slices must be reviewed before closure; workers notify, supervisor closes
        "C-slice-review-before-close",
    }),
    PhaseId.P10_CODE_REVIEW: frozenset(_GENERAL_CONSTRAINTS | {
        # Code review → consensus required (all 3 reviewers ACCEPT)
        "C-review-consensus",
        # Code review → binary voting
        "C-review-binary",
        # Code review → severity tree must be created eagerly
        "C-severity-eager",
        # Code review → BLOCKER findings need dual parents
        "C-blocker-dual-parent",
        # Code review tasks → naming convention
        "C-review-naming",
        # Follow-up epic timing after code review
        "C-followup-timing",
        # Follow-up lifecycle management
        "C-followup-lifecycle",
        # Follow-up leaf adoption
        "C-followup-leaf-adoption",
        # Cartographers switch to reviewer role in p10
        "C-supervisor-cartographers",
        # Slices reviewed before closure — supervisor closes after review passes
        "C-slice-review-before-close",
        # Review-fix cycles capped at 3; remaining IMPORTANTs move to FOLLOWUP
        "C-max-review-cycles",
    }),
    PhaseId.P11_IMPL_UAT: frozenset(_GENERAL_CONSTRAINTS | {
        # Implementation UAT → verbatim capture
        "C-ure-verbatim",
    }),
    PhaseId.P12_LANDING: frozenset(_GENERAL_CONSTRAINTS | {
        # Landing phase commits code
        "C-agent-commit",
    }),
    # Terminal state — intentionally empty: no constraints apply after landing
    PhaseId.COMPLETE: frozenset(),
}


# ─── Context Lookup Functions ─────────────────────────────────────────────────


def _build_constraint_contexts(constraint_ids: frozenset[str]) -> frozenset[ConstraintContext]:
    """Build frozenset of ConstraintContext objects from a set of constraint IDs.

    Looks up each constraint ID in CONSTRAINT_SPECS and creates a ConstraintContext
    with the typed when and then fields from the ConstraintSpec.

    Raises KeyError for unknown constraint IDs (indicates a bug in _ROLE_CONSTRAINTS
    or _PHASE_CONSTRAINTS — the hand-authored dicts must only reference valid IDs).
    """
    contexts: set[ConstraintContext] = set()
    for cid in constraint_ids:
        spec = CONSTRAINT_SPECS.get(cid)
        if spec is None:
            raise KeyError(
                f"Constraint ID {cid!r} in _ROLE_CONSTRAINTS/_PHASE_CONSTRAINTS "
                f"not found in CONSTRAINT_SPECS. "
                f"Fix: update _ROLE_CONSTRAINTS/_PHASE_CONSTRAINTS to use a valid constraint ID."
            )
        contexts.add(ConstraintContext(
            id=spec.id,
            given=spec.given,
            when=spec.when,
            then=spec.then,
            should_not=spec.should_not,
        ))
    return frozenset(contexts)


def get_role_context(role: RoleId) -> RoleContext:
    """Return context injection fragment for the given agent role.

    Populates RoleContext with:
    - phases: frozenset[PhaseId] — phases where this role is an owner_role,
              derived by inverting PHASE_SPECS[phase].owner_roles.
    - constraints: frozenset[ConstraintContext] — typed when+then objects from
                   _ROLE_CONSTRAINTS[role] looked up in CONSTRAINT_SPECS.
    - commands: tuple[str, ...] — command names from COMMAND_SPECS where role_ref == role.
    - handoffs: tuple[str, ...] — handoff IDs from HANDOFF_SPECS where role is source or target.

    Args:
        role: The agent role to build context for.

    Returns:
        RoleContext frozen dataclass with all fields populated.
    """
    # Invert PHASE_SPECS[phase].owner_roles to find phases owned by this role.
    owned_phases: set[PhaseId] = {
        phase_id
        for phase_id, spec in PHASE_SPECS.items()
        if role in spec.owner_roles
    }

    # Build ConstraintContext objects from the hand-authored role constraint mapping.
    constraint_ids = _ROLE_CONSTRAINTS.get(role, frozenset())
    constraints = _build_constraint_contexts(constraint_ids)

    # Collect commands where role_ref matches this role.
    commands: tuple[str, ...] = tuple(
        sorted(
            spec.name
            for spec in COMMAND_SPECS.values()
            if spec.role_ref == role
        )
    )

    # Collect handoff IDs where this role is source or target.
    handoffs: tuple[str, ...] = tuple(
        sorted(
            spec.id
            for spec in HANDOFF_SPECS.values()
            if spec.source_role == role or spec.target_role == role
        )
    )

    return RoleContext(
        role=role,
        phases=frozenset(owned_phases),
        constraints=constraints,
        commands=commands,
        handoffs=handoffs,
    )


def get_phase_context(phase: PhaseId) -> PhaseContext:
    """Return context injection fragment for the given protocol phase.

    Populates PhaseContext with:
    - constraints: frozenset[ConstraintContext] — typed when+then objects from
                   _PHASE_CONSTRAINTS[phase] looked up in CONSTRAINT_SPECS.
    - labels: tuple[str, ...] — label values from LABEL_SPECS where phase_ref matches.
    - transitions: tuple[Transition, ...] — valid transitions from PHASE_SPECS[phase].

    Args:
        phase: The protocol phase to build context for.

    Returns:
        PhaseContext frozen dataclass with all fields populated.
    """
    # Build ConstraintContext objects from the hand-authored phase constraint mapping.
    constraint_ids = _PHASE_CONSTRAINTS.get(phase, frozenset())
    constraints = _build_constraint_contexts(constraint_ids)

    # Collect labels where phase_ref matches this phase's value.
    phase_value = phase.value
    labels: tuple[str, ...] = tuple(
        sorted(
            spec.value
            for spec in LABEL_SPECS.values()
            if spec.phase_ref == phase_value
        )
    )

    # Get valid transitions from PHASE_SPECS.
    phase_spec = PHASE_SPECS.get(phase)
    transitions: tuple[Transition, ...] = phase_spec.transitions if phase_spec is not None else ()

    return PhaseContext(
        phase=phase,
        constraints=constraints,
        labels=labels,
        transitions=transitions,
    )


# ─── Role Context Rendering ─────────────────────────────────────────────────


def render_role_context_as_text(role: RoleId) -> str:
    """Render role constraints as numbered, titled plain-text for prompt injection.

    Format per constraint:
        N. constraint: C-id
           given:      <given text>
           when:       <when text>
           then:       <then text>
           should not: <should_not text>

    Returns a ready-to-embed string with a header line and all constraints
    numbered and vertically aligned.
    """
    ctx = get_role_context(role)
    constraints = sorted(ctx.constraints, key=lambda c: c.id)
    n = len(constraints)

    lines: list[str] = [f"## Role Constraints: {role.value} ({n} constraints)"]
    lines.append("")

    # Determine number width for right-aligning numbers
    num_width = len(str(n))

    for i, c in enumerate(constraints, start=1):
        num_str = str(i).rjust(num_width)
        # Constraint header line
        lines.append(f"{num_str}. constraint: {c.id}")
        # GWT+S fields — labels left-aligned at fixed indent
        indent = " " * (num_width + 2)  # align under the 'c' in 'constraint'
        lines.append(f"{indent}given:      {c.given}")
        lines.append(f"{indent}when:       {c.when}")
        lines.append(f"{indent}then:       {c.then}")
        lines.append(f"{indent}should not: {c.should_not}")
        lines.append("")

    return "\n".join(lines)


def render_role_context_as_xml(role: RoleId) -> str:
    """Render role constraints as XML for structured prompt injection.

    Format:
        <role-constraints role="{role}" count="{N}">
          <constraint id="C-id" n="{N}">
            <given>{given}</given>
            <when>{when}</when>
            <then>{then}</then>
            <should-not>{should_not}</should-not>
          </constraint>
          ...
        </role-constraints>
    """
    ctx = get_role_context(role)
    constraints = sorted(ctx.constraints, key=lambda c: c.id)
    n = len(constraints)

    _QUOT = {'"': "&quot;"}
    role_escaped = xml_escape(role.value, entities=_QUOT)
    lines: list[str] = [
        f'<role-constraints role="{role_escaped}" count="{n}">'
    ]

    for i, c in enumerate(constraints, start=1):
        id_escaped = xml_escape(c.id, entities=_QUOT)
        lines.append(f'  <constraint id="{id_escaped}" n="{i}">')
        lines.append(f"    <given>{xml_escape(c.given)}</given>")
        lines.append(f"    <when>{xml_escape(c.when)}</when>")
        lines.append(f"    <then>{xml_escape(c.then)}</then>")
        lines.append(f"    <should-not>{xml_escape(c.should_not)}</should-not>")
        lines.append("  </constraint>")

    lines.append("</role-constraints>")

    return "\n".join(lines)
