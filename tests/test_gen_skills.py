"""Tests for scripts/aura_protocol/gen_skills.py.

Acceptance Criteria covered:
- AC4:  Given SKILL.md with markers, header updated, body preserved.
- AC4a: MarkerError raised on missing markers (UAT-5) — no silent prepending.
- AC4a: MarkerError raised on malformed markers (reversed order, duplicates).
- AC2a: Unified diff printed to stdout when content changes (UAT-2).
- AC8:  Jinja2 templates render with StrictUndefined, parametrized over 4 roles.
"""

from __future__ import annotations

import pathlib
import re

import jinja2
import pytest

from aura_protocol.gen_skills import (
    GENERATED_BEGIN,
    GENERATED_END,
    MarkerError,
    generate_skill,
)
from aura_protocol.types import RoleId

# ─── Constants ────────────────────────────────────────────────────────────────

# The 4 roles the generator must support (AC8)
ALL_ROLES = [
    RoleId.SUPERVISOR,
    RoleId.WORKER,
    RoleId.REVIEWER,
    RoleId.ARCHITECT,
]

# Template directory relative to the repo root (resolved at import time)
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE_DIR = _REPO_ROOT / "skills" / "templates"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_skill_file(
    tmp_path: pathlib.Path,
    content: str,
    filename: str = "SKILL.md",
) -> pathlib.Path:
    """Write *content* to a temp SKILL.md and return its path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def _minimal_with_markers(body: str = "") -> str:
    """Return minimal SKILL.md text containing valid markers and optional body."""
    lines = [
        "---",
        "name: test",
        "---",
        GENERATED_BEGIN,
        "(old generated content)",
        GENERATED_END,
    ]
    content = "\n".join(lines) + "\n"
    if body:
        content += body
    return content


# ─── AC4: Header updated, body preserved ──────────────────────────────────────


class TestHeaderUpdatedBodyPreserved:
    """AC4: generate_skill() updates the header but keeps hand-authored body."""

    def test_body_below_end_marker_is_preserved(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Hand-authored body below END marker must be unchanged after generation."""
        hand_authored = "## Hand-authored section\n\nDo not overwrite me.\n"
        content = _minimal_with_markers(body=hand_authored)
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert hand_authored in result, (
            "Hand-authored body below END marker was not preserved in output."
        )

    def test_generated_header_contains_role_name(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Generated section should mention the role name."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert "Worker" in result, (
            "Generated header should contain role name 'Worker'."
        )

    def test_markers_present_in_output(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Output must contain both BEGIN and END markers."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert GENERATED_BEGIN in result
        assert GENERATED_END in result

    def test_begin_marker_before_end_marker_in_output(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """BEGIN marker must appear before END marker in output."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        begin_pos = result.index(GENERATED_BEGIN)
        end_pos = result.index(GENERATED_END)
        assert begin_pos < end_pos, (
            "BEGIN marker must appear before END marker in generated output."
        )

    def test_write_true_updates_file_on_disk(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """With write=True, the file on disk is updated."""
        old_body = "## Old generated\n(will be replaced)\n"
        content = _minimal_with_markers(body="## Preserved body\n")
        skill_path = _make_skill_file(tmp_path, content)

        generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=True,
        )

        written = skill_path.read_text(encoding="utf-8")
        assert GENERATED_BEGIN in written
        assert GENERATED_END in written

    def test_write_false_does_not_touch_file(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """With write=False, the file on disk is unchanged."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert skill_path.read_text(encoding="utf-8") == content


# ─── AC4a: MarkerError on missing markers ─────────────────────────────────────


class TestMarkerErrorMissingMarkers:
    """AC4a / UAT-5: MarkerError raised on missing markers — no silent prepending."""

    def test_missing_both_markers_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """File with no markers at all must raise MarkerError."""
        content = "---\nname: unmarked\n---\n\n# No markers here.\n"
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )

    def test_missing_begin_marker_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """File with only END marker (BEGIN absent) must raise MarkerError."""
        content = f"---\nname: test\n---\n\nSome text\n{GENERATED_END}\n"
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )

    def test_missing_end_marker_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """File with only BEGIN marker (END absent) must raise MarkerError."""
        content = f"---\nname: test\n---\n\n{GENERATED_BEGIN}\nSome text\n"
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )

    def test_marker_error_message_describes_fix(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """MarkerError message must describe how to fix the problem."""
        content = "# No markers\n"
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError, match=r"(?i)(marker|begin|end)"):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )


# ─── AC4a: MarkerError on malformed markers ───────────────────────────────────


class TestMarkerErrorMalformedMarkers:
    """AC4a: MarkerError raised for malformed markers (reversed, duplicates)."""

    def test_reversed_markers_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """END before BEGIN must raise MarkerError."""
        content = (
            "---\nname: test\n---\n\n"
            f"{GENERATED_END}\n"
            "Some content\n"
            f"{GENERATED_BEGIN}\n"
        )
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )

    def test_duplicate_begin_marker_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Two BEGIN markers must raise MarkerError."""
        content = (
            f"{GENERATED_BEGIN}\n"
            "First header\n"
            f"{GENERATED_BEGIN}\n"
            "Second header\n"
            f"{GENERATED_END}\n"
        )
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )

    def test_duplicate_end_marker_raises_marker_error(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Two END markers must raise MarkerError."""
        content = (
            f"{GENERATED_BEGIN}\n"
            "Header\n"
            f"{GENERATED_END}\n"
            "body\n"
            f"{GENERATED_END}\n"
        )
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
            )


# ─── AC2a: Diff output ────────────────────────────────────────────────────────


class TestDiffOutput:
    """AC2a / UAT-2: Unified diff printed to stdout when content changes."""

    def test_diff_printed_when_content_changes(
        self,
        tmp_path: pathlib.Path,
        capsys,
    ) -> None:
        """generate_skill(..., diff=True) prints a unified diff when content changes."""
        # Minimal markers with old generated content that differs from new render
        old_generated = "Old content that will differ from new render\n"
        content = (
            f"{GENERATED_BEGIN}\n"
            f"{old_generated}"
            f"{GENERATED_END}\n"
        )
        skill_path = _make_skill_file(tmp_path, content)

        generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=True,
            write=False,
        )

        captured = capsys.readouterr()
        # Unified diff format starts with "---" or "+++" or "@@"
        assert captured.out, (
            "Expected diff output on stdout when content changes, but got nothing."
        )
        # Verify actual changed lines are present (not just file header lines).
        # Real changed lines start with exactly '-' or '+' followed by a non-dash/non-plus
        # character, distinguishing them from file header lines ('---'/'+++').
        assert any(
            (line.startswith("-") and not line.startswith("---"))
            or (line.startswith("+") and not line.startswith("+++"))
            for line in captured.out.splitlines()
        ), "stdout output does not contain actual changed lines (only headers or metadata)."

    def test_no_diff_printed_when_content_unchanged(
        self,
        tmp_path: pathlib.Path,
        capsys,
    ) -> None:
        """generate_skill(..., diff=True) prints nothing when content is identical."""
        # Pre-render the content and use it as existing file content
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        # First generation to get the real output
        first_result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        # Write first result as current file content
        skill_path.write_text(first_result, encoding="utf-8")
        capsys.readouterr()  # Clear captured output

        # Second generation — content should match, no diff expected
        generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=True,
            write=False,
        )

        captured = capsys.readouterr()
        assert captured.out == "", (
            "Expected no diff output when content is unchanged, "
            f"but got: {captured.out!r}"
        )

    def test_diff_false_produces_no_output(
        self,
        tmp_path: pathlib.Path,
        capsys,
    ) -> None:
        """generate_skill(..., diff=False) must not print anything."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        captured = capsys.readouterr()
        assert captured.out == "", (
            "Expected no stdout output with diff=False, "
            f"but got: {captured.out!r}"
        )


# ─── AC8: Template rendering with StrictUndefined ─────────────────────────────


class TestTemplateRenderingAllRoles:
    """AC8: Jinja2 templates render with StrictUndefined, parametrized over 4 roles."""

    @pytest.mark.parametrize("role_id", ALL_ROLES)
    def test_template_renders_without_error(
        self,
        role_id: RoleId,
        tmp_path: pathlib.Path,
    ) -> None:
        """Template must render successfully for each of the 4 roles."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content, filename=f"SKILL_{role_id.value}.md")

        # Must not raise any exception (including UndefinedError from StrictUndefined)
        result = generate_skill(
            role_id,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("role_id", ALL_ROLES)
    def test_rendered_output_contains_role_value(
        self,
        role_id: RoleId,
        tmp_path: pathlib.Path,
    ) -> None:
        """Rendered output must reference the role's id value."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content, filename=f"SKILL_{role_id.value}.md")

        result = generate_skill(
            role_id,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert role_id.value in result, (
            f"Expected role id '{role_id.value}' in rendered output for {role_id}."
        )

    @pytest.mark.parametrize("role_id", ALL_ROLES)
    def test_rendered_output_contains_markers(
        self,
        role_id: RoleId,
        tmp_path: pathlib.Path,
    ) -> None:
        """Rendered output must contain both markers for each role."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content, filename=f"SKILL_{role_id.value}.md")

        result = generate_skill(
            role_id,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert GENERATED_BEGIN in result, (
            f"BEGIN marker missing from output for role {role_id}."
        )
        assert GENERATED_END in result, (
            f"END marker missing from output for role {role_id}."
        )

    @pytest.mark.parametrize("role_id", ALL_ROLES)
    def test_body_preserved_for_all_roles(
        self,
        role_id: RoleId,
        tmp_path: pathlib.Path,
    ) -> None:
        """Hand-authored body must be preserved for each of the 4 roles."""
        body = f"## Hand-authored section for {role_id.value}\n\nKeep me.\n"
        content = _minimal_with_markers(body=body)
        skill_path = _make_skill_file(tmp_path, content, filename=f"SKILL_{role_id.value}.md")

        result = generate_skill(
            role_id,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert body in result, (
            f"Hand-authored body not preserved for role {role_id}."
        )


# ─── Startup Sequence section ─────────────────────────────────────────────────


class TestStartupSequenceSection:
    """Startup Sequence section rendered from PROCEDURE_STEPS (B4)."""

    def test_supervisor_output_contains_startup_sequence(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor SKILL.md must contain a Startup Sequence section."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert "### Startup Sequence" in result, (
            "Supervisor output must contain '### Startup Sequence' section."
        )

    def test_worker_output_contains_startup_sequence(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Worker SKILL.md must contain a Startup Sequence section."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert "### Startup Sequence" in result, (
            "Worker output must contain '### Startup Sequence' section."
        )

    def test_supervisor_startup_sequence_has_step_entries(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor startup sequence must list step entries."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        # Steps are rendered as "**Step N:** description"
        assert "**Step 1:**" in result, (
            "Supervisor startup sequence must have Step 1."
        )
        assert "**Step 4:**" in result, (
            "Supervisor startup sequence must have Step 4."
        )

    def test_supervisor_step4_shows_next_state(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor step 4 must show → `p8` transition."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        # Step 4 has next_state=PhaseId.P8_IMPL_PLAN so should render → `p8`
        assert "→ `p8`" in result, (
            "Supervisor step 4 must render '→ `p8`' transition."
        )

    def test_worker_step3_shows_next_state(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Worker step 3 must show → `p9` transition."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        # Step 3 has next_state=PhaseId.P9_SLICE so should render → `p9`
        assert "→ `p9`" in result, (
            "Worker step 3 must render '→ `p9`' transition."
        )

    def test_roles_without_steps_show_no_startup_sequence_message(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Roles without procedure steps render the 'no startup sequence' message."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.REVIEWER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert "_(No startup sequence defined for this role)_" in result, (
            "Reviewer (no steps) must render the no-startup-sequence placeholder."
        )


# ─── AC8: StrictUndefined regression protection ───────────────────────────────


class TestStrictUndefined:
    """AC8: Jinja2 StrictUndefined is active — undefined variables raise UndefinedError."""

    def test_undefined_variable_raises_undefined_error(self, tmp_path: pathlib.Path) -> None:
        """generate_skill() must raise jinja2.UndefinedError when the template references
        an undefined variable.

        This is a regression test for the StrictUndefined mode set in gen_skills.py.
        If someone removes ``undefined=StrictUndefined`` from the Environment
        constructor, this test will fail, catching the regression.

        The test goes through generate_skill() — NOT a manually constructed
        jinja2.Environment — so it exercises the actual production code path.
        """
        # (a) Create a temp template dir with skill_header.j2 containing an undefined var.
        #     The template file MUST be named skill_header.j2 — _render_header() loads it
        #     via env.get_template('skill_header.j2').  Any other name causes
        #     TemplateNotFound, not UndefinedError.
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "skill_header.j2").write_text(
            "{{ undefined_var }}", encoding="utf-8"
        )

        # (b) Create a valid SKILL.md with BEGIN/END markers at skill_path.
        #     Without valid markers generate_skill() raises MarkerError before rendering.
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text(
            f"{GENERATED_BEGIN}\n(placeholder)\n{GENERATED_END}\n",
            encoding="utf-8",
        )

        # generate_skill() must raise UndefinedError because skill_header.j2
        # references {{ undefined_var }} which is not provided to the render context.
        with pytest.raises(jinja2.UndefinedError):
            generate_skill(RoleId.SUPERVISOR, skill_path, template_dir=template_dir)


# ─── Marker string values ─────────────────────────────────────────────────────


class TestUpdatedMarkerStrings:
    """Marker constants must contain 'aura schema'."""

    def test_generated_begin_contains_aura_schema(self) -> None:
        """GENERATED_BEGIN must contain 'aura schema'."""
        assert "aura schema" in GENERATED_BEGIN, (
            f"GENERATED_BEGIN must contain 'aura schema', got: {GENERATED_BEGIN!r}"
        )

    def test_generated_end_contains_aura_schema(self) -> None:
        """GENERATED_END must contain 'aura schema'."""
        assert "aura schema" in GENERATED_END, (
            f"GENERATED_END must contain 'aura schema', got: {GENERATED_END!r}"
        )

    def test_begin_is_html_comment(self) -> None:
        """GENERATED_BEGIN must be a valid HTML comment."""
        assert GENERATED_BEGIN.startswith("<!--") and GENERATED_BEGIN.endswith("-->")

    def test_end_is_html_comment(self) -> None:
        """GENERATED_END must be a valid HTML comment."""
        assert GENERATED_END.startswith("<!--") and GENERATED_END.endswith("-->")


# ─── Init mode ─────────────────────────────────────────────────────────────────


class TestInitMode:
    """--init mode: prepend markers to unmarked files before generating."""

    def test_init_mode_adds_markers_to_unmarked_file(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """init=True prepends markers to a file without them, then generates header."""
        content = "# Hand-authored content\n\nKeep this body.\n"
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=True,
            init=True,
        )

        # Markers must be present in output
        assert GENERATED_BEGIN in result
        assert GENERATED_END in result
        # Original body must be preserved
        assert "Hand-authored content" in result
        assert "Keep this body." in result
        # File on disk must match
        written = skill_path.read_text(encoding="utf-8")
        assert written == result

    def test_init_mode_noop_on_marked_file(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """init=True doesn't double-add markers to a file that already has them."""
        content = _minimal_with_markers(body="## Existing body\n")
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
            init=True,
        )

        # Should have exactly one pair of markers
        assert result.count(GENERATED_BEGIN) == 1
        assert result.count(GENERATED_END) == 1
        # Body preserved
        assert "Existing body" in result

    def test_init_mode_false_raises_on_unmarked_file(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """init=False (default) still raises MarkerError on unmarked file."""
        content = "# No markers here\n"
        skill_path = _make_skill_file(tmp_path, content)

        with pytest.raises(MarkerError):
            generate_skill(
                RoleId.SUPERVISOR,
                skill_path,
                template_dir=TEMPLATE_DIR,
                diff=False,
                write=False,
                init=False,
            )

    def test_init_mode_generates_valid_header(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """init=True generates a valid header (not just empty markers)."""
        content = "# Worker skill\n"
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
            init=True,
        )

        # Header must contain role name from rendered template
        assert "Worker" in result
        # Must contain protocol sections
        assert "## Protocol Context" in result


# ─── ProcedureStep rendering ──────────────────────────────────────────────────


class TestProcedureStepsInGeneratedHeader:
    """ProcedureStep fields (instruction, command, context) rendered in SKILL.md."""

    def test_supervisor_has_step_instructions(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor steps must render instruction text."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        # Supervisor has steps — check that Step 1 instruction text is present
        assert "**Step 1:**" in result
        # The instruction text should be a non-empty string after "Step N:"
        lines = [l for l in result.splitlines() if "**Step 1:**" in l]
        assert len(lines) == 1
        # After "**Step 1:** " there should be instruction text
        step_line = lines[0]
        after_prefix = step_line.split("**Step 1:**")[1].strip()
        assert len(after_prefix) > 0, "Step 1 instruction text is empty"

    def test_worker_has_step_instructions(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Worker steps must render instruction text."""
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        result = generate_skill(
            RoleId.WORKER,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert "**Step 1:**" in result
        lines = [l for l in result.splitlines() if "**Step 1:**" in l]
        assert len(lines) == 1
        step_line = lines[0]
        after_prefix = step_line.split("**Step 1:**")[1].strip()
        assert len(after_prefix) > 0, "Step 1 instruction text is empty"


# ─── ProcedureStep rendering format (B2) ─────────────────────────────────────


class TestProcedureStepFormatting:
    """B2: generate_skill() renders ProcedureStep.command with backticks and
    ProcedureStep.context with em-dash italic pattern."""

    def test_supervisor_steps_rendered_with_backtick_command(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor output must contain a backtick-wrapped command string.

        Supervisor steps with a .command field (e.g. 'Skill(/aura:supervisor)')
        must be rendered inside backticks in the generated SKILL.md header.
        """
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        output = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert re.search(r"`[^`]+`", output), (
            "Expected at least one backtick-wrapped command in generate_skill() output "
            "for the supervisor role."
        )

    def test_supervisor_steps_rendered_with_em_dash_italic_context(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Supervisor output must contain an em-dash italic context string.

        Supervisor steps with a .context field must be rendered using the
        em-dash italic pattern ( — _..._) in the generated SKILL.md header.
        """
        content = _minimal_with_markers()
        skill_path = _make_skill_file(tmp_path, content)

        output = generate_skill(
            RoleId.SUPERVISOR,
            skill_path,
            template_dir=TEMPLATE_DIR,
            diff=False,
            write=False,
        )

        assert re.search(r"— _[^_]+_", output), (
            "Expected at least one em-dash italic context pattern ( — _..._) in "
            "generate_skill() output for the supervisor role."
        )
