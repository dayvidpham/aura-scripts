"""Tests for aura_protocol.interfaces.

Covers:
- AC9: Protocol isinstance() checks (structural subtyping, no inheritance required)
- AC10: ModelId.parse() validates format correctly
- A2A Part union type coverage (TextPart, FilePart, DataPart)
- ToolCall creation
- Event stub re-exports are accessible from interfaces module
- Frozen dataclass immutability for A2A types and ModelId
"""

from __future__ import annotations

import asyncio

import pytest

from aura_protocol.constraints import RuntimeConstraintChecker
from aura_protocol.interfaces import (
    AuditEvent,
    AuditTrail,
    ConstraintCheckEvent,
    ConstraintValidatorInterface,
    DataPart,
    FilePart,
    ModelId,
    Part,
    PermissionDecision,
    PhaseTransitionEvent,
    ReviewVoteEvent,
    SecurityGate,
    TextPart,
    ToolCall,
    ToolPermissionRequest,
    TranscriptRecorder,
)
from aura_protocol.types import PhaseId, RoleId, VoteType


# ─── AC9: Protocol isinstance() checks ───────────────────────────────────────


class TestConstraintValidatorInterfaceProtocol:
    """AC9: ConstraintValidatorInterface structural subtyping."""

    def test_isinstance_true_for_matching_class(self) -> None:
        """Given class with validate() method when isinstance checked then True."""

        class ConcreteValidator:
            def validate(self, state: object) -> list:
                return []

        validator = ConcreteValidator()
        assert isinstance(validator, ConstraintValidatorInterface)

    def test_isinstance_false_without_validate_method(self) -> None:
        """Given class without validate() when isinstance checked then False."""

        class NotAValidator:
            def check(self, state: object) -> list:
                return []

        obj = NotAValidator()
        assert not isinstance(obj, ConstraintValidatorInterface)

    def test_does_not_require_subclassing(self) -> None:
        """Should not require subclassing ConstraintValidatorInterface."""

        class IndependentValidator:
            """Completely independent class — no inheritance from interface."""

            def validate(self, state: object) -> list:
                return []

        # Must be True without any inheritance
        assert IndependentValidator.__bases__ == (object,)
        assert isinstance(IndependentValidator(), ConstraintValidatorInterface)

    def test_plain_object_fails(self) -> None:
        """Given plain object with no matching methods then isinstance is False."""
        assert not isinstance(object(), ConstraintValidatorInterface)

    def test_runtime_constraint_checker_satisfies_interface(self) -> None:
        """AC8: RuntimeConstraintChecker must satisfy ConstraintValidatorInterface.

        Given RuntimeConstraintChecker (which has a validate() method) when
        isinstance checked against ConstraintValidatorInterface then True.

        This verifies that the production checker implements the public protocol
        contract via structural subtyping — no explicit inheritance required.
        """
        checker = RuntimeConstraintChecker()
        assert isinstance(checker, ConstraintValidatorInterface)


class TestTranscriptRecorderProtocol:
    """AC9: TranscriptRecorder structural subtyping."""

    def test_isinstance_true_for_matching_class(self) -> None:
        """Given class with all 3 async methods when isinstance checked then True."""

        class ConcreteRecorder:
            async def record_phase_transition(self, event: object) -> None:
                pass

            async def record_constraint_check(self, event: object) -> None:
                pass

            async def record_review_vote(self, event: object) -> None:
                pass

        recorder = ConcreteRecorder()
        assert isinstance(recorder, TranscriptRecorder)

    def test_isinstance_false_missing_method(self) -> None:
        """Given class missing one method when isinstance checked then False."""

        class IncompleteRecorder:
            async def record_phase_transition(self, event: object) -> None:
                pass

            async def record_constraint_check(self, event: object) -> None:
                pass

            # Missing: record_review_vote

        obj = IncompleteRecorder()
        assert not isinstance(obj, TranscriptRecorder)

    def test_does_not_require_subclassing(self) -> None:
        """Should not require subclassing TranscriptRecorder."""

        class StandaloneRecorder:
            async def record_phase_transition(self, event: object) -> None:
                pass

            async def record_constraint_check(self, event: object) -> None:
                pass

            async def record_review_vote(self, event: object) -> None:
                pass

        assert StandaloneRecorder.__bases__ == (object,)
        assert isinstance(StandaloneRecorder(), TranscriptRecorder)


class TestSecurityGateProtocol:
    """AC9: SecurityGate structural subtyping."""

    def test_isinstance_true_for_matching_class(self) -> None:
        """Given class with check_tool_permission() when isinstance checked then True."""

        class ConcreteGate:
            async def check_tool_permission(self, request: object) -> PermissionDecision:
                return PermissionDecision(allowed=True)

        gate = ConcreteGate()
        assert isinstance(gate, SecurityGate)

    def test_isinstance_false_without_method(self) -> None:
        """Given class without check_tool_permission() then isinstance is False."""

        class NotAGate:
            async def allow_all(self, request: object) -> bool:
                return True

        obj = NotAGate()
        assert not isinstance(obj, SecurityGate)

    def test_does_not_require_subclassing(self) -> None:
        """Should not require subclassing SecurityGate."""

        class ExternalGate:
            async def check_tool_permission(self, request: object) -> PermissionDecision:
                return PermissionDecision(allowed=False, reason="denied")

        assert ExternalGate.__bases__ == (object,)
        assert isinstance(ExternalGate(), SecurityGate)


class TestAuditTrailProtocol:
    """AC9: AuditTrail structural subtyping."""

    def test_isinstance_true_for_matching_class(self) -> None:
        """Given class with record_event() and query_events() then isinstance is True."""

        class ConcreteAuditTrail:
            async def record_event(self, event: object) -> None:
                pass

            async def query_events(
                self, *, phase: object = None, role: object = None
            ) -> list:
                return []

        trail = ConcreteAuditTrail()
        assert isinstance(trail, AuditTrail)

    def test_isinstance_false_missing_query_method(self) -> None:
        """Given class missing query_events() then isinstance is False."""

        class IncompleteTrail:
            async def record_event(self, event: object) -> None:
                pass

            # Missing: query_events

        obj = IncompleteTrail()
        assert not isinstance(obj, AuditTrail)

    def test_does_not_require_subclassing(self) -> None:
        """Should not require subclassing AuditTrail."""

        class ExternalAuditTrail:
            async def record_event(self, event: object) -> None:
                pass

            async def query_events(
                self, *, phase: object = None, role: object = None
            ) -> list:
                return []

        assert ExternalAuditTrail.__bases__ == (object,)
        assert isinstance(ExternalAuditTrail(), AuditTrail)


# ─── AC10: ModelId.parse() ────────────────────────────────────────────────────


class TestModelIdParse:
    """AC10: ModelId.parse() validates provider/model format."""

    def test_parse_simple_model_id(self) -> None:
        """Given 'anthropic/claude-opus-4-6' when parsed then correct fields."""
        m = ModelId.parse("anthropic/claude-opus-4-6")
        assert m.provider == "anthropic"
        assert m.model == "claude-opus-4-6"

    def test_parse_openai_model(self) -> None:
        """Given 'openai/gpt-4o' when parsed then provider='openai', model='gpt-4o'."""
        m = ModelId.parse("openai/gpt-4o")
        assert m.provider == "openai"
        assert m.model == "gpt-4o"

    def test_parse_splits_on_first_slash_only(self) -> None:
        """Given 'a/b/c' when parsed then provider='a', model='b/c'."""
        m = ModelId.parse("a/b/c")
        assert m.provider == "a"
        assert m.model == "b/c"

    def test_parse_model_with_multiple_slashes(self) -> None:
        """Given 'provider/org/team/model' when parsed then provider='provider', model='org/team/model'."""
        m = ModelId.parse("provider/org/team/model")
        assert m.provider == "provider"
        assert m.model == "org/team/model"

    def test_parse_invalid_no_slash_raises_value_error(self) -> None:
        """Given string without '/' when parsed then ValueError raised."""
        with pytest.raises(ValueError, match="Invalid model ID"):
            ModelId.parse("invalid-no-slash")

    def test_parse_empty_string_raises_value_error(self) -> None:
        """Given empty string when parsed then ValueError raised."""
        with pytest.raises(ValueError):
            ModelId.parse("")

    def test_parse_only_slash_raises_value_error(self) -> None:
        """Given '/' only when parsed then ValueError (empty provider)."""
        with pytest.raises(ValueError):
            ModelId.parse("/")

    def test_parse_leading_slash_raises_value_error(self) -> None:
        """Given '/model' when parsed then ValueError (empty provider)."""
        with pytest.raises(ValueError):
            ModelId.parse("/model")

    def test_parse_trailing_slash_raises_value_error(self) -> None:
        """Given 'provider/' when parsed then ValueError (empty model)."""
        with pytest.raises(ValueError):
            ModelId.parse("provider/")

    def test_str_roundtrip(self) -> None:
        """Given ModelId when str() called then original format restored."""
        original = "anthropic/claude-opus-4-6"
        m = ModelId.parse(original)
        assert str(m) == original

    def test_model_id_is_frozen(self) -> None:
        """Given ModelId instance when field assignment attempted then raises."""
        m = ModelId.parse("anthropic/claude-opus-4-6")
        with pytest.raises(Exception):
            m.provider = "openai"  # type: ignore[misc]

    def test_model_id_equality(self) -> None:
        """Given two ModelIds with same fields when compared then equal."""
        m1 = ModelId.parse("anthropic/claude-opus-4-6")
        m2 = ModelId(provider="anthropic", model="claude-opus-4-6")
        assert m1 == m2

    def test_model_id_hashable(self) -> None:
        """Given frozen ModelId when used as dict key then works."""
        m = ModelId.parse("anthropic/claude-opus-4-6")
        d = {m: "value"}
        assert d[m] == "value"


# ─── A2A Part Union ───────────────────────────────────────────────────────────


class TestA2APartTypes:
    """Part union covers TextPart, FilePart, DataPart."""

    def test_text_part_creation(self) -> None:
        part = TextPart(text="hello world")
        assert part.text == "hello world"

    def test_file_part_creation(self) -> None:
        part = FilePart(file_uri="file:///path/to/file.py", mime_type="text/x-python")
        assert part.file_uri == "file:///path/to/file.py"
        assert part.mime_type == "text/x-python"

    def test_file_part_optional_mime_type(self) -> None:
        part = FilePart(file_uri="file:///path/to/data")
        assert part.mime_type is None

    def test_data_part_creation(self) -> None:
        payload = {"key": "value", "count": 42}
        part = DataPart(data=payload)
        assert part.data == payload

    def test_text_part_is_part_union(self) -> None:
        """TextPart is an instance of TextPart (member of Part union)."""
        part: Part = TextPart(text="test")
        assert isinstance(part, TextPart)

    def test_file_part_is_part_union(self) -> None:
        """FilePart is an instance of FilePart (member of Part union)."""
        part: Part = FilePart(file_uri="file:///x")
        assert isinstance(part, FilePart)

    def test_data_part_is_part_union(self) -> None:
        """DataPart is an instance of DataPart (member of Part union)."""
        part: Part = DataPart(data={})
        assert isinstance(part, DataPart)

    def test_text_part_is_frozen(self) -> None:
        part = TextPart(text="immutable")
        with pytest.raises(Exception):
            part.text = "mutated"  # type: ignore[misc]

    def test_file_part_is_frozen(self) -> None:
        part = FilePart(file_uri="file:///x")
        with pytest.raises(Exception):
            part.file_uri = "file:///y"  # type: ignore[misc]

    def test_data_part_is_frozen(self) -> None:
        part = DataPart(data={"x": 1})
        with pytest.raises(Exception):
            part.data = {}  # type: ignore[misc]


# ─── ToolCall ─────────────────────────────────────────────────────────────────


class TestToolCall:
    """ToolCall creation and immutability."""

    def test_tool_call_creation(self) -> None:
        tc = ToolCall(tool_name="bash", tool_input={"command": "ls -la"})
        assert tc.tool_name == "bash"
        assert tc.tool_input == {"command": "ls -la"}
        assert tc.tool_output is None

    def test_tool_call_with_output(self) -> None:
        tc = ToolCall(
            tool_name="bash",
            tool_input={"command": "echo hello"},
            tool_output={"stdout": "hello\n", "exit_code": 0},
        )
        assert tc.tool_output == {"stdout": "hello\n", "exit_code": 0}

    def test_tool_call_is_frozen(self) -> None:
        tc = ToolCall(tool_name="tool", tool_input={})
        with pytest.raises(Exception):
            tc.tool_name = "other"  # type: ignore[misc]

    def test_tool_call_is_hashable(self) -> None:
        """Frozen dataclass should be hashable when fields are hashable."""
        # Note: dict fields make this not directly hashable — this documents that
        # expected behavior. ToolCall with dict fields is NOT hashable.
        tc = ToolCall(tool_name="bash", tool_input={"cmd": "ls"})
        with pytest.raises(TypeError):
            hash(tc)


# ─── Event Stub Re-exports ────────────────────────────────────────────────────


class TestEventStubReExports:
    """Event stub types must be importable from interfaces module."""

    def test_phase_transition_event_importable(self) -> None:
        """PhaseTransitionEvent is re-exported from interfaces."""
        event = PhaseTransitionEvent(
            epoch_id="epoch-1",
            from_phase=PhaseId.P1_REQUEST,
            to_phase=PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="classification confirmed",
        )
        assert event.from_phase == PhaseId.P1_REQUEST
        assert event.to_phase == PhaseId.P2_ELICIT

    def test_constraint_check_event_importable(self) -> None:
        """ConstraintCheckEvent is re-exported from interfaces."""
        event = ConstraintCheckEvent(
            epoch_id="epoch-1",
            phase=PhaseId.P4_REVIEW,
            constraint_id="C-review-consensus",
            passed=False,
            message="Only 2 of 3 votes",
        )
        assert not event.passed

    def test_review_vote_event_importable(self) -> None:
        """ReviewVoteEvent is re-exported from interfaces."""
        event = ReviewVoteEvent(
            epoch_id="epoch-1",
            phase=PhaseId.P4_REVIEW,
            axis="A",
            vote=VoteType.ACCEPT,
            reviewer_id="reviewer-a",
        )
        assert event.vote == VoteType.ACCEPT

    def test_audit_event_importable(self) -> None:
        """AuditEvent is re-exported from interfaces.

        payload is dict[str, Any] — structured event details, not a JSON string.
        """
        event = AuditEvent(
            epoch_id="epoch-1",
            event_type="phase_transition",
            phase=PhaseId.P9_SLICE,
            role=RoleId.SUPERVISOR,
            payload={"from": "p8", "to": "p9"},
        )
        assert event.event_type == "phase_transition"

    def test_tool_permission_request_importable(self) -> None:
        """ToolPermissionRequest is re-exported from interfaces."""
        req = ToolPermissionRequest(
            epoch_id="epoch-1",
            phase=PhaseId.P9_SLICE,
            role=RoleId.WORKER,
            tool_name="bash",
            tool_input_summary="ls -la",
        )
        assert req.tool_name == "bash"

    def test_permission_decision_importable(self) -> None:
        """PermissionDecision is re-exported from interfaces."""
        decision = PermissionDecision(allowed=True, reason=None)
        assert decision.allowed

    def test_event_stubs_are_frozen(self) -> None:
        """Re-exported event stubs must remain frozen (immutable)."""
        event = PhaseTransitionEvent(
            epoch_id="epoch-1",
            from_phase=PhaseId.P1_REQUEST,
            to_phase=PhaseId.P2_ELICIT,
            triggered_by="architect",
            condition_met="confirmed",
        )
        with pytest.raises(Exception):
            event.epoch_id = "mutated"  # type: ignore[misc]
