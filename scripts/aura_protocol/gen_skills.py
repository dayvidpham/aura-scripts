"""SKILL.md header generator for the Aura protocol.

Generates the protocol-driven header section of each role's SKILL.md
file using Jinja2 templates rendered from the canonical Python types.

Usage
-----
Markers must be placed manually in the target SKILL.md before this
script will touch it:

    <!-- BEGIN GENERATED FROM aura schema -->
    (any existing content here will be replaced)
    <!-- END GENERATED FROM aura schema -->

Running generate_skill() on a file that is missing either marker raises
MarkerError — no silent prepending.  Use ``init=True`` to prepend markers
to files that lack them before generating.

Usage (CLI)
-----------
    python -m aura_protocol.gen_skills              # generate all roles
    python -m aura_protocol.gen_skills --init       # add markers + generate

Public API
----------
- GENERATED_BEGIN  : str  — exact begin-marker literal
- GENERATED_END    : str  — exact end-marker literal
- MarkerError      : exception raised when markers are absent/malformed
- generate_skill() : renders template and optionally writes + diffs
"""

from __future__ import annotations

import difflib
import pathlib
from typing import Sequence

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from aura_protocol.types import (
    COMMAND_SPECS,
    HANDOFF_SPECS,
    PHASE_SPECS,
    PROCEDURE_STEPS,
    ROLE_SPECS,
    CommandSpec,
    ConstraintContext,
    HandoffSpec,
    PhaseId,
    PhaseSpec,
    RoleId,
    RoleSpec,
)

# ─── Marker constants ─────────────────────────────────────────────────────────

GENERATED_BEGIN = "<!-- BEGIN GENERATED FROM aura schema -->"
GENERATED_END = "<!-- END GENERATED FROM aura schema -->"

# ─── Default template directory ───────────────────────────────────────────────

_SKILLS_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "skills" / "templates"


# ─── Error type ───────────────────────────────────────────────────────────────


class MarkerError(ValueError):
    """Raised when SKILL.md is missing or has malformed generated markers.

    What went wrong: The target file does not contain the required marker
    pair that delimits the generated section.

    Why: gen_skills.py refuses to operate on unmarked files to prevent
    accidental overwrite of hand-authored content. The developer must
    manually place markers before the generator will run.

    How to fix: Add the following pair to the target SKILL.md (in order):

        <!-- BEGIN GENERATED FROM aura schema -->
        <!-- END GENERATED FROM aura schema -->

    The hand-authored body goes below the END marker; the generator will
    replace everything between (and including) the markers.
    """


# ─── Context builders ─────────────────────────────────────────────────────────


def _commands_for_role(role_id: RoleId) -> list[CommandSpec]:
    """Return all CommandSpecs whose role_ref matches role_id."""
    return [
        cmd
        for cmd in COMMAND_SPECS.values()
        if cmd.role_ref == role_id
    ]


def _skill_names_for_role(role_id: RoleId) -> list[str]:
    """Return skill invocation names for a role's sub-commands.

    Converts command names to skill directory names: `aura:a:b` → `aura:a-b`.
    Skips the main role command (e.g., `aura:worker` for the worker role).

    What went wrong if list is empty: no sub-commands defined for this role.
    Why: COMMAND_SPECS only has the main role entry and no sub-commands.
    Where: types.py COMMAND_SPECS dict.
    How to fix: add CommandSpec entries with role_ref matching role_id.
    """
    main_cmd = f"aura:{role_id.value}"
    result = []
    for cmd in _commands_for_role(role_id):
        if cmd.name == main_cmd:
            continue
        parts = cmd.name.split(":")
        # aura:a:b → aura:a-b  (join first two with ':', rest with '-')
        if len(parts) >= 3:
            skill_name = f"{parts[0]}:{parts[1]}-{'-'.join(parts[2:])}"
        else:
            skill_name = cmd.name
        result.append(skill_name)
    return result


def _constraints_for_role(role_id: RoleId) -> list[ConstraintContext]:
    """Return ConstraintContext objects relevant to a given role.

    Uses get_role_context() to return only the role-scoped constraints,
    derived from _ROLE_CONSTRAINTS in context_injection.py.
    """
    from aura_protocol.context_injection import get_role_context
    return list(get_role_context(role_id).constraints)


def _handoffs_for_role(role_id: RoleId) -> list[HandoffSpec]:
    """Return HandoffSpecs where role appears as source or target."""
    return [
        h
        for h in HANDOFF_SPECS.values()
        if h.source_role == role_id or h.target_role == role_id
    ]


def _owned_phase_details(role_spec: RoleSpec) -> list[PhaseSpec]:
    """Return PhaseSpec objects for phases owned by the role, sorted by number."""
    result = []
    for phase_id in role_spec.owned_phases:
        phase_spec = PHASE_SPECS.get(phase_id)
        if phase_spec is not None:
            result.append(phase_spec)
    return sorted(result, key=lambda p: p.number)


# ─── Marker parsing ───────────────────────────────────────────────────────────


def _find_marker_positions(
    lines: Sequence[str],
    skill_path: pathlib.Path,
) -> tuple[int, int]:
    """Return (begin_idx, end_idx) line indices for the marker pair.

    Parameters
    ----------
    lines:
        File content split into lines (with newlines retained).
    skill_path:
        Path used in error messages only.

    Raises
    ------
    MarkerError
        If BEGIN marker is absent, END marker is absent, or END comes
        before BEGIN (reversed / malformed).
    """
    begin_idx: int | None = None
    end_idx: int | None = None

    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if stripped == GENERATED_BEGIN:
            if begin_idx is not None:
                raise MarkerError(
                    f"Malformed markers in {skill_path}: "
                    f"duplicate BEGIN marker at line {i + 1}. "
                    f"Expected exactly one '{GENERATED_BEGIN}' and one '{GENERATED_END}'. "
                    "Remove the duplicate and re-run."
                )
            begin_idx = i
        elif stripped == GENERATED_END:
            if end_idx is not None:
                raise MarkerError(
                    f"Malformed markers in {skill_path}: "
                    f"duplicate END marker at line {i + 1}. "
                    f"Expected exactly one '{GENERATED_BEGIN}' and one '{GENERATED_END}'. "
                    "Remove the duplicate and re-run."
                )
            end_idx = i

    if begin_idx is None and end_idx is None:
        raise MarkerError(
            f"Missing markers in {skill_path}: "
            f"neither '{GENERATED_BEGIN}' nor '{GENERATED_END}' found. "
            "This file has not been prepared for gen_skills.py. "
            "Add both markers (in order) to the file, then re-run."
        )

    if begin_idx is None:
        raise MarkerError(
            f"Malformed markers in {skill_path}: "
            f"'{GENERATED_END}' found at line {end_idx + 1} but "  # type: ignore[operator]
            f"'{GENERATED_BEGIN}' is missing. "
            "Add the BEGIN marker above the END marker and re-run."
        )

    if end_idx is None:
        raise MarkerError(
            f"Malformed markers in {skill_path}: "
            f"'{GENERATED_BEGIN}' found at line {begin_idx + 1} but "
            f"'{GENERATED_END}' is missing. "
            "Add the END marker below the BEGIN marker and re-run."
        )

    if end_idx < begin_idx:
        raise MarkerError(
            f"Malformed markers in {skill_path}: "
            f"END marker (line {end_idx + 1}) appears before "
            f"BEGIN marker (line {begin_idx + 1}). "
            "Swap the markers so BEGIN comes first, then re-run."
        )

    return begin_idx, end_idx


# ─── Template rendering ───────────────────────────────────────────────────────


def _render_header(
    role_id: RoleId,
    template_dir: pathlib.Path,
) -> str:
    """Render the generated header block for a role.

    Returns the rendered string including the BEGIN/END markers.
    Uses Jinja2 StrictUndefined — any undefined variable causes an error.
    """
    role_spec: RoleSpec = ROLE_SPECS[role_id]

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("skill_header.j2")

    # Build phase slug map: PhaseId → "p7-handoff" (for display only; .value stays "p7").
    # Falls back to bare .value for terminal states (e.g. COMPLETE) that have no PhaseSpec.
    phase_slug: dict[PhaseId, str] = {
        phase_id: (
            f"{spec.id.value}-{spec.name.lower().replace(' ', '-')}"
            if (spec := PHASE_SPECS.get(phase_id)) is not None
            else phase_id.value
        )
        for phase_id in PhaseId
    }

    # Sort owned phases by declaration order in PhaseId (not string order)
    owned_phases_sorted = [p for p in PhaseId if p in set(role_spec.owned_phases)]

    context: dict = {
        "role": role_spec,
        "commands": _commands_for_role(role_id),
        "constraints": _constraints_for_role(role_id),
        "handoffs": _handoffs_for_role(role_id),
        "owned_phases": owned_phases_sorted,
        "phases_detail": _owned_phase_details(role_spec),
        "steps": list(PROCEDURE_STEPS.get(role_id, [])),
        "phase_slug": phase_slug,
        "sub_skills": _skill_names_for_role(role_id),
    }

    return template.render(**context)


# ─── Public API ───────────────────────────────────────────────────────────────


def _has_markers(content: str) -> bool:
    """Return True if content contains both BEGIN and END markers."""
    return GENERATED_BEGIN in content and GENERATED_END in content


def generate_skill(
    role_id: RoleId,
    skill_path: pathlib.Path | str,
    *,
    template_dir: pathlib.Path | str | None = None,
    diff: bool = True,
    write: bool = True,
    init: bool = False,
) -> str:
    """Generate the SKILL.md header for a role and (optionally) write it.

    Parameters
    ----------
    role_id:
        The role to generate for (must be in ROLE_SPECS).
    skill_path:
        Path to the target SKILL.md file.  The file must already exist
        and contain the BEGIN/END marker pair (unless *init* is True).
    template_dir:
        Directory containing ``skill_header.j2``.  Defaults to the
        ``skills/templates/`` directory relative to the repo root.
    diff:
        If True (default), print a unified diff of old vs new content to
        stdout before writing.  No diff printed when there are no changes.
    write:
        If True (default), write the new content to *skill_path*.
        Set False for dry-run / test assertions.
    init:
        If True, prepend BEGIN/END markers to files that lack them before
        generating.  Files that already have markers are left as-is.
        When False (default), missing markers raise MarkerError.

    Returns
    -------
    str
        The complete new file content (header + preserved body).

    Raises
    ------
    MarkerError
        If *skill_path* is missing the BEGIN/END marker pair or the
        markers are malformed (e.g., reversed order, duplicate), and
        *init* is False.
    FileNotFoundError
        If *skill_path* does not exist.
    jinja2.UndefinedError
        If the template references a variable not supplied by the context
        (caught at render time due to StrictUndefined).
    """
    skill_path = pathlib.Path(skill_path)
    if template_dir is None:
        template_dir = _SKILLS_TEMPLATES_DIR
    template_dir = pathlib.Path(template_dir)

    # Read existing file
    old_content = skill_path.read_text(encoding="utf-8")

    # In --init mode, prepend markers if missing
    if init and not _has_markers(old_content):
        marker_prefix = f"{GENERATED_BEGIN}\n{GENERATED_END}\n\n"
        old_content = marker_prefix + old_content
        # Write the marker-prepended content so subsequent logic works
        if write:
            skill_path.write_text(old_content, encoding="utf-8")

    old_lines = old_content.splitlines(keepends=True)

    # Locate markers — raises MarkerError on any problem
    begin_idx, end_idx = _find_marker_positions(old_lines, skill_path)

    # Render the new generated header (includes markers)
    rendered_header = _render_header(role_id, template_dir)

    # Ensure header ends with newline for clean concatenation
    if not rendered_header.endswith("\n"):
        rendered_header += "\n"

    # Preserve the hand-authored body below the END marker
    body_lines = old_lines[end_idx + 1 :]
    body = "".join(body_lines)

    # Assemble new content: generated header (includes frontmatter + heading +
    # BEGIN…END block) followed by the hand-authored body.  The prefix
    # (everything before the BEGIN marker in the old file) is intentionally
    # dropped — frontmatter and the role heading are owned by the template.
    new_content = rendered_header + body

    # Print unified diff if requested and content changed
    if diff and new_content != old_content:
        old_name = str(skill_path)
        new_name = str(skill_path) + " (generated)"
        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=old_name,
                tofile=new_name,
            )
        )
        print("".join(diff_lines), end="")

    # Write to file if requested
    if write:
        skill_path.write_text(new_content, encoding="utf-8")

    return new_content


# ─── CLI ──────────────────────────────────────────────────────────────────────

# Mapping from RoleId → skill directory name (relative to skills/)
_ROLE_SKILL_DIRS: dict[RoleId, str] = {
    RoleId.SUPERVISOR: "supervisor",
    RoleId.WORKER: "worker",
    RoleId.REVIEWER: "reviewer",
    RoleId.ARCHITECT: "architect",
}


def main() -> int:
    """CLI entry point. Generates SKILL.md headers for all roles.

    Usage: python -m aura_protocol.gen_skills [--init]

    --init: Prepend BEGIN/END markers to SKILL.md files that lack them,
            then generate headers. Without --init, files missing markers
            raise MarkerError.

    Returns: 0 on success, 1 on error.
    """
    import sys

    init_mode = "--init" in sys.argv[1:]
    script_dir = pathlib.Path(__file__).resolve().parent
    skills_dir = script_dir.parent.parent / "skills"

    errors: list[str] = []
    for role_id, dir_name in _ROLE_SKILL_DIRS.items():
        skill_path = skills_dir / dir_name / "SKILL.md"
        if not skill_path.exists():
            print(f"Skipping {skill_path} (not found)", file=sys.stderr)
            continue
        try:
            generate_skill(role_id, skill_path, diff=True, init=init_mode)
            print(f"Generated {skill_path}")
        except MarkerError as e:
            errors.append(str(e))
            print(f"ERROR: {e}", file=sys.stderr)
        except OSError as e:
            errors.append(str(e))
            print(f"ERROR writing {skill_path}: {e}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s) encountered.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
