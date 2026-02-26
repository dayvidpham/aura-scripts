"""Generate skills/protocol/schema.xml from Python type definitions.

Reads all canonical dicts from aura_protocol.types and produces a schema.xml
that matches the existing structure and passes validate_schema.py with 0 errors.

New in this generator (UAT-2, UAT-3):
- role-ref and phase-ref attributes on <constraint> elements, derived from
  context_injection._ROLE_CONSTRAINTS and _PHASE_CONSTRAINTS (single source).
- Unified diff shown to stdout before writing (UAT-2).
- SUBSTEP_DATA, _PHASE_TRANSITIONS, _PHASE_TASK_TITLES derived from types.py (DRY).

Public API:
    generate_schema(output, diff=True) -> str

    Returns the generated XML string.
    If diff=True and the file already exists, prints a unified diff before writing.
    Writes to output path only if content has changed (or file does not exist).
    Raises OSError on write failure.
"""

from __future__ import annotations

import difflib
import io
import xml.etree.ElementTree as ET
from pathlib import Path

from aura_protocol.context_injection import (
    _GENERAL_CONSTRAINTS as _CI_GENERAL_CONSTRAINTS,
    _PHASE_CONSTRAINTS as _CI_PHASE_CONSTRAINTS,
    _ROLE_CONSTRAINTS as _CI_ROLE_CONSTRAINTS,
)
from aura_protocol.types import (
    COMMAND_SPECS,
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    LABEL_SPECS,
    PHASE_SPECS,
    PROCEDURE_STEPS,
    REVIEW_AXIS_SPECS,
    ROLE_SPECS,
    SUBSTEP_DATA,
    TITLE_CONVENTIONS,
    ContentLevel,
    ExecutionMode,
    PhaseId,
    RoleId,
)


# ─── Constraint→Role/Phase Mappings (UAT-3, multi-value REVISE) ───────────────
# Derived from context_injection._ROLE_CONSTRAINTS and _PHASE_CONSTRAINTS (single source).
# gen_schema needs constraint→role(s) (1:many), while context_injection has
# role→constraints (1:many). These dicts are built by inverting context_injection's
# mappings at import time so the two modules stay in sync automatically.
#
# role-ref: ALL matching roles, comma-separated (e.g. "reviewer,supervisor,epoch").
# Constraints in _GENERAL_CONSTRAINTS (all roles) → None (omit role-ref from XML).
# phase-ref: ALL matching phases, comma-separated (e.g. "p4,p10").
# Constraints present in ALL phases (general) → None (omit phase-ref from XML).

_ROLE_PRIORITY: tuple[RoleId, ...] = (
    RoleId.EPOCH, RoleId.REVIEWER, RoleId.ARCHITECT, RoleId.SUPERVISOR, RoleId.WORKER,
)

_PHASE_ORDER: tuple[PhaseId, ...] = (
    PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P3_PROPOSE,
    PhaseId.P4_REVIEW, PhaseId.P5_UAT, PhaseId.P6_RATIFY,
    PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
    PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT, PhaseId.P12_LANDING,
)


def _build_constraint_role_refs() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for cid in CONSTRAINT_SPECS:
        if cid in _CI_GENERAL_CONSTRAINTS:
            result[cid] = None  # general = applies to all roles, omit from XML
            continue
        matching = [
            role for role in _ROLE_PRIORITY
            if cid in _CI_ROLE_CONSTRAINTS.get(role, frozenset())
        ]
        result[cid] = ",".join(r.value for r in matching) if matching else None
    return result


def _build_constraint_phase_refs() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for cid in CONSTRAINT_SPECS:
        if cid in _CI_GENERAL_CONSTRAINTS:
            result[cid] = None  # general = applies to all phases, omit from XML
            continue
        in_all = all(
            cid in constraints
            for phase, constraints in _CI_PHASE_CONSTRAINTS.items()
            if phase != PhaseId.COMPLETE  # terminal state has no constraints by design
        )
        if in_all:
            result[cid] = None  # applies to all phases, omit
            continue
        matching_phases = [
            phase for phase in _PHASE_ORDER
            if cid in _CI_PHASE_CONSTRAINTS.get(phase, frozenset())
        ]
        result[cid] = ",".join(p.value for p in matching_phases) if matching_phases else None
    return result


# Constraint → comma-separated role string(s) (or None for global) — for XML role-ref attribute.
_ROLE_CONSTRAINTS: dict[str, str | None] = _build_constraint_role_refs()

# Constraint → comma-separated phase string(s) (or None for global) — for XML phase-ref attribute.
_PHASE_CONSTRAINTS: dict[str, str | None] = _build_constraint_phase_refs()


# ─── Phase substep, task-title, and transition data ───────────────────────────
# Derived from types.py canonical dicts (mk16). No parallel static dicts here.

# SUBSTEP_DATA: moved to types.py as SUBSTEP_DATA (single source of truth).
# gen_schema reads it via the SUBSTEP_DATA import above.

# ─── Per-phase task-title data (derived from TITLE_CONVENTIONS) ───────────────
# Grouped by phase_ref. For phases with multiple titles, the substep ID is
# extracted from the label_ref (e.g. "L-p2s2_1" → substep="s2_1").

def _build_phase_task_titles() -> dict[str, list[dict]]:
    """Derive per-phase task-title hints from TITLE_CONVENTIONS."""
    by_phase: dict[str, list] = {}
    for tc in TITLE_CONVENTIONS:
        if tc.phase_ref:
            by_phase.setdefault(tc.phase_ref, []).append(tc)
    result: dict[str, list[dict]] = {}
    for pid, tcs in by_phase.items():
        entries = []
        multi = len(tcs) > 1
        for tc in tcs:
            entry: dict = {"pattern": tc.pattern}
            if multi:
                # Extract substep id from label_ref: "L-p2s2_1" → "s2_1"
                label = tc.label_ref[2:]          # drop "L-" prefix: "p2s2_1"
                parts = label.split("s", 1)       # ["p2", "2_1"]
                if len(parts) == 2:
                    entry["substep"] = "s" + parts[1]
            if tc.note:
                entry["convention"] = tc.note
            entries.append(entry)
        result[pid] = entries
    return result


_PHASE_TASK_TITLES: dict[str, list[dict]] = _build_phase_task_titles()


# ─── Phase transition data (derived from PHASE_SPECS) ─────────────────────────
# Supplement: skill-invocation for p7→p8 transition (not in types.py Transition).

_P7_SKILL_INVOCATION: dict[str, str] = {
    "target-role": "supervisor",
    "command-ref": "cmd-supervisor",
    "directive": "Supervisor launch prompt MUST start with Skill(/aura:supervisor)",
}


def _build_phase_transitions() -> dict[str, list[dict]]:
    """Derive phase transition dicts from PHASE_SPECS[phase].transitions."""
    result: dict[str, list[dict]] = {}
    for phase_id, phase_spec in PHASE_SPECS.items():
        pid = phase_id.value
        trans_list = []
        for t in phase_spec.transitions:
            entry: dict = {
                "to-phase": t.to_phase.value,
                "condition": t.condition,
            }
            if t.action is not None:
                entry["action"] = t.action
            # Add skill-invocation supplement for p7→p8 (C-handoff-skill-invocation)
            if phase_id == PhaseId.P7_HANDOFF and t.to_phase == PhaseId.P8_IMPL_PLAN:
                entry["skill-invocation"] = _P7_SKILL_INVOCATION
            trans_list.append(entry)
        if trans_list:
            result[pid] = trans_list
    return result


_PHASE_TRANSITIONS: dict[str, list[dict]] = _build_phase_transitions()


# ─── Role delegate data ───────────────────────────────────────────────────────

_ROLE_DELEGATES: dict[str, list[dict]] = {
    "epoch": [
        {"to-role": "architect", "phases": "p1,p2,p3,p4,p5,p6,p7"},
        {"to-role": "supervisor", "phases": "p7,p8,p9,p10,p11,p12"},
    ],
}


# ─── Role extra data ──────────────────────────────────────────────────────────
# label-awareness, invariants, standing-teams, ownership-model, uses-axes

_ROLE_LABEL_AWARENESS: dict[str, str] = {
    "architect": (
        "aura:p1-user, aura:p2-user, aura:p3-plan, aura:p4-plan, "
        "aura:p5-user, aura:p6-plan, aura:p7-plan"
    ),
    "reviewer": (
        "aura:p4-plan:s4-review, aura:p10-impl:s10-review, "
        "aura:severity:blocker, aura:severity:important, aura:severity:minor"
    ),
    "supervisor": (
        "aura:p7-plan, aura:p8-impl, aura:p9-impl, aura:p10-impl, "
        "aura:p11-user, aura:p12-impl, aura:epic-followup"
    ),
    "worker": "aura:p9-impl:s9-slice",
}

_ROLE_INVARIANTS: dict[str, list[str]] = {
    "supervisor": [
        "NEVER implements code — always spawns workers",
        "NEVER explores codebase directly — delegates to standing explore team",
        "ALWAYS creates leaf tasks within each slice — no undecomposed slices",
        "Creates follow-up epic when code review has IMPORTANT or MINOR findings",
    ],
}

_ROLE_OWNERSHIP_MODEL: dict[str, str] = {
    "worker": (
        "One worker per production code path. Owns full vertical\n"
        "      (types → tests → implementation → wiring)."
    ),
}

_ROLE_USES_AXES: dict[str, list[str]] = {
    "reviewer": ["axis-A", "axis-B", "axis-C"],
}


# ─── Command group data ───────────────────────────────────────────────────────
# Comment headers to group commands in the output

_COMMAND_COMMENTS: dict[str, str] = {
    "cmd-epoch":             "Orchestration",
    "cmd-user-request":      "User interaction",
    "cmd-architect":         "Architect",
    "cmd-supervisor":        "Supervisor",
    "cmd-worker":            "Worker",
    "cmd-reviewer":          "Reviewer",
    "cmd-impl-slice":        "Implementation coordination",
    "cmd-msg-send":          "Messaging (Beads-based IPC)",
    "cmd-explore":           "Exploration",
    "cmd-test":              "Utilities",
}


# ─── Handoff extra data ───────────────────────────────────────────────────────

_HANDOFF_FILE_PATTERNS: dict[str, str] = {
    "h1": "architect-to-supervisor.md",
    "h2": "supervisor-to-worker.md",
    "h3": "supervisor-to-reviewer.md",
    "h4": "worker-to-reviewer.md",
    "h5": "reviewer-to-followup.md",
    "h6": "supervisor-to-architect.md",
}

_HANDOFF_SKILL_INVOCATIONS: dict[str, dict] = {
    "h1": {
        "directive": "Skill(/aura:supervisor)",
        "note": (
            "Supervisor launch prompt MUST start with this invocation. Without it, "
            "supervisor skips explore team setup and leaf task creation."
        ),
    },
    "h2": {
        "directive": "Skill(/aura:worker)",
        "note": "Worker message MUST include explicit instruction to call this skill.",
    },
    "h3": {
        "directive": "Skill(/aura:reviewer)",
        "note": "Reviewer prompt MUST include instruction to call this skill.",
    },
}

_HANDOFF_NOTES: dict[str, str] = {
    "h5": (
        "Reviewer hands IMPORTANT/MINOR findings to supervisor, who creates the follow-up epic"
    ),
    "h6": (
        "Follow-up specific. Supervisor completes FOLLOWUP_URE and FOLLOWUP_URD,\n"
        "      then hands off to architect with scoped findings and requirements\n"
        "      for FOLLOWUP_PROPOSAL creation."
    ),
}

_HANDOFF_TRIGGERS: dict[str, str] = {
    "h5": "IMPORTANT or MINOR findings exist",
    "h6": "follow-up lifecycle only",
}


# ─── XML Generation ───────────────────────────────────────────────────────────


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Add pretty-print indentation to an XML element tree in-place."""
    indent_str = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent_str + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_str
        for child in elem:
            _indent(child, level + 1)
        # Fix last child's tail
        if not child.tail or not child.tail.strip():
            child.tail = indent_str
    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_str


def _build_enums(root: ET.Element) -> None:
    """Append <enums> section to root."""
    enums = ET.SubElement(root, "enums")

    # DomainType
    domain_enum = ET.SubElement(enums, "enum", name="DomainType")
    ET.SubElement(domain_enum, "value", id="user",
                  description="User-facing interaction (requests, elicitation, UAT)")
    ET.SubElement(domain_enum, "value", id="plan",
                  description="Planning and design (proposals, reviews, ratification)")
    ET.SubElement(domain_enum, "value", id="impl",
                  description="Implementation (slices, code review, landing)")

    # VoteType
    vote_enum = ET.SubElement(enums, "enum", name="VoteType")
    ET.SubElement(vote_enum, "value", id="ACCEPT",
                  description="All review criteria satisfied; no BLOCKER items")
    ET.SubElement(vote_enum, "value", id="REVISE",
                  description="BLOCKER issues found; must provide actionable feedback")

    # SeverityLevel
    sev_enum = ET.SubElement(enums, "enum", name="SeverityLevel")
    ET.SubElement(sev_enum, "value", id="BLOCKER", blocks="true",
                  label="aura:severity:blocker",
                  description="Security, type errors, test failures, broken production code paths")
    ET.SubElement(sev_enum, "value", id="IMPORTANT", blocks="false",
                  label="aura:severity:important",
                  description="Performance, missing validation, architectural concerns")
    ET.SubElement(sev_enum, "value", id="MINOR", blocks="false",
                  label="aura:severity:minor",
                  description="Style, optional optimizations, naming improvements")

    # ExecutionMode
    exec_enum = ET.SubElement(enums, "enum", name="ExecutionMode")
    ET.SubElement(exec_enum, "value", id="sequential",
                  description="Must complete before next step starts")
    ET.SubElement(exec_enum, "value", id="parallel",
                  description="Can run concurrently with sibling steps in same parallel-group")

    # ContentLevel
    content_enum = ET.SubElement(enums, "enum", name="ContentLevel")
    ET.SubElement(content_enum, "value", id="full-provenance",
                  description="Full inline context with all decisions and rationale")
    ET.SubElement(content_enum, "value", id="summary-with-ids",
                  description="Summary with Beads task ID references")

    # Classification axes (comment)
    enums.append(ET.Comment(" Classification axes (s1_1-classify) "))

    # ClassificationScope
    scope_enum = ET.SubElement(enums, "enum", name="ClassificationScope")
    ET.SubElement(scope_enum, "value", id="single-file",
                  description="Change is isolated to a single file")
    ET.SubElement(scope_enum, "value", id="module",
                  description="Change spans a module or package")
    ET.SubElement(scope_enum, "value", id="cross-cutting",
                  description="Change affects multiple modules or subsystems")

    # ClassificationComplexity
    complexity_enum = ET.SubElement(enums, "enum", name="ClassificationComplexity")
    ET.SubElement(complexity_enum, "value", id="low",
                  description="Straightforward implementation, familiar patterns")
    ET.SubElement(complexity_enum, "value", id="medium",
                  description="Some design decisions needed, moderate scope")
    ET.SubElement(complexity_enum, "value", id="high",
                  description="Significant design work, unfamiliar territory, or many moving parts")

    # ClassificationRisk
    risk_enum = ET.SubElement(enums, "enum", name="ClassificationRisk")
    ET.SubElement(risk_enum, "value", id="internal-only",
                  description="No external API changes, no breaking changes")
    ET.SubElement(risk_enum, "value", id="new-api",
                  description="Introduces new public interfaces or APIs")
    ET.SubElement(risk_enum, "value", id="breaking-changes",
                  description="Modifies existing behavior or public contracts")

    # ClassificationNovelty
    novelty_enum = ET.SubElement(enums, "enum", name="ClassificationNovelty")
    ET.SubElement(novelty_enum, "value", id="familiar",
                  description="Well-known patterns, team has done this before")
    ET.SubElement(novelty_enum, "value", id="new-territory",
                  description="Unfamiliar domain, requires research and exploration")

    # ResearchDepth
    research_enum = ET.SubElement(enums, "enum", name="ResearchDepth")
    ET.SubElement(research_enum, "value", id="quick-scan",
                  description=(
                      "Familiar domain, low complexity — brief prior art check (local only)"
                  ))
    ET.SubElement(research_enum, "value", id="standard-research",
                  description=(
                      "Moderate complexity or some novelty — find existing patterns "
                      "and standards (local + docs)"
                  ))
    ET.SubElement(research_enum, "value", id="deep-dive",
                  description=(
                      "High complexity, new territory, or high risk — "
                      "thorough domain analysis (local + web)"
                  ))


def _build_labels(root: ET.Element) -> None:
    """Append <labels> section to root, derived from LABEL_SPECS."""
    labels = ET.SubElement(root, "labels")
    labels.append(ET.Comment(" Phase labels (one per substep) "))

    # Phase labels first (non-special), then special labels
    phase_label_ids = [
        "L-p1s1_1", "L-p1s1_2", "L-p1s1_3",
        "L-p2s2_1", "L-p2s2_2",
        "L-p3s3", "L-p4s4", "L-p5s5", "L-p6s6", "L-p7s7",
        "L-p8s8", "L-p9s9", "L-p10s10", "L-p11s11", "L-p12s12",
    ]
    special_label_ids = [
        "L-urd", "L-superseded",
        "L-sev-blocker", "L-sev-import", "L-sev-minor",
        "L-followup",
    ]

    for lid in phase_label_ids:
        spec = LABEL_SPECS[lid]
        attrs: dict[str, str] = {"id": spec.id, "value": spec.value}
        if spec.phase_ref:
            attrs["phase-ref"] = spec.phase_ref
        if spec.substep_ref:
            attrs["substep-ref"] = spec.substep_ref
        ET.SubElement(labels, "label", **attrs)

    labels.append(ET.Comment(" Special labels (not phase-scoped) "))
    for lid in special_label_ids:
        spec = LABEL_SPECS[lid]
        attrs = {"id": spec.id, "value": spec.value, "special": "true"}
        if spec.description:
            attrs["description"] = spec.description
        if spec.severity_ref:
            attrs["severity-ref"] = spec.severity_ref
        ET.SubElement(labels, "label", **attrs)


def _build_review_axes(root: ET.Element) -> None:
    """Append <review-axes> section to root, derived from REVIEW_AXIS_SPECS."""
    axes_el = ET.SubElement(root, "review-axes")

    for axis_id in ("axis-A", "axis-B", "axis-C"):
        spec = REVIEW_AXIS_SPECS[axis_id]
        axis_el = ET.SubElement(axes_el, "axis",
                                id=spec.id,
                                letter=spec.letter.value,
                                name=spec.name,
                                short=spec.short)
        kq_el = ET.SubElement(axis_el, "key-questions")
        for q in spec.key_questions:
            q_el = ET.SubElement(kq_el, "q")
            q_el.text = q


def _build_phases(root: ET.Element) -> None:
    """Append <phases> section to root, derived from PHASE_SPECS."""
    phases_el = ET.SubElement(root, "phases")

    # Phase ordering: p1 through p12 by number
    ordered_phase_ids = [
        pid for pid in [
            PhaseId.P1_REQUEST, PhaseId.P2_ELICIT, PhaseId.P3_PROPOSE,
            PhaseId.P4_REVIEW, PhaseId.P5_UAT, PhaseId.P6_RATIFY,
            PhaseId.P7_HANDOFF, PhaseId.P8_IMPL_PLAN, PhaseId.P9_SLICE,
            PhaseId.P10_CODE_REVIEW, PhaseId.P11_IMPL_UAT, PhaseId.P12_LANDING,
        ]
    ]

    for phase_id in ordered_phase_ids:
        spec = PHASE_SPECS[phase_id]
        pid = spec.id.value

        phase_el = ET.SubElement(phases_el, "phase",
                                  id=pid,
                                  number=str(spec.number),
                                  domain=spec.domain.value,
                                  name=spec.name)

        # Description
        desc_el = ET.SubElement(phase_el, "description")
        # Use the name to derive description (from schema.xml)
        _phase_descriptions = {
            "p1": "Capture, classify, research, and explore user request",
            "p2": "User Requirements Elicitation survey and URD creation",
            "p3": "Architect creates technical proposal",
            "p4": "3 axis-specific reviewers assess proposal",
            "p5": "User acceptance test on the plan",
            "p6": "Ratify the accepted proposal, supersede old ones",
            "p7": "Architect hands off to supervisor",
            "p8": "Supervisor decomposes ratified plan into vertical slices",
            "p9": "Parallel workers implement vertical slices",
            "p10": "3 axis-specific reviewers review ALL slices",
            "p11": "User acceptance test on the implementation",
            "p12": "Commit, push, close tasks, hand off",
        }
        desc_el.text = _phase_descriptions[pid]

        # Substeps (from types.py SUBSTEP_DATA — single source of truth)
        substep_data_list = SUBSTEP_DATA.get(pid, [])
        if substep_data_list:
            substeps_el = ET.SubElement(phase_el, "substeps")
            for sd in substep_data_list:
                attrs: dict[str, str] = {
                    "id": sd["id"],
                    "type": sd["type"],
                    "execution": sd["execution"],
                    "order": sd["order"],
                }
                if "parallel-group" in sd:
                    attrs["parallel-group"] = sd["parallel-group"]
                attrs["label-ref"] = sd["label-ref"]

                substep_el = ET.SubElement(substeps_el, "substep", **attrs)

                sub_desc_el = ET.SubElement(substep_el, "description")
                sub_desc_el.text = sd["description"]

                # Extra label (e.g. URD label on s2_2)
                if "extra-label" in sd:
                    ET.SubElement(substep_el, "extra-label", ref=sd["extra-label"])

                # Instances (e.g. count="3" per="review-axis")
                if "instances" in sd:
                    inst = sd["instances"]
                    ET.SubElement(substep_el, "instances",
                                  count=inst["count"], per=inst["per"])

                # Startup sequence for p8/s8 supervisor steps
                if sd.get("startup-sequence"):
                    startup_el = ET.SubElement(substep_el, "startup-sequence")
                    sup_steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
                    for step in sup_steps:
                        step_el = ET.SubElement(startup_el, "step",
                                                order=str(step.order),
                                                id=step.id)
                        instr_el = ET.SubElement(step_el, "instruction")
                        instr_el.text = step.instruction
                        if step.command is not None:
                            cmd_el = ET.SubElement(step_el, "command")
                            cmd_el.text = step.command
                        if step.context is not None:
                            ctx_el = ET.SubElement(step_el, "context")
                            ctx_el.text = step.context
                        if step.next_state is not None:
                            ns_el = ET.SubElement(step_el, "next-state")
                            ns_el.text = step.next_state.value

        # Task-title(s) for this phase
        if pid in _PHASE_TASK_TITLES:
            for tt in _PHASE_TASK_TITLES[pid]:
                tt_el = ET.SubElement(phase_el, "task-title", pattern=tt["pattern"])
                if "substep" in tt:
                    tt_el.set("substep", tt["substep"])
                if "convention" in tt:
                    conv_el = ET.SubElement(tt_el, "convention")
                    conv_el.text = tt["convention"]

        # Severity-tree (p4: disabled, p10: enabled)
        if pid == "p4":
            ET.SubElement(phase_el, "severity-tree",
                          enabled="false",
                          reason="Plan reviews use binary ACCEPT/REVISE only")
        elif pid == "p9":
            # TDD layers
            tdd_el = ET.SubElement(phase_el, "tdd-layers")
            worker_steps = PROCEDURE_STEPS[RoleId.WORKER]
            layer_names = ["Types", "Tests", "Implementation"]
            for step in worker_steps:
                ET.SubElement(tdd_el, "layer",
                              number=str(step.order),
                              name=layer_names[step.order - 1],
                              description=step.instruction)
        elif pid == "p10":
            sev_tree = ET.SubElement(phase_el, "severity-tree",
                                     enabled="true", creation="eager")
            rule1 = ET.SubElement(sev_tree, "rule")
            rule1.text = "Always create 3 severity groups per review round, even if empty."
            rule2 = ET.SubElement(sev_tree, "rule")
            rule2.text = "Empty groups have no children and are closed immediately."
            ET.SubElement(sev_tree, "group",
                          **{"severity-ref": "BLOCKER",
                             "label-ref": "L-sev-blocker",
                             "dual-parent": "true"})
            ET.SubElement(sev_tree, "group",
                          **{"severity-ref": "IMPORTANT",
                             "label-ref": "L-sev-import"})
            ET.SubElement(sev_tree, "group",
                          **{"severity-ref": "MINOR",
                             "label-ref": "L-sev-minor"})

            # followup-epic
            ET.SubElement(phase_el, "followup-epic",
                          **{"label-ref": "L-followup",
                             "trigger": (
                                 "review-completion AND (IMPORTANT OR MINOR findings exist)"
                             ),
                             "gated-on-blocker": "false",
                             "owner-role": "supervisor"})

        # same-actor-as (p6: same as p5)
        if pid == "p6":
            ET.SubElement(phase_el, "same-actor-as",
                          **{"phase-ref": "p5",
                             "note": (
                                 "Architect performs p5, p6, p7 "
                                 "— no handoff between them"
                             )})

        # Transitions
        trans_list = _PHASE_TRANSITIONS.get(pid, [])
        if trans_list:
            transitions_el = ET.SubElement(phase_el, "transitions")
            for t in trans_list:
                t_attrs: dict[str, str] = {
                    "to-phase": t["to-phase"],
                    "condition": t["condition"],
                }
                if "action" in t:
                    t_attrs["action"] = t["action"]
                t_el = ET.SubElement(transitions_el, "transition", **t_attrs)

                # Skill invocation in transition (p7→p8)
                if "skill-invocation" in t:
                    si = t["skill-invocation"]
                    si_attrs: dict[str, str] = {
                        "target-role": si["target-role"],
                        "command-ref": si["command-ref"],
                        "directive": si["directive"],
                    }
                    ET.SubElement(t_el, "skill-invocation", **si_attrs)


def _build_roles(root: ET.Element) -> None:
    """Append <roles> section to root, derived from ROLE_SPECS."""
    roles_el = ET.SubElement(root, "roles")

    role_order = [RoleId.EPOCH, RoleId.ARCHITECT, RoleId.REVIEWER,
                  RoleId.SUPERVISOR, RoleId.WORKER]

    for role_id in role_order:
        spec = ROLE_SPECS[role_id]
        rid = spec.id.value

        role_el = ET.SubElement(roles_el, "role",
                                 id=rid,
                                 name=spec.name,
                                 description=spec.description)

        # owns-phases
        owns_el = ET.SubElement(role_el, "owns-phases")
        # Sort phases by number to ensure consistent output
        sorted_phases = sorted(spec.owned_phases,
                               key=lambda p: int(p.value[1:]) if p.value[1:].isdigit() else 0)
        for phase_ref in sorted_phases:
            ET.SubElement(owns_el, "phase-ref", ref=phase_ref.value)

        # Delegates (epoch only)
        if rid in _ROLE_DELEGATES:
            delegates_el = ET.SubElement(role_el, "delegates")
            for delegate in _ROLE_DELEGATES[rid]:
                ET.SubElement(delegates_el, "delegate",
                              **{"to-role": delegate["to-role"],
                                 "phases": delegate["phases"]})

        # Label awareness
        if rid in _ROLE_LABEL_AWARENESS:
            la_el = ET.SubElement(role_el, "label-awareness")
            la_el.text = "\n      " + _ROLE_LABEL_AWARENESS[rid] + "\n    "

        # Uses axes (reviewer)
        if rid in _ROLE_USES_AXES:
            uses_el = ET.SubElement(role_el, "uses-axes")
            for axis_ref in _ROLE_USES_AXES[rid]:
                ET.SubElement(uses_el, "axis-ref", ref=axis_ref)

        # Invariants (supervisor)
        if rid in _ROLE_INVARIANTS:
            inv_parent = ET.SubElement(role_el, "invariants")
            for inv_text in _ROLE_INVARIANTS[rid]:
                inv_el = ET.SubElement(inv_parent, "invariant")
                inv_el.text = inv_text

        # Standing teams (supervisor)
        if rid == "supervisor":
            teams_el = ET.SubElement(role_el, "standing-teams")
            team_el = ET.SubElement(teams_el, "team",
                                    id="explore-team",
                                    purpose="Context-cached codebase exploration agents")
            desc_el = ET.SubElement(team_el, "description")
            desc_el.text = (
                "\n          Standing team of explore agents created via TeamCreate "
                "at the start of Phase 8.\n"
                "          Each agent is scoped to a specific codebase domain. "
                "Agents retain context between\n"
                "          queries, making follow-up questions on the same domain "
                "near-zero-cost.\n"
                "          Minimum 1 agent; scale based on feature complexity (1-4 agents).\n"
                "        "
            )
            at_el = ET.SubElement(team_el, "agent-template",
                                  role="explore",
                                  **{"skill-ref": "cmd-explore",
                                     "invocation": "Skill(/aura:explore)",
                                     "min-count": "1",
                                     "max-count": "4"})
            scoping_el = ET.SubElement(at_el, "scoping")
            scoping_el.text = (
                "Each agent assigned a specific codebase domain "
                "(e.g., CLI wiring, DB layer, build system)"
            )
            lc_el = ET.SubElement(at_el, "lifecycle")
            lc_el.text = (
                "Created before exploration, shut down after all slices have leaf tasks"
            )

        # Ownership model (worker)
        if rid in _ROLE_OWNERSHIP_MODEL:
            om_el = ET.SubElement(role_el, "ownership-model")
            om_el.text = "\n      " + _ROLE_OWNERSHIP_MODEL[rid] + "\n    "


def _build_commands(root: ET.Element) -> None:
    """Append <commands> section to root, derived from COMMAND_SPECS."""
    commands_el = ET.SubElement(root, "commands")

    # Ordered command IDs matching schema.xml order
    command_order = [
        # Orchestration
        "cmd-epoch", "cmd-plan", "cmd-status",
        # User interaction
        "cmd-user-request", "cmd-user-elicit", "cmd-user-uat",
        # Architect
        "cmd-architect", "cmd-arch-propose", "cmd-arch-review",
        "cmd-arch-ratify", "cmd-arch-handoff",
        # Supervisor
        "cmd-supervisor", "cmd-sup-plan", "cmd-sup-spawn",
        "cmd-sup-track", "cmd-sup-commit",
        # Worker
        "cmd-worker", "cmd-work-impl", "cmd-work-complete", "cmd-work-blocked",
        # Reviewer
        "cmd-reviewer", "cmd-rev-plan", "cmd-rev-code",
        "cmd-rev-comment", "cmd-rev-vote",
        # Implementation coordination
        "cmd-impl-slice", "cmd-impl-review",
        # Messaging
        "cmd-msg-send", "cmd-msg-receive", "cmd-msg-broadcast", "cmd-msg-ack",
        # Exploration
        "cmd-explore", "cmd-research",
        # Utilities
        "cmd-test", "cmd-feedback",
    ]

    # Group comment markers
    _group_start_comments = {
        "cmd-epoch": " ── Orchestration ──────────────────────────────────────────────── ",
        "cmd-user-request": " ── User interaction ───────────────────────────────────────── ",
        "cmd-architect": " ── Architect ──────────────────────────────────────────────────── ",
        "cmd-supervisor": " ── Supervisor ─────────────────────────────────────────────────── ",
        "cmd-worker": " ── Worker ─────────────────────────────────────────────────────── ",
        "cmd-reviewer": " ── Reviewer ───────────────────────────────────────────────────── ",
        "cmd-impl-slice": " ── Implementation coordination ────────────────────────────────── ",
        "cmd-msg-send": " ── Messaging (Beads-based IPC) ────────────────────────────────── ",
        "cmd-explore": " ── Exploration ────────────────────────────────────────────────── ",
        "cmd-test": " ── Utilities ──────────────────────────────────────────────────── ",
    }

    for cid in command_order:
        if cid not in COMMAND_SPECS:
            continue
        spec = COMMAND_SPECS[cid]

        # Add group comment
        if cid in _group_start_comments:
            commands_el.append(ET.Comment(_group_start_comments[cid]))

        cmd_attrs: dict[str, str] = {"id": spec.id, "name": spec.name}
        if spec.role_ref is not None:
            cmd_attrs["role-ref"] = spec.role_ref.value
        cmd_attrs["description"] = spec.description

        cmd_el = ET.SubElement(commands_el, "command", **cmd_attrs)

        # phases
        if spec.phases:
            phases_el = ET.SubElement(cmd_el, "phases")
            for phase_ref in spec.phases:
                ET.SubElement(phases_el, "phase-ref", ref=phase_ref)

        # creates-labels
        if spec.creates_labels:
            cl_el = ET.SubElement(cmd_el, "creates-labels")
            for label_ref in spec.creates_labels:
                ET.SubElement(cl_el, "label-ref", ref=label_ref)

        # file
        file_el = ET.SubElement(cmd_el, "file")
        file_el.text = spec.file

        # cmd-explore special note
        if cid == "cmd-explore":
            note_el = ET.SubElement(cmd_el, "note")
            note_el.text = (
                "Used in Phase 1 (s1_3) by architect, and in Phase 8 by "
                "supervisor's standing explore team."
            )


def _build_handoffs(root: ET.Element) -> None:
    """Append <handoffs> section to root, derived from HANDOFF_SPECS."""
    handoffs_el = ET.SubElement(root, "handoffs",
                                **{"storage-pattern": (
                                    ".git/.aura/handoff/"
                                    "{request-task-id}/{source}-to-{target}.md"
                                )})

    handoff_order = ["h1", "h2", "h3", "h4", "h5", "h6"]

    for hid in handoff_order:
        spec = HANDOFF_SPECS[hid]
        h_attrs: dict[str, str] = {
            "id": spec.id,
            "source-role": spec.source_role.value,
            "target-role": spec.target_role.value,
            "at-phase": spec.at_phase.value,
            "content-level": spec.content_level.value,
        }
        if hid in _HANDOFF_FILE_PATTERNS:
            h_attrs["file-pattern"] = _HANDOFF_FILE_PATTERNS[hid]
        if hid in _HANDOFF_TRIGGERS:
            h_attrs["trigger"] = _HANDOFF_TRIGGERS[hid]
            if hid == "h6":
                h_attrs["context"] = _HANDOFF_TRIGGERS[hid]
                del h_attrs["trigger"]

        h_el = ET.SubElement(handoffs_el, "handoff", **h_attrs)

        # required-fields
        rf_el = ET.SubElement(h_el, "required-fields")
        rf_el.text = "\n      " + ", ".join(spec.required_fields) + "\n    "

        # skill-invocation
        if hid in _HANDOFF_SKILL_INVOCATIONS:
            si = _HANDOFF_SKILL_INVOCATIONS[hid]
            si_attrs: dict[str, str] = {"directive": si["directive"]}
            if "note" in si:
                si_attrs["note"] = si["note"]
            ET.SubElement(h_el, "skill-invocation", **si_attrs)

        # notes
        if hid in _HANDOFF_NOTES:
            note_el = ET.SubElement(h_el, "note")
            note_el.text = "\n      " + _HANDOFF_NOTES[hid] + "\n    "

    # same-actor-transitions
    sat_el = ET.SubElement(handoffs_el, "same-actor-transitions",
                           note="No handoff document needed")
    ET.SubElement(sat_el, "transition",
                  **{"from-phase": "p5", "to-phase": "p6", "actor": "architect"})
    ET.SubElement(sat_el, "transition",
                  **{"from-phase": "p6", "to-phase": "p7", "actor": "architect"})


def _build_constraints(root: ET.Element) -> None:
    """Append <constraints> section to root, derived from CONSTRAINT_SPECS.

    Adds role-ref and phase-ref attributes on each constraint element
    derived from _ROLE_CONSTRAINTS and _PHASE_CONSTRAINTS static dicts (UAT-3).
    """
    constraints_el = ET.SubElement(root, "constraints")

    # Constraint order derived from CONSTRAINT_SPECS (Python is SoT — dict insertion order)
    constraint_order = list(CONSTRAINT_SPECS.keys())

    # Group comment markers for constraints
    _constraint_group_comments = {
        "C-audit-never-delete": " Audit trail ",
        "C-review-consensus":   " Reviews ",
        "C-vertical-slices":    " Ownership ",
        "C-dep-direction":      " Task management ",
        "C-agent-commit":       " Git ",
        "C-proposal-naming":    " Naming ",
        "C-ure-verbatim":       " User interviews ",
        "C-followup-lifecycle": " Follow-up lifecycle ",
        "C-actionable-errors":  " Error quality ",
        "C-worker-gates":       " Worker completion ",
    }

    for cid in constraint_order:
        spec = CONSTRAINT_SPECS[cid]

        if cid in _constraint_group_comments:
            constraints_el.append(ET.Comment(_constraint_group_comments[cid]))

        c_attrs: dict[str, str] = {
            "id": spec.id,
            "given": spec.given,
            "when": spec.when,
            "then": spec.then,
            "should-not": spec.should_not,
        }
        # UAT-3: add role-ref and phase-ref when present
        role_ref = _ROLE_CONSTRAINTS.get(cid)
        if role_ref is not None:
            c_attrs["role-ref"] = role_ref
        phase_ref = _PHASE_CONSTRAINTS.get(cid)
        if phase_ref is not None:
            c_attrs["phase-ref"] = phase_ref

        ET.SubElement(constraints_el, "constraint", **c_attrs)


def _build_task_titles(root: ET.Element) -> None:
    """Append <task-titles> section to root, derived from TITLE_CONVENTIONS."""
    task_titles_el = ET.SubElement(root, "task-titles")

    for tc in TITLE_CONVENTIONS:
        attrs: dict[str, str] = {
            "pattern": tc.pattern,
            "label-ref": tc.label_ref,
            "created-by": tc.created_by,
        }
        if tc.phase_ref:
            attrs["phase-ref"] = tc.phase_ref
        if tc.extra_label_ref:
            attrs["extra-label-ref"] = tc.extra_label_ref
        if tc.note:
            attrs["note"] = tc.note

        ET.SubElement(task_titles_el, "title-convention", **attrs)


def _build_documents(root: ET.Element) -> None:
    """Append <documents> section to root (static structure from schema.xml)."""
    docs_el = ET.SubElement(root, "documents")

    # Document definitions (static — mirrors schema.xml)
    _documents: list[dict] = [
        {
            "id": "doc-readme", "path": "protocol/README.md",
            "purpose": "Protocol entry point and quick-start guide",
            "covers": [
                {"type": "phase", "refs": "p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12",
                 "depth": "overview"},
                {"type": "label", "refs": "all", "depth": "schema-summary"},
            ],
        },
        {
            "id": "doc-claude", "path": "protocol/CLAUDE.md",
            "purpose": (
                "Core agent directive: philosophy, constraints, roles, label schema"
            ),
            "covers": [
                {"type": "phase", "refs": "p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12",
                 "depth": "summary"},
                {"type": "role", "refs": "architect,reviewer,supervisor,worker",
                 "depth": "summary"},
                {"type": "label", "refs": "all", "depth": "full"},
                {"type": "constraint", "refs": "all-protocol", "depth": "full"},
                {"type": "task-title", "refs": "all", "depth": "full"},
                {"type": "handoff", "refs": "h1,h2,h3,h4,h5,h6", "depth": "summary"},
                {"type": "severity", "refs": "BLOCKER,IMPORTANT,MINOR", "depth": "full"},
                {"type": "review-axis", "refs": "axis-A,axis-B,axis-C", "depth": "summary"},
            ],
        },
        {
            "id": "doc-constraints", "path": "protocol/CONSTRAINTS.md",
            "purpose": (
                "Coding standards, checklists, severity definitions, naming conventions"
            ),
            "covers": [
                {"type": "constraint", "refs": "all", "depth": "full"},
                {"type": "severity", "refs": "BLOCKER,IMPORTANT,MINOR", "depth": "full"},
                {"type": "vote", "refs": "ACCEPT,REVISE", "depth": "full"},
                {"type": "label", "refs": "all", "depth": "schema"},
                {"type": "task-title", "refs": "all", "depth": "full"},
            ],
        },
        {
            "id": "doc-process", "path": "protocol/PROCESS.md",
            "purpose": (
                "Step-by-step workflow execution (single source of truth)"
            ),
            "covers": [
                {"type": "phase", "refs": "p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12",
                 "depth": "full"},
                {"type": "substep", "refs": "all", "depth": "full"},
                {"type": "role", "refs": "architect,reviewer,supervisor,worker",
                 "depth": "tools-matrix"},
                {"type": "command", "refs": "all", "depth": "tools-matrix"},
                {"type": "label", "refs": "all", "depth": "full"},
                {"type": "transition", "refs": "all", "depth": "full"},
                {"type": "severity", "refs": "BLOCKER,IMPORTANT,MINOR", "depth": "full"},
            ],
        },
        {
            "id": "doc-agents", "path": "protocol/AGENTS.md",
            "purpose": "Role taxonomy: phases owned, tools, handoffs per agent",
            "covers": [
                {"type": "role", "refs": "epoch,architect,reviewer,supervisor,worker",
                 "depth": "full"},
                {"type": "phase", "refs": "all", "depth": "role-mapping"},
                {"type": "command", "refs": "all", "depth": "role-mapping"},
                {"type": "handoff", "refs": "h1,h2,h3,h4,h5,h6", "depth": "full"},
                {"type": "review-axis", "refs": "axis-A,axis-B,axis-C", "depth": "full"},
            ],
        },
        {
            "id": "doc-skills", "path": "protocol/SKILLS.md",
            "purpose": (
                "Command reference: all /aura:* skills mapped to phase and role"
            ),
            "covers": [
                {"type": "command", "refs": "all", "depth": "full"},
                {"type": "phase", "refs": "all", "depth": "command-mapping"},
                {"type": "role", "refs": "all", "depth": "command-mapping"},
                {"type": "label", "refs": "all", "depth": "command-creates"},
                {"type": "review-axis", "refs": "axis-A,axis-B,axis-C", "depth": "summary"},
            ],
        },
        {
            "id": "doc-handoff", "path": "protocol/HANDOFF_TEMPLATE.md",
            "purpose": "Standardized template for 6 actor-change transitions",
            "covers": [
                {"type": "handoff", "refs": "h1,h2,h3,h4,h5,h6", "depth": "full"},
                {"type": "role", "refs": "architect,supervisor,worker,reviewer",
                 "depth": "handoff-fields"},
            ],
        },
        {
            "id": "doc-migration", "path": "protocol/MIGRATION_v1_to_v2.md",
            "purpose": "Label and title migration from v1 to v2",
            "covers": [
                {"type": "label", "refs": "all", "depth": "v1-v2-mapping"},
                {"type": "task-title", "refs": "all", "depth": "v1-v2-mapping"},
                {"type": "vote", "refs": "ACCEPT,REVISE", "depth": "v1-v2-mapping"},
            ],
        },
        {
            "id": "doc-uat-template", "path": "protocol/UAT_TEMPLATE.md",
            "purpose": "User Acceptance Test structured output template",
            "covers": [
                {"type": "phase", "refs": "p5,p11", "depth": "template"},
            ],
        },
        {
            "id": "doc-uat-example", "path": "protocol/UAT_EXAMPLE.md",
            "purpose": "Worked UAT example",
            "covers": [
                {"type": "phase", "refs": "p5", "depth": "example"},
            ],
        },
        {
            "id": "doc-schema", "path": "protocol/schema.xml",
            "purpose": (
                "This file: canonical machine-readable protocol definition (BCNF)"
            ),
            "covers": [
                {"type": "all", "depth": "full",
                 "note": (
                     "Single source of truth for all entity definitions and relationships"
                 )},
            ],
        },
    ]

    _root_docs: list[dict] = [
        {
            "id": "doc-root-readme", "path": "README.md",
            "purpose": "Project README with workflow overview, commands, structure",
            "covers": [
                {"type": "phase", "refs": "all", "depth": "overview"},
                {"type": "command", "refs": "all", "depth": "table"},
                {"type": "role", "refs": "all", "depth": "table"},
            ],
        },
        {
            "id": "doc-root-agents", "path": "AGENTS.md",
            "purpose": "Agent orchestration guide for this repository",
            "covers": [
                {"type": "role", "refs": "all", "depth": "orchestration"},
                {"type": "constraint", "refs": "C-dep-direction,C-agent-commit",
                 "depth": "full"},
            ],
        },
    ]

    docs_el.append(ET.Comment(" Root-level docs (project-specific, not protocol-reusable) "))

    all_docs = _documents + _root_docs
    for doc in all_docs:
        doc_el = ET.SubElement(docs_el, "document",
                               id=doc["id"],
                               path=doc["path"],
                               purpose=doc["purpose"])
        covers_el = ET.SubElement(doc_el, "covers")
        for cover in doc["covers"]:
            attrs: dict[str, str] = {
                "type": cover["type"],
                "depth": cover["depth"],
            }
            if "refs" in cover:
                attrs["refs"] = cover["refs"]
            if "note" in cover:
                attrs["note"] = cover["note"]
            ET.SubElement(covers_el, "entity", **attrs)


def _build_dependency_model(root: ET.Element) -> None:
    """Append <dependency-model> section to root (static)."""
    dm_el = ET.SubElement(root, "dependency-model")

    rule_el = ET.SubElement(dm_el, "rule")
    rule_el.text = (
        "\n    Parent (stays open) is blocked-by child (must finish first).\n"
        "    Work flows bottom-up; closure flows top-down.\n  "
    )
    chain_el = ET.SubElement(dm_el, "canonical-chain")
    chain_el.text = (
        "\n    REQUEST → blocked-by ELICIT → blocked-by PROPOSAL\n"
        "      → blocked-by IMPL_PLAN → blocked-by SLICE-N → blocked-by leaf tasks\n  "
    )
    cmd_el = ET.SubElement(dm_el, "command")
    cmd_el.text = "bd dep add {parent-id} --blocked-by {child-id}"
    anti_el = ET.SubElement(dm_el, "anti-pattern")
    anti_el.text = "bd dep add {child-id} --blocked-by {parent-id}"
    ref_el = ET.SubElement(
        dm_el, "reference-links",
        note="URD and other reference docs use frontmatter, not blocking deps"
    )
    pattern_el = ET.SubElement(ref_el, "pattern")
    pattern_el.text = (
        "\n      description frontmatter:\n"
        "        references:\n"
        "          urd: {urd-task-id}\n"
        "          request: {request-task-id}\n    "
    )


def _build_followup_lifecycle(root: ET.Element) -> None:
    """Append <followup-lifecycle> section to root (static)."""
    fl_el = ET.SubElement(root, "followup-lifecycle")

    trigger_el = ET.SubElement(fl_el, "trigger")
    trigger_el.text = "Code review completion AND (IMPORTANT OR MINOR findings exist)"
    owner_el = ET.SubElement(fl_el, "owner-role")
    owner_el.text = "supervisor"
    gated_el = ET.SubElement(fl_el, "gated-on-blocker")
    gated_el.text = "false"

    dep_chain = ET.SubElement(
        fl_el, "dependency-chain",
        note="Same protocol phases but with FOLLOWUP_ prefix"
    )
    dep_chain.append(ET.Comment(
        "\n      FOLLOWUP epic (aura:epic-followup)\n"
        "        ├── relates_to: original URD\n"
        "        ├── relates_to: original REVIEW-A/B/C tasks\n"
        "        └── blocked-by: FOLLOWUP_URE\n"
        "              └── blocked-by: FOLLOWUP_URD\n"
        "                    └── blocked-by: FOLLOWUP_PROPOSAL-1\n"
        "                          └── blocked-by: FOLLOWUP_IMPL_PLAN\n"
        "                                ├── blocked-by: FOLLOWUP_SLICE-1\n"
        "                                │     ├── blocked-by: important-leaf-task-...\n"
        "                                │     └── blocked-by: minor-leaf-task-...\n"
        "                                └── blocked-by: FOLLOWUP_SLICE-2\n"
        "                                      └── blocked-by: ...\n    "
    ))

    _followup_steps: list[dict] = [
        {
            "task-title": "FOLLOWUP: {description}", "phase-ref": "p10",
            "description": (
                "Epic created by supervisor. References original URD and review tasks."
            ),
        },
        {
            "task-title": "FOLLOWUP_URE: {description}", "phase-ref": "p2",
            "description": "Scoping URE with user to determine which findings to address.",
        },
        {
            "task-title": "FOLLOWUP_URD: {description}", "phase-ref": "p2",
            "description": "Requirements doc for follow-up scope. References original URD.",
        },
        {
            "task-title": "FOLLOWUP_PROPOSAL-{N}: {description}", "phase-ref": "p3",
            "description": (
                "Proposal accounting for original URD + FOLLOWUP_URD + outstanding findings."
            ),
        },
        {
            "task-title": "FOLLOWUP_IMPL_PLAN: {description}", "phase-ref": "p8",
            "description": "Supervisor decomposes follow-up into slices.",
        },
        {
            "task-title": "FOLLOWUP_SLICE-{N}: {description}", "phase-ref": "p9",
            "description": (
                "Each slice adopts original IMPORTANT/MINOR leaf tasks as children."
            ),
        },
    ]

    for step in _followup_steps:
        ET.SubElement(dep_chain, "step",
                      **{"task-title": step["task-title"],
                         "phase-ref": step["phase-ref"],
                         "description": step["description"]})

    lta_el = ET.SubElement(fl_el, "leaf-task-adoption")
    lta_rule = ET.SubElement(lta_el, "rule")
    lta_rule.text = (
        "\n      When supervisor creates FOLLOWUP_SLICE-N, the IMPORTANT/MINOR leaf tasks\n"
        "      from the original review gain a second parent: the follow-up slice.\n"
        "      This is the same dual-parent pattern as BLOCKER findings.\n    "
    )
    lta_cmd = ET.SubElement(lta_el, "command")
    lta_cmd.text = (
        "\n      bd dep add {followup-slice-id} --blocked-by {important-leaf-task-id}\n"
        "      bd dep add {followup-slice-id} --blocked-by {minor-leaf-task-id}\n    "
    )
    lta_note = ET.SubElement(lta_el, "note")
    lta_note.text = (
        "\n      Leaf tasks retain their original parent (the severity group from the "
        "original review)\n"
        "      AND gain the follow-up slice as a second parent. Both must close for the "
        "leaf to be\n"
        "      fully resolved.\n    "
    )

    refs_el = ET.SubElement(fl_el, "references")
    ET.SubElement(refs_el, "ref",
                  type="relates_to",
                  target="original URD",
                  note="Follow-up epic references original URD via frontmatter")
    ET.SubElement(refs_el, "ref",
                  type="relates_to",
                  target="original REVIEW tasks",
                  note="Follow-up epic references review tasks via frontmatter")

    handoff_chain_el = ET.SubElement(
        fl_el, "handoff-chain",
        note="How handoffs flow through the follow-up lifecycle"
    )
    handoff_chain_el.append(ET.Comment(
        "\n      The follow-up lifecycle uses 6 handoff transitions (h1-h6), where h6 is "
        "unique to the follow-up lifecycle\n"
        "      but scoped to the follow-up epic. The storage path changes to use the\n"
        "      follow-up epic ID instead of the original request ID.\n\n"
        "      Storage: .git/.aura/handoff/{followup-epic-id}/{source}-to-{target}.md\n    "
    ))

    _handoff_chain_steps: list[dict] = [
        {
            "order": "1", "handoff-ref": "h5",
            "description": (
                "Reviewer → Followup: Bridge from original review to follow-up epic. "
                "Created by supervisor when IMPORTANT/MINOR findings exist. "
                "This handoff STARTS the follow-up lifecycle."
            ),
        },
        {
            "order": "2", "handoff-ref": "none", "same-actor": "true",
            "description": (
                "Supervisor creates FOLLOWUP_URE (same actor — supervisor owns "
                "follow-up epic and initiates scoping)"
            ),
        },
        {
            "order": "3", "handoff-ref": "none", "same-actor": "true",
            "description": (
                "Supervisor creates FOLLOWUP_URD (same actor within Phase 2 — "
                "supervisor synthesizes follow-up requirements)"
            ),
        },
        {
            "order": "4", "handoff-ref": "h6",
            "description": (
                "Supervisor → Architect: Hands off completed FOLLOWUP_URE + "
                "FOLLOWUP_URD to architect for FOLLOWUP_PROPOSAL creation. "
                "Architect receives scoped findings and requirements."
            ),
        },
        {
            "order": "5", "handoff-ref": "h1",
            "description": (
                "Architect → Supervisor: After FOLLOWUP_PROPOSAL is ratified, "
                "architect hands off to supervisor for FOLLOWUP_IMPL_PLAN. "
                "Handoff doc references original URD, FOLLOWUP_URD, and outstanding findings."
            ),
        },
        {
            "order": "6", "handoff-ref": "h2",
            "description": (
                "Supervisor → Worker: FOLLOWUP_SLICE-N assignment. Worker receives "
                "both the follow-up slice spec AND the original leaf task IDs they must resolve."
            ),
        },
        {
            "order": "7", "handoff-ref": "h3",
            "description": (
                "Supervisor → Reviewer: Code review of follow-up slices. Reviewer "
                "receives follow-up context + original findings being addressed."
            ),
        },
        {
            "order": "8", "handoff-ref": "h4",
            "description": (
                "Worker → Reviewer: Worker completes follow-up slice. Handoff includes "
                "which original leaf tasks were resolved."
            ),
        },
    ]

    for step in _handoff_chain_steps:
        attrs: dict[str, str] = {
            "order": step["order"],
            "handoff-ref": step["handoff-ref"],
            "description": step["description"],
        }
        if "same-actor" in step:
            attrs["same-actor"] = step["same-actor"]
        ET.SubElement(handoff_chain_el, "transition", **attrs)


def _build_procedure_steps(root: ET.Element) -> None:
    """Append <procedure-steps> section to root, derived from PROCEDURE_STEPS.

    Emits one <role ref="..."> per role that has non-empty steps. Each step
    becomes a <step> element with 'order' and 'id' as XML attributes, and
    instruction/command/context/next-state as child elements (only emitted
    when non-None).

    All attribute and text values are XML-escaped by ElementTree automatically.
    """
    # Role ordering for deterministic output
    role_order = [RoleId.EPOCH, RoleId.ARCHITECT, RoleId.REVIEWER,
                  RoleId.SUPERVISOR, RoleId.WORKER]

    proc_el = ET.SubElement(root, "procedure-steps")

    for role_id in role_order:
        steps = PROCEDURE_STEPS.get(role_id, ())
        if not steps:
            continue

        role_el = ET.SubElement(proc_el, "role", ref=role_id.value)
        for step in steps:
            step_el = ET.SubElement(role_el, "step",
                                    order=str(step.order),
                                    id=step.id)
            instr_el = ET.SubElement(step_el, "instruction")
            instr_el.text = step.instruction
            if step.command is not None:
                cmd_el = ET.SubElement(step_el, "command")
                cmd_el.text = step.command
            if step.context is not None:
                ctx_el = ET.SubElement(step_el, "context")
                ctx_el.text = step.context
            if step.next_state is not None:
                ns_el = ET.SubElement(step_el, "next-state")
                ns_el.text = step.next_state.value


# ─── Section comment helper ────────────────────────────────────────────────────


def _section_comment(title: str) -> ET.Element:
    """Return a comment element with section divider formatting."""
    bar = "═" * 71
    return ET.Comment(
        f" {bar}\n"
        f"     {title}\n"
        f"     {bar} "
    )


# ─── XML Serialization ────────────────────────────────────────────────────────


def _serialize_tree(root: ET.Element) -> str:
    """Serialize an ElementTree to a well-formatted XML string.

    Uses ET.indent (Python 3.9+) for indentation.
    """
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    buf = io.BytesIO()
    tree.write(buf, encoding="UTF-8", xml_declaration=True)
    content = buf.getvalue().decode("UTF-8")
    # Normalize declaration encoding to uppercase (ET writes uppercase already)
    return content + "\n"


# ─── Public API ───────────────────────────────────────────────────────────────


def generate_schema(output: Path, diff: bool = True) -> str:
    """Generate schema.xml from Python type definitions.

    Reads all canonical dicts from aura_protocol.types and produces a
    schema.xml that structurally matches skills/protocol/schema.xml and
    passes validate_schema.py with 0 errors.

    Adds role-ref and phase-ref attributes to <constraint> elements (UAT-3).
    Shows unified diff of changes before writing when diff=True (UAT-2).

    Args:
        output: Path to write the generated schema.xml. The parent directory
            must exist.
        diff: If True and the output file already exists, print a unified diff
            of old vs. new content to stdout before writing. Default: True.

    Returns:
        The generated XML content as a string.

    Raises:
        OSError: If the output path's parent directory does not exist or is
            not writable. The error message includes the output path and the
            OS error details.

    Side effects:
        When diff=True and the output already exists with identical content,
        prints "No changes --- schema.xml is up to date." to stdout (no write).
    """
    # Build the XML tree
    root = ET.Element("aura-protocol", version="2.0")

    # Header comment
    root.append(ET.Comment(
        "\n  Aura Protocol Schema v2.0\n\n"
        "  Canonical, machine-readable definition of the Aura multi-agent protocol.\n"
        "  All markdown documentation (PROCESS.md, AGENTS.md, SKILLS.md, etc.) is\n"
        "  derived from this schema. Changes to the protocol MUST be reflected here first.\n\n"
        "  Design: Boyce-Codd Normal Form (BCNF)\n"
        "  - Each fact stored exactly once\n"
        "  - Relationships via idref attributes, no duplication\n"
        "  - No transitive dependencies\n"
        "  - Enums define closed sets; entities reference enums by id\n"
    ))

    # Sections with divider comments
    root.append(_section_comment("ENUMERATIONS"))
    _build_enums(root)

    root.append(_section_comment(
        "LABELS (closed set)\n\n"
        "     Label schema: aura:p{phase}-{domain}:s{step}-{type}\n"
        "     Special labels do not follow the phase pattern."
    ))
    _build_labels(root)

    root.append(_section_comment("REVIEW AXES"))
    _build_review_axes(root)

    root.append(_section_comment(
        "PHASES (12-phase lifecycle)\n\n"
        "     Order of operations is defined by:\n"
        "       1. phase/@number (global ordering)\n"
        "       2. substep/@order within a phase\n"
        "       3. substep/@execution + @parallel-group (concurrency)\n"
        "       4. transition/@condition (gate to next phase)"
    ))
    _build_phases(root)

    root.append(_section_comment(
        "ROLES\n\n"
        "     Each role owns a set of phases and has access to specific commands.\n"
        "     The role-phase mapping is the primary relationship; commands are\n"
        "     grouped under their owning role."
    ))
    _build_roles(root)

    root.append(_section_comment(
        "COMMANDS (skills)\n\n"
        "     Each skill maps to a SKILL.md file in skills/, belongs to a role,\n"
        "     operates in specific phases, and may create specific labels on tasks."
    ))
    _build_commands(root)

    root.append(_section_comment(
        "HANDOFFS (actor-change transitions)\n\n"
        "     6 transitions require handoff documents.\n"
        "     Same-actor transitions (p5→p6, p6→p7) do NOT require handoffs."
    ))
    _build_handoffs(root)

    root.append(_section_comment(
        "CONSTRAINTS (Given/When/Then/Should)\n\n"
        "     Protocol-level constraints. Coding-standard constraints live in\n"
        "     CONSTRAINTS.md and are not duplicated here."
    ))
    _build_constraints(root)

    root.append(_section_comment(
        "TASK TITLE CONVENTIONS\n\n"
        "     Mapping from task titles to labels and creating roles."
    ))
    _build_task_titles(root)

    root.append(_section_comment(
        "DOCUMENTS\n\n"
        "     Mapping from protocol documentation files to the entities they cover."
    ))
    _build_documents(root)

    root.append(_section_comment(
        "DEPENDENCY DIRECTION (Beads)\n\n"
        "     Canonical definition of how work flows through the dependency tree."
    ))
    _build_dependency_model(root)

    root.append(_section_comment(
        "FOLLOW-UP LIFECYCLE (R6 from URD)\n\n"
        "     When code review produces IMPORTANT or MINOR findings, the supervisor\n"
        "     creates a follow-up epic that runs the same protocol phases with\n"
        "     FOLLOWUP_* prefixed task types. The IMPORTANT/MINOR leaf tasks from\n"
        "     the original review gain a second parent: the follow-up slice they\n"
        "     are assigned to (dual-parent).\n\n"
        "     Kind: Separate enum values (FOLLOWUP_URE, FOLLOWUP_SLICE, etc.).\n"
        "     Simple single-parent epic relationship — no followup-of-followup."
    ))
    _build_followup_lifecycle(root)

    root.append(_section_comment(
        "PROCEDURE STEPS\n\n"
        "     Per-role ordered steps (startup sequence for supervisor,\n"
        "     TDD layers for worker). Only roles with non-empty steps are listed."
    ))
    _build_procedure_steps(root)

    # Serialize
    content = _serialize_tree(root)

    # Diff output (UAT-2)
    if diff and output.exists():
        old_content = output.read_text(encoding="UTF-8")
        old_lines = old_content.splitlines(keepends=True)
        new_lines = content.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{output.name}",
            tofile=f"b/{output.name}",
            lineterm="",
        ))
        if diff_lines:
            print(f"\n--- Unified diff for {output} ---")
            for line in diff_lines:
                print(line)
            print(f"--- End diff ({len(diff_lines)} lines) ---\n")
        else:
            print(f"No changes — {output.name} is up to date.")

    # Write if changed or new
    if not output.exists() or output.read_text(encoding="UTF-8") != content:
        output.write_text(content, encoding="UTF-8")

    return content


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point. Generates schema.xml and validates it.

    Usage: python -m aura_protocol.gen_schema [output-path]

    Default output: skills/protocol/schema.xml (relative to script's parent dir).
    Returns: 0 on success, 1 on error.
    """
    import sys

    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
    else:
        script_dir = Path(__file__).resolve().parent
        output = script_dir.parent.parent / "skills" / "protocol" / "schema.xml"

    try:
        old_content = output.read_text(encoding="UTF-8") if output.exists() else None
        content = generate_schema(output, diff=True)
        if old_content != content:
            print(f"Generated {output} ({len(content)} bytes)")
        return 0
    except OSError as e:
        print(f"Error writing {output}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
