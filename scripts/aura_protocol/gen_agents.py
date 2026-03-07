"""Agent definition generator for the Aura protocol.

Generates agents/{role_name}.md files from schema data for roles that
have tools defined. Output files are fully generated (no hand-authored
sections) and overwritten on each run.

Usage (CLI)
-----------
    python -m aura_protocol.gen_agents              # generate all roles with tools

Public API
----------
- generate_agent() : renders template and optionally writes the agent definition
"""

from __future__ import annotations

import difflib
import pathlib

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from aura_protocol.context_injection import (
    RoleContext,
    get_role_context,
)
from aura_protocol.types import (
    CONSTRAINT_SPECS,
    PHASE_SPECS,
    ROLE_SPECS,
    ConstraintSpec,
    PhaseId,
    PhaseSpec,
    RoleId,
    RoleSpec,
)

# ─── Default directories ─────────────────────────────────────────────────────

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_SKILLS_TEMPLATES_DIR = _REPO_ROOT / "skills" / "templates"
_AGENTS_DIR = _REPO_ROOT / "agents"

# ─── Context builders ────────────────────────────────────────────────────────


def _constraints_from_role_context(
    role_ctx: RoleContext,
) -> list[ConstraintSpec]:
    """Return ConstraintSpec objects from a pre-built RoleContext.

    Extracts constraint IDs from the RoleContext's ConstraintContext objects,
    then looks them up in CONSTRAINT_SPECS to return the full spec objects.
    Returns specs sorted by ID for deterministic template output.
    """
    constraint_ids = {c.id for c in role_ctx.constraints}
    return sorted(
        [spec for cid, spec in CONSTRAINT_SPECS.items() if cid in constraint_ids],
        key=lambda s: s.id,
    )


def _owned_phase_details(role_spec: RoleSpec) -> list[PhaseSpec]:
    """Return PhaseSpec objects for phases owned by the role, sorted by number."""
    result = []
    for phase_id in role_spec.owned_phases:
        phase_spec = PHASE_SPECS.get(phase_id)
        if phase_spec is not None:
            result.append(phase_spec)
    return sorted(result, key=lambda p: p.number)


# ─── Template rendering ──────────────────────────────────────────────────────


def _render_agent(
    role_id: RoleId,
    template_dir: pathlib.Path,
) -> str:
    """Render the agent definition markdown for a role.

    Returns the rendered string ready for writing to agents/{role}.md.
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
    template = env.get_template("agent_definition.j2")

    # Build phase slug map: PhaseId -> "p7-handoff"
    phase_slug: dict[PhaseId, str] = {
        phase_id: (
            f"{spec.id.value}-{spec.name.lower().replace(' ', '-')}"
            if (spec := PHASE_SPECS.get(phase_id)) is not None
            else phase_id.value
        )
        for phase_id in PhaseId
    }

    role_ctx = get_role_context(role_id)

    context: dict = {
        "role": role_spec,
        "phases_detail": _owned_phase_details(role_spec),
        "phase_slug": phase_slug,
        "constraints": _constraints_from_role_context(role_ctx),
        "behaviors": list(role_spec.behaviors),
        "checklists": list(role_ctx.checklists),
        "workflows": list(role_ctx.workflows),
    }

    return template.render(**context)


# ─── Public API ───────────────────────────────────────────────────────────────


def generate_agent(
    role_id: RoleId,
    agent_path: pathlib.Path | str,
    *,
    template_dir: pathlib.Path | str | None = None,
    diff: bool = True,
    write: bool = True,
) -> str:
    """Generate agents/{role}.md for a role and (optionally) write it.

    Parameters
    ----------
    role_id:
        The role to generate for (must be in ROLE_SPECS and have tools defined).
    agent_path:
        Path to the target agent .md file.
    template_dir:
        Directory containing ``agent_definition.j2``.  Defaults to
        ``skills/templates/`` relative to the repo root.
    diff:
        If True (default), print a unified diff to stdout when content changes.
    write:
        If True (default), write the new content to *agent_path*.

    Returns
    -------
    str
        The rendered agent definition content.
    """
    agent_path = pathlib.Path(agent_path)
    if template_dir is None:
        template_dir = _SKILLS_TEMPLATES_DIR
    template_dir = pathlib.Path(template_dir)

    # Read old content if file exists (for diffing)
    old_content = ""
    if agent_path.exists():
        old_content = agent_path.read_text(encoding="utf-8")

    new_content = _render_agent(role_id, template_dir)

    # Ensure content ends with newline
    if not new_content.endswith("\n"):
        new_content += "\n"

    # Print unified diff if requested and content changed
    if diff and new_content != old_content:
        old_name = str(agent_path)
        new_name = str(agent_path) + " (generated)"
        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=old_name,
                tofile=new_name,
            )
        )
        if diff_lines:
            print("".join(diff_lines), end="")

    # Write to file if requested
    if write:
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_path.write_text(new_content, encoding="utf-8")

    return new_content


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point. Generates agent definitions for all roles with tools.

    Usage: python -m aura_protocol.gen_agents

    Only generates for roles that have tools defined (non-empty tuple).

    Returns: 0 on success, 1 on error.
    """
    import sys

    errors: list[str] = []

    for role_id, role_spec in ROLE_SPECS.items():
        # Only generate for roles with tools defined
        if not role_spec.tools:
            continue

        agent_path = _AGENTS_DIR / f"{role_id.value}.md"
        try:
            generate_agent(role_id, agent_path, diff=True)
            print(f"Generated {agent_path}")
        except OSError as e:
            errors.append(str(e))
            print(f"ERROR writing {agent_path}: {e}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s) encountered.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
