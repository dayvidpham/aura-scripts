"""Tests for aura_protocol.gen_schema — schema.xml generator.

Acceptance criteria covered:
- AC2:  gen_schema.py output passes validate_schema.py with 0 errors
- AC2a: Prints unified diff of changes before writing (UAT-2)
- AC2b: schema.xml constraint elements include role-ref and phase-ref attributes (UAT-3)
- AC3:  Round-trip consistency — types.py → gen_schema → parse_schema → field-by-field match
- AC7:  All existing tests continue to pass (verified by running full test suite)
"""

from __future__ import annotations

import io
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from aura_protocol import (
    COMMAND_SPECS,
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    LABEL_SPECS,
    PHASE_SPECS,
    PROCEDURE_STEPS,
    REVIEW_AXIS_SPECS,
    ROLE_SPECS,
    TITLE_CONVENTIONS,
    RoleId,
)
from aura_protocol.gen_schema import (
    _CONSTRAINT_TO_PHASE_REF,
    _CONSTRAINT_TO_ROLE_REF,
    generate_schema,
)
from aura_protocol.gen_skills import GENERATED_BEGIN, GENERATED_END, generate_skill
from aura_protocol.gen_types import generate_types_source
from aura_protocol.schema_parser import parse_schema


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def generated_schema_path(tmp_path_factory) -> Path:
    """Generate schema.xml once for the entire module (no diff output)."""
    out = tmp_path_factory.mktemp("schema") / "schema.xml"
    generate_schema(out, diff=False)
    return out


@pytest.fixture(scope="module")
def generated_xml_root(generated_schema_path: Path) -> ET.Element:
    """Parse the generated XML once for the module."""
    tree = ET.parse(generated_schema_path)
    return tree.getroot()


@pytest.fixture(scope="module")
def parsed_spec(generated_schema_path: Path):
    """Parse the generated schema via schema_parser (round-trip)."""
    return parse_schema(generated_schema_path)


# ─── AC2: Validation passes ───────────────────────────────────────────────────


class TestValidationPasses:
    """AC2: gen_schema.py output passes validate_schema.py with 0 errors."""

    def test_generated_schema_passes_validate_schema(
        self, generated_schema_path: Path
    ) -> None:
        """The generated schema.xml must pass all validate_schema.py checks."""
        # Import validate from scripts (added to pythonpath by pytest)
        from validate_schema import validate  # type: ignore[import]

        errors = validate(generated_schema_path)
        assert errors == [], (
            f"validate_schema.py found {len(errors)} error(s):\n"
            + "\n".join(f"  {e}" for e in errors)
        )

    def test_generated_xml_is_parseable(self, generated_schema_path: Path) -> None:
        """The generated file must be valid XML."""
        tree = ET.parse(generated_schema_path)
        root = tree.getroot()
        assert root.tag == "aura-protocol"
        assert root.get("version") == "2.0"

    def test_generated_schema_has_all_top_level_sections(
        self, generated_xml_root: ET.Element
    ) -> None:
        """All required top-level sections must be present."""
        required_sections = [
            "enums", "labels", "review-axes", "phases", "roles",
            "commands", "handoffs", "constraints", "task-titles",
            "documents", "dependency-model", "followup-lifecycle",
            "procedure-steps",
        ]
        for section in required_sections:
            assert generated_xml_root.find(section) is not None, (
                f"Missing top-level section <{section}> in generated schema.xml"
            )


# ─── AC2a: Diff output ────────────────────────────────────────────────────────


class TestDiffOutput:
    """AC2a: Prints unified diff of changes before writing (UAT-2)."""

    def test_diff_shown_when_file_exists_and_changed(self, tmp_path: Path) -> None:
        """When an existing file differs, a unified diff is printed to stdout."""
        output = tmp_path / "schema.xml"
        # First write with a custom content to establish "old" file
        output.write_text("<root>old content</root>\n", encoding="UTF-8")

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            generate_schema(output, diff=True)
        finally:
            sys.stdout = old_stdout

        diff_output = captured.getvalue()
        # Verify real changed lines are present (not just the header '--- Unified diff...')
        # At least one line must start with '+' or '-' excluding the '---'/'+++' file headers
        diff_lines = diff_output.splitlines()
        real_diff_lines = [
            ln for ln in diff_lines
            if (ln.startswith("+") or ln.startswith("-"))
            and not ln.startswith("---")
            and not ln.startswith("+++")
        ]
        assert len(real_diff_lines) > 0, (
            "Expected at least one real diff line (starting with '+' or '-') "
            "in unified diff output when file content changed, "
            f"got: {diff_output[:300]!r}"
        )

    def test_no_diff_when_content_unchanged(self, tmp_path: Path) -> None:
        """When content is identical, 'No changes' message is printed."""
        output = tmp_path / "schema.xml"
        # First generate
        generate_schema(output, diff=False)

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            generate_schema(output, diff=True)
        finally:
            sys.stdout = old_stdout

        diff_output = captured.getvalue()
        assert "No changes" in diff_output, (
            f"Expected 'No changes' message when content unchanged, "
            f"got: {diff_output[:200]!r}"
        )

    def test_no_diff_when_diff_disabled(self, tmp_path: Path) -> None:
        """When diff=False, no output is produced."""
        output = tmp_path / "schema.xml"
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            generate_schema(output, diff=False)
        finally:
            sys.stdout = old_stdout

        diff_output = captured.getvalue()
        assert diff_output == "", (
            f"Expected no stdout output when diff=False, "
            f"got: {diff_output[:200]!r}"
        )

    def test_diff_output_is_unified_format(self, tmp_path: Path) -> None:
        """Diff output uses unified diff format (--- / +++ / @@ headers)."""
        output = tmp_path / "schema.xml"
        output.write_text("<?xml version='1.0'?><root/>", encoding="UTF-8")

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            generate_schema(output, diff=True)
        finally:
            sys.stdout = old_stdout

        diff_output = captured.getvalue()
        # Check for at least one unified diff line marker
        has_diff = any(
            marker in diff_output
            for marker in ["---", "+++", "@@", "No changes"]
        )
        assert has_diff, (
            f"Diff output does not look like unified diff format: "
            f"{diff_output[:500]!r}"
        )


# ─── Procedure-steps section ──────────────────────────────────────────────────


class TestProcedureStepsSection:
    """Verify <procedure-steps> section is generated with correct structure."""

    def test_procedure_steps_section_exists(
        self, generated_xml_root: ET.Element
    ) -> None:
        """The generated XML must contain a <procedure-steps> section."""
        proc_el = generated_xml_root.find("procedure-steps")
        assert proc_el is not None, (
            "Missing <procedure-steps> section in generated schema.xml"
        )

    def test_supervisor_role_in_procedure_steps(
        self, generated_xml_root: ET.Element
    ) -> None:
        """<procedure-steps> must contain a <role ref='supervisor'> with steps."""
        proc_el = generated_xml_root.find("procedure-steps")
        assert proc_el is not None

        roles = {r.get("ref"): r for r in proc_el.findall("role")}
        assert "supervisor" in roles, (
            "Missing <role ref='supervisor'> in <procedure-steps>"
        )
        sup_role = roles["supervisor"]
        steps = sup_role.findall("step")
        assert len(steps) == len(PROCEDURE_STEPS[RoleId.SUPERVISOR]), (
            f"Supervisor step count mismatch: "
            f"XML={len(steps)}, Python={len(PROCEDURE_STEPS[RoleId.SUPERVISOR])}"
        )
        # Verify first step has id and order attributes, and <instruction> child element
        first_step = steps[0]
        assert first_step.get("id") is not None, (
            "First supervisor step missing 'id' attribute"
        )
        assert first_step.get("order") == "1", (
            f"First supervisor step order should be '1', got {first_step.get('order')!r}"
        )
        instr_el = first_step.find("instruction")
        assert instr_el is not None and instr_el.text, (
            "First supervisor step missing <instruction> child element"
        )

    def test_worker_role_in_procedure_steps(
        self, generated_xml_root: ET.Element
    ) -> None:
        """<procedure-steps> must contain a <role ref='worker'> with steps."""
        proc_el = generated_xml_root.find("procedure-steps")
        assert proc_el is not None

        roles = {r.get("ref"): r for r in proc_el.findall("role")}
        assert "worker" in roles, (
            "Missing <role ref='worker'> in <procedure-steps>"
        )
        worker_role = roles["worker"]
        steps = worker_role.findall("step")
        assert len(steps) == len(PROCEDURE_STEPS[RoleId.WORKER]), (
            f"Worker step count mismatch: "
            f"XML={len(steps)}, Python={len(PROCEDURE_STEPS[RoleId.WORKER])}"
        )

    def test_empty_roles_excluded(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Roles with empty PROCEDURE_STEPS must not appear in <procedure-steps>."""
        proc_el = generated_xml_root.find("procedure-steps")
        assert proc_el is not None

        role_refs = {r.get("ref") for r in proc_el.findall("role")}
        for role_id, steps in PROCEDURE_STEPS.items():
            if not steps:
                assert role_id.value not in role_refs, (
                    f"Role {role_id.value!r} has empty PROCEDURE_STEPS "
                    f"but appears in <procedure-steps> XML"
                )

    def test_optional_child_elements_present_when_set(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Steps with command/context in Python emit those as child elements; next-state as attribute."""
        proc_el = generated_xml_root.find("procedure-steps")
        assert proc_el is not None

        sup_role = None
        for r in proc_el.findall("role"):
            if r.get("ref") == "supervisor":
                sup_role = r
                break
        assert sup_role is not None

        xml_steps = sup_role.findall("step")
        python_steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        for xml_step, py_step in zip(xml_steps, python_steps):
            # id and order are XML attributes
            assert xml_step.get("id") == py_step.id, (
                f"Step {py_step.order} id mismatch: "
                f"XML={xml_step.get('id')!r}, Python={py_step.id!r}"
            )
            # instruction is always a child element
            instr_el = xml_step.find("instruction")
            assert instr_el is not None and instr_el.text is not None, (
                f"Step {py_step.order} missing <instruction> child element"
            )
            assert instr_el.text.strip() == py_step.instruction, (
                f"Step {py_step.order} instruction mismatch"
            )
            # command: child element when set, absent when None
            cmd_el = xml_step.find("command")
            if py_step.command is not None:
                assert cmd_el is not None and cmd_el.text is not None, (
                    f"Step {py_step.order} missing <command> child element"
                )
                assert cmd_el.text.strip() == py_step.command, (
                    f"Step {py_step.order} command mismatch"
                )
            else:
                assert cmd_el is None, (
                    f"Step {py_step.order} should not have <command> child element"
                )
            # context: child element when set, absent when None
            ctx_el = xml_step.find("context")
            if py_step.context is not None:
                assert ctx_el is not None and ctx_el.text is not None, (
                    f"Step {py_step.order} missing <context> child element"
                )
                assert ctx_el.text.strip() == py_step.context, (
                    f"Step {py_step.order} context mismatch"
                )
            else:
                assert ctx_el is None, (
                    f"Step {py_step.order} should not have <context> child element"
                )
            # next-state: XML attribute when set, absent when None
            ns_attr = xml_step.get("next-state")
            if py_step.next_state is not None:
                assert ns_attr is not None, (
                    f"Step {py_step.order} missing next-state attribute"
                )
                assert ns_attr == py_step.next_state.value, (
                    f"Step {py_step.order} next-state mismatch"
                )
            else:
                assert ns_attr is None, (
                    f"Step {py_step.order} should not have next-state attribute"
                )


# ─── No-changes message ──────────────────────────────────────────────────────


class TestNoChangesMessage:
    """Verify 'No changes' message when schema content is unchanged."""

    def test_no_changes_on_second_generate(self, tmp_path: Path) -> None:
        """Running generate_schema twice should print 'No changes' on second run."""
        output = tmp_path / "schema.xml"
        # First generate (creates the file)
        generate_schema(output, diff=False)

        # Second generate with diff=True (should detect no changes)
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            generate_schema(output, diff=True)
        finally:
            sys.stdout = old_stdout

        diff_output = captured.getvalue()
        assert "No changes" in diff_output, (
            f"Expected 'No changes' message on second generate, "
            f"got: {diff_output[:300]!r}"
        )
        assert "up to date" in diff_output, (
            f"Expected 'up to date' in no-changes message, "
            f"got: {diff_output[:300]!r}"
        )


# ─── AC2b: role-ref/phase-ref on constraint elements ─────────────────────────


class TestConstraintRolePhaseRefs:
    """AC2b: schema.xml constraint elements include role-ref and phase-ref attributes (UAT-3)."""

    def test_constraints_have_role_ref_when_defined(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Constraints with role-ref in _CONSTRAINT_TO_ROLE_REF have role-ref attribute in XML."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None, "<constraints> section missing"

        for constraint in constraints_el.findall("constraint"):
            cid = constraint.get("id")
            if cid is None:
                continue
            expected_role = _CONSTRAINT_TO_ROLE_REF.get(cid)
            xml_role = constraint.get("role-ref")
            assert xml_role == expected_role, (
                f"Constraint {cid!r}: expected role-ref={expected_role!r}, "
                f"got role-ref={xml_role!r}"
            )

    def test_constraints_have_phase_ref_when_defined(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Constraints with phase-ref in _CONSTRAINT_TO_PHASE_REF have phase-ref attribute in XML."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None, "<constraints> section missing"

        for constraint in constraints_el.findall("constraint"):
            cid = constraint.get("id")
            if cid is None:
                continue
            expected_phase = _CONSTRAINT_TO_PHASE_REF.get(cid)
            xml_phase = constraint.get("phase-ref")
            assert xml_phase == expected_phase, (
                f"Constraint {cid!r}: expected phase-ref={expected_phase!r}, "
                f"got phase-ref={xml_phase!r}"
            )

    def test_at_least_some_constraints_have_role_ref(
        self, generated_xml_root: ET.Element
    ) -> None:
        """At least one constraint must have a role-ref attribute."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None

        role_refs = [
            c.get("role-ref")
            for c in constraints_el.findall("constraint")
            if c.get("role-ref") is not None
        ]
        assert len(role_refs) > 0, (
            "Expected at least one constraint with role-ref attribute"
        )

    def test_at_least_some_constraints_have_phase_ref(
        self, generated_xml_root: ET.Element
    ) -> None:
        """At least one constraint must have a phase-ref attribute."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None

        phase_refs = [
            c.get("phase-ref")
            for c in constraints_el.findall("constraint")
            if c.get("phase-ref") is not None
        ]
        assert len(phase_refs) > 0, (
            "Expected at least one constraint with phase-ref attribute"
        )

    def test_role_ref_values_are_valid_role_ids(
        self, generated_xml_root: ET.Element
    ) -> None:
        """role-ref values on constraints must be valid role IDs (comma-separated allowed)."""
        valid_role_ids = {r.value for r in RoleId}
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None

        for constraint in constraints_el.findall("constraint"):
            role_ref = constraint.get("role-ref")
            if role_ref is not None:
                # role-ref may be comma-separated (multi-value, e.g. "reviewer,supervisor")
                for part in role_ref.split(","):
                    part = part.strip()
                    assert part in valid_role_ids, (
                        f"Constraint {constraint.get('id')!r} has invalid "
                        f"role-ref part={part!r} in role-ref={role_ref!r}. "
                        f"Valid: {sorted(valid_role_ids)}"
                    )

    def test_known_role_specific_constraints(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Specific well-known constraints must have correct role-ref values."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None

        by_id: dict[str, ET.Element] = {}
        for c in constraints_el.findall("constraint"):
            cid = c.get("id")
            if cid:
                by_id[cid] = c

        # Supervisor-only constraints (not shared with epoch)
        supervisor_only_constraints = [
            "C-supervisor-no-impl",
            "C-slice-leaf-tasks",
            "C-vertical-slices",
        ]
        for cid in supervisor_only_constraints:
            if cid in by_id:
                assert by_id[cid].get("role-ref") == "supervisor", (
                    f"{cid} should have role-ref='supervisor', "
                    f"got {by_id[cid].get('role-ref')!r}"
                )

        # Ride the Wave constraints shared between epoch and supervisor
        ride_the_wave_constraints = [
            "C-supervisor-cartographers",
            "C-integration-points",
            "C-slice-review-before-close",
            "C-max-review-cycles",
        ]
        for cid in ride_the_wave_constraints:
            if cid in by_id:
                role_ref = by_id[cid].get("role-ref", "")
                role_parts = set(role_ref.split(","))
                assert "supervisor" in role_parts, (
                    f"{cid} should include 'supervisor' in role-ref, "
                    f"got {role_ref!r}"
                )
                assert "epoch" in role_parts, (
                    f"{cid} should include 'epoch' in role-ref (Ride the Wave), "
                    f"got {role_ref!r}"
                )

        # Worker-specific constraint
        if "C-worker-gates" in by_id:
            assert by_id["C-worker-gates"].get("role-ref") == "worker", (
                "C-worker-gates should have role-ref='worker'"
            )

        # Reviewer-specific constraints
        reviewer_constraints = ["C-review-binary", "C-severity-eager"]
        for cid in reviewer_constraints:
            if cid in by_id:
                assert by_id[cid].get("role-ref") == "reviewer", (
                    f"{cid} should have role-ref='reviewer', "
                    f"got {by_id[cid].get('role-ref')!r}"
                )


# ─── AC3: Round-trip consistency ──────────────────────────────────────────────


class TestRoundTripConsistency:
    """AC3: types.py → gen_schema → parse_schema → field-by-field match."""

    def test_roundtrip_phase_count(self, parsed_spec) -> None:
        """Round-trip: phase count matches PHASE_SPECS."""
        # PHASE_SPECS has 12 phases (excludes COMPLETE sentinel)
        expected = sum(1 for _ in PHASE_SPECS)
        assert len(parsed_spec.phases) == expected, (
            f"Round-trip phase count mismatch: "
            f"parsed={len(parsed_spec.phases)}, expected={expected}"
        )

    def test_roundtrip_phase_ids(self, parsed_spec) -> None:
        """Round-trip: all phase IDs from PHASE_SPECS appear in parsed schema."""
        python_phase_ids = {spec.id.value for spec in PHASE_SPECS.values()}
        parsed_phase_ids = set(parsed_spec.phases)
        assert python_phase_ids == parsed_phase_ids, (
            f"Round-trip phase ID mismatch.\n"
            f"In Python only: {python_phase_ids - parsed_phase_ids}\n"
            f"In parsed only: {parsed_phase_ids - python_phase_ids}"
        )

    def test_roundtrip_phase_ordering(self, parsed_spec) -> None:
        """Round-trip: phases are in sequential numeric order p1..p12."""
        expected_order = [f"p{i}" for i in range(1, 13)]
        assert list(parsed_spec.phases) == expected_order, (
            f"Round-trip phase ordering mismatch: {list(parsed_spec.phases)}"
        )

    def test_roundtrip_role_count(self, parsed_spec) -> None:
        """Round-trip: role count matches ROLE_SPECS."""
        assert len(parsed_spec.roles) == len(ROLE_SPECS), (
            f"Round-trip role count mismatch: "
            f"parsed={len(parsed_spec.roles)}, expected={len(ROLE_SPECS)}"
        )

    def test_roundtrip_role_ids(self, parsed_spec) -> None:
        """Round-trip: all RoleId values appear in parsed schema roles."""
        python_role_ids = set(ROLE_SPECS.keys())
        parsed_role_ids = set(parsed_spec.roles.keys())
        assert python_role_ids == parsed_role_ids, (
            f"Round-trip role ID mismatch.\n"
            f"In Python only: {python_role_ids - parsed_role_ids}\n"
            f"In parsed only: {parsed_role_ids - python_role_ids}"
        )

    def test_roundtrip_role_names_match(self, parsed_spec) -> None:
        """Round-trip: role names match field-by-field."""
        for role_id, python_spec in ROLE_SPECS.items():
            parsed_role = parsed_spec.roles.get(role_id)
            assert parsed_role is not None, (
                f"Role {role_id} missing from parsed schema"
            )
            assert parsed_role.name == python_spec.name, (
                f"Role {role_id} name mismatch: "
                f"parsed={parsed_role.name!r}, python={python_spec.name!r}"
            )

    def test_roundtrip_role_owned_phases_match(self, parsed_spec) -> None:
        """Round-trip: role owned_phases match field-by-field."""
        for role_id, python_spec in ROLE_SPECS.items():
            parsed_role = parsed_spec.roles.get(role_id)
            assert parsed_role is not None, f"Role {role_id} missing"
            assert parsed_role.owned_phases == python_spec.owned_phases, (
                f"Role {role_id} owned_phases mismatch:\n"
                f"  parsed:  {sorted(parsed_role.owned_phases)}\n"
                f"  python:  {sorted(python_spec.owned_phases)}"
            )

    def test_roundtrip_command_count(self, parsed_spec) -> None:
        """Round-trip: command count matches COMMAND_SPECS."""
        assert len(parsed_spec.commands) == len(COMMAND_SPECS), (
            f"Round-trip command count mismatch: "
            f"parsed={len(parsed_spec.commands)}, expected={len(COMMAND_SPECS)}"
        )

    def test_roundtrip_command_ids(self, parsed_spec) -> None:
        """Round-trip: all command IDs from COMMAND_SPECS appear in parsed schema."""
        python_ids = set(COMMAND_SPECS.keys())
        parsed_ids = set(parsed_spec.commands.keys())
        assert python_ids == parsed_ids, (
            f"Round-trip command ID mismatch.\n"
            f"In Python only: {python_ids - parsed_ids}\n"
            f"In parsed only: {parsed_ids - python_ids}"
        )

    def test_roundtrip_command_names_match(self, parsed_spec) -> None:
        """Round-trip: command names match field-by-field."""
        for cid, python_spec in COMMAND_SPECS.items():
            parsed_cmd = parsed_spec.commands.get(cid)
            assert parsed_cmd is not None, f"Command {cid} missing from parsed schema"
            assert parsed_cmd.name == python_spec.name, (
                f"Command {cid} name mismatch: "
                f"parsed={parsed_cmd.name!r}, python={python_spec.name!r}"
            )

    def test_roundtrip_command_role_refs_match(self, parsed_spec) -> None:
        """Round-trip: command role_refs match field-by-field."""
        for cid, python_spec in COMMAND_SPECS.items():
            parsed_cmd = parsed_spec.commands.get(cid)
            if parsed_cmd is None:
                continue
            assert parsed_cmd.role_ref == python_spec.role_ref, (
                f"Command {cid} role_ref mismatch: "
                f"parsed={parsed_cmd.role_ref!r}, python={python_spec.role_ref!r}"
            )

    def test_roundtrip_command_phases_match(self, parsed_spec) -> None:
        """Round-trip: command phases match field-by-field."""
        for cid, python_spec in COMMAND_SPECS.items():
            parsed_cmd = parsed_spec.commands.get(cid)
            if parsed_cmd is None:
                continue
            assert set(parsed_cmd.phases) == set(python_spec.phases), (
                f"Command {cid} phases mismatch: "
                f"parsed={sorted(parsed_cmd.phases)}, "
                f"python={sorted(python_spec.phases)}"
            )

    def test_roundtrip_constraint_count(self, parsed_spec) -> None:
        """Round-trip: constraint count matches CONSTRAINT_SPECS."""
        assert len(parsed_spec.constraints) == len(CONSTRAINT_SPECS), (
            f"Round-trip constraint count mismatch: "
            f"parsed={len(parsed_spec.constraints)}, expected={len(CONSTRAINT_SPECS)}"
        )

    def test_roundtrip_constraint_ids(self, parsed_spec) -> None:
        """Round-trip: all constraint IDs from CONSTRAINT_SPECS appear in parsed schema."""
        python_ids = set(CONSTRAINT_SPECS.keys())
        parsed_ids = set(parsed_spec.constraints.keys())
        assert python_ids == parsed_ids, (
            f"Round-trip constraint ID mismatch.\n"
            f"In Python only: {python_ids - parsed_ids}\n"
            f"In parsed only: {parsed_ids - python_ids}"
        )

    def test_roundtrip_constraint_fields_match(self, parsed_spec) -> None:
        """Round-trip: constraint given/when/then/should-not match field-by-field."""
        for cid, python_spec in CONSTRAINT_SPECS.items():
            parsed_constraint = parsed_spec.constraints.get(cid)
            assert parsed_constraint is not None, (
                f"Constraint {cid} missing from parsed schema"
            )
            assert parsed_constraint.given == python_spec.given, (
                f"Constraint {cid} 'given' mismatch: "
                f"parsed={parsed_constraint.given!r}, python={python_spec.given!r}"
            )
            assert parsed_constraint.when == python_spec.when, (
                f"Constraint {cid} 'when' mismatch: "
                f"parsed={parsed_constraint.when!r}, python={python_spec.when!r}"
            )
            assert parsed_constraint.then == python_spec.then, (
                f"Constraint {cid} 'then' mismatch: "
                f"parsed={parsed_constraint.then!r}, python={python_spec.then!r}"
            )
            assert parsed_constraint.should_not == python_spec.should_not, (
                f"Constraint {cid} 'should-not' mismatch: "
                f"parsed={parsed_constraint.should_not!r}, python={python_spec.should_not!r}"
            )

    def test_roundtrip_handoff_count(self, parsed_spec) -> None:
        """Round-trip: handoff count matches HANDOFF_SPECS."""
        assert len(parsed_spec.handoffs) == len(HANDOFF_SPECS), (
            f"Round-trip handoff count mismatch: "
            f"parsed={len(parsed_spec.handoffs)}, expected={len(HANDOFF_SPECS)}"
        )

    def test_roundtrip_handoff_ids(self, parsed_spec) -> None:
        """Round-trip: all handoff IDs from HANDOFF_SPECS appear in parsed schema."""
        python_ids = set(HANDOFF_SPECS.keys())
        parsed_ids = set(parsed_spec.handoffs.keys())
        assert python_ids == parsed_ids, (
            f"Round-trip handoff ID mismatch.\n"
            f"In Python only: {python_ids - parsed_ids}\n"
            f"In parsed only: {parsed_ids - python_ids}"
        )

    def test_roundtrip_handoff_fields_match(self, parsed_spec) -> None:
        """Round-trip: handoff source/target/phase/content fields match."""
        for hid, python_spec in HANDOFF_SPECS.items():
            parsed_h = parsed_spec.handoffs.get(hid)
            assert parsed_h is not None, f"Handoff {hid} missing from parsed schema"
            assert parsed_h.source_role == python_spec.source_role, (
                f"Handoff {hid} source_role mismatch"
            )
            assert parsed_h.target_role == python_spec.target_role, (
                f"Handoff {hid} target_role mismatch"
            )
            assert parsed_h.at_phase == python_spec.at_phase, (
                f"Handoff {hid} at_phase mismatch"
            )
            assert parsed_h.content_level == python_spec.content_level, (
                f"Handoff {hid} content_level mismatch"
            )

    def test_roundtrip_label_count(self, parsed_spec) -> None:
        """Round-trip: label count matches LABEL_SPECS."""
        assert len(parsed_spec.labels) == len(LABEL_SPECS), (
            f"Round-trip label count mismatch: "
            f"parsed={len(parsed_spec.labels)}, expected={len(LABEL_SPECS)}"
        )

    def test_roundtrip_label_ids(self, parsed_spec) -> None:
        """Round-trip: all label IDs from LABEL_SPECS appear in parsed schema."""
        python_ids = set(LABEL_SPECS.keys())
        parsed_ids = set(parsed_spec.labels.keys())
        assert python_ids == parsed_ids, (
            f"Round-trip label ID mismatch.\n"
            f"In Python only: {python_ids - parsed_ids}\n"
            f"In parsed only: {parsed_ids - python_ids}"
        )

    def test_roundtrip_label_values_match(self, parsed_spec) -> None:
        """Round-trip: label values match field-by-field."""
        for lid, python_spec in LABEL_SPECS.items():
            parsed_label = parsed_spec.labels.get(lid)
            assert parsed_label is not None, f"Label {lid} missing from parsed schema"
            assert parsed_label.value == python_spec.value, (
                f"Label {lid} value mismatch: "
                f"parsed={parsed_label.value!r}, python={python_spec.value!r}"
            )
            assert parsed_label.special == python_spec.special, (
                f"Label {lid} special flag mismatch: "
                f"parsed={parsed_label.special!r}, python={python_spec.special!r}"
            )

    def test_roundtrip_review_axis_count(self, parsed_spec) -> None:
        """Round-trip: review axis count matches REVIEW_AXIS_SPECS."""
        assert len(parsed_spec.review_axes) == len(REVIEW_AXIS_SPECS), (
            f"Round-trip review axis count mismatch: "
            f"parsed={len(parsed_spec.review_axes)}, expected={len(REVIEW_AXIS_SPECS)}"
        )

    def test_roundtrip_review_axis_fields_match(self, parsed_spec) -> None:
        """Round-trip: review axis id/letter/name match field-by-field."""
        for aid, python_spec in REVIEW_AXIS_SPECS.items():
            parsed_axis = parsed_spec.review_axes.get(aid)
            assert parsed_axis is not None, f"Review axis {aid} missing from parsed schema"
            assert parsed_axis.letter == python_spec.letter, (
                f"Axis {aid} letter mismatch: "
                f"parsed={parsed_axis.letter!r}, python={python_spec.letter!r}"
            )
            assert parsed_axis.name == python_spec.name, (
                f"Axis {aid} name mismatch"
            )

    def test_roundtrip_title_convention_count(self, parsed_spec) -> None:
        """Round-trip: title convention count matches TITLE_CONVENTIONS."""
        assert len(parsed_spec.title_conventions) == len(TITLE_CONVENTIONS), (
            f"Round-trip title convention count mismatch: "
            f"parsed={len(parsed_spec.title_conventions)}, "
            f"expected={len(TITLE_CONVENTIONS)}"
        )

    def test_roundtrip_title_convention_patterns_match(self, parsed_spec) -> None:
        """Round-trip: title convention patterns all present."""
        python_patterns = {tc.pattern for tc in TITLE_CONVENTIONS}
        parsed_patterns = {tc.pattern for tc in parsed_spec.title_conventions}
        assert python_patterns == parsed_patterns, (
            f"Round-trip title convention pattern mismatch.\n"
            f"In Python only: {python_patterns - parsed_patterns}\n"
            f"In parsed only: {parsed_patterns - python_patterns}"
        )

    def test_roundtrip_procedure_steps_supervisor(self, parsed_spec) -> None:
        """Round-trip (AC-B3-1): supervisor procedure steps match PROCEDURE_STEPS —
        all 6 fields asserted field-by-field.

        Supervisor steps are parsed from <startup-sequence> in schema.xml phase p8;
        the parser round-trips id, order, instruction, command, context, and
        next_state for each step.
        """
        python_steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        parsed_steps = parsed_spec.procedure_steps.get(RoleId.SUPERVISOR, ())
        assert len(parsed_steps) == len(python_steps), (
            f"Supervisor procedure step count mismatch: "
            f"parsed={len(parsed_steps)}, python={len(python_steps)}"
        )
        for i, (py_step, parsed_step) in enumerate(zip(python_steps, parsed_steps)):
            assert parsed_step.id == py_step.id, (
                f"Supervisor step[{i}] id mismatch: "
                f"parsed={parsed_step.id!r}, python={py_step.id!r}"
            )
            assert parsed_step.order == py_step.order, (
                f"Supervisor step[{i}] order mismatch: "
                f"parsed={parsed_step.order!r}, python={py_step.order!r}"
            )
            assert parsed_step.instruction == py_step.instruction, (
                f"Supervisor step[{i}] instruction mismatch: "
                f"parsed={parsed_step.instruction!r}, python={py_step.instruction!r}"
            )
            assert parsed_step.command == py_step.command, (
                f"Supervisor step[{i}] command mismatch: "
                f"parsed={parsed_step.command!r}, python={py_step.command!r}"
            )
            assert parsed_step.context == py_step.context, (
                f"Supervisor step[{i}] context mismatch: "
                f"parsed={parsed_step.context!r}, python={py_step.context!r}"
            )
            assert parsed_step.next_state == py_step.next_state, (
                f"Supervisor step[{i}] next_state mismatch: "
                f"parsed={parsed_step.next_state!r}, python={py_step.next_state!r}"
            )

    def test_roundtrip_procedure_steps_worker(self, parsed_spec) -> None:
        """Round-trip (AC-B3-2): worker procedure steps match PROCEDURE_STEPS —
        id/order/instruction match; command/context/next_state are each explicitly None.

        Worker steps are parsed from <tdd-layers> in schema.xml phase p9.  The parser
        intentionally does not set command, context, or next_state for worker steps
        (those fields are not present in <tdd-layers>), so each must be None.
        """
        python_steps = PROCEDURE_STEPS[RoleId.WORKER]
        parsed_steps = parsed_spec.procedure_steps.get(RoleId.WORKER, ())
        assert len(parsed_steps) == len(python_steps), (
            f"Worker procedure step count mismatch: "
            f"parsed={len(parsed_steps)}, python={len(python_steps)}"
        )
        for i, (py_step, parsed_step) in enumerate(zip(python_steps, parsed_steps)):
            assert parsed_step.id == py_step.id, (
                f"Worker step[{i}] id mismatch: "
                f"parsed={parsed_step.id!r}, python={py_step.id!r}"
            )
            assert parsed_step.order == py_step.order, (
                f"Worker step[{i}] order mismatch: "
                f"parsed={parsed_step.order!r}, python={py_step.order!r}"
            )
            assert parsed_step.instruction == py_step.instruction, (
                f"Worker step[{i}] instruction mismatch: "
                f"parsed={parsed_step.instruction!r}, python={py_step.instruction!r}"
            )
            # Worker steps come from <tdd-layers>, not <startup-sequence>;
            # the parser intentionally discards command/context/next_state.
            assert parsed_step.command is None, (
                f"Worker step[{i}] command must be None "
                f"(worker steps have no command in <tdd-layers>), "
                f"got {parsed_step.command!r}"
            )
            assert parsed_step.context is None, (
                f"Worker step[{i}] context must be None "
                f"(worker steps have no context in <tdd-layers>), "
                f"got {parsed_step.context!r}"
            )
            assert parsed_step.next_state is None, (
                f"Worker step[{i}] next_state must be None "
                f"(worker steps have no next-state in <tdd-layers>), "
                f"got {parsed_step.next_state!r}"
            )


# ─── Return value tests ───────────────────────────────────────────────────────


class TestReturnValue:
    """generate_schema() must return the generated XML string."""

    def test_returns_string(self, tmp_path: Path) -> None:
        """generate_schema returns a str."""
        output = tmp_path / "schema.xml"
        result = generate_schema(output, diff=False)
        assert isinstance(result, str), (
            f"Expected str return, got {type(result)}"
        )

    def test_returns_nonempty_string(self, tmp_path: Path) -> None:
        """generate_schema returns a non-empty string."""
        output = tmp_path / "schema.xml"
        result = generate_schema(output, diff=False)
        assert result is not None and len(result) > 0, (
            "generate_schema returned empty or None"
        )

    def test_returns_valid_xml_string(self, tmp_path: Path) -> None:
        """The returned string is valid XML."""
        output = tmp_path / "schema.xml"
        result = generate_schema(output, diff=False)
        assert result is not None
        root = ET.fromstring(result)
        assert root.tag == "aura-protocol"

    def test_writes_same_content_as_return(self, tmp_path: Path) -> None:
        """The content written to disk matches the returned string."""
        output = tmp_path / "schema.xml"
        result = generate_schema(output, diff=False)
        assert result is not None
        written = output.read_text(encoding="UTF-8")
        assert result == written, (
            "Returned string does not match file content written to disk"
        )

    def test_idempotent_second_call(self, tmp_path: Path) -> None:
        """Calling generate_schema twice produces identical output."""
        output = tmp_path / "schema.xml"
        result1 = generate_schema(output, diff=False)
        result2 = generate_schema(output, diff=False)
        assert result1 == result2, (
            "generate_schema is not idempotent: second call differs from first"
        )


# ─── AC10: End-to-end pipeline test ───────────────────────────────────────────


class TestAC10Pipeline:
    """AC10: Full pipeline parse_schema → gen_types → gen_schema → validate → gen_skills.

    Confirms all four modules compose correctly without errors or exceptions.
    """

    def test_full_pipeline_succeeds(self, tmp_path: Path) -> None:
        """AC10: parse_schema → gen_types (draft) → gen_schema → validate → gen_skills pipeline succeeds."""
        from validate_schema import validate  # type: ignore[import]

        # Step 1: parse_schema from the canonical schema.xml on disk
        schema_xml = Path(__file__).resolve().parent.parent / "skills" / "protocol" / "schema.xml"
        assert schema_xml.exists(), f"Canonical schema.xml not found at {schema_xml}"
        spec = parse_schema(schema_xml)
        assert spec is not None, "parse_schema returned None"

        # Step 2: gen_types — generate draft Python source from parsed spec
        types_source = generate_types_source(spec)
        assert isinstance(types_source, str) and len(types_source) > 0, (
            "generate_types_source returned empty or non-string"
        )

        # Step 3: gen_schema — generate schema.xml from Python type definitions
        output = tmp_path / "schema.xml"
        schema_content = generate_schema(output, diff=False)
        assert isinstance(schema_content, str) and len(schema_content) > 0, (
            "generate_schema returned empty or non-string"
        )
        assert output.exists(), "generate_schema did not write the output file"

        # Step 4: validate — confirm generated schema.xml passes validation
        errors = validate(output)
        assert errors == [], (
            f"validate_schema found {len(errors)} error(s) in generated schema:\n"
            + "\n".join(f"  {e}" for e in errors)
        )

        # Step 5: gen_skills — generate a skill from the schema (worker role)
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text(
            f"---\nname: test-worker\n---\n{GENERATED_BEGIN}\n(old content)\n{GENERATED_END}\n",
            encoding="utf-8",
        )
        from aura_protocol.types import RoleId
        skill_result = generate_skill(
            RoleId.WORKER,
            skill_path,
            diff=False,
            write=False,
        )
        assert isinstance(skill_result, str) and len(skill_result) > 0, (
            "generate_skill returned empty or non-string"
        )
        assert GENERATED_BEGIN in skill_result, (
            "generate_skill output missing BEGIN marker"
        )
        assert GENERATED_END in skill_result, (
            "generate_skill output missing END marker"
        )


# ─── Drift test: committed schema.xml must match generator output ──────────────


class TestSchemaXmlDrift:
    """Verify committed schema.xml matches generator output."""

    def test_generated_schema_matches_canonical(self, tmp_path: Path) -> None:
        """skills/protocol/schema.xml must match generate_schema() output."""
        canonical = (
            Path(__file__).parent.parent / "skills" / "protocol" / "schema.xml"
        ).read_text(encoding="utf-8")
        output_path = tmp_path / "schema.xml"
        content = generate_schema(output_path, diff=False)
        assert content == canonical, (
            "Generated schema.xml differs from canonical. "
            "Run: uv run python scripts/aura_protocol/gen_schema.py to regenerate."
        )


# ─── D1: Slug pin literals — guard against silent step ID renames ──────────────


class TestSlugPinLiterals:
    """D1: Literal string assertions that specific step IDs exist in PROCEDURE_STEPS.

    These are NOT Python-vs-Python cross-checks. They use literal strings to
    guard against silent renames of well-known step IDs (e.g. via refactoring).
    If a step is renamed in types.py, these tests will fail and require
    an explicit update here — providing a visible audit trail.
    """

    def test_supervisor_call_skill_slug(self) -> None:
        """S-supervisor-call-skill must exist as a supervisor procedure step."""
        assert any(s.id == "S-supervisor-call-skill" for s in PROCEDURE_STEPS[RoleId.SUPERVISOR]), (
            "Expected step 'S-supervisor-call-skill' in PROCEDURE_STEPS[SUPERVISOR]. "
            "If this step was renamed, update the literal here to reflect the new name."
        )

    def test_supervisor_cartographers_slug(self) -> None:
        """S-supervisor-cartographers must exist as a supervisor procedure step."""
        assert any(s.id == "S-supervisor-cartographers" for s in PROCEDURE_STEPS[RoleId.SUPERVISOR]), (
            "Expected step 'S-supervisor-cartographers' in PROCEDURE_STEPS[SUPERVISOR]. "
            "If this step was renamed, update the literal here to reflect the new name."
        )

    def test_worker_types_slug(self) -> None:
        """S-worker-types must exist as a worker procedure step."""
        assert any(s.id == "S-worker-types" for s in PROCEDURE_STEPS[RoleId.WORKER]), (
            "Expected step 'S-worker-types' in PROCEDURE_STEPS[WORKER]. "
            "If this step was renamed, update the literal here to reflect the new name."
        )
