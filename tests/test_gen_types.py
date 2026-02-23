"""Tests for scripts/aura_protocol/gen_types.py.

AC1b: generate_types_source(spec) produces valid Python source from SchemaSpec (UAT-1).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aura_protocol.gen_types import generate_types_source
from aura_protocol.schema_parser import SchemaSpec, parse_schema
from aura_protocol.types import RoleId

# ─── Fixtures ─────────────────────────────────────────────────────────────────

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "skills" / "protocol" / "schema.xml"


@pytest.fixture(scope="module")
def parsed_spec() -> SchemaSpec:
    """Parse schema.xml once for the entire module."""
    assert SCHEMA_PATH.exists(), f"schema.xml not found at {SCHEMA_PATH}"
    return parse_schema(SCHEMA_PATH)


@pytest.fixture(scope="module")
def generated_source(parsed_spec: SchemaSpec) -> str:
    """Generate source once for the entire module."""
    return generate_types_source(parsed_spec)


# ─── Valid Python ──────────────────────────────────────────────────────────────


class TestGenTypesValidPython:
    """AC1b: Output must be valid Python source."""

    def test_output_is_valid_python(self, generated_source: str) -> None:
        """ast.parse() must succeed on generated source."""
        try:
            tree = ast.parse(generated_source)
        except SyntaxError as e:
            pytest.fail(
                f"generate_types_source() produced invalid Python: {e}\n"
                f"Source snippet:\n{generated_source[:500]}"
            )
        assert tree is not None

    def test_output_is_non_empty(self, generated_source: str) -> None:
        """Output must not be empty."""
        assert len(generated_source.strip()) > 0

    def test_output_has_header_comment(self, generated_source: str) -> None:
        """Output must start with the auto-generated header."""
        assert "AUTO-GENERATED DRAFT" in generated_source
        assert "DO NOT COMMIT DIRECTLY" in generated_source

    def test_output_has_bootstrap_warning(self, generated_source: str) -> None:
        """Output must mention this is a one-time bootstrap tool."""
        assert "bootstrap" in generated_source.lower() or "one-time" in generated_source.lower()


# ─── Expected definitions ─────────────────────────────────────────────────────


class TestGenTypesContainsExpectedDefinitions:
    """Output must contain all expected enum and class definitions."""

    def test_contains_execution_mode_enum(self, generated_source: str) -> None:
        assert "class ExecutionMode" in generated_source

    def test_contains_content_level_enum(self, generated_source: str) -> None:
        assert "class ContentLevel" in generated_source

    def test_contains_review_axis_enum(self, generated_source: str) -> None:
        assert "class ReviewAxis" in generated_source

    def test_contains_substep_spec_class(self, generated_source: str) -> None:
        assert "class SubstepSpec" in generated_source

    def test_contains_role_spec_class(self, generated_source: str) -> None:
        assert "class RoleSpec" in generated_source

    def test_contains_delegate_spec_class(self, generated_source: str) -> None:
        assert "class DelegateSpec" in generated_source

    def test_contains_command_spec_class(self, generated_source: str) -> None:
        assert "class CommandSpec" in generated_source

    def test_contains_label_spec_class(self, generated_source: str) -> None:
        assert "class LabelSpec" in generated_source

    def test_contains_review_axis_spec_class(self, generated_source: str) -> None:
        assert "class ReviewAxisSpec" in generated_source

    def test_contains_title_convention_class(self, generated_source: str) -> None:
        assert "class TitleConvention" in generated_source

    def test_contains_procedure_step_class(self, generated_source: str) -> None:
        assert "class ProcedureStep" in generated_source

    def test_contains_constraint_context_class(self, generated_source: str) -> None:
        assert "class ConstraintContext" in generated_source

    def test_contains_role_specs_dict(self, generated_source: str) -> None:
        assert "ROLE_SPECS" in generated_source

    def test_contains_command_specs_dict(self, generated_source: str) -> None:
        assert "COMMAND_SPECS" in generated_source

    def test_contains_label_specs_dict(self, generated_source: str) -> None:
        assert "LABEL_SPECS" in generated_source

    def test_contains_review_axis_specs_dict(self, generated_source: str) -> None:
        assert "REVIEW_AXIS_SPECS" in generated_source

    def test_contains_title_conventions_list(self, generated_source: str) -> None:
        assert "TITLE_CONVENTIONS" in generated_source

    def test_contains_procedure_steps_dict(self, generated_source: str) -> None:
        assert "PROCEDURE_STEPS" in generated_source


# ─── Data integrity ───────────────────────────────────────────────────────────


class TestGenTypesDataIntegrity:
    """Generated source contains schema-derived content."""

    def test_all_role_ids_in_source(self, generated_source: str) -> None:
        """All 5 role names appear in the generated source."""
        for role in RoleId:
            assert role.name in generated_source or role.value in generated_source, (
                f"Role {role.name}/{role.value} not found in generated source"
            )

    def test_execution_mode_values_in_source(self, generated_source: str) -> None:
        assert "sequential" in generated_source
        assert "parallel" in generated_source

    def test_content_level_values_in_source(self, generated_source: str) -> None:
        assert "full-provenance" in generated_source
        assert "summary-with-ids" in generated_source

    def test_review_axis_letters_in_source(self, generated_source: str) -> None:
        for letter in ("A", "B", "C"):
            assert f"= '{letter}'" in generated_source or f'= "{letter}"' in generated_source, (
                f"ReviewAxis letter {letter!r} not found in generated source"
            )

    def test_phase_labels_in_source(self, generated_source: str) -> None:
        """Phase label ids like L-p1s1_1 appear in generated source."""
        assert "L-p1s1_1" in generated_source

    def test_command_count_in_source(self, parsed_spec: SchemaSpec, generated_source: str) -> None:
        """All command ids appear in the COMMAND_SPECS dict output."""
        for cid in parsed_spec.commands:
            assert cid in generated_source, (
                f"Command id {cid!r} not found in generated source"
            )

    def test_frozen_dataclass_decorator_present(self, generated_source: str) -> None:
        """All spec dataclass definitions use @dataclass(frozen=True), verified per-class."""
        expected_frozen_classes = {
            "SubstepSpec",
            "RoleSpec",
            "DelegateSpec",
            "CommandSpec",
            "LabelSpec",
            "ReviewAxisSpec",
            "TitleConvention",
            "ProcedureStep",
            "ConstraintContext",
        }
        tree = ast.parse(generated_source)
        frozen_classes: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "dataclass"
                    and any(
                        isinstance(kw, ast.keyword)
                        and kw.arg == "frozen"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                        for kw in decorator.keywords
                    )
                ):
                    frozen_classes.add(node.name)
        assert frozen_classes == expected_frozen_classes, (
            f"Classes with @dataclass(frozen=True) mismatch.\n"
            f"Expected: {sorted(expected_frozen_classes)}\n"
            f"Got: {sorted(frozen_classes)}"
        )

    def test_from_annotations_import(self, generated_source: str) -> None:
        """Output includes from __future__ import annotations."""
        assert "from __future__ import annotations" in generated_source


# ─── Return type ──────────────────────────────────────────────────────────────


class TestGenTypesReturnType:
    """generate_types_source() returns str."""

    def test_returns_string(self, parsed_spec: SchemaSpec) -> None:
        source = generate_types_source(parsed_spec)
        assert isinstance(source, str)

    def test_deterministic_for_same_spec(self, parsed_spec: SchemaSpec) -> None:
        """Calling generate_types_source twice with same spec returns same result."""
        source1 = generate_types_source(parsed_spec)
        source2 = generate_types_source(parsed_spec)
        assert source1 == source2
