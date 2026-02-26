#!/usr/bin/env python3
"""Validate skills/protocol/schema.xml structural and referential integrity."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ErrorLayer(Enum):
    STRUCTURAL = "Structural"
    REFERENTIAL = "Referential Integrity"
    SEMANTIC = "Semantic"


@dataclass
class ValidationError:
    layer: ErrorLayer
    element_path: str
    message: str

    def __str__(self) -> str:
        return f"{self.element_path}: {self.message}"


@dataclass
class SchemaIndex:
    """All ID sets and metadata extracted from a parsed schema."""

    phase_ids: set[str] = field(default_factory=set)
    substep_ids: set[str] = field(default_factory=set)
    label_ids: set[str] = field(default_factory=set)
    role_ids: set[str] = field(default_factory=set)
    command_ids: set[str] = field(default_factory=set)
    axis_ids: set[str] = field(default_factory=set)
    handoff_ids: set[str] = field(default_factory=set)
    constraint_ids: set[str] = field(default_factory=set)
    document_ids: set[str] = field(default_factory=set)
    team_ids: set[str] = field(default_factory=set)
    enum_value_ids: dict[str, set[str]] = field(default_factory=dict)
    severity_ids: set[str] = field(default_factory=set)

    # Metadata for semantic checks
    phase_numbers: dict[str, int] = field(default_factory=dict)
    startup_step_orders: dict[str, list[int]] = field(default_factory=dict)
    phase_domains: dict[str, str] = field(default_factory=dict)
    phase_substep_orders: dict[str, list[tuple[str, int, str]]] = field(
        default_factory=dict
    )
    label_values: dict[str, str] = field(default_factory=dict)
    axis_letters: dict[str, str] = field(default_factory=dict)
    role_phase_refs: dict[str, set[str]] = field(default_factory=dict)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _elem_desc(elem: ET.Element) -> str:
    tag = elem.tag
    id_val = elem.get("id")
    if id_val:
        return f"{tag}[@id='{id_val}']"
    name = elem.get("name")
    if name:
        return f"{tag}[@name='{name}']"
    pattern = elem.get("pattern")
    if pattern:
        return f"{tag}[@pattern='{pattern}']"
    ref = elem.get("ref")
    if ref:
        return f"{tag}[@ref='{ref}']"
    return tag


def _check_required(
    errors: list[ValidationError],
    elem_desc: str,
    elem: ET.Element,
    attrs: list[str],
) -> None:
    for attr in attrs:
        val = elem.get(attr)
        if val is None or val.strip() == "":
            errors.append(
                ValidationError(
                    layer=ErrorLayer.STRUCTURAL,
                    element_path=elem_desc,
                    message=f"missing required attribute '{attr}'",
                )
            )


def _check_ref(
    errors: list[ValidationError],
    elem_desc: str,
    attr_name: str,
    attr_val: str | None,
    target_set: set[str],
    target_name: str,
) -> None:
    if attr_val is not None and attr_val not in target_set:
        errors.append(
            ValidationError(
                layer=ErrorLayer.REFERENTIAL,
                element_path=elem_desc,
                message=f"{attr_name}='{attr_val}': no {target_name} with id '{attr_val}'",
            )
        )


def _check_id_unique(
    errors: list[ValidationError],
    id_val: str,
    id_set: set[str],
    elem_desc: str,
    type_name: str,
) -> None:
    if id_val in id_set:
        errors.append(
            ValidationError(
                layer=ErrorLayer.STRUCTURAL,
                element_path=elem_desc,
                message=f"duplicate {type_name} id '{id_val}'",
            )
        )
    id_set.add(id_val)


# ─── Layer 1: Structural + Index Building ────────────────────────────────────


def build_index(root: ET.Element) -> tuple[SchemaIndex, list[ValidationError]]:
    """Extract all IDs and check structural requirements in one pass."""
    idx = SchemaIndex()
    errors: list[ValidationError] = []

    # Enums
    for enum_el in root.iter("enum"):
        enum_name = enum_el.get("name", "")
        value_ids: set[str] = set()
        for val in enum_el.findall("value"):
            desc = f"enum[@name='{enum_name}']/{_elem_desc(val)}"
            _check_required(errors, desc, val, ["id", "description"])
            vid = val.get("id")
            if vid:
                if vid in value_ids:
                    errors.append(
                        ValidationError(
                            layer=ErrorLayer.STRUCTURAL,
                            element_path=desc,
                            message=f"duplicate value id '{vid}' within enum '{enum_name}'",
                        )
                    )
                value_ids.add(vid)
        idx.enum_value_ids[enum_name] = value_ids
    idx.severity_ids = set(idx.enum_value_ids.get("SeverityLevel", set()))

    # Labels
    for label in root.iter("label"):
        desc = _elem_desc(label)
        _check_required(errors, desc, label, ["id", "value"])
        lid = label.get("id")
        if lid:
            _check_id_unique(errors, lid, idx.label_ids, desc, "label")
        is_special = label.get("special") == "true"
        if not is_special:
            _check_required(errors, desc, label, ["phase-ref", "substep-ref"])
        val = label.get("value")
        if lid and val:
            idx.label_values[lid] = val

    # Review axes
    for axis in root.iter("axis"):
        desc = _elem_desc(axis)
        _check_required(errors, desc, axis, ["id", "letter", "name"])
        aid = axis.get("id")
        if aid:
            _check_id_unique(errors, aid, idx.axis_ids, desc, "axis")
        letter = axis.get("letter")
        if aid and letter:
            idx.axis_letters[aid] = letter

    # Phases and substeps
    for phase in root.iter("phase"):
        desc = _elem_desc(phase)
        _check_required(errors, desc, phase, ["id", "number", "domain", "name"])
        pid = phase.get("id")
        if pid:
            _check_id_unique(errors, pid, idx.phase_ids, desc, "phase")
            num_str = phase.get("number")
            if num_str:
                try:
                    idx.phase_numbers[pid] = int(num_str)
                except ValueError:
                    errors.append(
                        ValidationError(
                            layer=ErrorLayer.STRUCTURAL,
                            element_path=desc,
                            message=f"number='{num_str}' is not a valid integer",
                        )
                    )
            domain = phase.get("domain")
            if domain:
                idx.phase_domains[pid] = domain

        substep_data: list[tuple[str, int, str]] = []
        for substep in phase.iter("substep"):
            sdesc = f"{desc}/{_elem_desc(substep)}"
            _check_required(
                errors, sdesc, substep, ["id", "type", "execution", "order", "label-ref"]
            )
            sid = substep.get("id")
            if sid:
                _check_id_unique(errors, sid, idx.substep_ids, sdesc, "substep")
            order_str = substep.get("order")
            execution = substep.get("execution", "")
            order = 0
            if order_str:
                try:
                    order = int(order_str)
                except ValueError:
                    errors.append(
                        ValidationError(
                            layer=ErrorLayer.STRUCTURAL,
                            element_path=sdesc,
                            message=f"order='{order_str}' is not a valid integer",
                        )
                    )
            # Startup sequence steps
            startup_seq = substep.find("startup-sequence")
            if startup_seq is not None:
                step_orders: list[int] = []
                for step_el in startup_seq.findall("step"):
                    step_desc = f"{sdesc}/startup-sequence/step[@order='{step_el.get('order', '')}']"
                    _check_required(errors, step_desc, step_el, ["order"])
                    sorder_str = step_el.get("order")
                    if sorder_str:
                        try:
                            step_orders.append(int(sorder_str))
                        except ValueError:
                            errors.append(
                                ValidationError(
                                    layer=ErrorLayer.STRUCTURAL,
                                    element_path=step_desc,
                                    message=f"order='{sorder_str}' is not a valid integer",
                                )
                            )
                if sid:
                    idx.startup_step_orders[sid] = step_orders

            if sid:
                substep_data.append((sid, order, execution))
        if pid:
            idx.phase_substep_orders[pid] = substep_data

    # Roles (only under <roles> section — other <role> elements e.g. in
    # <procedure-steps> use ref= not id=/name= and are validated separately)
    roles_el = root.find("roles")
    for role in (roles_el.findall("role") if roles_el is not None else []):
        desc = _elem_desc(role)
        _check_required(errors, desc, role, ["id", "name"])
        rid = role.get("id")
        if rid:
            _check_id_unique(errors, rid, idx.role_ids, desc, "role")
            phase_refs: set[str] = set()
            owns_phases = role.find("owns-phases")
            if owns_phases is not None:
                for pr in owns_phases.findall("phase-ref"):
                    ref = pr.get("ref")
                    if ref:
                        phase_refs.add(ref)
            idx.role_phase_refs[rid] = phase_refs

            # Standing teams
            for team in role.iter("team"):
                team_desc = f"{desc}/standing-teams/{_elem_desc(team)}"
                _check_required(errors, team_desc, team, ["id"])
                tid = team.get("id")
                if tid:
                    _check_id_unique(errors, tid, idx.team_ids, team_desc, "team")
                for agent_tmpl in team.findall("agent-template"):
                    at_desc = f"{team_desc}/agent-template"
                    _check_required(
                        errors, at_desc, agent_tmpl,
                        ["role", "skill-ref", "invocation", "min-count", "max-count"],
                    )
                    for count_attr in ("min-count", "max-count"):
                        count_str = agent_tmpl.get(count_attr)
                        if count_str:
                            try:
                                int(count_str)
                            except ValueError:
                                errors.append(
                                    ValidationError(
                                        layer=ErrorLayer.STRUCTURAL,
                                        element_path=at_desc,
                                        message=f"{count_attr}='{count_str}' is not a valid integer",
                                    )
                                )

    # Commands (only within <commands> section, not <command> text elements elsewhere)
    commands_section = root.find("commands")
    if commands_section is not None:
        for cmd in commands_section.findall("command"):
            desc = _elem_desc(cmd)
            _check_required(errors, desc, cmd, ["id", "name"])
            cid = cmd.get("id")
            if cid:
                _check_id_unique(errors, cid, idx.command_ids, desc, "command")

    # Handoffs
    for handoff in root.iter("handoff"):
        desc = _elem_desc(handoff)
        _check_required(
            errors,
            desc,
            handoff,
            ["id", "source-role", "target-role", "at-phase", "content-level"],
        )
        hid = handoff.get("id")
        if hid:
            _check_id_unique(errors, hid, idx.handoff_ids, desc, "handoff")

    # Constraints
    for constraint in root.iter("constraint"):
        desc = _elem_desc(constraint)
        _check_required(
            errors, desc, constraint, ["id", "given", "when", "then", "should-not"]
        )
        cid = constraint.get("id")
        if cid:
            _check_id_unique(errors, cid, idx.constraint_ids, desc, "constraint")

    # Documents
    for doc in root.iter("document"):
        desc = _elem_desc(doc)
        _check_required(errors, desc, doc, ["id", "path"])
        did = doc.get("id")
        if did:
            _check_id_unique(errors, did, idx.document_ids, desc, "document")

    # Title conventions
    for tc in root.iter("title-convention"):
        desc = _elem_desc(tc)
        _check_required(errors, desc, tc, ["pattern", "label-ref", "created-by"])

    # Skill invocations (structural: directive required)
    for si in root.iter("skill-invocation"):
        cmd_ref = si.get("command-ref")
        si_desc = f"skill-invocation[@command-ref='{cmd_ref}']" if cmd_ref else "skill-invocation"
        _check_required(errors, si_desc, si, ["directive"])

    return idx, errors


# ─── Layer 2: Referential Integrity ──────────────────────────────────────────


_ENTITY_TYPE_MAP: dict[str, str] = {
    "phase": "phase_ids",
    "substep": "substep_ids",
    "label": "label_ids",
    "role": "role_ids",
    "command": "command_ids",
    "constraint": "constraint_ids",
    "handoff": "handoff_ids",
    "review-axis": "axis_ids",
    "severity": "severity_ids",
}


def _entity_type_to_set(type_attr: str, index: SchemaIndex) -> set[str] | None:
    field_name = _ENTITY_TYPE_MAP.get(type_attr)
    if field_name:
        return getattr(index, field_name)
    if type_attr == "vote":
        return index.enum_value_ids.get("VoteType", set())
    return None


def check_refs(root: ET.Element, index: SchemaIndex) -> list[ValidationError]:
    """Check all cross-references resolve to existing IDs."""
    errors: list[ValidationError] = []

    # Labels: phase-ref, substep-ref, severity-ref
    for label in root.iter("label"):
        desc = _elem_desc(label)
        _check_ref(errors, desc, "phase-ref", label.get("phase-ref"), index.phase_ids, "phase")
        _check_ref(errors, desc, "substep-ref", label.get("substep-ref"), index.substep_ids, "substep")
        _check_ref(errors, desc, "severity-ref", label.get("severity-ref"), index.severity_ids, "severity")

    # Substeps: label-ref
    for substep in root.iter("substep"):
        desc = _elem_desc(substep)
        _check_ref(errors, desc, "label-ref", substep.get("label-ref"), index.label_ids, "label")

    # Extra-label: ref
    for el in root.iter("extra-label"):
        desc = _elem_desc(el)
        _check_ref(errors, desc, "ref", el.get("ref"), index.label_ids, "label")

    # Commands: role-ref (scoped to <commands> section)
    commands_section = root.find("commands")
    if commands_section is not None:
        for cmd in commands_section.findall("command"):
            desc = _elem_desc(cmd)
            _check_ref(errors, desc, "role-ref", cmd.get("role-ref"), index.role_ids, "role")

    # phase-ref child elements: ref → phase_ids
    for el in root.iter("phase-ref"):
        ref = el.get("ref")
        if ref is not None:
            _check_ref(errors, f"phase-ref[@ref='{ref}']", "ref", ref, index.phase_ids, "phase")

    # label-ref child elements: ref → label_ids
    for el in root.iter("label-ref"):
        ref = el.get("ref")
        if ref is not None:
            _check_ref(errors, f"label-ref[@ref='{ref}']", "ref", ref, index.label_ids, "label")

    # axis-ref child elements: ref → axis_ids
    for el in root.iter("axis-ref"):
        ref = el.get("ref")
        if ref is not None:
            _check_ref(errors, f"axis-ref[@ref='{ref}']", "ref", ref, index.axis_ids, "axis")

    # Handoffs: source-role, target-role, at-phase
    for handoff in root.iter("handoff"):
        desc = _elem_desc(handoff)
        _check_ref(errors, desc, "source-role", handoff.get("source-role"), index.role_ids, "role")
        _check_ref(errors, desc, "target-role", handoff.get("target-role"), index.role_ids, "role")
        _check_ref(errors, desc, "at-phase", handoff.get("at-phase"), index.phase_ids, "phase")

    # Transitions: to-phase (skip "complete" as a terminal sentinel)
    for t in root.iter("transition"):
        to_phase = t.get("to-phase")
        if to_phase is not None and to_phase != "complete":
            _check_ref(
                errors,
                f"transition[@to-phase='{to_phase}']",
                "to-phase",
                to_phase,
                index.phase_ids,
                "phase",
            )

    # same-actor-as: phase-ref
    for el in root.iter("same-actor-as"):
        _check_ref(errors, "same-actor-as", "phase-ref", el.get("phase-ref"), index.phase_ids, "phase")

    # Title conventions: label-ref, phase-ref, extra-label-ref
    for tc in root.iter("title-convention"):
        desc = _elem_desc(tc)
        _check_ref(errors, desc, "label-ref", tc.get("label-ref"), index.label_ids, "label")
        _check_ref(errors, desc, "phase-ref", tc.get("phase-ref"), index.phase_ids, "phase")
        _check_ref(errors, desc, "extra-label-ref", tc.get("extra-label-ref"), index.label_ids, "label")

    # severity-tree groups: severity-ref, label-ref
    for st in root.iter("severity-tree"):
        for g in st.findall("group"):
            g_desc = f"severity-tree/group[@severity-ref='{g.get('severity-ref', '')}']"
            _check_ref(errors, g_desc, "severity-ref", g.get("severity-ref"), index.severity_ids, "severity")
            _check_ref(errors, g_desc, "label-ref", g.get("label-ref"), index.label_ids, "label")

    # followup-epic: label-ref
    for fe in root.iter("followup-epic"):
        _check_ref(errors, "followup-epic", "label-ref", fe.get("label-ref"), index.label_ids, "label")

    # delegate: to-role, phases (comma-separated)
    for d in root.iter("delegate"):
        d_desc = f"delegate[@to-role='{d.get('to-role', '')}']"
        _check_ref(errors, d_desc, "to-role", d.get("to-role"), index.role_ids, "role")
        phases_str = d.get("phases", "")
        if phases_str:
            for p in phases_str.split(","):
                p = p.strip()
                if p:
                    _check_ref(errors, d_desc, "phases", p, index.phase_ids, "phase")

    # Skill invocations: command-ref → command_ids
    for si in root.iter("skill-invocation"):
        cmd_ref = si.get("command-ref")
        si_desc = f"skill-invocation[@command-ref='{cmd_ref}']" if cmd_ref else "skill-invocation"
        _check_ref(errors, si_desc, "command-ref", cmd_ref, index.command_ids, "command")

    # Agent templates: skill-ref → command_ids
    for at in root.iter("agent-template"):
        at_desc = _elem_desc(at)
        _check_ref(errors, at_desc, "skill-ref", at.get("skill-ref"), index.command_ids, "command")

    # Document entities: refs (comma-separated or wildcard)
    for doc in root.iter("document"):
        doc_desc = _elem_desc(doc)
        for entity in doc.iter("entity"):
            refs = entity.get("refs", "")
            if refs in ("all", "all-protocol", ""):
                continue
            type_attr = entity.get("type", "")
            if type_attr == "all":
                continue
            target_set = _entity_type_to_set(type_attr, index)
            if target_set is None:
                continue
            e_desc = f"{doc_desc}/entity[@type='{type_attr}']"
            for ref in refs.split(","):
                ref = ref.strip()
                if ref:
                    _check_ref(errors, e_desc, "refs", ref, target_set, type_attr)

    return errors


# ─── Layer 3: Semantic Rules ─────────────────────────────────────────────────

_EXPECTED_DOMAINS: dict[int, str] = {
    1: "user",  2: "user",  3: "plan",  4: "plan",
    5: "user",  6: "plan",  7: "plan",  8: "impl",
    9: "impl",  10: "impl", 11: "user", 12: "impl",
}


def check_semantics(root: ET.Element, index: SchemaIndex) -> list[ValidationError]:
    """Check protocol-level semantic rules."""
    errors: list[ValidationError] = []

    # 1. Phase numbers sequential (contiguous 1..N)
    numbers = sorted(index.phase_numbers.values())
    if numbers:
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            missing = set(expected) - set(numbers)
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path="phases",
                    message=f"Phase numbers not sequential: found {numbers}"
                    + (f" (missing {sorted(missing)})" if missing else ""),
                )
            )

    # 2. Phase domain consistency
    for pid, num in index.phase_numbers.items():
        domain = index.phase_domains.get(pid)
        expected_domain = _EXPECTED_DOMAINS.get(num)
        if domain and expected_domain and domain != expected_domain:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"phase[@id='{pid}']",
                    message=f"domain='{domain}' but phase {num} should be '{expected_domain}'",
                )
            )

    # 3. Each phase has >= 1 substep
    for pid in index.phase_ids:
        substeps = index.phase_substep_orders.get(pid, [])
        if not substeps:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"phase[@id='{pid}']",
                    message="phase has no substeps",
                )
            )

    # 4. Substep order sequential within phase (starting from 1)
    for pid, substeps in index.phase_substep_orders.items():
        if not substeps:
            continue
        orders = sorted(set(s[1] for s in substeps))
        expected_orders = list(range(1, max(orders) + 1)) if orders else []
        if orders != expected_orders:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"phase[@id='{pid}']",
                    message=f"substep orders not sequential: found {orders}, expected {expected_orders}",
                )
            )

    # 5. Parallel substeps must have parallel-group
    for phase in root.iter("phase"):
        pid = phase.get("id", "")
        for substep in phase.iter("substep"):
            if (
                substep.get("execution") == "parallel"
                and not substep.get("parallel-group")
                and substep.find("instances") is None
            ):
                errors.append(
                    ValidationError(
                        layer=ErrorLayer.SEMANTIC,
                        element_path=f"phase[@id='{pid}']/{_elem_desc(substep)}",
                        message="execution='parallel' but missing 'parallel-group' attribute",
                    )
                )

    # 6. Label value uniqueness
    seen_values: dict[str, str] = {}
    for lid, val in index.label_values.items():
        if val in seen_values:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"label[@id='{lid}']",
                    message=f"duplicate value '{val}' (first seen on label[@id='{seen_values[val]}'])",
                )
            )
        else:
            seen_values[val] = lid

    # 9. Each role owns >= 1 phase
    for rid, phases in index.role_phase_refs.items():
        if not phases:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"role[@id='{rid}']",
                    message="role owns no phases",
                )
            )

    # 10. Each command with <phases> must have a <file> child
    commands_section = root.find("commands")
    for cmd in (commands_section.findall("command") if commands_section is not None else []):
        if cmd.find("phases") is not None and cmd.find("file") is None:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=_elem_desc(cmd),
                    message="command has <phases> but no <file> child",
                )
            )

    # 11. Review axis letters unique
    seen_letters: dict[str, str] = {}
    for aid, letter in index.axis_letters.items():
        if letter in seen_letters:
            errors.append(
                ValidationError(
                    layer=ErrorLayer.SEMANTIC,
                    element_path=f"axis[@id='{aid}']",
                    message=f"duplicate letter '{letter}' (first seen on axis[@id='{seen_letters[letter]}'])",
                )
            )
        else:
            seen_letters[letter] = aid

    # 12. Startup sequence step orders sequential
    for sid, orders in index.startup_step_orders.items():
        if orders:
            sorted_orders = sorted(orders)
            expected = list(range(1, len(orders) + 1))
            if sorted_orders != expected:
                errors.append(
                    ValidationError(
                        layer=ErrorLayer.SEMANTIC,
                        element_path=f"substep[@id='{sid}']/startup-sequence",
                        message=f"step orders not sequential: found {sorted_orders}, expected {expected}",
                    )
                )

    # 13. Agent template min-count <= max-count
    for at in root.iter("agent-template"):
        min_str = at.get("min-count")
        max_str = at.get("max-count")
        if min_str and max_str:
            try:
                if int(min_str) > int(max_str):
                    at_desc = _elem_desc(at) or "agent-template"
                    errors.append(
                        ValidationError(
                            layer=ErrorLayer.SEMANTIC,
                            element_path=at_desc,
                            message=f"min-count ({min_str}) > max-count ({max_str})",
                        )
                    )
            except ValueError:
                pass  # Non-integer caught by structural layer

    # 14. Domain enum values match phase domains
    domain_enum_values = index.enum_value_ids.get("DomainType", set())
    if domain_enum_values:
        for pid, domain in index.phase_domains.items():
            if domain not in domain_enum_values:
                errors.append(
                    ValidationError(
                        layer=ErrorLayer.SEMANTIC,
                        element_path=f"phase[@id='{pid}']",
                        message=f"domain='{domain}' not in DomainType enum {sorted(domain_enum_values)}",
                    )
                )

    return errors


# ─── Orchestration ────────────────────────────────────────────────────────────


def validate_tree(root: ET.Element) -> list[ValidationError]:
    """Run all validation layers on a parsed XML tree."""
    index, structural_errors = build_index(root)
    ref_errors = check_refs(root, index)
    semantic_errors = check_semantics(root, index)
    return structural_errors + ref_errors + semantic_errors


def validate(path: Path) -> list[ValidationError]:
    """Run all validation layers. Convenience wrapper that handles parsing."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [
            ValidationError(
                layer=ErrorLayer.STRUCTURAL,
                element_path=str(path),
                message=f"XML parse error: {e}",
            )
        ]
    return validate_tree(tree.getroot())


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point. Returns exit code: 0=valid, 1=errors, 2=parse/file error."""
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        script_dir = Path(__file__).resolve().parent
        path = script_dir.parent / "skills" / "protocol" / "schema.xml"

    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"Error: XML parse error: {e}", file=sys.stderr)
        return 2

    errors = validate_tree(tree.getroot())

    if not errors:
        print(f"Schema validation: {path.name} OK")
        return 0

    by_layer: dict[ErrorLayer, list[ValidationError]] = {}
    for e in errors:
        by_layer.setdefault(e.layer, []).append(e)

    for layer in ErrorLayer:
        layer_errors = by_layer.get(layer, [])
        if layer_errors:
            print(f"\n=== {layer.value} Errors ===")
            for e in layer_errors:
                print(f"  {e}")

    print(f"\nSchema validation: {len(errors)} error(s) found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
