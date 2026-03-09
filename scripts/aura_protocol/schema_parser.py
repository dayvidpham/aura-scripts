"""Schema parser for skills/protocol/schema.xml.

Parses the canonical Aura protocol schema into typed Python specs.

Public API:
    SchemaSpec       — root container with all parsed entities
    SchemaParseError — raised when schema.xml is malformed or missing required entities
    parse_schema(path) → SchemaSpec

Design notes:
- Reuses traversal patterns from scripts/validate_schema.py (build_index, check_refs).
- Raises SchemaParseError on any structural problem (missing file, bad XML, missing entities).
- Never silently skips entities — raises on unexpected missing required attributes.
- Returns a complete, immutable SchemaSpec; no partial results.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from aura_protocol.types import (
    BehaviorSpec,
    Checklist,
    ChecklistItem,
    CodeExample,
    CommandId,
    CommandSpec,
    ConstraintSpec,
    ContentLevel,
    CoordinationCommand,
    ExecutionMode,
    ExitCondition,
    ExitConditionType,
    ExampleLabel,
    ExampleLang,
    Figure,
    FigureId,
    FigureType,
    GateType,
    HandoffSpec,
    LabelSpec,
    PhaseId,
    ProcedureStep,
    ReviewAxis,
    ReviewAxisSpec,
    RoleId,
    RoleSpec,
    SectionRef,
    SubstepSpec,
    SubstepType,
    TitleConvention,
    Workflow,
    WorkflowAction,
    WorkflowExecution,
    WorkflowStage,
)


# ─── Exception ────────────────────────────────────────────────────────────────


class SchemaParseError(Exception):
    """Raised when schema.xml is malformed or missing required entities.

    Actionable: the message describes (1) what went wrong, (2) why it happened,
    (3) where it failed, (4) what it means, and (5) how to fix it.
    """


# ─── Root Container ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SchemaSpec:
    """Complete parsed schema: all entities from schema.xml in typed form.

    Entity counts verified by integration tests (test_schema_parser.py):
    - 12 phases
    - 5 roles
    - 35 commands
    - 23 constraints (dict[str, ConstraintSpec])
    - 6 handoffs
    - 21 labels
    - 3 review axes
    - title_conventions: list[TitleConvention] (16 entries in schema.xml v2.0)
    - role_specs: dict[RoleId, RoleSpec]
    - substep_specs: dict[str, SubstepSpec] — keyed by substep id
    - procedure_steps: dict[RoleId, tuple[ProcedureStep, ...]] — from startup-sequence
    """

    phases: tuple[str, ...]               # Ordered phase IDs (p1..p12)
    roles: dict[RoleId, RoleSpec]
    commands: dict[str, CommandSpec]
    constraints: dict[str, ConstraintSpec]
    handoffs: dict[str, HandoffSpec]
    labels: dict[str, LabelSpec]
    review_axes: dict[str, ReviewAxisSpec]
    title_conventions: list[TitleConvention]
    substep_specs: dict[str, SubstepSpec]  # keyed by substep id
    procedure_steps: dict[RoleId, tuple[ProcedureStep, ...]]  # from startup-sequence
    checklists: dict[str, Checklist]
    coordination_commands: dict[str, CoordinationCommand]
    workflows: dict[str, Workflow]
    figures: dict[FigureId, Figure]


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _require(
    value: str | None,
    attr: str,
    context: str,
    path: Path,
) -> str:
    """Return value or raise SchemaParseError with actionable message."""
    if value is None or value.strip() == "":
        raise SchemaParseError(
            f"Missing required attribute '{attr}' on {context} "
            f"in {path}. "
            f"This attribute is required by the schema parser. "
            f"Fix: add the missing attribute to the schema.xml element."
        )
    return value


def _parse_phases(root: ET.Element, path: Path) -> tuple[str, ...]:
    """Extract ordered phase IDs from <phases> section."""
    phases_el = root.find("phases")
    if phases_el is None:
        raise SchemaParseError(
            f"Missing <phases> section in {path}. "
            f"schema.xml must have a top-level <phases> element. "
            f"Fix: add <phases>...</phases> to schema.xml."
        )
    result: list[tuple[int, str]] = []
    for phase in phases_el.findall("phase"):
        pid = _require(phase.get("id"), "id", f"<phase>", path)
        num_str = _require(phase.get("number"), "number", f"<phase id='{pid}'>", path)
        try:
            num = int(num_str)
        except ValueError:
            raise SchemaParseError(
                f"Invalid phase number '{num_str}' on <phase id='{pid}'> in {path}. "
                f"Phase number must be an integer. "
                f"Fix: correct the 'number' attribute value."
            )
        result.append((num, pid))
    result.sort(key=lambda x: x[0])
    return tuple(pid for _, pid in result)


def _parse_substeps(root: ET.Element, path: Path) -> dict[str, SubstepSpec]:
    """Extract all substep specs from all phases."""
    result: dict[str, SubstepSpec] = {}
    phases_el = root.find("phases")
    if phases_el is None:
        return result
    for phase in phases_el.findall("phase"):
        substeps_el = phase.find("substeps")
        if substeps_el is None:
            continue
        for substep in substeps_el.findall("substep"):
            sid = _require(substep.get("id"), "id", "<substep>", path)
            stype_str = _require(substep.get("type"), "type", f"<substep id='{sid}'>", path)
            try:
                stype = SubstepType(stype_str)
            except ValueError:
                raise SchemaParseError(
                    f"Unknown substep type '{stype_str}' on <substep id='{sid}'> in {path}. "
                    f"Valid values: {[t.value for t in SubstepType]}. "
                    f"Fix: correct the 'type' attribute."
                )
            execution_str = _require(
                substep.get("execution"), "execution", f"<substep id='{sid}'>", path
            )
            try:
                execution = ExecutionMode(execution_str)
            except ValueError:
                raise SchemaParseError(
                    f"Unknown execution mode '{execution_str}' on <substep id='{sid}'> in {path}. "
                    f"Valid values: {[m.value for m in ExecutionMode]}. "
                    f"Fix: correct the 'execution' attribute."
                )
            order_str = _require(substep.get("order"), "order", f"<substep id='{sid}'>", path)
            try:
                order = int(order_str)
            except ValueError:
                raise SchemaParseError(
                    f"Invalid substep order '{order_str}' on <substep id='{sid}'> in {path}. "
                    f"Order must be an integer. "
                    f"Fix: correct the 'order' attribute value."
                )
            label_ref = _require(
                substep.get("label-ref"), "label-ref", f"<substep id='{sid}'>", path
            )
            desc_el = substep.find("description")
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else None
            result[sid] = SubstepSpec(
                id=sid,
                type=stype,
                execution=execution,
                order=order,
                label_ref=label_ref,
                parallel_group=substep.get("parallel-group"),
                description=desc,
            )
    return result


def _parse_procedure_steps(
    root: ET.Element, path: Path
) -> dict[RoleId, tuple[ProcedureStep, ...]]:
    """Extract startup-sequence steps from substeps in Phase 8 (supervisor role).

    Phase 8's substep s8 has a <startup-sequence> that defines supervisor steps.
    Each <step> has 'order' and 'id' as XML attributes; instruction/command/context/
    next-state are child elements (only present when non-None).
    Worker role steps derive from TDD layer descriptions in Phase 9 (<tdd-layers>).
    Other roles get empty tuples.
    """
    steps: dict[RoleId, tuple[ProcedureStep, ...]] = {role: () for role in RoleId}

    phases_el = root.find("phases")
    if phases_el is None:
        return steps

    # Supervisor: startup-sequence in phase p8 substep s8
    for phase in phases_el.findall("phase"):
        if phase.get("id") != "p8":
            continue
        substeps_el = phase.find("substeps")
        if substeps_el is None:
            break
        for substep in substeps_el.findall("substep"):
            startup_seq = substep.find("startup-sequence")
            if startup_seq is None:
                continue
            sup_steps: list[ProcedureStep] = []
            for step_el in startup_seq.findall("step"):
                order_str = _require(
                    step_el.get("order"), "order", "<startup-sequence/step>", path
                )
                try:
                    order = int(order_str)
                except ValueError:
                    raise SchemaParseError(
                        f"Invalid startup step order '{order_str}' in {path}. "
                        f"Order must be an integer. "
                        f"Fix: correct the 'order' attribute."
                    )
                step_id = _require(
                    step_el.get("id"), "id", "<startup-sequence/step>", path
                )
                # instruction child element (required)
                instr_el = step_el.find("instruction")
                if instr_el is None or not instr_el.text:
                    raise SchemaParseError(
                        f"Missing required <instruction> child element on <step id='{step_id}'> "
                        f"in startup-sequence in {path}. "
                        f"Instruction is required for all procedure steps. "
                        f"Fix: add <instruction>...</instruction> as a child element of the <step>."
                    )
                instruction = instr_el.text.strip()
                # optional child elements
                cmd_el = step_el.find("command")
                command = cmd_el.text.strip() if cmd_el is not None and cmd_el.text else None
                ctx_el = step_el.find("context")
                context = ctx_el.text.strip() if ctx_el is not None and ctx_el.text else None
                # next-state is optional — attribute may be absent; None if not present
                ns_val = step_el.get("next-state")
                next_state: PhaseId | None = None
                if ns_val:
                    try:
                        next_state = PhaseId(ns_val)
                    except ValueError:
                        raise SchemaParseError(
                            f"Unknown next-state '{ns_val}' in startup step "
                            f"order='{order}' in {path}. "
                            f"Valid phases: {[p.value for p in PhaseId]}. "
                            f"Fix: correct the 'next-state' attribute on <step>."
                        )
                sup_steps.append(ProcedureStep(
                    id=step_id,
                    order=order,
                    instruction=instruction,
                    command=command,
                    context=context,
                    next_state=next_state,
                ))
            sup_steps.sort(key=lambda s: s.order)
            steps[RoleId.Supervisor] = tuple(sup_steps)
        break

    # Worker: TDD layer descriptions from phase p9 <tdd-layers>
    # Worker steps use a simplified format (description attribute, no id in XML).
    # We synthesize ids from the layer number.
    for phase in phases_el.findall("phase"):
        if phase.get("id") != "p9":
            continue
        tdd_layers = phase.find("tdd-layers")
        if tdd_layers is None:
            break
        worker_steps: list[ProcedureStep] = []
        _worker_ids = ["S-worker-types", "S-worker-tests", "S-worker-impl"]
        for layer in tdd_layers.findall("layer"):
            num_str = layer.get("number", "")
            desc = layer.get("description", "")
            try:
                num = int(num_str)
            except ValueError:
                continue
            step_id = _worker_ids[num - 1] if 1 <= num <= len(_worker_ids) else f"S-worker-step{num}"
            worker_steps.append(ProcedureStep(id=step_id, order=num, instruction=desc))
        worker_steps.sort(key=lambda s: s.order)
        steps[RoleId.Worker] = tuple(worker_steps)
        break

    return steps


def _parse_roles(root: ET.Element, path: Path) -> dict[RoleId, RoleSpec]:
    """Extract all role specs from <roles> section."""
    roles_el = root.find("roles")
    if roles_el is None:
        raise SchemaParseError(
            f"Missing <roles> section in {path}. "
            f"schema.xml must have a top-level <roles> element. "
            f"Fix: add <roles>...</roles> to schema.xml."
        )
    result: dict[RoleId, RoleSpec] = {}
    for role in roles_el.findall("role"):
        rid_str = _require(role.get("id"), "id", "<role>", path)
        try:
            rid = RoleId(rid_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown role id '{rid_str}' in {path}. "
                f"Valid role ids: {[r.value for r in RoleId]}. "
                f"Fix: correct the 'id' attribute or add the role to RoleId enum."
            )
        name = _require(role.get("name"), "name", f"<role id='{rid_str}'>", path)
        description = role.get("description") or ""
        owned_phases: set[PhaseId] = set()
        owns_phases_el = role.find("owns-phases")
        if owns_phases_el is not None:
            for pr in owns_phases_el.findall("phase-ref"):
                ref = pr.get("ref")
                if ref:
                    try:
                        owned_phases.add(PhaseId(ref))
                    except ValueError:
                        raise SchemaParseError(
                            f"Unknown phase ref '{ref}' in owns-phases for role "
                            f"'{rid_str}' in {path}. "
                            f"Valid phase ids: {[p.value for p in PhaseId]}. "
                            f"Fix: correct the 'ref' attribute or add the phase to PhaseId enum."
                        )
        intro_el = role.find("introduction")
        introduction = intro_el.text.strip() if intro_el is not None and intro_el.text else None
        on_el = role.find("ownership-narrative")
        ownership_narrative = (
            on_el.text.strip() if on_el is not None and on_el.text else None
        )
        behaviors = _parse_behaviors(role, path)

        # Parse <tools>, <model>, <thinking> elements (optional)
        tools_el = role.find("tools")
        tools: tuple[str, ...] = ()
        if tools_el is not None and tools_el.text:
            tools = tuple(t.strip() for t in tools_el.text.split(",") if t.strip())
        model_el = role.find("model")
        model: str | None = model_el.text.strip() if model_el is not None and model_el.text else None
        thinking_el = role.find("thinking")
        thinking: str | None = (
            thinking_el.text.strip() if thinking_el is not None and thinking_el.text else None
        )

        result[rid] = RoleSpec(
            id=rid,
            name=name,
            description=description,
            owned_phases=frozenset(owned_phases),
            introduction=introduction,
            ownership_narrative=ownership_narrative,
            behaviors=behaviors,
            tools=tools,
            model=model,
            thinking=thinking,
        )
    return result


def _parse_commands(root: ET.Element, path: Path) -> dict[str, CommandSpec]:
    """Extract all command specs from <commands> section."""
    commands_el = root.find("commands")
    if commands_el is None:
        raise SchemaParseError(
            f"Missing <commands> section in {path}. "
            f"schema.xml must have a top-level <commands> element. "
            f"Fix: add <commands>...</commands> to schema.xml."
        )
    result: dict[str, CommandSpec] = {}
    for cmd in commands_el.findall("command"):
        cid = _require(cmd.get("id"), "id", "<command>", path)
        name = _require(cmd.get("name"), "name", f"<command id='{cid}'>", path)
        description = cmd.get("description") or ""

        # role-ref (optional for some commands)
        role_ref: RoleId | None = None
        role_ref_str = cmd.get("role-ref")
        if role_ref_str:
            try:
                role_ref = RoleId(role_ref_str)
            except ValueError:
                raise SchemaParseError(
                    f"Unknown role-ref '{role_ref_str}' on <command id='{cid}'> in {path}. "
                    f"Valid role ids: {[r.value for r in RoleId]}. "
                    f"Fix: correct the 'role-ref' attribute."
                )

        # phases
        phases: list[str] = []
        phases_el = cmd.find("phases")
        if phases_el is not None:
            for pr in phases_el.findall("phase-ref"):
                ref = pr.get("ref")
                if ref:
                    phases.append(ref)

        # file
        file_el = cmd.find("file")
        file_path_str = file_el.text.strip() if file_el is not None and file_el.text else ""

        # creates-labels
        creates_labels: list[str] = []
        creates_labels_el = cmd.find("creates-labels")
        if creates_labels_el is not None:
            for lr in creates_labels_el.findall("label-ref"):
                ref = lr.get("ref")
                if ref:
                    creates_labels.append(ref)

        result[cid] = CommandSpec(
            id=cid,
            name=name,
            description=description,
            role_ref=role_ref,
            phases=tuple(phases),
            file=file_path_str,
            creates_labels=tuple(creates_labels),
        )
    return result


def _parse_constraints(
    root: ET.Element, path: Path
) -> dict[str, ConstraintSpec]:
    """Extract all constraints from <constraints> section.

    Returns dict[id, ConstraintSpec].
    """
    constraints_el = root.find("constraints")
    if constraints_el is None:
        raise SchemaParseError(
            f"Missing <constraints> section in {path}. "
            f"schema.xml must have a top-level <constraints> element. "
            f"Fix: add <constraints>...</constraints> to schema.xml."
        )
    result: dict[str, ConstraintSpec] = {}
    for c in constraints_el.findall("constraint"):
        cid = _require(c.get("id"), "id", "<constraint>", path)
        given = _require(c.get("given"), "given", f"<constraint id='{cid}'>", path)
        when = _require(c.get("when"), "when", f"<constraint id='{cid}'>", path)
        then = _require(c.get("then"), "then", f"<constraint id='{cid}'>", path)
        should_not = _require(
            c.get("should-not"), "should-not", f"<constraint id='{cid}'>", path
        )
        command = c.get("command")
        examples = _parse_examples(c, path)
        result[cid] = ConstraintSpec(
            id=cid, given=given, when=when, then=then, should_not=should_not,
            command=command, examples=examples,
        )
    return result


def _parse_handoffs(root: ET.Element, path: Path) -> dict[str, HandoffSpec]:
    """Extract all handoff specs from <handoffs> section."""
    handoffs_el = root.find("handoffs")
    if handoffs_el is None:
        raise SchemaParseError(
            f"Missing <handoffs> section in {path}. "
            f"schema.xml must have a top-level <handoffs> element. "
            f"Fix: add <handoffs>...</handoffs> to schema.xml."
        )
    result: dict[str, HandoffSpec] = {}
    for h in handoffs_el.findall("handoff"):
        hid = _require(h.get("id"), "id", "<handoff>", path)
        source_role_str = _require(
            h.get("source-role"), "source-role", f"<handoff id='{hid}'>", path
        )
        target_role_str = _require(
            h.get("target-role"), "target-role", f"<handoff id='{hid}'>", path
        )
        at_phase_str = _require(
            h.get("at-phase"), "at-phase", f"<handoff id='{hid}'>", path
        )
        content_level_str = _require(
            h.get("content-level"), "content-level", f"<handoff id='{hid}'>", path
        )

        try:
            source_role = RoleId(source_role_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown source-role '{source_role_str}' on <handoff id='{hid}'> in {path}. "
                f"Valid roles: {[r.value for r in RoleId]}. "
                f"Fix: correct the 'source-role' attribute."
            )
        try:
            target_role = RoleId(target_role_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown target-role '{target_role_str}' on <handoff id='{hid}'> in {path}. "
                f"Valid roles: {[r.value for r in RoleId]}. "
                f"Fix: correct the 'target-role' attribute."
            )
        try:
            at_phase = PhaseId(at_phase_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown at-phase '{at_phase_str}' on <handoff id='{hid}'> in {path}. "
                f"Valid phases: {[p.value for p in PhaseId]}. "
                f"Fix: correct the 'at-phase' attribute."
            )
        try:
            content_level = ContentLevel(content_level_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown content-level '{content_level_str}' on <handoff id='{hid}'> in {path}. "
                f"Valid levels: {[c.value for c in ContentLevel]}. "
                f"Fix: correct the 'content-level' attribute."
            )

        # required-fields (comma-separated text in child element)
        required_fields: list[str] = []
        rf_el = h.find("required-fields")
        if rf_el is not None and rf_el.text:
            for field in rf_el.text.split(","):
                field = field.strip()
                if field:
                    required_fields.append(field)

        result[hid] = HandoffSpec(
            id=hid,
            source_role=source_role,
            target_role=target_role,
            at_phase=at_phase,
            content_level=content_level,
            required_fields=tuple(required_fields),
        )
    return result


def _parse_labels(root: ET.Element, path: Path) -> dict[str, LabelSpec]:
    """Extract all label specs from <labels> section."""
    labels_el = root.find("labels")
    if labels_el is None:
        raise SchemaParseError(
            f"Missing <labels> section in {path}. "
            f"schema.xml must have a top-level <labels> element. "
            f"Fix: add <labels>...</labels> to schema.xml."
        )
    result: dict[str, LabelSpec] = {}
    for label in labels_el.findall("label"):
        lid = _require(label.get("id"), "id", "<label>", path)
        value = _require(label.get("value"), "value", f"<label id='{lid}'>", path)
        special = label.get("special") == "true"
        result[lid] = LabelSpec(
            id=lid,
            value=value,
            special=special,
            phase_ref=label.get("phase-ref"),
            substep_ref=label.get("substep-ref"),
            severity_ref=label.get("severity-ref"),
            description=label.get("description"),
        )
    return result


def _parse_review_axes(root: ET.Element, path: Path) -> dict[str, ReviewAxisSpec]:
    """Extract all review axis specs from <review-axes> section."""
    axes_el = root.find("review-axes")
    if axes_el is None:
        raise SchemaParseError(
            f"Missing <review-axes> section in {path}. "
            f"schema.xml must have a top-level <review-axes> element. "
            f"Fix: add <review-axes>...</review-axes> to schema.xml."
        )
    result: dict[str, ReviewAxisSpec] = {}
    for axis in axes_el.findall("axis"):
        aid = _require(axis.get("id"), "id", "<axis>", path)
        letter_str = _require(axis.get("letter"), "letter", f"<axis id='{aid}'>", path)
        name = _require(axis.get("name"), "name", f"<axis id='{aid}'>", path)
        short = axis.get("short") or ""

        try:
            letter = ReviewAxis(letter_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown review axis letter '{letter_str}' on <axis id='{aid}'> in {path}. "
                f"Valid letters: {[a.value for a in ReviewAxis]}. "
                f"Fix: correct the 'letter' attribute."
            )

        key_questions: list[str] = []
        kq_el = axis.find("key-questions")
        if kq_el is not None:
            for q in kq_el.findall("q"):
                if q.text:
                    key_questions.append(q.text.strip())

        result[aid] = ReviewAxisSpec(
            id=aid,
            letter=letter,
            name=name,
            short=short,
            key_questions=tuple(key_questions),
        )
    return result


def _parse_title_conventions(root: ET.Element, path: Path) -> list[TitleConvention]:
    """Extract all title conventions from <task-titles> section."""
    task_titles_el = root.find("task-titles")
    if task_titles_el is None:
        raise SchemaParseError(
            f"Missing <task-titles> section in {path}. "
            f"schema.xml must have a top-level <task-titles> element. "
            f"Fix: add <task-titles>...</task-titles> to schema.xml."
        )
    result: list[TitleConvention] = []
    for tc in task_titles_el.findall("title-convention"):
        pattern = _require(tc.get("pattern"), "pattern", "<title-convention>", path)
        label_ref = _require(
            tc.get("label-ref"), "label-ref", f"<title-convention pattern='{pattern}'>", path
        )
        created_by = _require(
            tc.get("created-by"), "created-by", f"<title-convention pattern='{pattern}'>", path
        )
        result.append(TitleConvention(
            pattern=pattern,
            label_ref=label_ref,
            created_by=created_by,
            phase_ref=tc.get("phase-ref"),
            extra_label_ref=tc.get("extra-label-ref"),
            note=tc.get("note"),
        ))
    return result


def _parse_examples(parent_elem: ET.Element, path: Path) -> tuple[CodeExample, ...]:
    """Parse <example> child elements of a constraint or step element.

    Returns empty tuple when no <example> children are present.
    """
    examples: list[CodeExample] = []
    for ex_el in parent_elem.findall("example"):
        eid = _require(ex_el.get("id"), "id", "<example>", path)
        lang_str = _require(ex_el.get("lang"), "lang", f"<example id='{eid}'>", path)
        label_str = _require(ex_el.get("label"), "label", f"<example id='{eid}'>", path)
        try:
            lang = ExampleLang(lang_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown example lang '{lang_str}' on <example id='{eid}'> in {path}. "
                f"Valid langs: {[l.value for l in ExampleLang]}. "
                f"Fix: correct the 'lang' attribute."
            )
        try:
            label = ExampleLabel(label_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown example label '{label_str}' on <example id='{eid}'> in {path}. "
                f"Valid labels: {[l.value for l in ExampleLabel]}. "
                f"Fix: correct the 'label' attribute."
            )
        code_el = ex_el.find("code")
        code = code_el.text.strip() if code_el is not None and code_el.text else ""
        examples.append(CodeExample(
            id=eid,
            lang=lang,
            label=label,
            code=code,
            also_illustrates=ex_el.get("also-illustrates"),
        ))
    return tuple(examples)


def _parse_behaviors(role_elem: ET.Element, path: Path) -> tuple[BehaviorSpec, ...]:
    """Parse <behaviors>/<behavior> child elements of a role element.

    Returns empty tuple when no <behaviors> section is present.
    """
    behaviors_el = role_elem.find("behaviors")
    if behaviors_el is None:
        return ()
    behaviors: list[BehaviorSpec] = []
    for b_el in behaviors_el.findall("behavior"):
        bid = _require(b_el.get("id"), "id", "<behavior>", path)
        given = _require(b_el.get("given"), "given", f"<behavior id='{bid}'>", path)
        when = _require(b_el.get("when"), "when", f"<behavior id='{bid}'>", path)
        then = _require(b_el.get("then"), "then", f"<behavior id='{bid}'>", path)
        should_not = _require(
            b_el.get("should-not"), "should-not", f"<behavior id='{bid}'>", path
        )
        behaviors.append(BehaviorSpec(
            id=bid, given=given, when=when, then=then, should_not=should_not,
        ))
    return tuple(behaviors)


def _parse_checklists(root: ET.Element, path: Path) -> dict[str, Checklist]:
    """Extract all checklists from <checklists> section.

    Returns empty dict when <checklists> section is absent (backward-compatible).
    """
    checklists_el = root.find("checklists")
    if checklists_el is None:
        return {}
    result: dict[str, Checklist] = {}
    for cl_el in checklists_el.findall("checklist"):
        cl_id = _require(cl_el.get("id"), "id", "<checklist>", path)
        role_ref_str = _require(
            cl_el.get("role-ref"), "role-ref", f"<checklist id='{cl_id}'>", path
        )
        gate_str = _require(
            cl_el.get("gate"), "gate", f"<checklist id='{cl_id}'>", path
        )
        try:
            role_ref = RoleId(role_ref_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown role-ref '{role_ref_str}' on <checklist id='{cl_id}'> in {path}. "
                f"Valid roles: {[r.value for r in RoleId]}. "
                f"Fix: correct the 'role-ref' attribute."
            )
        try:
            gate = GateType(gate_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown gate '{gate_str}' on <checklist id='{cl_id}'> in {path}. "
                f"Valid gates: {[g.value for g in GateType]}. "
                f"Fix: correct the 'gate' attribute."
            )
        items: list[ChecklistItem] = []
        for item_el in cl_el.findall("item"):
            item_id = _require(
                item_el.get("id"), "id", f"<item> in checklist '{cl_id}'", path
            )
            required_str = item_el.get("required", "true")
            required = required_str.lower() != "false"
            text = item_el.text.strip() if item_el.text else ""
            items.append(ChecklistItem(id=item_id, text=text, required=required))
        result[cl_id] = Checklist(role_ref=role_ref, gate=gate, items=tuple(items))
    return result


def _parse_coordination_commands(
    root: ET.Element, path: Path
) -> dict[str, CoordinationCommand]:
    """Extract all coordination commands from <coordination-commands> section.

    Returns empty dict when <coordination-commands> section is absent.
    """
    coord_el = root.find("coordination-commands")
    if coord_el is None:
        return {}
    result: dict[str, CoordinationCommand] = {}
    for cmd_el in coord_el.findall("coord-cmd"):
        cid = _require(cmd_el.get("id"), "id", "<coord-cmd>", path)
        action = _require(cmd_el.get("action"), "action", f"<coord-cmd id='{cid}'>", path)
        template = _require(
            cmd_el.get("template"), "template", f"<coord-cmd id='{cid}'>", path
        )
        role_ref: RoleId | None = None
        role_ref_str = cmd_el.get("role-ref")
        if role_ref_str:
            try:
                role_ref = RoleId(role_ref_str)
            except ValueError:
                raise SchemaParseError(
                    f"Unknown role-ref '{role_ref_str}' on <coord-cmd id='{cid}'> in {path}. "
                    f"Valid roles: {[r.value for r in RoleId]}. "
                    f"Fix: correct the 'role-ref' attribute."
                )
        shared = cmd_el.get("shared", "false").lower() == "true"
        result[cid] = CoordinationCommand(
            id=cid, action=action, template=template, role_ref=role_ref, shared=shared,
        )
    return result


def _parse_workflows(root: ET.Element, path: Path) -> dict[str, Workflow]:
    """Extract all workflows from <workflows> section.

    Returns empty dict when <workflows> section is absent.
    """
    workflows_el = root.find("workflows")
    if workflows_el is None:
        return {}
    result: dict[str, Workflow] = {}
    for wf_el in workflows_el.findall("workflow"):
        wid = _require(wf_el.get("id"), "id", "<workflow>", path)
        name = _require(wf_el.get("name"), "name", f"<workflow id='{wid}'>", path)
        role_ref_str = _require(
            wf_el.get("role-ref"), "role-ref", f"<workflow id='{wid}'>", path
        )
        description = wf_el.get("description") or ""
        try:
            role_ref = RoleId(role_ref_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown role-ref '{role_ref_str}' on <workflow id='{wid}'> in {path}. "
                f"Valid roles: {[r.value for r in RoleId]}. "
                f"Fix: correct the 'role-ref' attribute."
            )
        stages: list[WorkflowStage] = []
        for stage_el in wf_el.findall("stage"):
            stage_id = _require(stage_el.get("id"), "id", "<stage>", path)
            stage_name = _require(
                stage_el.get("name"), "name", f"<stage id='{stage_id}'>", path
            )
            order_str = _require(
                stage_el.get("order"), "order", f"<stage id='{stage_id}'>", path
            )
            execution_str = _require(
                stage_el.get("execution"), "execution", f"<stage id='{stage_id}'>", path
            )
            try:
                order = int(order_str)
            except ValueError:
                raise SchemaParseError(
                    f"Invalid stage order '{order_str}' on <stage id='{stage_id}'> in {path}. "
                    f"Order must be an integer. "
                    f"Fix: correct the 'order' attribute."
                )
            try:
                execution = WorkflowExecution(execution_str)
            except ValueError:
                raise SchemaParseError(
                    f"Unknown execution '{execution_str}' on <stage id='{stage_id}'> in {path}. "
                    f"Valid values: {[e.value for e in WorkflowExecution]}. "
                    f"Fix: correct the 'execution' attribute."
                )
            phase_ref: PhaseId | None = None
            phase_ref_str = stage_el.get("phase-ref")
            if phase_ref_str:
                try:
                    phase_ref = PhaseId(phase_ref_str)
                except ValueError:
                    raise SchemaParseError(
                        f"Unknown phase-ref '{phase_ref_str}' on <stage id='{stage_id}'> in {path}. "
                        f"Valid phases: {[p.value for p in PhaseId]}. "
                        f"Fix: correct the 'phase-ref' attribute."
                    )
            actions: list[WorkflowAction] = []
            for action_el in stage_el.findall("action"):
                action_id = _require(action_el.get("id"), "id", "<action>", path)
                instruction = _require(
                    action_el.get("instruction"), "instruction",
                    f"<action id='{action_id}'>", path,
                )
                actions.append(WorkflowAction(
                    id=action_id,
                    instruction=instruction,
                    command=action_el.get("command"),
                ))
            exit_conditions: list[ExitCondition] = []
            for ec_el in stage_el.findall("exit-condition"):
                type_str = _require(ec_el.get("type"), "type", "<exit-condition>", path)
                condition = _require(
                    ec_el.get("condition"), "condition", "<exit-condition>", path
                )
                try:
                    ec_type = ExitConditionType(type_str)
                except ValueError:
                    raise SchemaParseError(
                        f"Unknown exit-condition type '{type_str}' in {path}. "
                        f"Valid types: {[t.value for t in ExitConditionType]}. "
                        f"Fix: correct the 'type' attribute."
                    )
                exit_conditions.append(ExitCondition(type=ec_type, condition=condition))
            stages.append(WorkflowStage(
                id=stage_id,
                name=stage_name,
                order=order,
                execution=execution,
                phase_ref=phase_ref,
                actions=tuple(actions),
                exit_conditions=tuple(exit_conditions),
            ))
        result[wid] = Workflow(
            id=wid,
            name=name,
            role_ref=role_ref,
            description=description,
            stages=tuple(stages),
        )
    return result


def _parse_figures(root: ET.Element, path: Path) -> dict[FigureId, Figure]:
    """Extract all figures from <figures> section.

    Returns empty dict when <figures> section is absent.
    """
    figures_el = root.find("figures")
    if figures_el is None:
        return {}
    result: dict[FigureId, Figure] = {}
    for fig_el in figures_el.findall("figure"):
        fid_str = _require(fig_el.get("id"), "id", "<figure>", path)
        title = _require(fig_el.get("title"), "title", f"<figure id='{fid_str}'>", path)
        type_str = _require(fig_el.get("type"), "type", f"<figure id='{fid_str}'>", path)
        section_ref_str = _require(
            fig_el.get("section-ref"), "section-ref", f"<figure id='{fid_str}'>", path
        )
        try:
            fid = FigureId(fid_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown figure id '{fid_str}' in {path}. "
                f"Valid ids: {[f.value for f in FigureId]}. "
                f"Fix: correct the 'id' attribute or add to FigureId enum."
            )
        try:
            fig_type = FigureType(type_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown figure type '{type_str}' on <figure id='{fid_str}'> in {path}. "
                f"Valid types: {[t.value for t in FigureType]}. "
                f"Fix: correct the 'type' attribute."
            )
        try:
            section_ref = SectionRef(section_ref_str)
        except ValueError:
            raise SchemaParseError(
                f"Unknown section-ref '{section_ref_str}' on <figure id='{fid_str}'> in {path}. "
                f"Valid refs: {[s.value for s in SectionRef]}. "
                f"Fix: correct the 'section-ref' attribute."
            )
        role_refs: set[RoleId] = set()
        for rr_el in fig_el.findall("role-ref"):
            rr_str = _require(
                rr_el.get("ref"), "ref", f"<role-ref> in <figure id='{fid_str}'>", path
            )
            try:
                role_refs.add(RoleId(rr_str))
            except ValueError:
                raise SchemaParseError(
                    f"Unknown role-ref '{rr_str}' on <figure id='{fid_str}'> in {path}. "
                    f"Valid roles: {[r.value for r in RoleId]}. "
                    f"Fix: correct the 'ref' attribute."
                )
        workflow_refs: set[str] = set()
        for wr_el in fig_el.findall("workflow-ref"):
            wr_str = _require(
                wr_el.get("ref"), "ref", f"<workflow-ref> in <figure id='{fid_str}'>", path
            )
            workflow_refs.add(wr_str)
        command_refs: set[CommandId] = set()
        for cr_el in fig_el.findall("command-ref"):
            cr_str = _require(
                cr_el.get("ref"), "ref", f"<command-ref> in <figure id='{fid_str}'>", path
            )
            try:
                command_refs.add(CommandId(cr_str))
            except ValueError:
                raise SchemaParseError(
                    f"Unknown command-ref '{cr_str}' on <figure id='{fid_str}'> in {path}. "
                    f"Valid command ids: {[c.value for c in CommandId]}. "
                    f"Fix: correct the 'ref' attribute."
                )
        result[fid] = Figure(
            id=fid,
            title=title,
            type=fig_type,
            role_refs=frozenset(role_refs),
            section_ref=section_ref,
            workflow_refs=frozenset(workflow_refs),
            command_refs=frozenset(command_refs),
        )
    return result


# ─── Public API ───────────────────────────────────────────────────────────────


def parse_schema(path: Path) -> SchemaSpec:
    """Parse skills/protocol/schema.xml into a complete SchemaSpec.

    Args:
        path: Absolute or relative path to schema.xml.

    Returns:
        SchemaSpec with all 12 phases, 5 roles, 35 commands, 23 constraints,
        6 handoffs, 21 labels, 3 review axes, 16 title conventions,
        4 checklists, 10 coordination commands, 3 workflows, and procedure
        steps with substep specs.

    Raises:
        SchemaParseError: If the file does not exist, is not valid XML, or is
            missing required sections or attributes. The error message is
            actionable and describes what went wrong and how to fix it.

    Example::

        from pathlib import Path
        from aura_protocol.schema_parser import parse_schema

        spec = parse_schema(Path("skills/protocol/schema.xml"))
        assert len(spec.phases) == 12
        assert len(spec.roles) == 5
    """
    if not path.exists():
        raise SchemaParseError(
            f"Schema file not found: {path}. "
            f"Expected the Aura protocol schema at this path. "
            f"Fix: ensure schema.xml exists at the expected location, "
            f"typically skills/protocol/schema.xml relative to the project root."
        )

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise SchemaParseError(
            f"XML parse error in {path}: {e}. "
            f"The schema file is not valid XML. "
            f"Fix: correct the XML syntax error at the reported line/column."
        ) from e

    root = tree.getroot()

    if root.tag != "aura-protocol":
        raise SchemaParseError(
            f"Unexpected root element <{root.tag}> in {path}. "
            f"Expected <aura-protocol>. "
            f"Fix: ensure the root element of schema.xml is <aura-protocol>."
        )

    phases = _parse_phases(root, path)
    substep_specs = _parse_substeps(root, path)
    procedure_steps = _parse_procedure_steps(root, path)
    roles = _parse_roles(root, path)
    commands = _parse_commands(root, path)
    constraints = _parse_constraints(root, path)
    handoffs = _parse_handoffs(root, path)
    labels = _parse_labels(root, path)
    review_axes = _parse_review_axes(root, path)
    title_conventions = _parse_title_conventions(root, path)
    checklists = _parse_checklists(root, path)
    coordination_commands = _parse_coordination_commands(root, path)
    workflows = _parse_workflows(root, path)
    figures = _parse_figures(root, path)

    return SchemaSpec(
        phases=phases,
        roles=roles,
        commands=commands,
        constraints=constraints,
        handoffs=handoffs,
        labels=labels,
        review_axes=review_axes,
        title_conventions=title_conventions,
        substep_specs=substep_specs,
        procedure_steps=procedure_steps,
        checklists=checklists,
        coordination_commands=coordination_commands,
        workflows=workflows,
        figures=figures,
    )
