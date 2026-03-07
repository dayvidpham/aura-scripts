#!/usr/bin/env python3
"""aura-msg — CLI stub for Aura Protocol model harness hooks.

Planned subcommands (not yet implemented):
    start-epoch    — Start a new Aura epoch
    signal-vote    — Signal a review vote on an axis
    query-state    — Query current workflow state
    advance-phase  — Request a phase advance

Usage:
    aura-msg --help
    aura-msg <subcommand> --help
"""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aura-msg",
        description=(
            "CLI stub for Aura Protocol model harness hooks. "
            "All subcommands are planned and not yet implemented."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")

    subparsers.add_parser(
        "start-epoch",
        help="Start a new Aura epoch (not implemented)",
    )
    subparsers.add_parser(
        "signal-vote",
        help="Signal a review vote on an axis (not implemented)",
    )
    subparsers.add_parser(
        "query-state",
        help="Query current workflow state (not implemented)",
    )
    subparsers.add_parser(
        "advance-phase",
        help="Request a phase advance (not implemented)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand is None:
        parser.print_help()
        sys.exit(0)

    print(f"aura-msg: '{args.subcommand}' is not implemented", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
