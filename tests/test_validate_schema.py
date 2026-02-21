"""Combinatorial tests for schema validation using mutation fixtures.

The fixture (tests/fixtures/schema_valid_minimal.xml) defines a minimal but
complete valid schema. Each mutation transforms it into a schema with exactly
one detectable error. Tests verify the validator catches the right error at
the right layer.

Organized by test class:
- TestValidSchemas: baseline valid schemas produce zero errors
- TestMutationDetection: parametrized — each mutation produces expected error
- TestCLI: subprocess invocation of the script
- TestFixtureStatistics: coverage summary
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from validate_schema import ErrorLayer, ValidationError, validate, validate_tree

from fixtures.schema_fixture import (
    ALL_MUTATIONS,
    REFERENTIAL_MUTATIONS,
    SEMANTIC_MUTATIONS,
    STRUCTURAL_MUTATIONS,
    SchemaFixture,
    SchemaMutation,
)

# ─── Paths ────────────────────────────────────────────────────────────────────

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_schema.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURE_DIR / "schema_valid_minimal.xml"
REAL_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "skills" / "protocol" / "schema.xml"
)

# ─── Known issues in the real schema (documented, not bugs) ──────────────────

KNOWN_REAL_SCHEMA_ISSUES: set[str] = set()


# ─── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def schema_fixture() -> SchemaFixture:
    """Load the minimal valid schema fixture."""
    return SchemaFixture(FIXTURE_PATH)


# ─── Valid schema tests ──────────────────────────────────────────────────────


class TestValidSchemas:
    """Valid schemas should produce zero errors."""

    def test_fixture_produces_no_errors(self, schema_fixture: SchemaFixture):
        """The minimal test fixture should pass all validation layers."""
        root = schema_fixture.fresh_root()
        errors = validate_tree(root)
        assert errors == [], (
            f"Valid fixture has {len(errors)} error(s):\n"
            + "\n".join(f"  {e}" for e in errors)
        )

    def test_fixture_via_file_path(self):
        """validate(path) convenience wrapper works on the fixture."""
        errors = validate(FIXTURE_PATH)
        assert errors == []

    def test_real_schema(self):
        """The actual protocol schema.xml should pass (modulo known issues)."""
        if not REAL_SCHEMA_PATH.exists():
            pytest.skip("Real schema not found")
        errors = validate(REAL_SCHEMA_PATH)
        unexpected = [e for e in errors if str(e) not in KNOWN_REAL_SCHEMA_ISSUES]
        assert unexpected == [], (
            f"Unexpected errors in real schema:\n"
            + "\n".join(f"  {e}" for e in unexpected)
        )

    def test_real_schema_known_issues_documented(self):
        """If known issues are fixed upstream, update KNOWN_REAL_SCHEMA_ISSUES."""
        if not REAL_SCHEMA_PATH.exists():
            pytest.skip("Real schema not found")
        errors = validate(REAL_SCHEMA_PATH)
        actual_issues = {str(e) for e in errors}
        stale = KNOWN_REAL_SCHEMA_ISSUES - actual_issues
        if stale:
            pytest.fail(
                f"Known issues have been fixed — remove from KNOWN_REAL_SCHEMA_ISSUES:\n"
                + "\n".join(f"  {s}" for s in stale)
            )


# ─── Mutation detection (parametrized) ───────────────────────────────────────


class TestMutationDetection:
    """Each mutation should produce at least one error of the expected type."""

    @pytest.mark.parametrize(
        "mutation",
        [
            pytest.param(m, id=f"{m.category}:{m.name}")
            for m in SchemaFixture(FIXTURE_PATH).generate_all_mutations()
        ],
    )
    def test_each_mutation(
        self, mutation: SchemaMutation, schema_fixture: SchemaFixture
    ):
        root = schema_fixture.apply_mutation(mutation)
        errors = validate_tree(root)
        matching = [
            e
            for e in errors
            if e.layer == mutation.layer
            and mutation.expected_fragment in e.message
        ]
        assert matching, (
            f"Expected {mutation.layer.value} error containing "
            f"'{mutation.expected_fragment}' ({mutation.description})\n"
            f"Got {len(errors)} error(s):\n"
            + "\n".join(f"  [{e.layer.value}] {e}" for e in errors)
        )


class TestStructuralMutations:
    """Structural layer: missing required attributes."""

    @pytest.mark.parametrize(
        "mutation",
        [
            pytest.param(m, id=f"{m.category}:{m.name}")
            for m in SchemaFixture(FIXTURE_PATH).generate_structural_mutations()
        ],
    )
    def test_structural_error_detected(
        self, mutation: SchemaMutation, schema_fixture: SchemaFixture
    ):
        root = schema_fixture.apply_mutation(mutation)
        errors = validate_tree(root)
        structural_errors = [e for e in errors if e.layer == ErrorLayer.STRUCTURAL]
        assert structural_errors, (
            f"No structural errors for mutation '{mutation.name}': {mutation.description}"
        )
        assert any(mutation.expected_fragment in e.message for e in structural_errors)


class TestReferentialMutations:
    """Referential layer: dangling cross-references."""

    @pytest.mark.parametrize(
        "mutation",
        [
            pytest.param(m, id=f"{m.category}:{m.name}")
            for m in SchemaFixture(FIXTURE_PATH).generate_referential_mutations()
        ],
    )
    def test_referential_error_detected(
        self, mutation: SchemaMutation, schema_fixture: SchemaFixture
    ):
        root = schema_fixture.apply_mutation(mutation)
        errors = validate_tree(root)
        ref_errors = [e for e in errors if e.layer == ErrorLayer.REFERENTIAL]
        assert ref_errors, (
            f"No referential errors for mutation '{mutation.name}': {mutation.description}"
        )
        assert any(mutation.expected_fragment in e.message for e in ref_errors)


class TestSemanticMutations:
    """Semantic layer: protocol-level rule violations."""

    @pytest.mark.parametrize(
        "mutation",
        [
            pytest.param(m, id=f"{m.category}:{m.name}")
            for m in SchemaFixture(FIXTURE_PATH).generate_semantic_mutations()
        ],
    )
    def test_semantic_error_detected(
        self, mutation: SchemaMutation, schema_fixture: SchemaFixture
    ):
        root = schema_fixture.apply_mutation(mutation)
        errors = validate_tree(root)
        sem_errors = [e for e in errors if e.layer == ErrorLayer.SEMANTIC]
        assert sem_errors, (
            f"No semantic errors for mutation '{mutation.name}': {mutation.description}"
        )
        assert any(mutation.expected_fragment in e.message for e in sem_errors)


# ─── CLI integration tests ───────────────────────────────────────────────────


class TestCLI:
    """Test the script via subprocess invocation."""

    def test_valid_schema_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(FIXTURE_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_missing_file_exits_two(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "/nonexistent/schema.xml"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2

    def test_malformed_xml_exits_two(self, tmp_path: Path):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<not-closed>")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(bad_xml)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2

    def test_errors_exit_one(self, tmp_path: Path, schema_fixture: SchemaFixture):
        """A mutated schema should exit 1 with error output."""
        from fixtures.schema_fixture import STRUCTURAL_MUTATIONS

        mutation = STRUCTURAL_MUTATIONS[0]  # missing_phase_domain
        root = schema_fixture.apply_mutation(mutation)
        path = tmp_path / "schema.xml"
        tree = ET.ElementTree(root)
        tree.write(str(path), xml_declaration=True, encoding="unicode")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "error(s) found" in result.stdout


# ─── Fixture statistics ──────────────────────────────────────────────────────


class TestFixtureStatistics:
    """Coverage summary for the mutation fixture."""

    def test_mutation_coverage_summary(self, schema_fixture: SchemaFixture):
        structural = list(schema_fixture.generate_structural_mutations())
        referential = list(schema_fixture.generate_referential_mutations())
        semantic = list(schema_fixture.generate_semantic_mutations())

        print(f"\nMutation Coverage Summary:")
        print(f"  Structural:  {len(structural)} mutations")
        print(f"  Referential: {len(referential)} mutations")
        print(f"  Semantic:    {len(semantic)} mutations")
        print(
            f"  Total:       {len(structural) + len(referential) + len(semantic)} mutations"
        )

        print(f"\nStructural by category:")
        _print_by_category(structural)
        print(f"\nReferential by category:")
        _print_by_category(referential)
        print(f"\nSemantic by category:")
        _print_by_category(semantic)

        assert len(structural) >= 10, "Should cover major structural rules"
        assert len(referential) >= 8, "Should cover major ref checks"
        assert len(semantic) >= 8, "Should cover major semantic rules"

    def test_all_layers_covered(self, schema_fixture: SchemaFixture):
        """Every ErrorLayer should have at least one mutation."""
        mutations = list(schema_fixture.generate_all_mutations())
        layers_covered = {m.layer for m in mutations}
        for layer in ErrorLayer:
            assert layer in layers_covered, f"No mutations for {layer.value}"

    def test_no_duplicate_mutation_names(self, schema_fixture: SchemaFixture):
        mutations = list(schema_fixture.generate_all_mutations())
        names = [m.name for m in mutations]
        assert len(names) == len(set(names)), (
            f"Duplicate mutation names: "
            + str([n for n in names if names.count(n) > 1])
        )


def _print_by_category(mutations: list[SchemaMutation]) -> None:
    by_cat: dict[str, int] = {}
    for m in mutations:
        by_cat[m.category] = by_cat.get(m.category, 0) + 1
    for cat, count in sorted(by_cat.items()):
        print(f"    {cat}: {count}")


# Need ET import for the CLI test that writes mutated XML
import xml.etree.ElementTree as ET
