"""SQLite-backed audit trail for aurad (SLICE-5).

SqliteAuditTrail implements the AuditTrail Protocol from interfaces.py using
an aiosqlite-backed SQLite database. This provides durable event persistence
across aurad restarts, unlike InMemoryAuditTrail which loses data on stop.

Schema (audit_events table):
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    epoch_id    TEXT NOT NULL
    phase       TEXT NOT NULL   (PhaseId.value)
    role        TEXT NOT NULL   (RoleId.value)
    event_type  TEXT NOT NULL
    payload     TEXT NOT NULL   (JSON-serialized dict)
    timestamp   TEXT NOT NULL   (ISO-8601 UTC)

Usage:
    trail = SqliteAuditTrail(db_path=Path("~/.local/share/aura/audit.db"))
    await trail.record_event(event)
    events = await trail.query_events(epoch_id="ep-1")
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from aura_protocol.types import AuditEvent, EventType, PhaseId, RoleId

logger = logging.getLogger(__name__)


async def ensure_schema(db_path: Path) -> None:
    """Create the audit_events table if it does not exist.

    Uses aiosqlite for async DB access. Called at startup inside the async
    main() before the worker loop starts.

    Args:
        db_path: Path to the SQLite database file. Parent directories are
                 created if they do not exist.

    Creates:
        audit_events table with columns:
            id         INTEGER PRIMARY KEY AUTOINCREMENT
            epoch_id   TEXT NOT NULL
            phase      TEXT NOT NULL
            role       TEXT NOT NULL
            event_type TEXT NOT NULL
            payload    TEXT NOT NULL  (JSON)
            timestamp  TEXT NOT NULL  (ISO-8601 UTC)
    """
    import aiosqlite

    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                epoch_id   TEXT NOT NULL,
                phase      TEXT NOT NULL,
                role       TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload    TEXT NOT NULL,
                timestamp  TEXT NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_epoch_id ON audit_events (epoch_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_phase ON audit_events (phase)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_role ON audit_events (role)"
        )
        await db.commit()
    logger.info("SqliteAuditTrail schema ensured at %s", db_path)


class SqliteAuditTrail:
    """SQLite-backed AuditTrail implementation (SLICE-5).

    Persists AuditEvent records to a SQLite database via aiosqlite so the
    aurad worker loop remains non-blocking. ensure_schema() is called
    synchronously at startup before the async event loop starts.

    Implements: AuditTrail Protocol from aura_protocol.interfaces

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def record_event(self, event: AuditEvent) -> None:
        """Persist an AuditEvent to the SQLite database.

        Args:
            event: AuditEvent frozen dataclass to record.

        Raises:
            RuntimeError: If aiosqlite is not installed or the DB is unavailable.
                          Where: SqliteAuditTrail.record_event at {db_path}
                          Why: aiosqlite write failed
                          Fix: Ensure aiosqlite is installed and DB path is writable.
        """
        import aiosqlite

        timestamp = datetime.now(UTC).isoformat()
        payload_json = json.dumps(event.payload)

        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                """
                INSERT INTO audit_events (epoch_id, phase, role, event_type, payload, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.epoch_id,
                    event.phase.value,
                    event.role.value,
                    event.event_type,
                    payload_json,
                    timestamp,
                ),
            )
            await db.commit()
        logger.debug(
            "SqliteAuditTrail: recorded %s event for epoch=%s phase=%s",
            event.event_type,
            event.epoch_id,
            event.phase.value,
        )

    async def query_events(
        self,
        *,
        epoch_id: str | None = None,
        phase: PhaseId | None = None,
        role: RoleId | None = None,
    ) -> list[AuditEvent]:
        """Query recorded audit events with optional filters.

        Each active filter becomes a WHERE clause. Enum fields use .value so
        the SQL compares against the string stored at record_event() time.

        Args:
            epoch_id: Optional epoch filter.
            phase:    Optional phase filter (PhaseId enum member).
            role:     Optional role filter (RoleId enum member).

        Returns:
            Matching AuditEvent instances in chronological order (by id).

        Raises:
            RuntimeError: If the database is unavailable.
                          Where: SqliteAuditTrail.query_events at {db_path}
                          Fix: Ensure DB file exists (run ensure_schema first).
        """
        import aiosqlite

        clauses: list[str] = []
        params: list[str] = []

        if epoch_id is not None:
            clauses.append("epoch_id = ?")
            params.append(epoch_id)
        if phase is not None:
            clauses.append("phase = ?")
            params.append(phase.value)
        if role is not None:
            clauses.append("role = ?")
            params.append(role.value)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT epoch_id, event_type, phase, role, payload FROM audit_events {where} ORDER BY id"

        async with aiosqlite.connect(str(self._db_path)) as db:
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

        events: list[AuditEvent] = []
        for row in rows:
            epoch_id_col, event_type_col, phase_col, role_col, payload_col = row
            events.append(
                AuditEvent(
                    epoch_id=epoch_id_col,
                    event_type=EventType(event_type_col),
                    phase=PhaseId(phase_col),
                    role=RoleId(role_col),
                    payload=json.loads(payload_col),
                )
            )
        return events
