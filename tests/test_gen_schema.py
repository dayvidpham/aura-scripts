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
    _PHASE_CONSTRAINTS,
    _ROLE_CONSTRAINTS,
    generate_schema,
)
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
        # A unified diff should contain --- and +++ lines
        assert "---" in diff_output or "+++" in diff_output or "diff" in diff_output, (
            "Expected unified diff output when file exists and content changed, "
            f"got: {diff_output[:200]!r}"
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


# ─── AC2b: role-ref/phase-ref on constraint elements ─────────────────────────


class TestConstraintRolePhaseRefs:
    """AC2b: schema.xml constraint elements include role-ref and phase-ref attributes (UAT-3)."""

    def test_constraints_have_role_ref_when_defined(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Constraints with role-ref in _ROLE_CONSTRAINTS have role-ref attribute in XML."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None, "<constraints> section missing"

        for constraint in constraints_el.findall("constraint"):
            cid = constraint.get("id")
            if cid is None:
                continue
            expected_role = _ROLE_CONSTRAINTS.get(cid)
            xml_role = constraint.get("role-ref")
            assert xml_role == expected_role, (
                f"Constraint {cid!r}: expected role-ref={expected_role!r}, "
                f"got role-ref={xml_role!r}"
            )

    def test_constraints_have_phase_ref_when_defined(
        self, generated_xml_root: ET.Element
    ) -> None:
        """Constraints with phase-ref in _PHASE_CONSTRAINTS have phase-ref attribute in XML."""
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None, "<constraints> section missing"

        for constraint in constraints_el.findall("constraint"):
            cid = constraint.get("id")
            if cid is None:
                continue
            expected_phase = _PHASE_CONSTRAINTS.get(cid)
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
        """role-ref values on constraints must be valid role IDs."""
        valid_role_ids = {r.value for r in RoleId}
        constraints_el = generated_xml_root.find("constraints")
        assert constraints_el is not None

        for constraint in constraints_el.findall("constraint"):
            role_ref = constraint.get("role-ref")
            if role_ref is not None:
                assert role_ref in valid_role_ids, (
                    f"Constraint {constraint.get('id')!r} has invalid "
                    f"role-ref={role_ref!r}. Valid: {sorted(valid_role_ids)}"
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

        # Supervisor-specific constraints
        supervisor_constraints = [
            "C-supervisor-no-impl",
            "C-supervisor-explore-team",
            "C-slice-leaf-tasks",
            "C-vertical-slices",
        ]
        for cid in supervisor_constraints:
            if cid in by_id:
                assert by_id[cid].get("role-ref") == "supervisor", (
                    f"{cid} should have role-ref='supervisor', "
                    f"got {by_id[cid].get('role-ref')!r}"
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
        """Round-trip: supervisor procedure steps match PROCEDURE_STEPS."""
        python_steps = PROCEDURE_STEPS[RoleId.SUPERVISOR]
        parsed_steps = parsed_spec.procedure_steps.get(RoleId.SUPERVISOR, ())
        assert len(parsed_steps) == len(python_steps), (
            f"Supervisor procedure step count mismatch: "
            f"parsed={len(parsed_steps)}, python={len(python_steps)}"
        )

    def test_roundtrip_procedure_steps_worker(self, parsed_spec) -> None:
        """Round-trip: worker procedure steps match PROCEDURE_STEPS."""
        python_steps = PROCEDURE_STEPS[RoleId.WORKER]
        parsed_steps = parsed_spec.procedure_steps.get(RoleId.WORKER, ())
        assert len(parsed_steps) == len(python_steps), (
            f"Worker procedure step count mismatch: "
            f"parsed={len(parsed_steps)}, python={len(python_steps)}"
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
