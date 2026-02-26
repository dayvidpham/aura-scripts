"""Tests for scripts/aura_protocol/schema_parser.py.

AC1: parse_schema() returns SchemaSpec with correct entity counts.
AC1a: SchemaParseError raised on malformed XML (3+ error-path tests).
"""

from __future__ import annotations

import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from aura_protocol.schema_parser import SchemaParseError, SchemaSpec, parse_schema
from aura_protocol.types import ContentLevel, ExecutionMode, PhaseId, ReviewAxis, RoleId

# ─── Schema path ──────────────────────────────────────────────────────────────

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "skills" / "protocol" / "schema.xml"


# ─── Happy path: entity count verification ────────────────────────────────────


@pytest.fixture(scope="module")
def parsed_spec() -> SchemaSpec:
    """Parse schema.xml once for the entire module."""
    assert SCHEMA_PATH.exists(), f"schema.xml not found at {SCHEMA_PATH}"
    return parse_schema(SCHEMA_PATH)


class TestSchemaParserEntityCounts:
    """AC1: parse_schema() returns correct entity counts matching schema.xml."""

    def test_phase_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 12 phases extracted."""
        assert len(parsed_spec.phases) == 12, (
            f"Expected 12 phases, got {len(parsed_spec.phases)}: {parsed_spec.phases}"
        )

    def test_role_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 5 roles extracted."""
        assert len(parsed_spec.roles) == 5, (
            f"Expected 5 roles, got {len(parsed_spec.roles)}: {list(parsed_spec.roles.keys())}"
        )

    def test_command_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 35 commands extracted."""
        assert len(parsed_spec.commands) == 35, (
            f"Expected 35 commands, got {len(parsed_spec.commands)}: {list(parsed_spec.commands.keys())}"
        )

    def test_constraint_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 26 constraints extracted."""
        assert len(parsed_spec.constraints) == 26, (
            f"Expected 26 constraints, got {len(parsed_spec.constraints)}"
        )

    def test_handoff_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 6 handoffs extracted."""
        assert len(parsed_spec.handoffs) == 6, (
            f"Expected 6 handoffs, got {len(parsed_spec.handoffs)}: {list(parsed_spec.handoffs.keys())}"
        )

    def test_label_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 21 labels extracted."""
        assert len(parsed_spec.labels) == 21, (
            f"Expected 21 labels, got {len(parsed_spec.labels)}"
        )

    def test_review_axis_count(self, parsed_spec: SchemaSpec) -> None:
        """AC1: 3 review axes extracted."""
        assert len(parsed_spec.review_axes) == 3, (
            f"Expected 3 review axes, got {len(parsed_spec.review_axes)}"
        )


class TestSchemaParserPhaseOrdering:
    """Phases are ordered numerically 1..12."""

    def test_phases_ordered_numerically(self, parsed_spec: SchemaSpec) -> None:
        assert parsed_spec.phases[0] == "p1"
        assert parsed_spec.phases[-1] == "p12"

    def test_all_phase_ids_present(self, parsed_spec: SchemaSpec) -> None:
        expected = {f"p{i}" for i in range(1, 13)}
        assert set(parsed_spec.phases) == expected


class TestSchemaParserRoles:
    """Role specs contain expected data."""

    def test_all_role_ids_present(self, parsed_spec: SchemaSpec) -> None:
        expected = set(RoleId)
        assert set(parsed_spec.roles.keys()) == expected

    def test_supervisor_owned_phases(self, parsed_spec: SchemaSpec) -> None:
        sup = parsed_spec.roles[RoleId.SUPERVISOR]
        # Supervisor owns p7..p12
        assert PhaseId.P7_HANDOFF in sup.owned_phases
        assert PhaseId.P8_IMPL_PLAN in sup.owned_phases
        assert PhaseId.P12_LANDING in sup.owned_phases

    def test_worker_owned_phases(self, parsed_spec: SchemaSpec) -> None:
        worker = parsed_spec.roles[RoleId.WORKER]
        assert worker.owned_phases == frozenset({PhaseId.P9_SLICE})

    def test_epoch_owns_all_phases(self, parsed_spec: SchemaSpec) -> None:
        epoch = parsed_spec.roles[RoleId.EPOCH]
        assert len(epoch.owned_phases) == 12


class TestSchemaParserCommands:
    """Command specs contain expected data."""

    def test_cmd_worker_present(self, parsed_spec: SchemaSpec) -> None:
        assert "cmd-worker" in parsed_spec.commands
        cmd = parsed_spec.commands["cmd-worker"]
        assert cmd.role_ref == RoleId.WORKER
        assert "p9" in cmd.phases

    def test_cmd_supervisor_present(self, parsed_spec: SchemaSpec) -> None:
        assert "cmd-supervisor" in parsed_spec.commands
        cmd = parsed_spec.commands["cmd-supervisor"]
        assert cmd.role_ref == RoleId.SUPERVISOR

    def test_cmd_status_no_role(self, parsed_spec: SchemaSpec) -> None:
        """cmd-status has no role-ref in schema.xml."""
        assert "cmd-status" in parsed_spec.commands
        cmd = parsed_spec.commands["cmd-status"]
        assert cmd.role_ref is None


class TestSchemaParserHandoffs:
    """Handoff specs contain expected data."""

    def test_h1_content_level_full_provenance(self, parsed_spec: SchemaSpec) -> None:
        h1 = parsed_spec.handoffs["h1"]
        assert h1.content_level == ContentLevel.FULL_PROVENANCE

    def test_h2_supervisor_to_worker(self, parsed_spec: SchemaSpec) -> None:
        h2 = parsed_spec.handoffs["h2"]
        assert h2.source_role == RoleId.SUPERVISOR
        assert h2.target_role == RoleId.WORKER

    def test_handoff_required_fields_not_empty(self, parsed_spec: SchemaSpec) -> None:
        for hid, h in parsed_spec.handoffs.items():
            assert len(h.required_fields) > 0, f"Handoff {hid} has no required fields"


class TestSchemaParserReviewAxes:
    """Review axis specs contain expected data."""

    def test_axis_a_correctness(self, parsed_spec: SchemaSpec) -> None:
        axis_a = parsed_spec.review_axes["axis-A"]
        assert axis_a.letter == ReviewAxis.A
        assert axis_a.name == "Correctness"
        assert len(axis_a.key_questions) >= 3

    def test_axis_b_test_quality(self, parsed_spec: SchemaSpec) -> None:
        axis_b = parsed_spec.review_axes["axis-B"]
        assert axis_b.letter == ReviewAxis.B
        assert "Test quality" in axis_b.name

    def test_axis_c_elegance(self, parsed_spec: SchemaSpec) -> None:
        axis_c = parsed_spec.review_axes["axis-C"]
        assert axis_c.letter == ReviewAxis.C
        assert axis_c.name == "Elegance"


class TestSchemaParserLabels:
    """Label specs contain expected data."""

    def test_phase_label_not_special(self, parsed_spec: SchemaSpec) -> None:
        label = parsed_spec.labels["L-p1s1_1"]
        assert not label.special
        assert label.phase_ref == "p1"

    def test_special_labels(self, parsed_spec: SchemaSpec) -> None:
        special_ids = {"L-urd", "L-superseded", "L-sev-blocker", "L-sev-import",
                       "L-sev-minor", "L-followup"}
        for lid in special_ids:
            assert lid in parsed_spec.labels, f"Missing special label {lid}"
            assert parsed_spec.labels[lid].special, f"Label {lid} should be special"


class TestSchemaParserSubsteps:
    """Substep specs extracted from phases."""

    def test_substep_ids_extracted(self, parsed_spec: SchemaSpec) -> None:
        assert len(parsed_spec.substep_specs) > 0

    def test_substep_execution_modes_valid(self, parsed_spec: SchemaSpec) -> None:
        for sid, substep in parsed_spec.substep_specs.items():
            assert isinstance(substep.execution, ExecutionMode), (
                f"Substep {sid} has invalid execution mode: {substep.execution}"
            )


class TestSchemaParserProcedureSteps:
    """Procedure steps extracted for supervisor and worker."""

    def test_supervisor_has_steps(self, parsed_spec: SchemaSpec) -> None:
        steps = parsed_spec.procedure_steps[RoleId.SUPERVISOR]
        assert len(steps) > 0, "Supervisor should have procedure steps"

    def test_supervisor_steps_ordered(self, parsed_spec: SchemaSpec) -> None:
        steps = parsed_spec.procedure_steps[RoleId.SUPERVISOR]
        orders = [s.order for s in steps]
        assert orders == sorted(orders), "Supervisor steps should be in order"

    def test_worker_has_steps(self, parsed_spec: SchemaSpec) -> None:
        steps = parsed_spec.procedure_steps[RoleId.WORKER]
        assert len(steps) > 0, "Worker should have TDD layer steps"

    def test_other_roles_empty(self, parsed_spec: SchemaSpec) -> None:
        for role in [RoleId.EPOCH, RoleId.ARCHITECT, RoleId.REVIEWER]:
            steps = parsed_spec.procedure_steps[role]
            assert steps == (), f"Role {role} should have empty procedure steps"


# ─── Error paths: SchemaParseError on malformed input ─────────────────────────


class TestSchemaParserErrorPaths:
    """AC1a: SchemaParseError raised on malformed input (3+ error-path tests)."""

    def test_error_on_missing_file(self, tmp_path: Path) -> None:
        """SchemaParseError when file does not exist."""
        missing = tmp_path / "nonexistent_schema.xml"
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(missing)
        assert "not found" in str(exc_info.value).lower() or "Schema file" in str(exc_info.value)

    def test_error_on_invalid_xml(self, tmp_path: Path) -> None:
        """SchemaParseError when XML is malformed (unclosed tag)."""
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<aura-protocol><phases><phase id='p1'")
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(bad_xml)
        msg = str(exc_info.value)
        assert "XML parse error" in msg or "parse error" in msg.lower()

    def test_error_on_wrong_root_element(self, tmp_path: Path) -> None:
        """SchemaParseError when root element is not <aura-protocol>."""
        bad_xml = tmp_path / "wrong_root.xml"
        bad_xml.write_text('<?xml version="1.0"?><wrong-root/>')
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(bad_xml)
        assert "root element" in str(exc_info.value).lower() or "aura-protocol" in str(exc_info.value)

    def test_error_on_missing_phases_section(self, tmp_path: Path) -> None:
        """SchemaParseError when <phases> section is absent."""
        xml = tmp_path / "no_phases.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <roles/>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "phases" in str(exc_info.value).lower()

    def test_error_on_missing_roles_section(self, tmp_path: Path) -> None:
        """SchemaParseError when <roles> section is absent."""
        xml = tmp_path / "no_roles.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases/>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "roles" in str(exc_info.value).lower()

    def test_error_on_phase_missing_id(self, tmp_path: Path) -> None:
        """SchemaParseError when a phase element is missing 'id' attribute."""
        xml = tmp_path / "phase_no_id.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases>
                <phase number="1" domain="user" name="Request"/>
              </phases>
              <roles/>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "id" in str(exc_info.value).lower() or "'id'" in str(exc_info.value)

    def test_error_on_phase_invalid_number(self, tmp_path: Path) -> None:
        """SchemaParseError when phase number is not an integer."""
        xml = tmp_path / "phase_bad_number.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases>
                <phase id="p1" number="not-a-number" domain="user" name="Request"/>
              </phases>
              <roles/>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "number" in str(exc_info.value).lower() or "integer" in str(exc_info.value).lower()

    def test_parse_schema_raises_on_missing_instruction(self, tmp_path: Path) -> None:
        """SchemaParseError raised when a <step> in a startup-sequence has no <instruction>."""
        # The parser looks for startup-sequence inside substeps of phase p8.
        # Construct a minimal schema with a phase p8 substep containing a
        # startup-sequence where the step is missing its <instruction> child element.
        xml_content = textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases>
                <phase id="p8" number="8" domain="impl" name="Impl Plan">
                  <substeps>
                    <substep id="s8" type="plan" execution="sequential" order="1"
                             label-ref="L-p8s8">
                      <startup-sequence role="supervisor">
                        <step order="1" id="S-test">
                          <!-- No <instruction> child element — must raise SchemaParseError -->
                        </step>
                      </startup-sequence>
                    </substep>
                  </substeps>
                </phase>
              </phases>
              <roles/>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """)
        schema_path = tmp_path / "schema_missing_instruction.xml"
        schema_path.write_text(xml_content)
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(schema_path)
        assert "S-test" in str(exc_info.value), (
            f"Expected step id 'S-test' in error message, got: {exc_info.value}"
        )

    def test_error_on_unknown_role_id(self, tmp_path: Path) -> None:
        """SchemaParseError when a role has an id not in the RoleId enum."""
        xml = tmp_path / "unknown_role.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases/>
              <roles>
                <role id="unknown-role" name="Unknown"/>
              </roles>
              <commands/>
              <constraints/>
              <handoffs/>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "unknown" in str(exc_info.value).lower() or "role" in str(exc_info.value).lower()

    def test_error_on_unknown_content_level(self, tmp_path: Path) -> None:
        """SchemaParseError when handoff has unknown content-level value."""
        xml = tmp_path / "bad_content_level.xml"
        xml.write_text(textwrap.dedent("""\
            <?xml version="1.0"?>
            <aura-protocol version="2.0">
              <phases/>
              <roles/>
              <commands/>
              <constraints/>
              <handoffs>
                <handoff id="h1" source-role="architect" target-role="supervisor"
                         at-phase="p7" content-level="unknown-level"/>
              </handoffs>
              <labels/>
              <review-axes/>
              <task-titles/>
            </aura-protocol>
        """))
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(xml)
        assert "content-level" in str(exc_info.value) or "unknown" in str(exc_info.value).lower()


class TestSchemaParserReturnType:
    """parse_schema() returns a frozen SchemaSpec."""

    def test_returns_schema_spec_instance(self, parsed_spec: SchemaSpec) -> None:
        assert isinstance(parsed_spec, SchemaSpec)

    def test_schema_spec_is_frozen(self, parsed_spec: SchemaSpec) -> None:
        """SchemaSpec is a frozen dataclass — can't set attributes."""
        with pytest.raises((AttributeError, TypeError)):
            parsed_spec.phases = ()  # type: ignore[misc]

    def test_error_message_is_actionable(self, tmp_path: Path) -> None:
        """Error messages contain 'Fix:' guidance."""
        missing = tmp_path / "not_here.xml"
        with pytest.raises(SchemaParseError) as exc_info:
            parse_schema(missing)
        msg = str(exc_info.value)
        assert "Fix:" in msg, f"Error message is not actionable (missing 'Fix:'): {msg}"
