#!/usr/bin/env python3
"""Temporal worker for Aura Protocol v3.

Entry point for running the EpochWorkflow worker. Connects to a Temporal
server, registers EpochWorkflow and all associated activities, and runs until
interrupted.

Configuration (CLI args take precedence over env vars):
    --namespace       Temporal namespace  (env: TEMPORAL_NAMESPACE,  default: "default")
    --task-queue      Temporal task queue (env: TEMPORAL_TASK_QUEUE, default: "aura")
    --server-address  Temporal server     (env: TEMPORAL_ADDRESS,    default: "localhost:7233")

Activities registered:
    check_constraints     — constraint checking for phase advances
    record_transition     — transition audit stub (v1 in-memory; v2 durable)
    record_audit_event    — persist AuditEvent to configured AuditTrail
    query_audit_events    — query AuditEvents by epoch_id + optional phase

Workflows registered:
    EpochWorkflow         — top-level epoch lifecycle workflow (12 phases)
    SliceWorkflow         — child workflow for a single P9_SLICE (runs concurrently)
    ReviewPhaseWorkflow   — child workflow for P10_CODE_REVIEW (vote-driven)

Usage:
    bin/aurad.py                                       # defaults + env vars
    bin/aurad.py --namespace dev --task-queue aura     # explicit args
    TEMPORAL_NAMESPACE=prod bin/aurad.py               # env var override
"""

import argparse
import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from pathlib import Path

from aura_protocol.config import default_config_path, load_yaml_section, resolve_connection
from aura_protocol.audit_activities import (
    InMemoryAuditTrail,
    init_audit_trail,
    query_audit_events,
    record_audit_event,
)
from aura_protocol.sqlite_audit import SqliteAuditTrail, _ensure_schema
from aura_protocol.workflow import (
    EpochWorkflow,
    ReviewPhaseWorkflow,
    SliceWorkflow,
    check_constraints,
    record_transition,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments with environment variable fallbacks.

    Priority (highest → lowest):
        1. Explicit CLI flag (e.g. --namespace my-ns)
        2. Environment variable (e.g. TEMPORAL_NAMESPACE=my-ns)
        3. Built-in default ("default", "aura", "localhost:7233")

    Args:
        argv: Argument list to parse. If None, reads from sys.argv[1:] (default
              argparse behaviour). Pass an explicit list (e.g. ["--namespace", "prod"])
              in tests to avoid relying on sys.argv patching.

    Returns:
        Parsed namespace with .namespace, .task_queue, .server_address.
    """
    parser = argparse.ArgumentParser(
        description="aurad — Temporal worker daemon for Aura Protocol v3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables:\n"
            "  TEMPORAL_NAMESPACE   Temporal namespace (default: 'default')\n"
            "  TEMPORAL_TASK_QUEUE  Task queue name   (default: 'aura')\n"
            "  TEMPORAL_ADDRESS     Server address    (default: 'localhost:7233')\n"
        ),
    )
    parser.add_argument(
        "--namespace",
        default=os.environ.get("TEMPORAL_NAMESPACE", "default"),
        metavar="NS",
        help="Temporal namespace (env: TEMPORAL_NAMESPACE, default: 'default')",
    )
    parser.add_argument(
        "--task-queue",
        default=os.environ.get("TEMPORAL_TASK_QUEUE", "aura"),
        metavar="QUEUE",
        help="Temporal task queue name (env: TEMPORAL_TASK_QUEUE, default: 'aura')",
    )
    parser.add_argument(
        "--server-address",
        default=os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        metavar="ADDR",
        help="Temporal server address (env: TEMPORAL_ADDRESS, default: 'localhost:7233')",
    )
    parser.add_argument(
        "--audit-trail",
        choices=["memory", "sqlite"],
        default=os.environ.get("AURAD_AUDIT_TRAIL", "memory"),
        metavar="BACKEND",
        help=(
            "Audit trail backend: 'memory' (default, in-process) or 'sqlite' "
            "(durable, XDG path ~/.local/share/aura/plugin/audit.db). "
            "Env: AURAD_AUDIT_TRAIL."
        ),
    )
    return parser.parse_args(argv)


async def run_worker(namespace: str, task_queue: str, server_address: str) -> None:
    """Connect to Temporal and run the EpochWorkflow worker.

    Extracted from main() to make it testable without sys.argv parsing.

    Args:
        namespace:      Temporal namespace to connect to.
        task_queue:     Task queue name to listen on.
        server_address: Temporal server address (host:port).
    """
    client = await Client.connect(server_address, namespace=namespace)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[EpochWorkflow, SliceWorkflow, ReviewPhaseWorkflow],
        activities=[
            check_constraints,
            record_transition,
            record_audit_event,
            query_audit_events,
        ],
    ):
        logger.info(
            "Worker running: namespace=%r task_queue=%r server=%r",
            namespace,
            task_queue,
            server_address,
        )
        # Block until SIGINT/SIGTERM.
        await asyncio.Event().wait()


async def main() -> None:
    """Parse args, initialize audit trail, and start the worker."""
    args = parse_args()

    # Resolve connection config using shared config module.
    # parse_args() already handles CLI > env via argparse defaults;
    # passing its results as cli_args ensures they take priority over YAML.
    config_path = default_config_path()
    yaml_section = load_yaml_section(config_path, "aurad")
    conn = resolve_connection(
        cli_args={
            "namespace": args.namespace,
            "task_queue": args.task_queue,
            "server_address": args.server_address,
        },
        yaml_section=yaml_section,
    )

    # Initialize the audit trail before the worker starts.
    # --audit-trail memory (default): in-process, lost on restart
    # --audit-trail sqlite: durable, persisted to XDG data dir
    if args.audit_trail == "sqlite":
        db_path = Path.home() / ".local" / "share" / "aura" / "plugin" / "audit.db"
        _ensure_schema(db_path)
        trail = SqliteAuditTrail(db_path=db_path)
        init_audit_trail(trail)
        logger.info("Audit trail initialized (SqliteAuditTrail at %s).", db_path)
    else:
        init_audit_trail(InMemoryAuditTrail())
        logger.info("Audit trail initialized (InMemoryAuditTrail).")

    await run_worker(
        namespace=conn.namespace,
        task_queue=conn.task_queue,
        server_address=conn.server_address,
    )


if __name__ == "__main__":
    asyncio.run(main())
