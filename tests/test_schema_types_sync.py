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
    CONSTRAINT_SPECS,
    HANDOFF_SPECS,
    PHASE_DOMAIN,
    PHASE_SPECS,
    Domain,
    HandoffSpec,
    PhaseId,
    RoleId,
    SeverityLevel,
    Transition,
    VoteType,
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
