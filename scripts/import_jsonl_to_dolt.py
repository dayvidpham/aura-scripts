#!/usr/bin/env python3
"""Import issues.jsonl into the Dolt backend via direct MySQL connection.

Reads each JSONL line and inserts into: issues, labels, dependencies, comments.
Then runs `bd dolt commit` to persist the Dolt history.

Usage:
    python3 scripts/import_jsonl_to_dolt.py [--dry-run] [--jsonl PATH]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pymysql

BEADS_DIR = Path(__file__).resolve().parent.parent / ".beads"
DEFAULT_JSONL = BEADS_DIR / "issues.jsonl"

DOLT_HOST = "127.0.0.1"
DOLT_PORT = 3307
DOLT_USER = "root"
DOLT_DB = "beads_aura-plugins"


def connect() -> pymysql.Connection:
    return pymysql.connect(
        host=DOLT_HOST,
        port=DOLT_PORT,
        user=DOLT_USER,
        database=DOLT_DB,
        autocommit=True,
    )


def import_issue(cur: pymysql.cursors.Cursor, issue: dict) -> None:
    issue_id = issue["id"]

    # -- issues table --
    cur.execute(
        """INSERT INTO issues
           (id, title, description, design, acceptance_criteria, notes,
            status, priority, issue_type, owner, assignee,
            created_at, created_by, updated_at, closed_at, close_reason)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            issue_id,
            issue.get("title", ""),
            issue.get("description", ""),
            issue.get("design", ""),
            issue.get("acceptance_criteria", ""),
            issue.get("notes", ""),
            issue.get("status", "open"),
            issue.get("priority", 2),
            issue.get("issue_type", "task"),
            issue.get("owner") or None,
            issue.get("assignee") or None,
            issue.get("created_at", ""),
            issue.get("created_by") or None,
            issue.get("updated_at", ""),
            issue.get("closed_at") or None,
            issue.get("close_reason") or None,
        ),
    )

    # -- labels table --
    for label in issue.get("labels", []):
        cur.execute(
            "INSERT INTO labels (issue_id, label) VALUES (%s, %s)",
            (issue_id, label),
        )

    # -- dependencies table --
    for dep in issue.get("dependencies", []):
        dep_meta = dep.get("metadata", "{}")
        if isinstance(dep_meta, dict):
            dep_meta = json.dumps(dep_meta)
        cur.execute(
            """INSERT INTO dependencies
               (issue_id, depends_on_id, type, created_at, created_by, metadata)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                dep["issue_id"],
                dep["depends_on_id"],
                dep.get("type", "blocks"),
                dep.get("created_at", ""),
                dep.get("created_by") or None,
                dep_meta,
            ),
        )

    # -- comments table --
    for comment in issue.get("comments", []):
        cur.execute(
            """INSERT INTO comments (id, issue_id, author, text, created_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                comment["id"],
                comment["issue_id"],
                comment.get("author", ""),
                comment.get("text", ""),
                comment.get("created_at", ""),
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import issues.jsonl into Dolt")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate only")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL, help="Path to issues.jsonl")
    args = parser.parse_args()

    jsonl_path: Path = args.jsonl
    if not jsonl_path.exists():
        print(f"ERROR: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    issues = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                issues.append(json.loads(line))

    print(f"Loaded {len(issues)} issues from {jsonl_path}")

    if args.dry_run:
        print("[dry-run] Parsed OK. Would insert:")
        print(f"  Issues: {len(issues)}")
        print(f"  Labels: {sum(len(i.get('labels', [])) for i in issues)}")
        print(f"  Dependencies: {sum(len(i.get('dependencies', [])) for i in issues)}")
        print(f"  Comments: {sum(len(i.get('comments', [])) for i in issues)}")
        return

    conn = connect()
    cur = conn.cursor()

    # Check current count
    cur.execute("SELECT COUNT(*) FROM issues")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"WARNING: issues table already has {count} rows", file=sys.stderr)
        resp = input("Continue anyway? [y/N] ")
        if resp.lower() != "y":
            sys.exit(1)

    # Disable FK checks for bulk import
    cur.execute("SET FOREIGN_KEY_CHECKS=0")

    errors = []
    for i, issue in enumerate(issues, 1):
        issue_id = issue["id"]
        try:
            import_issue(cur, issue)
            print(f"  [{i}/{len(issues)}] {issue_id}: {issue.get('title', '')[:60]}")
        except Exception as e:
            errors.append((issue_id, str(e)))
            print(f"  [{i}/{len(issues)}] FAILED {issue_id}: {e}", file=sys.stderr)

    # Re-enable FK checks
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    cur.close()
    conn.close()

    print(f"\nImported {len(issues) - len(errors)}/{len(issues)} issues")
    if errors:
        print(f"Errors ({len(errors)}):")
        for eid, msg in errors:
            print(f"  {eid}: {msg}")

    # Dolt commit via bd CLI
    if not errors:
        print("\nCommitting to Dolt...")
        result = subprocess.run(
            ["bd", "dolt", "commit"],
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Dolt commit error: {result.stderr}", file=sys.stderr)
    else:
        print("\nSkipping Dolt commit due to errors.")


if __name__ == "__main__":
    main()
