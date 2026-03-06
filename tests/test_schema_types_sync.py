"""Integration test: Python types in aura_protocol.types must match schema.xml.

AC8: Given Python type definitions when compared against schema.xml then every
PhaseId, Domain, RoleId, VoteType, and SeverityLevel has a corresponding
schema.xml element should never drift from schema.xml.

These tests parse the real schema.xml and compare against the Python type
definitions in aura_protocol/types.py. If schema.xml changes, these tests
will catch any Python drift.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from aura_protocol import (
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
    CommandId,
    Domain,
    HandoffSpec,
    PhaseId,
    RoleId,
    SeverityLevel,
    SkillRef,
    Transition,
    VoteType,
)
from aura_protocol.types import (
    CHECKLIST_SPECS,
    COORDINATION_COMMANDS,
    FIGURE_SPECS,
    WORKFLOW_SPECS,
    ExampleLabel,
    ExampleLang,
    ExitConditionType,
    FigureId,
    FigureType,
    GateType,
    WorkflowExecution,
)

# ─── Schema Path ──────────────────────────────────────────────────────────────

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "skills" / "protocol" / "schema.xml"


@pytest.fixture(scope="module")
def schema_root() -> ET.Element:
    """Parse schema.xml once for the entire module."""
    assert SCHEMA_PATH.exists(), f"schema.xml not found at {SCHEMA_PATH}"
    tree = ET.parse(SCHEMA_PATH)
    return tree.getroot()


# ─── Enum Sync ────────────────────────────────────────────────────────────────


class TestPhaseIdMatchesSchema:
    """Every PhaseId must have a corresponding <phase id="..."> in schema.xml."""

    def test_all_phase_ids_in_schema(self, schema_root: ET.Element) -> None:
        schema_phase_ids = {p.get("id") for p in schema_root.iter("phase") if p.get("id")}
        # COMPLETE is a terminal sentinel not defined as a <phase> element
        python_phase_ids = {p.value for p in PhaseId if p != PhaseId.COMPLETE}
        assert python_phase_ids == schema_phase_ids, (
            f"Python PhaseId values not matching schema.xml phases.\n"
            f"In Python only: {python_phase_ids - schema_phase_ids}\n"
            f"In schema only: {schema_phase_ids - python_phase_ids}"
        )

    def test_phase_count_matches(self, schema_root: ET.Element) -> None:
        schema_count = len({p.get("id") for p in schema_root.iter("phase") if p.get("id")})
        python_count = len([p for p in PhaseId if p != PhaseId.COMPLETE])
        assert python_count == schema_count, (
            f"Phase count mismatch: Python has {python_count}, schema.xml has {schema_count}"
        )

    def test_complete_sentinel_not_in_schema_phases(self, schema_root: ET.Element) -> None:
        schema_phase_ids = {p.get("id") for p in schema_root.iter("phase") if p.get("id")}
        assert "complete" not in schema_phase_ids, (
            "schema.xml has 'complete' as a phase element — COMPLETE is expected to be a sentinel only"
        )


class TestDomainMatchesSchema:
    """Every Domain value must have a corresponding entry in schema.xml DomainType enum."""

    def test_all_domain_values_in_schema(self, schema_root: ET.Element) -> None:
        domain_enum = None
        for enum_el in schema_root.iter("enum"):
            if enum_el.get("name") == "DomainType":
                domain_enum = enum_el
                break
        assert domain_enum is not None, "DomainType enum not found in schema.xml"

        schema_domain_ids = {v.get("id") for v in domain_enum.findall("value") if v.get("id")}
        python_domain_values = {d.value for d in Domain}
        assert python_domain_values == schema_domain_ids, (
            f"Python Domain values not matching schema.xml DomainType.\n"
            f"In Python only: {python_domain_values - schema_domain_ids}\n"
            f"In schema only: {schema_domain_ids - python_domain_values}"
        )


class TestRoleIdMatchesSchema:
    """Every RoleId must have a corresponding <role id="..."> in schema.xml."""

    def test_all_role_ids_in_schema(self, schema_root: ET.Element) -> None:
        schema_role_ids = {r.get("id") for r in schema_root.iter("role") if r.get("id")}
        python_role_ids = {r.value for r in RoleId}
        assert python_role_ids == schema_role_ids, (
            f"Python RoleId values not matching schema.xml roles.\n"
            f"In Python only: {python_role_ids - schema_role_ids}\n"
            f"In schema only: {schema_role_ids - python_role_ids}"
        )


class TestVoteTypeMatchesSchema:
    """Every VoteType value must have a corresponding entry in schema.xml VoteType enum."""

    def test_all_vote_types_in_schema(self, schema_root: ET.Element) -> None:
        vote_enum = None
        for enum_el in schema_root.iter("enum"):
            if enum_el.get("name") == "VoteType":
                vote_enum = enum_el
                break
        assert vote_enum is not None, "VoteType enum not found in schema.xml"

        schema_vote_ids = {v.get("id") for v in vote_enum.findall("value") if v.get("id")}
        python_vote_values = {v.value for v in VoteType}
        assert python_vote_values == schema_vote_ids, (
            f"Python VoteType values not matching schema.xml VoteType enum.\n"
            f"In Python only: {python_vote_values - schema_vote_ids}\n"
            f"In schema only: {schema_vote_ids - python_vote_values}"
        )


class TestSeverityLevelMatchesSchema:
    """Every SeverityLevel value must have a corresponding entry in schema.xml SeverityLevel enum."""

    def test_all_severity_levels_in_schema(self, schema_root: ET.Element) -> None:
        severity_enum = None
        for enum_el in schema_root.iter("enum"):
            if enum_el.get("name") == "SeverityLevel":
                severity_enum = enum_el
                break
        assert severity_enum is not None, "SeverityLevel enum not found in schema.xml"

        schema_severity_ids = {
            v.get("id") for v in severity_enum.findall("value") if v.get("id")
        }
        python_severity_values = {s.value for s in SeverityLevel}
        assert python_severity_values == schema_severity_ids, (
            f"Python SeverityLevel values not matching schema.xml SeverityLevel enum.\n"
            f"In Python only: {python_severity_values - schema_severity_ids}\n"
            f"In schema only: {schema_severity_ids - python_severity_values}"
        )


# ─── PHASE_DOMAIN Sync ────────────────────────────────────────────────────────


class TestPhaseDomainMatchesSchema:
    """PHASE_DOMAIN mapping must match schema.xml phase domain assignments."""

    def test_phase_domains_match_schema(self, schema_root: ET.Element) -> None:
        """Each phase in schema.xml has an expected domain; PHASE_DOMAIN must agree."""
        schema_phase_domains: dict[str, str] = {}
        for phase in schema_root.iter("phase"):
            pid = phase.get("id")
            domain = phase.get("domain")
            if pid and domain:
                schema_phase_domains[pid] = domain

        for phase_id, python_domain in PHASE_DOMAIN.items():
            schema_domain = schema_phase_domains.get(phase_id.value)
            assert schema_domain is not None, (
                f"Phase {phase_id.value} not found in schema.xml phases"
            )
            assert python_domain.value == schema_domain, (
                f"PHASE_DOMAIN[{phase_id}] = {python_domain.value!r} "
                f"but schema.xml says {schema_domain!r}"
            )

    def test_schema_domain_enum_matches_expected_domains_in_validate_schema(
        self, schema_root: ET.Element
    ) -> None:
        """The _EXPECTED_DOMAINS mapping in validate_schema.py defines the canonical
        phase-number-to-domain mapping. This test checks our PHASE_DOMAIN dict
        agrees with those expectations.

        _EXPECTED_DOMAINS from validate_schema.py:
          {1: "user", 2: "user", 3: "plan", 4: "plan",
           5: "user", 6: "plan", 7: "plan", 8: "impl",
           9: "impl", 10: "impl", 11: "user", 12: "impl"}
        """
        expected_by_number: dict[int, str] = {
            1: "user", 2: "user", 3: "plan", 4: "plan",
            5: "user", 6: "plan", 7: "plan", 8: "impl",
            9: "impl", 10: "impl", 11: "user", 12: "impl",
        }

        # Build phase_id -> number from schema
        phase_number_map: dict[str, int] = {}
        for phase in schema_root.iter("phase"):
            pid = phase.get("id")
            num_str = phase.get("number")
            if pid and num_str:
                phase_number_map[pid] = int(num_str)

        for phase_id, python_domain in PHASE_DOMAIN.items():
            phase_number = phase_number_map.get(phase_id.value)
            assert phase_number is not None, f"No number for phase {phase_id.value} in schema.xml"
            expected_domain = expected_by_number.get(phase_number)
            assert expected_domain is not None, (
                f"No expected domain for phase number {phase_number}"
            )
            assert python_domain.value == expected_domain, (
                f"PHASE_DOMAIN[{phase_id}] = {python_domain.value!r} "
                f"but expected {expected_domain!r} for phase number {phase_number}"
            )


# ─── PHASE_SPECS Transition Sync ──────────────────────────────────────────────


class TestPhaseSpecsTransitionsMatchSchema:
    """Transitions in PHASE_SPECS must match schema.xml <transition> elements."""

    def _get_schema_transitions(
        self, schema_root: ET.Element
    ) -> dict[str, list[dict[str, str | None]]]:
        """Extract all transitions from schema.xml keyed by phase id."""
        result: dict[str, list[dict[str, str | None]]] = {}
        for phase in schema_root.iter("phase"):
            pid = phase.get("id")
            if not pid:
                continue
            transitions_el = phase.find("transitions")
            if transitions_el is None:
                result[pid] = []
                continue
            trans_list = []
            for t in transitions_el.findall("transition"):
                trans_list.append({
                    "to_phase": t.get("to-phase"),
                    "condition": t.get("condition"),
                    "action": t.get("action"),
                })
            result[pid] = trans_list
        return result

    def test_all_phases_have_transitions_in_schema(self, schema_root: ET.Element) -> None:
        schema_transitions = self._get_schema_transitions(schema_root)
        for phase_id in PHASE_SPECS:
            assert phase_id.value in schema_transitions, (
                f"Phase {phase_id.value} not found in schema.xml transitions"
            )
            assert len(schema_transitions[phase_id.value]) > 0, (
                f"Phase {phase_id.value} has no transitions in schema.xml"
            )

    def test_transition_counts_match(self, schema_root: ET.Element) -> None:
        schema_transitions = self._get_schema_transitions(schema_root)
        for phase_id, spec in PHASE_SPECS.items():
            schema_count = len(schema_transitions.get(phase_id.value, []))
            python_count = len(spec.transitions)
            assert python_count == schema_count, (
                f"Phase {phase_id.value} transition count mismatch: "
                f"Python has {python_count}, schema.xml has {schema_count}"
            )

    def test_transition_to_phases_match(self, schema_root: ET.Element) -> None:
        schema_transitions = self._get_schema_transitions(schema_root)
        for phase_id, spec in PHASE_SPECS.items():
            schema_to_phases = {
                t["to_phase"] for t in schema_transitions.get(phase_id.value, [])
            }
            python_to_phases = {t.to_phase.value for t in spec.transitions}
            assert python_to_phases == schema_to_phases, (
                f"Phase {phase_id.value} transition to_phase mismatch.\n"
                f"Python: {python_to_phases}\nSchema: {schema_to_phases}"
            )


# ─── CONSTRAINT_SPECS Sync ────────────────────────────────────────────────────


class TestConstraintSpecsMatchSchema:
    """CONSTRAINT_SPECS must cover all <constraint> elements in schema.xml."""

    def test_all_schema_constraints_in_python(self, schema_root: ET.Element) -> None:
        schema_constraint_ids = {
            c.get("id") for c in schema_root.iter("constraint") if c.get("id")
        }
        python_constraint_ids = set(CONSTRAINT_SPECS.keys())
        assert python_constraint_ids == schema_constraint_ids, (
            f"Constraint mismatch.\n"
            f"In Python only: {python_constraint_ids - schema_constraint_ids}\n"
            f"In schema only: {schema_constraint_ids - python_constraint_ids}"
        )

    def test_constraint_given_when_then_match_schema(self, schema_root: ET.Element) -> None:
        for c in schema_root.iter("constraint"):
            cid = c.get("id")
            if not cid or cid not in CONSTRAINT_SPECS:
                continue
            spec = CONSTRAINT_SPECS[cid]
            assert spec.given == c.get("given"), (
                f"{cid} 'given' mismatch: Python={spec.given!r}, schema={c.get('given')!r}"
            )
            assert spec.when == c.get("when"), (
                f"{cid} 'when' mismatch: Python={spec.when!r}, schema={c.get('when')!r}"
            )
            assert spec.then == c.get("then"), (
                f"{cid} 'then' mismatch: Python={spec.then!r}, schema={c.get('then')!r}"
            )


# ─── HANDOFF_SPECS Sync ───────────────────────────────────────────────────────


class TestHandoffSpecsMatchSchema:
    """HANDOFF_SPECS must cover all <handoff> elements in schema.xml."""

    def test_all_schema_handoffs_in_python(self, schema_root: ET.Element) -> None:
        schema_handoff_ids = {
            h.get("id") for h in schema_root.iter("handoff") if h.get("id")
        }
        python_handoff_ids = set(HANDOFF_SPECS.keys())
        assert python_handoff_ids == schema_handoff_ids, (
            f"Handoff mismatch.\n"
            f"In Python only: {python_handoff_ids - schema_handoff_ids}\n"
            f"In schema only: {schema_handoff_ids - python_handoff_ids}"
        )

    def test_handoff_roles_match_schema(self, schema_root: ET.Element) -> None:
        for h in schema_root.iter("handoff"):
            hid = h.get("id")
            if not hid or hid not in HANDOFF_SPECS:
                continue
            spec = HANDOFF_SPECS[hid]
            assert spec.source_role.value == h.get("source-role"), (
                f"{hid} source_role mismatch: Python={spec.source_role.value!r}, "
                f"schema={h.get('source-role')!r}"
            )
            assert spec.target_role.value == h.get("target-role"), (
                f"{hid} target_role mismatch: Python={spec.target_role.value!r}, "
                f"schema={h.get('target-role')!r}"
            )
            assert spec.at_phase.value == h.get("at-phase"), (
                f"{hid} at_phase mismatch: Python={spec.at_phase.value!r}, "
                f"schema={h.get('at-phase')!r}"
            )
            assert spec.content_level == h.get("content-level"), (
                f"{hid} content_level mismatch: Python={spec.content_level!r}, "
                f"schema={h.get('content-level')!r}"
            )


# ─── ROLE_SPECS Sync ──────────────────────────────────────────────────────────


class TestRoleSpecsMatchSchema:
    """ROLE_SPECS must cover all <role> elements in schema.xml."""

    def test_all_schema_roles_in_python(self, schema_root: ET.Element) -> None:
        schema_role_ids = {r.get("id") for r in schema_root.iter("role") if r.get("id")}
        python_role_ids = {r.value for r in ROLE_SPECS.keys()}
        assert python_role_ids == schema_role_ids, (
            f"Role mismatch.\n"
            f"In Python only: {python_role_ids - schema_role_ids}\n"
            f"In schema only: {schema_role_ids - python_role_ids}"
        )

    def test_role_names_match_schema(self, schema_root: ET.Element) -> None:
        for role in schema_root.iter("role"):
            rid_str = role.get("id")
            if not rid_str:
                continue
            try:
                rid = RoleId(rid_str)
            except ValueError:
                continue
            if rid not in ROLE_SPECS:
                continue
            spec = ROLE_SPECS[rid]
            assert spec.name == role.get("name"), (
                f"Role {rid_str} name mismatch: Python={spec.name!r}, "
                f"schema={role.get('name')!r}"
            )

    def test_role_owned_phases_match_schema(self, schema_root: ET.Element) -> None:
        for role in schema_root.iter("role"):
            rid_str = role.get("id")
            if not rid_str:
                continue
            try:
                rid = RoleId(rid_str)
            except ValueError:
                continue
            if rid not in ROLE_SPECS:
                continue
            owns_phases = role.find("owns-phases")
            schema_phases: set[str] = set()
            if owns_phases is not None:
                for pr in owns_phases.findall("phase-ref"):
                    ref = pr.get("ref")
                    if ref:
                        schema_phases.add(ref)
            python_phases = ROLE_SPECS[rid].owned_phases
            assert python_phases == schema_phases, (
                f"Role {rid_str} owned_phases mismatch.\n"
                f"Python: {sorted(python_phases)}\n"
                f"Schema: {sorted(schema_phases)}"
            )


# ─── COMMAND_SPECS Sync ───────────────────────────────────────────────────────


class TestCommandSpecsMatchSchema:
    """COMMAND_SPECS must cover all <command> elements in schema.xml <commands> section."""

    def test_all_schema_commands_in_python(self, schema_root: ET.Element) -> None:
        commands_section = schema_root.find("commands")
        assert commands_section is not None, "<commands> section not found in schema.xml"
        schema_command_ids = {
            c.get("id") for c in commands_section.findall("command") if c.get("id")
        }
        python_command_ids = set(COMMAND_SPECS.keys())
        assert python_command_ids == schema_command_ids, (
            f"Command mismatch.\n"
            f"In Python only: {python_command_ids - schema_command_ids}\n"
            f"In schema only: {schema_command_ids - python_command_ids}"
        )

    def test_command_names_match_schema(self, schema_root: ET.Element) -> None:
        commands_section = schema_root.find("commands")
        if commands_section is None:
            return
        for cmd in commands_section.findall("command"):
            cid = cmd.get("id")
            if not cid or cid not in COMMAND_SPECS:
                continue
            spec = COMMAND_SPECS[cid]
            assert spec.name == cmd.get("name"), (
                f"Command {cid} name mismatch: Python={spec.name!r}, "
                f"schema={cmd.get('name')!r}"
            )

    def test_command_role_refs_match_schema(self, schema_root: ET.Element) -> None:
        commands_section = schema_root.find("commands")
        if commands_section is None:
            return
        for cmd in commands_section.findall("command"):
            cid = cmd.get("id")
            if not cid or cid not in COMMAND_SPECS:
                continue
            spec = COMMAND_SPECS[cid]
            schema_role_ref = cmd.get("role-ref")
            if schema_role_ref is None:
                assert spec.role_ref is None, (
                    f"Command {cid}: Python has role_ref={spec.role_ref!r}, schema has none"
                )
            else:
                assert spec.role_ref is not None and spec.role_ref.value == schema_role_ref, (
                    f"Command {cid} role_ref mismatch: Python={spec.role_ref!r}, "
                    f"schema={schema_role_ref!r}"
                )


# ─── LABEL_SPECS Sync ─────────────────────────────────────────────────────────


class TestLabelSpecsMatchSchema:
    """LABEL_SPECS must cover all <label> elements in schema.xml <labels> section."""

    def test_all_schema_labels_in_python(self, schema_root: ET.Element) -> None:
        labels_section = schema_root.find("labels")
        assert labels_section is not None, "<labels> section not found in schema.xml"
        schema_label_ids = {
            l.get("id") for l in labels_section.findall("label") if l.get("id")
        }
        python_label_ids = set(LABEL_SPECS.keys())
        assert python_label_ids == schema_label_ids, (
            f"Label mismatch.\n"
            f"In Python only: {python_label_ids - schema_label_ids}\n"
            f"In schema only: {schema_label_ids - python_label_ids}"
        )

    def test_label_values_match_schema(self, schema_root: ET.Element) -> None:
        labels_section = schema_root.find("labels")
        if labels_section is None:
            return
        for label in labels_section.findall("label"):
            lid = label.get("id")
            if not lid or lid not in LABEL_SPECS:
                continue
            spec = LABEL_SPECS[lid]
            assert spec.value == label.get("value"), (
                f"Label {lid} value mismatch: Python={spec.value!r}, "
                f"schema={label.get('value')!r}"
            )

    def test_label_special_flags_match_schema(self, schema_root: ET.Element) -> None:
        labels_section = schema_root.find("labels")
        if labels_section is None:
            return
        for label in labels_section.findall("label"):
            lid = label.get("id")
            if not lid or lid not in LABEL_SPECS:
                continue
            spec = LABEL_SPECS[lid]
            schema_special = label.get("special") == "true"
            assert spec.special == schema_special, (
                f"Label {lid} special flag mismatch: Python={spec.special!r}, "
                f"schema={schema_special!r}"
            )


# ─── REVIEW_AXIS_SPECS Sync ───────────────────────────────────────────────────


class TestReviewAxisSpecsMatchSchema:
    """REVIEW_AXIS_SPECS must cover all <axis> elements in schema.xml."""

    def test_all_schema_axes_in_python(self, schema_root: ET.Element) -> None:
        schema_axis_ids = {a.get("id") for a in schema_root.iter("axis") if a.get("id")}
        python_axis_ids = set(REVIEW_AXIS_SPECS.keys())
        assert python_axis_ids == schema_axis_ids, (
            f"Review axis mismatch.\n"
            f"In Python only: {python_axis_ids - schema_axis_ids}\n"
            f"In schema only: {schema_axis_ids - python_axis_ids}"
        )

    def test_axis_letters_match_schema(self, schema_root: ET.Element) -> None:
        for axis in schema_root.iter("axis"):
            aid = axis.get("id")
            if not aid or aid not in REVIEW_AXIS_SPECS:
                continue
            spec = REVIEW_AXIS_SPECS[aid]
            assert spec.letter.value == axis.get("letter"), (
                f"Axis {aid} letter mismatch: Python={spec.letter.value!r}, "
                f"schema={axis.get('letter')!r}"
            )

    def test_axis_names_match_schema(self, schema_root: ET.Element) -> None:
        for axis in schema_root.iter("axis"):
            aid = axis.get("id")
            if not aid or aid not in REVIEW_AXIS_SPECS:
                continue
            spec = REVIEW_AXIS_SPECS[aid]
            assert spec.name == axis.get("name"), (
                f"Axis {aid} name mismatch: Python={spec.name!r}, "
                f"schema={axis.get('name')!r}"
            )


# ─── TITLE_CONVENTIONS Sync ───────────────────────────────────────────────────


class TestTitleConventionsMatchSchema:
    """TITLE_CONVENTIONS must cover all <title-convention> elements in schema.xml."""

    def test_all_schema_title_conventions_in_python(self, schema_root: ET.Element) -> None:
        task_titles_el = schema_root.find("task-titles")
        assert task_titles_el is not None, "<task-titles> section not found in schema.xml"
        schema_patterns = {
            tc.get("pattern")
            for tc in task_titles_el.findall("title-convention")
            if tc.get("pattern")
        }
        python_patterns = {tc.pattern for tc in TITLE_CONVENTIONS}
        assert python_patterns == schema_patterns, (
            f"Title convention mismatch.\n"
            f"In Python only: {python_patterns - schema_patterns}\n"
            f"In schema only: {schema_patterns - python_patterns}"
        )

    def test_title_convention_label_refs_match_schema(self, schema_root: ET.Element) -> None:
        task_titles_el = schema_root.find("task-titles")
        if task_titles_el is None:
            return
        schema_by_pattern = {
            tc.get("pattern"): tc
            for tc in task_titles_el.findall("title-convention")
            if tc.get("pattern")
        }
        for tc in TITLE_CONVENTIONS:
            schema_tc = schema_by_pattern.get(tc.pattern)
            if schema_tc is None:
                continue
            assert tc.label_ref == schema_tc.get("label-ref"), (
                f"Title convention '{tc.pattern}' label_ref mismatch: "
                f"Python={tc.label_ref!r}, schema={schema_tc.get('label-ref')!r}"
            )


# ─── PROCEDURE_STEPS Sync ─────────────────────────────────────────────────────


class TestProcedureStepsMatchSchema:
    """PROCEDURE_STEPS must be populated for supervisor and worker (UAT-6)."""

    def test_all_roles_have_entry(self) -> None:
        """Every RoleId has an entry in PROCEDURE_STEPS (even if empty)."""
        for role in RoleId:
            assert role in PROCEDURE_STEPS, (
                f"Role {role} missing from PROCEDURE_STEPS"
            )

    def test_supervisor_has_procedure_steps(self) -> None:
        """Supervisor role has non-empty procedure steps (UAT-6)."""
        steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        assert len(steps) > 0, "PROCEDURE_STEPS[supervisor] must be non-empty (UAT-6)"

    def test_worker_has_procedure_steps(self) -> None:
        """Worker role has non-empty procedure steps (UAT-6)."""
        steps = PROCEDURE_STEPS[RoleId.WORKER]
        assert len(steps) > 0, "PROCEDURE_STEPS[worker] must be non-empty (UAT-6)"

    def test_supervisor_steps_from_schema(self, schema_root: ET.Element) -> None:
        """Supervisor PROCEDURE_STEPS match startup-sequence in schema.xml phase p8.

        For each step, asserts:
        - step.id matches the 'id' XML attribute on the <step> element
        - step.instruction matches the <instruction> child element text

        Steps carry 'order' and 'id' as XML attributes; instruction/command/context/
        next-state are child elements (only present when non-None).
        """
        steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        # Collect the raw <step> XML elements from phase p8 startup-sequence
        xml_steps: list[ET.Element] = []
        phases_el = schema_root.find("phases")
        if phases_el is not None:
            for phase in phases_el.findall("phase"):
                if phase.get("id") != "p8":
                    continue
                substeps_el = phase.find("substeps")
                if substeps_el is None:
                    break
                for substep in substeps_el.findall("substep"):
                    startup_seq = substep.find("startup-sequence")
                    if startup_seq is not None:
                        xml_steps.extend(startup_seq.findall("step"))
                break
        assert len(steps) == len(xml_steps), (
            f"Supervisor procedure step count mismatch: "
            f"Python has {len(steps)}, schema has {len(xml_steps)} startup steps"
        )
        for i, (step, xml_step) in enumerate(zip(steps, xml_steps)):
            # id must match XML attribute
            assert step.id == xml_step.get("id"), (
                f"Supervisor step {i + 1} id mismatch: "
                f"Python={step.id!r}, schema={xml_step.get('id')!r}"
            )
            # instruction must match <instruction> child element text
            instr_el = xml_step.find("instruction")
            expected_text = instr_el.text.strip() if instr_el is not None and instr_el.text else ""
            assert step.instruction == expected_text, (
                f"Supervisor step {i + 1} instruction mismatch: "
                f"Python={step.instruction!r}, schema={expected_text!r}"
            )

    def test_procedure_step_command_and_context_values(self) -> None:
        """At least one supervisor step has a known command value and at least one
        has a non-None context value.

        AC-B1-1: Given PROCEDURE_STEPS[RoleId.SUPERVISOR], when values are
        inspected directly, then at least one step has .command == SkillRef.SUPERVISOR
        and at least one step has non-None .context string.
        """
        steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        assert any(s.command == SkillRef.SUPERVISOR for s in steps), (
            "Expected at least one supervisor step with "
            f".command == {SkillRef.SUPERVISOR!r} in PROCEDURE_STEPS"
        )
        assert any(s.context is not None for s in steps), (
            "Expected at least one supervisor step with non-None .context "
            "in PROCEDURE_STEPS"
        )

    def test_procedure_steps_ordered(self) -> None:
        """Procedure steps are in ascending order for all populated roles."""
        for role, steps in PROCEDURE_STEPS.items():
            if not steps:
                continue
            orders = [s.order for s in steps]
            assert orders == sorted(orders), (
                f"Procedure steps for {role} are not in order: {orders}"
            )

    def test_procedure_step_next_state_is_phase_id_or_none(self) -> None:
        """Every ProcedureStep.next_state is either a PhaseId or None."""
        for role, steps in PROCEDURE_STEPS.items():
            for step in steps:
                assert step.next_state is None or isinstance(step.next_state, PhaseId), (
                    f"Role {role.value} step {step.order}: next_state must be PhaseId or None, "
                    f"got {type(step.next_state)!r}"
                )

    def test_supervisor_step4_next_state_is_p8(self) -> None:
        """Supervisor step 4 (decompose into slices) must have next_state=PhaseId.P8_IMPL_PLAN."""
        steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        step4 = next((s for s in steps if s.order == 4), None)
        assert step4 is not None, "Supervisor must have a step 4"
        assert step4.next_state == PhaseId.P8_IMPL_PLAN, (
            f"Supervisor step 4 next_state expected P8_IMPL_PLAN, got {step4.next_state!r}"
        )

    def test_supervisor_step6_next_state_is_p9(self) -> None:
        """Supervisor step 6 (spawn workers) must have next_state=PhaseId.P9_SLICE."""
        steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        step6 = next((s for s in steps if s.order == 6), None)
        assert step6 is not None, "Supervisor must have a step 6"
        assert step6.next_state == PhaseId.P9_SLICE, (
            f"Supervisor step 6 next_state expected P9_SLICE, got {step6.next_state!r}"
        )

    def test_worker_step3_next_state_is_p9(self) -> None:
        """Worker step 3 (make tests pass) must have next_state=PhaseId.P9_SLICE."""
        steps = PROCEDURE_STEPS[RoleId.WORKER]
        step3 = next((s for s in steps if s.order == 3), None)
        assert step3 is not None, "Worker must have a step 3"
        assert step3.next_state == PhaseId.P9_SLICE, (
            f"Worker step 3 next_state expected P9_SLICE, got {step3.next_state!r}"
        )


# ─── New enum sync tests (R10) ────────────────────────────────────────────────


class TestNewEnumsSyncVsSchema:
    """Sync tests for new enums: ExampleLabel, ExampleLang, GateType,
    WorkflowExecution, ExitConditionType vs schema.xml usage."""

    def test_gate_type_values_match_schema_checklist_attrs(
        self, schema_root: ET.Element
    ) -> None:
        """Every gate= attribute on <checklist> elements must be a valid GateType value."""
        schema_gate_values = {
            cl.get("gate")
            for cl in schema_root.iter("checklist")
            if cl.get("gate")
        }
        python_gate_values = {g.value for g in GateType}
        assert schema_gate_values == python_gate_values, (
            f"GateType values must exactly match schema.xml gate= attributes.\n"
            f"In schema only: {schema_gate_values - python_gate_values}\n"
            f"In Python only: {python_gate_values - schema_gate_values}"
        )

    def test_workflow_execution_values_match_schema_stage_attrs(
        self, schema_root: ET.Element
    ) -> None:
        """Every execution= attribute on <stage> elements must be a valid WorkflowExecution."""
        schema_execution_values = {
            s.get("execution")
            for s in schema_root.iter("stage")
            if s.get("execution")
        }
        python_execution_values = {e.value for e in WorkflowExecution}
        assert schema_execution_values == python_execution_values, (
            f"WorkflowExecution values must exactly match schema.xml execution= attributes.\n"
            f"In schema only: {schema_execution_values - python_execution_values}\n"
            f"In Python only: {python_execution_values - schema_execution_values}"
        )

    def test_exit_condition_type_values_match_schema_attrs(
        self, schema_root: ET.Element
    ) -> None:
        """Every type= attribute on <exit-condition> elements must be in ExitConditionType."""
        schema_type_values = {
            ec.get("type")
            for ec in schema_root.iter("exit-condition")
            if ec.get("type")
        }
        python_type_values = {t.value for t in ExitConditionType}
        assert schema_type_values == python_type_values, (
            f"ExitConditionType values must exactly match schema.xml type= attributes.\n"
            f"In schema only: {schema_type_values - python_type_values}\n"
            f"In Python only: {python_type_values - schema_type_values}"
        )

    def test_example_label_has_expected_values(self) -> None:
        """ExampleLabel enum has all expected values: correct, anti-pattern, context, template."""
        expected = {"correct", "anti-pattern", "context", "template"}
        python_values = {v.value for v in ExampleLabel}
        assert expected == python_values, (
            f"ExampleLabel mismatch.\n"
            f"Expected: {expected}\nGot: {python_values}"
        )

    def test_example_lang_has_expected_values(self) -> None:
        """ExampleLang enum has all expected values: bash, go, python, pseudo, xml, json, markdown."""
        expected = {"bash", "go", "python", "pseudo", "xml", "json", "markdown"}
        python_values = {v.value for v in ExampleLang}
        assert expected == python_values, (
            f"ExampleLang mismatch.\n"
            f"Expected: {expected}\nGot: {python_values}"
        )


# ─── CHECKLIST_SPECS sync tests ───────────────────────────────────────────────


class TestChecklistSpecsMatchSchema:
    """CHECKLIST_SPECS must cover all <checklist> elements in schema.xml."""

    def test_all_schema_checklists_in_python(self, schema_root: ET.Element) -> None:
        checklists_el = schema_root.find("checklists")
        if checklists_el is None:
            pytest.skip("No <checklists> section in schema.xml")
        schema_checklist_ids = {
            cl.get("id") for cl in checklists_el.findall("checklist") if cl.get("id")
        }
        python_checklist_ids = set(CHECKLIST_SPECS.keys())
        assert python_checklist_ids == schema_checklist_ids, (
            f"Checklist mismatch.\n"
            f"In Python only: {python_checklist_ids - schema_checklist_ids}\n"
            f"In schema only: {schema_checklist_ids - python_checklist_ids}"
        )

    def test_checklist_role_refs_match_schema(self, schema_root: ET.Element) -> None:
        checklists_el = schema_root.find("checklists")
        if checklists_el is None:
            return
        for cl in checklists_el.findall("checklist"):
            cl_id = cl.get("id")
            if not cl_id or cl_id not in CHECKLIST_SPECS:
                continue
            spec = CHECKLIST_SPECS[cl_id]
            assert spec.role_ref.value == cl.get("role-ref"), (
                f"Checklist {cl_id} role_ref mismatch: "
                f"Python={spec.role_ref.value!r}, schema={cl.get('role-ref')!r}"
            )

    def test_checklist_gate_matches_schema(self, schema_root: ET.Element) -> None:
        checklists_el = schema_root.find("checklists")
        if checklists_el is None:
            return
        for cl in checklists_el.findall("checklist"):
            cl_id = cl.get("id")
            if not cl_id or cl_id not in CHECKLIST_SPECS:
                continue
            spec = CHECKLIST_SPECS[cl_id]
            assert spec.gate.value == cl.get("gate"), (
                f"Checklist {cl_id} gate mismatch: "
                f"Python={spec.gate.value!r}, schema={cl.get('gate')!r}"
            )

    def test_checklist_item_counts_match_schema(self, schema_root: ET.Element) -> None:
        checklists_el = schema_root.find("checklists")
        if checklists_el is None:
            return
        for cl in checklists_el.findall("checklist"):
            cl_id = cl.get("id")
            if not cl_id or cl_id not in CHECKLIST_SPECS:
                continue
            schema_count = len(cl.findall("item"))
            python_count = len(CHECKLIST_SPECS[cl_id].items)
            assert python_count == schema_count, (
                f"Checklist {cl_id} item count mismatch: "
                f"Python={python_count}, schema={schema_count}"
            )


# ─── COORDINATION_COMMANDS sync tests ─────────────────────────────────────────


class TestCoordinationCommandsMatchSchema:
    """COORDINATION_COMMANDS must cover all <coord-cmd> elements in schema.xml."""

    def test_all_schema_coord_cmds_in_python(self, schema_root: ET.Element) -> None:
        coord_el = schema_root.find("coordination-commands")
        if coord_el is None:
            pytest.skip("No <coordination-commands> section in schema.xml")
        schema_cmd_ids = {
            cmd.get("id") for cmd in coord_el.findall("coord-cmd") if cmd.get("id")
        }
        python_cmd_ids = set(COORDINATION_COMMANDS.keys())
        assert python_cmd_ids == schema_cmd_ids, (
            f"Coordination command mismatch.\n"
            f"In Python only: {python_cmd_ids - schema_cmd_ids}\n"
            f"In schema only: {schema_cmd_ids - python_cmd_ids}"
        )

    def test_shared_flag_matches_schema(self, schema_root: ET.Element) -> None:
        coord_el = schema_root.find("coordination-commands")
        if coord_el is None:
            return
        for cmd in coord_el.findall("coord-cmd"):
            cid = cmd.get("id")
            if not cid or cid not in COORDINATION_COMMANDS:
                continue
            spec = COORDINATION_COMMANDS[cid]
            schema_shared = cmd.get("shared", "false").lower() == "true"
            assert spec.shared == schema_shared, (
                f"Coordination command {cid} shared flag mismatch: "
                f"Python={spec.shared!r}, schema={schema_shared!r}"
            )

    def test_action_matches_schema(self, schema_root: ET.Element) -> None:
        coord_el = schema_root.find("coordination-commands")
        if coord_el is None:
            return
        for cmd in coord_el.findall("coord-cmd"):
            cid = cmd.get("id")
            if not cid or cid not in COORDINATION_COMMANDS:
                continue
            spec = COORDINATION_COMMANDS[cid]
            assert spec.action == cmd.get("action"), (
                f"Coordination command {cid} action mismatch: "
                f"Python={spec.action!r}, schema={cmd.get('action')!r}"
            )


# ─── WORKFLOW_SPECS sync tests ─────────────────────────────────────────────────


class TestWorkflowSpecsMatchSchema:
    """WORKFLOW_SPECS must cover all <workflow> elements in schema.xml."""

    def test_all_schema_workflows_in_python(self, schema_root: ET.Element) -> None:
        workflows_el = schema_root.find("workflows")
        if workflows_el is None:
            pytest.skip("No <workflows> section in schema.xml")
        schema_wf_ids = {
            wf.get("id") for wf in workflows_el.findall("workflow") if wf.get("id")
        }
        python_wf_ids = set(WORKFLOW_SPECS.keys())
        assert python_wf_ids == schema_wf_ids, (
            f"Workflow mismatch.\n"
            f"In Python only: {python_wf_ids - schema_wf_ids}\n"
            f"In schema only: {schema_wf_ids - python_wf_ids}"
        )

    def test_workflow_role_refs_match_schema(self, schema_root: ET.Element) -> None:
        workflows_el = schema_root.find("workflows")
        if workflows_el is None:
            return
        for wf in workflows_el.findall("workflow"):
            wid = wf.get("id")
            if not wid or wid not in WORKFLOW_SPECS:
                continue
            spec = WORKFLOW_SPECS[wid]
            assert spec.role_ref.value == wf.get("role-ref"), (
                f"Workflow {wid} role_ref mismatch: "
                f"Python={spec.role_ref.value!r}, schema={wf.get('role-ref')!r}"
            )

    def test_workflow_stage_counts_match_schema(self, schema_root: ET.Element) -> None:
        workflows_el = schema_root.find("workflows")
        if workflows_el is None:
            return
        for wf in workflows_el.findall("workflow"):
            wid = wf.get("id")
            if not wid or wid not in WORKFLOW_SPECS:
                continue
            schema_stage_count = len(wf.findall("stage"))
            python_stage_count = len(WORKFLOW_SPECS[wid].stages)
            assert python_stage_count == schema_stage_count, (
                f"Workflow {wid} stage count mismatch: "
                f"Python={python_stage_count}, schema={schema_stage_count}"
            )


# ─── ConstraintSpec.command sync tests ────────────────────────────────────────


class TestConstraintSpecCommandSync:
    """ConstraintSpec.command field must match schema.xml constraint command= attribute."""

    def test_constraints_with_command_match_schema(
        self, schema_root: ET.Element
    ) -> None:
        """For constraints with command= attribute in schema.xml, verify Python has it."""
        for c in schema_root.iter("constraint"):
            cid = c.get("id")
            schema_command = c.get("command")
            if not cid or cid not in CONSTRAINT_SPECS:
                continue
            spec = CONSTRAINT_SPECS[cid]
            assert spec.command == schema_command, (
                f"Constraint {cid} command mismatch: "
                f"Python={spec.command!r}, schema={schema_command!r}"
            )

    def test_constraint_without_command_is_none(
        self, schema_root: ET.Element
    ) -> None:
        """Constraints without command= attribute in schema.xml have command=None."""
        for c in schema_root.iter("constraint"):
            cid = c.get("id")
            if not cid or c.get("command") is not None:
                continue
            if cid not in CONSTRAINT_SPECS:
                continue
            spec = CONSTRAINT_SPECS[cid]
            assert spec.command is None, (
                f"Constraint {cid} should have command=None "
                f"(no command= in schema.xml), got {spec.command!r}"
            )


# ─── RoleSpec new fields sync tests ───────────────────────────────────────────


class TestRoleSpecNewFieldsSync:
    """RoleSpec.introduction, ownership_narrative, and behaviors must match schema.xml."""

    def test_roles_with_introduction_have_text(self) -> None:
        """All 5 roles should have introduction text set (non-None, non-empty)."""
        roles_without = [
            role_id
            for role_id, spec in ROLE_SPECS.items()
            if not spec.introduction
        ]
        assert not roles_without, (
            f"These roles are missing introduction text: {roles_without}"
        )

    def test_roles_with_ownership_narrative(self) -> None:
        """All 5 roles should have ownership_narrative set."""
        roles_without = [
            role_id
            for role_id, spec in ROLE_SPECS.items()
            if not spec.ownership_narrative
        ]
        assert not roles_without, (
            f"These roles are missing ownership_narrative: {roles_without}"
        )

    def test_role_introduction_matches_schema(
        self, schema_root: ET.Element
    ) -> None:
        """RoleSpec.introduction matches <introduction> child element text in schema.xml."""
        for role in schema_root.find("roles").findall("role"):  # type: ignore[union-attr]
            rid_str = role.get("id")
            if not rid_str:
                continue
            try:
                rid = RoleId(rid_str)
            except ValueError:
                continue
            if rid not in ROLE_SPECS:
                continue
            intro_el = role.find("introduction")
            schema_intro = intro_el.text.strip() if intro_el is not None and intro_el.text else None
            spec = ROLE_SPECS[rid]
            assert spec.introduction == schema_intro, (
                f"Role {rid_str} introduction mismatch: "
                f"Python={spec.introduction!r}, schema={schema_intro!r}"
            )

    def test_role_behaviors_count_matches_schema(
        self, schema_root: ET.Element
    ) -> None:
        """RoleSpec.behaviors count matches number of <behavior> children in schema.xml."""
        for role in schema_root.find("roles").findall("role"):  # type: ignore[union-attr]
            rid_str = role.get("id")
            if not rid_str:
                continue
            try:
                rid = RoleId(rid_str)
            except ValueError:
                continue
            if rid not in ROLE_SPECS:
                continue
            behaviors_el = role.find("behaviors")
            schema_count = (
                len(behaviors_el.findall("behavior"))
                if behaviors_el is not None
                else 0
            )
            python_count = len(ROLE_SPECS[rid].behaviors)
            assert python_count == schema_count, (
                f"Role {rid_str} behaviors count mismatch: "
                f"Python={python_count}, schema={schema_count}"
            )


# ─── Figure Sync ─────────────────────────────────────────────────────────────


class TestFigureSpecsSync:
    """FIGURE_SPECS must stay in sync with FigureId enum and schema.xml."""

    def test_all_figure_workflow_refs_valid(self) -> None:
        """Every workflow_ref in FIGURE_SPECS must exist as a key in WORKFLOW_SPECS."""
        for fig_id, fig in FIGURE_SPECS.items():
            for wref in fig.workflow_refs:
                assert wref in WORKFLOW_SPECS, (
                    f"Figure {fig_id.value} references workflow '{wref}' "
                    f"which is not a key in WORKFLOW_SPECS"
                )

    def test_all_figure_role_refs_valid(self) -> None:
        """Every role_ref in FIGURE_SPECS must be a valid RoleId member."""
        for fig_id, fig in FIGURE_SPECS.items():
            for rref in fig.role_refs:
                assert isinstance(rref, RoleId), (
                    f"Figure {fig_id.value} has role_ref {rref!r} "
                    f"which is not a RoleId member"
                )

    def test_figure_type_values_in_schema(self, schema_root: ET.Element) -> None:
        """Each <figure type='...'> value in schema.xml must be a valid FigureType."""
        for fig_el in schema_root.iter("figure"):
            fig_type = fig_el.get("type")
            if fig_type is None:
                continue
            assert fig_type in {ft.value for ft in FigureType}, (
                f"schema.xml <figure> has type='{fig_type}' "
                f"which is not a valid FigureType member"
            )

    def test_figure_count_matches_schema(self, schema_root: ET.Element) -> None:
        """Count of <figure> elements in schema.xml must equal len(FIGURE_SPECS)."""
        schema_count = len(list(schema_root.iter("figure")))
        python_count = len(FIGURE_SPECS)
        assert python_count == schema_count, (
            f"Figure count mismatch: Python has {python_count}, "
            f"schema.xml has {schema_count}"
        )

    def test_figure_id_enum_matches_specs(self) -> None:
        """Set of FigureId members must equal set of FIGURE_SPECS keys."""
        enum_members = set(FigureId)
        spec_keys = set(FIGURE_SPECS.keys())
        assert enum_members == spec_keys, (
            f"FigureId enum members do not match FIGURE_SPECS keys.\n"
            f"In enum only: {enum_members - spec_keys}\n"
            f"In specs only: {spec_keys - enum_members}"
        )

    def test_all_figure_command_refs_valid(self) -> None:
        """Every command_ref in FIGURE_SPECS must be a valid CommandId member."""
        for fig_id, fig in FIGURE_SPECS.items():
            for cref in fig.command_refs:
                assert isinstance(cref, CommandId), (
                    f"Figure {fig_id.value} has command_ref {cref!r} "
                    f"which is not a CommandId member"
                )


# ─── CommandId + COMMAND_SPECS Sync ──────────────────────────────────────────


class TestCommandIdSync:
    """CommandId enum must stay in sync with COMMAND_SPECS keys."""

    def test_command_id_values_match_command_specs_keys(self) -> None:
        """Set of CommandId values must equal set of COMMAND_SPECS keys."""
        enum_values = {c.value for c in CommandId}
        spec_keys = set(COMMAND_SPECS.keys())
        assert enum_values == spec_keys, (
            f"CommandId values do not match COMMAND_SPECS keys.\n"
            f"In enum only: {enum_values - spec_keys}\n"
            f"In specs only: {spec_keys - enum_values}"
        )

    def test_command_specs_keys_are_command_id_instances(self) -> None:
        """Every key in COMMAND_SPECS must be a CommandId instance (not bare str)."""
        for key in COMMAND_SPECS:
            assert isinstance(key, CommandId), (
                f"COMMAND_SPECS key {key!r} is {type(key).__name__}, "
                f"expected CommandId instance"
            )

    def test_command_id_count_matches_specs(self) -> None:
        """Number of CommandId members must equal number of COMMAND_SPECS entries."""
        enum_count = len(CommandId)
        spec_count = len(COMMAND_SPECS)
        assert enum_count == spec_count, (
            f"CommandId has {enum_count} members but COMMAND_SPECS has {spec_count} entries"
        )
