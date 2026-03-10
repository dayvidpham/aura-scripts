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
from typing import Any

from temporalio.client import Client
from temporalio.worker import Worker

from pathlib import Path

from aura_protocol.config import AuradConfig, default_config_path, load_yaml_section, resolve_aurad_config
from aura_protocol.types import AuditTrailBackend
from aura_protocol.audit_activities import (
    InMemoryAuditTrail,
    init_audit_trail,
    query_audit_events,
    record_audit_event,
)
from aura_protocol.sqlite_audit import SqliteAuditTrail, ensure_schema
from aura_protocol.workflow import (
    EpochWorkflow,
    ReviewPhaseWorkflow,
    SliceWorkflow,
    check_constraints,
    ensure_search_attributes,
    record_transition,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> AuradConfig:
    """Parse CLI arguments and resolve full aurad config.

    Priority (highest → lowest):
        1. Explicit CLI flag (e.g. --namespace my-ns)
        2. Environment variable (e.g. TEMPORAL_NAMESPACE=my-ns)
        3. YAML config file (~/.config/aura/plugins/aurad.config.yaml)
        4. Built-in default ("default", "aura", "localhost:7233")

    Uses resolve_aurad_config() from the config module to implement the
    priority chain. argparse defaults are None (sentinel); the config
    module resolves final values.

    Args:
        argv: Argument list to parse. If None, reads from sys.argv[1:] (default
              argparse behaviour). Pass an explicit list (e.g. ["--namespace", "prod"])
              in tests to avoid relying on sys.argv patching.

    Returns:
        Frozen AuradConfig with resolved connection, audit_trail, and audit_db_path.
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
        default=None,
        metavar="NS",
        help=(
            "Temporal namespace -- isolates workflows from other teams/environments. "
            "Use a different namespace for dev vs prod. "
            "(env: TEMPORAL_NAMESPACE, default: 'default')"
        ),
    )
    parser.add_argument(
        "--task-queue",
        default=None,
        metavar="QUEUE",
        help=(
            "Temporal task queue -- routes workflows to specific worker pools. "
            "Use separate queues to isolate workloads or version deployments. "
            "(env: TEMPORAL_TASK_QUEUE, default: 'aura')"
        ),
    )
    parser.add_argument(
        "--server-address",
        default=None,
        metavar="ADDR",
        help=(
            "Temporal server host:port -- point to a remote cluster for "
            "shared/production use. (env: TEMPORAL_ADDRESS, default: 'localhost:7233')"
        ),
    )
    parser.add_argument(
        "--audit-trail",
        choices=[b.value for b in AuditTrailBackend],
        default=None,
        metavar="BACKEND",
        help=(
            "'memory' keeps events in-process (lost on restart), "
            "'sqlite' persists to disk for durable history across restarts. "
            "(env: AURAD_AUDIT_TRAIL, default: 'memory')"
        ),
    )
    parser.add_argument(
        "--audit-db-path",
        default=None,
        metavar="PATH",
        help=(
            "Path to SQLite audit database (only used with --audit-trail sqlite). "
            "Default: ~/.local/share/aura/plugin/audit.db. Env: AURAD_AUDIT_DB_PATH."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Log config resolution sources on startup.",
    )
    args = parser.parse_args(argv)

    # Build cli_args from only explicitly-provided CLI flags (non-None).
    cli_args: dict[str, str] = {}
    if args.namespace is not None:
        cli_args["namespace"] = args.namespace
    if args.task_queue is not None:
        cli_args["task_queue"] = args.task_queue
    if args.server_address is not None:
        cli_args["server_address"] = args.server_address
    if args.audit_trail is not None:
        cli_args["audit_trail"] = args.audit_trail
    if args.audit_db_path is not None:
        cli_args["audit_db_path"] = args.audit_db_path

    # Resolve: CLI > env > YAML > defaults.
    yaml_section = load_yaml_section(default_config_path(), "aurad")
    config = resolve_aurad_config(
        cli_args=cli_args,
        env_dict=dict(os.environ),
        yaml_section=yaml_section,
    )

    if args.verbose:
        _log_resolution(cli_args, dict(os.environ), yaml_section, config)

    return config


def _log_resolution(
    cli_args: dict[str, str],
    env_dict: dict[str, str],
    yaml_section: dict[str, Any],
    config: AuradConfig,
) -> None:
    """Log which source each config value was resolved from."""
    from aura_protocol.config import (
        ENV_AUDIT_DB_PATH,
        ENV_AUDIT_TRAIL,
        ENV_NAMESPACE,
        ENV_SERVER_ADDRESS,
        ENV_TASK_QUEUE,
    )

    def _source(cli_key: str, env_key: str, yaml_key: str) -> str:
        if cli_key in cli_args:
            return "CLI --" + cli_key.replace("_", "-")
        if env_key in env_dict:
            return f"env {env_key}"
        if yaml_key in yaml_section:
            return f"YAML {default_config_path()}"
        return "default"

    logger.info("aurad: config resolution:")
    logger.info("  namespace:      %r (from: %s)", config.connection.namespace,
                _source("namespace", ENV_NAMESPACE, "namespace"))
    logger.info("  task_queue:     %r (from: %s)", config.connection.task_queue,
                _source("task_queue", ENV_TASK_QUEUE, "task_queue"))
    logger.info("  server_address: %r (from: %s)", config.connection.server_address,
                _source("server_address", ENV_SERVER_ADDRESS, "server_address"))
    logger.info("  audit_trail:    %r (from: %s)", config.audit_trail.value,
                _source("audit_trail", ENV_AUDIT_TRAIL, "audit_trail"))
    logger.info("  audit_db_path:  %r (from: %s)", str(config.audit_db_path),
                _source("audit_db_path", ENV_AUDIT_DB_PATH, "audit_db_path"))


async def run_worker(namespace: str, task_queue: str, server_address: str) -> None:
    """Connect to Temporal and run the EpochWorkflow worker.

    Extracted from main() to make it testable without sys.argv parsing.

    Args:
        namespace:      Temporal namespace to connect to.
        task_queue:     Task queue name to listen on.
        server_address: Temporal server address (host:port).
    """
    client = await Client.connect(server_address, namespace=namespace)
    await ensure_search_attributes(client)

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
    config = parse_args()

    # Initialize the audit trail before the worker starts.
    if config.audit_trail == AuditTrailBackend.Sqlite:
        await ensure_schema(config.audit_db_path)
        trail = SqliteAuditTrail(db_path=config.audit_db_path)
        init_audit_trail(trail)
        logger.info("Audit trail initialized (SqliteAuditTrail at %s).", config.audit_db_path)
    else:
        init_audit_trail(InMemoryAuditTrail())
        logger.info("Audit trail initialized (InMemoryAuditTrail).")

    await run_worker(
        namespace=config.connection.namespace,
        task_queue=config.connection.task_queue,
        server_address=config.connection.server_address,
    )


if __name__ == "__main__":
    asyncio.run(main())
