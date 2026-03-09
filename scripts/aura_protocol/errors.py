"""Standardized error reporting for aura CLI tools."""

from __future__ import annotations

import sys
from enum import StrEnum


class ErrorCategory(StrEnum):
    """Categories for structured error reporting."""

    Connection = "connection error"
    Workflow = "workflow error"
    Validation = "validation error"


def report_error(
    category: ErrorCategory,
    *,
    what: str,
    why: str,
    impact: str,
    fix: str,
) -> None:
    """Print a structured error message to stderr."""
    print(f"{category}: {what}", file=sys.stderr)
    print(f"  why: {why}", file=sys.stderr)
    print(f"  impact: {impact}", file=sys.stderr)
    print(f"  fix: {fix}", file=sys.stderr)
