"""Structure verification for SLICE-1 schema extension types.

Covers R1-R7 types added in SLICE-1:
  - 5 new enums: ExampleLabel, ExampleLang, GateType, WorkflowExecution, ExitConditionType
  - 9 new frozen dataclasses: CodeExample, BehaviorSpec, ChecklistItem, Checklist,
      CoordinationCommand, WorkflowAction, ExitCondition, WorkflowStage, Workflow
  - 3 modified dataclasses (backward-compatible): ConstraintSpec, ProcedureStep, RoleSpec
  - 3 new canonical dicts: CHECKLIST_SPECS, COORDINATION_COMMANDS, WORKFLOW_SPECS
  - Updated ROLE_SPECS (introduction, ownership_narrative, behaviors)
  - Updated CONSTRAINT_SPECS (command field)

NOTE: Full integration tests (schema.xml sync) are added in SLICE-4.
"""

from __future__ import annotations

import dataclasses

import pytest

from aura_protocol.types import (
    # New enums
    ExampleLabel,
    ExampleLang,
    GateType,
    WorkflowExecution,
    ExitConditionType,
    # New dataclasses
    CodeExample,
    BehaviorSpec,
    ChecklistItem,
    Checklist,
    CoordinationCommand,
    WorkflowAction,
    ExitCondition,
    WorkflowStage,
    Workflow,
    # Modified dataclasses
    ConstraintSpec,
    ProcedureStep,
    RoleSpec,
    # New canonical dicts
    CHECKLIST_SPECS,
    COORDINATION_COMMANDS,
    WORKFLOW_SPECS,
    # Existing dicts
    ROLE_SPECS,
    CONSTRAINT_SPECS,
    # Supporting types
    RoleId,
    PhaseId,
)


# ─── New Enum Tests ───────────────────────────────────────────────────────────


class TestExampleLabel:
    def test_all_values_present(self) -> None:
        values = {e.value for e in ExampleLabel}
        assert values == {"correct", "anti-pattern", "context", "template"}

    def test_is_str(self) -> None:
        assert isinstance(ExampleLabel.CORRECT, str)
        assert ExampleLabel.CORRECT == "correct"

    def test_anti_pattern_value(self) -> None:
        assert ExampleLabel.ANTI_PATTERN == "anti-pattern"


class TestExampleLang:
    def test_all_values_present(self) -> None:
        values = {e.value for e in ExampleLang}
        assert values == {"bash", "go", "python", "pseudo", "xml", "json", "markdown"}

    def test_is_str(self) -> None:
        assert isinstance(ExampleLang.BASH, str)


class TestGateType:
    def test_all_values_present(self) -> None:
        values = {e.value for e in GateType}
        assert values == {"completion", "slice-closure", "review-ready", "landing"}

    def test_slice_closure_value(self) -> None:
        assert GateType.SLICE_CLOSURE == "slice-closure"


class TestWorkflowExecution:
    def test_all_values_present(self) -> None:
        values = {e.value for e in WorkflowExecution}
        assert values == {"sequential", "parallel", "conditional-loop"}

    def test_conditional_loop_value(self) -> None:
        assert WorkflowExecution.CONDITIONAL_LOOP == "conditional-loop"


class TestExitConditionType:
    def test_all_values_present(self) -> None:
        values = {e.value for e in ExitConditionType}
        assert values == {"success", "continue", "escalate", "proceed"}

    def test_is_str(self) -> None:
        assert isinstance(ExitConditionType.SUCCESS, str)


# ─── New Dataclass Tests ──────────────────────────────────────────────────────


class TestCodeExample:
    def test_frozen(self) -> None:
        ex = CodeExample(
            id="ex-1", lang=ExampleLang.BASH, label=ExampleLabel.CORRECT, code="echo hello"
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ex.code = "changed"  # type: ignore[misc]

    def test_also_illustrates_defaults_none(self) -> None:
        ex = CodeExample(
            id="ex-1", lang=ExampleLang.PYTHON, label=ExampleLabel.ANTI_PATTERN, code="pass"
        )
        assert ex.also_illustrates is None

    def test_all_fields(self) -> None:
        ex = CodeExample(
            id="ex-1",
            lang=ExampleLang.GO,
            label=ExampleLabel.CONTEXT,
            code="package main",
            also_illustrates="C-some-constraint",
        )
        assert ex.id == "ex-1"
        assert ex.lang == ExampleLang.GO
        assert ex.label == ExampleLabel.CONTEXT
        assert ex.also_illustrates == "C-some-constraint"


class TestBehaviorSpec:
    def test_frozen(self) -> None:
        b = BehaviorSpec(
            id="B-1", given="a", when="b", then="c", should_not="d"
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            b.given = "changed"  # type: ignore[misc]

    def test_all_fields(self) -> None:
        b = BehaviorSpec(
            id="B-test",
            given="condition",
            when="action",
            then="outcome",
            should_not="anti-pattern",
        )
        assert b.id == "B-test"
        assert b.given == "condition"


class TestChecklistItem:
    def test_frozen(self) -> None:
        item = ChecklistItem(id="CL-1", text="do something")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            item.text = "changed"  # type: ignore[misc]

    def test_required_defaults_true(self) -> None:
        item = ChecklistItem(id="CL-1", text="test")
        assert item.required is True

    def test_optional_item(self) -> None:
        item = ChecklistItem(id="CL-1", text="nice to have", required=False)
        assert item.required is False


class TestChecklist:
    def test_frozen(self) -> None:
        cl = Checklist(role_ref=RoleId.WORKER, gate=GateType.COMPLETION, items=())
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cl.gate = GateType.LANDING  # type: ignore[misc]

    def test_items_is_tuple(self) -> None:
        items = (ChecklistItem(id="CL-1", text="x"),)
        cl = Checklist(role_ref=RoleId.WORKER, gate=GateType.COMPLETION, items=items)
        assert isinstance(cl.items, tuple)


class TestCoordinationCommand:
    def test_frozen(self) -> None:
        cmd = CoordinationCommand(id="c-1", action="do", template="bd show <id>")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cmd.template = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        cmd = CoordinationCommand(id="c-1", action="do", template="bd show <id>")
        assert cmd.role_ref is None
        assert cmd.shared is False


class TestWorkflowAction:
    def test_frozen(self) -> None:
        action = WorkflowAction(id="a-1", instruction="do something")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            action.instruction = "changed"  # type: ignore[misc]

    def test_command_defaults_none(self) -> None:
        action = WorkflowAction(id="a-1", instruction="do something")
        assert action.command is None


class TestExitCondition:
    def test_frozen(self) -> None:
        ec = ExitCondition(type=ExitConditionType.SUCCESS, condition="all pass")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ec.condition = "changed"  # type: ignore[misc]

    def test_type_is_exit_condition_type_not_str(self) -> None:
        """ExitCondition.type MUST be ExitConditionType, NOT plain str."""
        ec = ExitCondition(type=ExitConditionType.ESCALATE, condition="blockers remain")
        assert isinstance(ec.type, ExitConditionType), (
            f"ExitCondition.type should be ExitConditionType, got {type(ec.type)}"
        )
        assert ec.type == ExitConditionType.ESCALATE

    def test_all_exit_condition_types_usable(self) -> None:
        for ect in ExitConditionType:
            ec = ExitCondition(type=ect, condition="test")
            assert isinstance(ec.type, ExitConditionType)


class TestWorkflowStage:
    def test_frozen(self) -> None:
        stage = WorkflowStage(
            id="s-1", name="Stage", order=1, execution=WorkflowExecution.SEQUENTIAL
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            stage.name = "changed"  # type: ignore[misc]

    def test_optional_fields_default(self) -> None:
        stage = WorkflowStage(
            id="s-1", name="Stage", order=1, execution=WorkflowExecution.PARALLEL
        )
        assert stage.phase_ref is None
        assert stage.actions == ()
        assert stage.exit_conditions == ()


class TestWorkflow:
    def test_frozen(self) -> None:
        wf = Workflow(
            id="wf-1",
            name="My Workflow",
            role_ref=RoleId.WORKER,
            description="desc",
            stages=(),
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            wf.name = "changed"  # type: ignore[misc]

    def test_stages_is_tuple(self) -> None:
        wf = Workflow(
            id="wf-1",
            name="My Workflow",
            role_ref=RoleId.SUPERVISOR,
            description="desc",
            stages=(
                WorkflowStage(
                    id="s-1", name="Stage", order=1, execution=WorkflowExecution.SEQUENTIAL
                ),
            ),
        )
        assert isinstance(wf.stages, tuple)
        assert len(wf.stages) == 1


# ─── Modified Dataclass Backward Compat Tests ─────────────────────────────────


class TestConstraintSpecBackwardCompat:
    def test_existing_usage_still_works(self) -> None:
        cs = ConstraintSpec(
            id="C-test",
            given="condition",
            when="action",
            then="outcome",
            should_not="bad",
        )
        assert cs.command is None
        assert cs.examples == ()

    def test_new_fields_usable(self) -> None:
        ex = CodeExample(
            id="ex-1", lang=ExampleLang.BASH, label=ExampleLabel.CORRECT, code="git agent-commit"
        )
        cs = ConstraintSpec(
            id="C-agent-commit",
            given="code ready",
            when="committing",
            then="use git agent-commit",
            should_not="use git commit",
            command="git agent-commit -m ...",
            examples=(ex,),
        )
        assert cs.command == "git agent-commit -m ..."
        assert len(cs.examples) == 1
        assert cs.examples[0].lang == ExampleLang.BASH

    def test_frozen(self) -> None:
        cs = ConstraintSpec(
            id="C-test", given="a", when="b", then="c", should_not="d"
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cs.given = "changed"  # type: ignore[misc]


class TestProcedureStepBackwardCompat:
    def test_existing_usage_still_works(self) -> None:
        ps = ProcedureStep(id="S-test", order=1, instruction="do it")
        assert ps.examples == ()
        assert ps.command is None
        assert ps.context is None
        assert ps.next_state is None

    def test_examples_field_usable(self) -> None:
        ex = CodeExample(
            id="ex-1", lang=ExampleLang.BASH, label=ExampleLabel.CORRECT, code="bd show <id>"
        )
        ps = ProcedureStep(
            id="S-test", order=1, instruction="check task", command="bd show <id>",
            examples=(ex,),
        )
        assert len(ps.examples) == 1


class TestRoleSpecBackwardCompat:
    def test_existing_usage_still_works(self) -> None:
        rs = RoleSpec(
            id=RoleId.WORKER,
            name="Worker",
            description="desc",
            owned_phases=frozenset({PhaseId.P9_SLICE}),
        )
        assert rs.introduction is None
        assert rs.ownership_narrative is None
        assert rs.behaviors == ()

    def test_new_fields_usable(self) -> None:
        beh = BehaviorSpec(
            id="B-test", given="a", when="b", then="c", should_not="d"
        )
        rs = RoleSpec(
            id=RoleId.WORKER,
            name="Worker",
            description="desc",
            owned_phases=frozenset({PhaseId.P9_SLICE}),
            introduction="You own a slice.",
            ownership_narrative="Full vertical slice ownership.",
            behaviors=(beh,),
        )
        assert rs.introduction == "You own a slice."
        assert len(rs.behaviors) == 1


# ─── Canonical Dict Tests ─────────────────────────────────────────────────────


class TestChecklistSpecs:
    def test_non_empty(self) -> None:
        assert len(CHECKLIST_SPECS) > 0

    def test_worker_completion_present(self) -> None:
        assert "worker-completion" in CHECKLIST_SPECS

    def test_worker_completion_structure(self) -> None:
        cl = CHECKLIST_SPECS["worker-completion"]
        assert cl.role_ref == RoleId.WORKER
        assert cl.gate == GateType.COMPLETION
        assert len(cl.items) >= 3

    def test_all_items_have_ids(self) -> None:
        for key, cl in CHECKLIST_SPECS.items():
            for item in cl.items:
                assert item.id, f"item in {key} has no id"

    def test_keys_follow_convention(self) -> None:
        """Keys must be '{role}-{gate}' format."""
        for key in CHECKLIST_SPECS:
            assert "-" in key, f"key '{key}' does not follow '{{role}}-{{gate}}' convention"


class TestCoordinationCommands:
    def test_non_empty(self) -> None:
        assert len(COORDINATION_COMMANDS) > 0

    def test_shared_commands_present(self) -> None:
        shared = [c for c in COORDINATION_COMMANDS.values() if c.shared]
        assert len(shared) >= 3, "Expected at least 3 shared coordination commands"

    def test_shared_commands_have_no_role_ref(self) -> None:
        for cmd in COORDINATION_COMMANDS.values():
            if cmd.shared:
                assert cmd.role_ref is None, (
                    f"Shared command {cmd.id} should have role_ref=None"
                )

    def test_all_commands_have_templates(self) -> None:
        for cmd in COORDINATION_COMMANDS.values():
            assert cmd.template, f"command {cmd.id} has empty template"


class TestWorkflowSpecs:
    def test_three_workflows_present(self) -> None:
        assert len(WORKFLOW_SPECS) == 3

    def test_expected_workflow_ids(self) -> None:
        assert "ride-the-wave" in WORKFLOW_SPECS
        assert "layer-cake" in WORKFLOW_SPECS
        assert "architect-state-flow" in WORKFLOW_SPECS

    def test_ride_the_wave_role(self) -> None:
        wf = WORKFLOW_SPECS["ride-the-wave"]
        assert wf.role_ref == RoleId.SUPERVISOR

    def test_layer_cake_role(self) -> None:
        wf = WORKFLOW_SPECS["layer-cake"]
        assert wf.role_ref == RoleId.WORKER

    def test_architect_state_flow_role(self) -> None:
        wf = WORKFLOW_SPECS["architect-state-flow"]
        assert wf.role_ref == RoleId.ARCHITECT

    def test_ride_the_wave_has_three_stages(self) -> None:
        wf = WORKFLOW_SPECS["ride-the-wave"]
        assert len(wf.stages) == 3

    def test_layer_cake_has_three_stages(self) -> None:
        wf = WORKFLOW_SPECS["layer-cake"]
        assert len(wf.stages) == 3

    def test_architect_state_flow_has_seven_stages(self) -> None:
        wf = WORKFLOW_SPECS["architect-state-flow"]
        assert len(wf.stages) == 7

    def test_all_exit_conditions_use_exit_condition_type(self) -> None:
        """Critical: ExitCondition.type must be ExitConditionType, not str."""
        for wf_id, wf in WORKFLOW_SPECS.items():
            for stage in wf.stages:
                for ec in stage.exit_conditions:
                    assert isinstance(ec.type, ExitConditionType), (
                        f"workflow '{wf_id}', stage '{stage.id}': "
                        f"exit_condition.type is {type(ec.type)}, expected ExitConditionType"
                    )

    def test_stages_have_increasing_order(self) -> None:
        for wf_id, wf in WORKFLOW_SPECS.items():
            orders = [s.order for s in wf.stages]
            assert orders == sorted(orders), (
                f"workflow '{wf_id}' stages are not in ascending order: {orders}"
            )


# ─── Updated ROLE_SPECS Tests ──────────────────────────────────────────────────


class TestRoleSpecsUpdated:
    def test_supervisor_has_introduction(self) -> None:
        sup = ROLE_SPECS[RoleId.SUPERVISOR]
        assert sup.introduction is not None
        assert len(sup.introduction) > 0

    def test_supervisor_has_ownership_narrative(self) -> None:
        sup = ROLE_SPECS[RoleId.SUPERVISOR]
        assert sup.ownership_narrative is not None

    _ROLES_WITH_BEHAVIORS = [
        RoleId.SUPERVISOR, RoleId.WORKER, RoleId.ARCHITECT, RoleId.REVIEWER,
    ]

    @pytest.mark.parametrize("role_id", _ROLES_WITH_BEHAVIORS)
    def test_every_impl_role_has_at_least_one_behavior(self, role_id: RoleId) -> None:
        role = ROLE_SPECS[role_id]
        assert len(role.behaviors) >= 1, (
            f"Role {role_id.value} has no behaviors defined"
        )

    @pytest.mark.parametrize("role_id", _ROLES_WITH_BEHAVIORS)
    def test_all_behaviors_have_non_empty_fields(self, role_id: RoleId) -> None:
        """Every behavior must have non-empty given/when/then/should_not."""
        role = ROLE_SPECS[role_id]
        for b in role.behaviors:
            assert b.id, f"Role {role_id.value}: behavior has empty id"
            assert b.given, f"Role {role_id.value}, {b.id}: empty 'given'"
            assert b.when, f"Role {role_id.value}, {b.id}: empty 'when'"
            assert b.then, f"Role {role_id.value}, {b.id}: empty 'then'"
            assert b.should_not, f"Role {role_id.value}, {b.id}: empty 'should_not'"

    def test_all_behavior_ids_unique_within_role(self) -> None:
        for role_id, role_spec in ROLE_SPECS.items():
            ids = [b.id for b in role_spec.behaviors]
            assert len(ids) == len(set(ids)), (
                f"role {role_id}: duplicate behavior ids: {ids}"
            )

    def test_existing_roles_still_have_correct_owned_phases(self) -> None:
        """Backward compat: owned_phases unchanged by new fields."""
        assert PhaseId.P9_SLICE in ROLE_SPECS[RoleId.WORKER].owned_phases
        assert PhaseId.P8_IMPL_PLAN in ROLE_SPECS[RoleId.SUPERVISOR].owned_phases
        assert PhaseId.P3_PROPOSE in ROLE_SPECS[RoleId.ARCHITECT].owned_phases


# ─── Updated CONSTRAINT_SPECS Tests ───────────────────────────────────────────


class TestConstraintSpecsUpdated:
    def test_agent_commit_has_command(self) -> None:
        cs = CONSTRAINT_SPECS["C-agent-commit"]
        assert cs.command is not None
        assert "git agent-commit" in cs.command

    def test_dep_direction_has_command(self) -> None:
        cs = CONSTRAINT_SPECS["C-dep-direction"]
        assert cs.command is not None
        assert "bd dep add" in cs.command

    def test_audit_dep_chain_has_command(self) -> None:
        cs = CONSTRAINT_SPECS["C-audit-dep-chain"]
        assert cs.command is not None
        assert "bd dep add" in cs.command

    def test_existing_constraints_backward_compat(self) -> None:
        """Constraints without explicit command still work (command=None)."""
        cs = CONSTRAINT_SPECS["C-review-consensus"]
        assert cs.command is None
        assert cs.examples == ()
