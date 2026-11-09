# SPDX-License-Identifier: Apache-2.0
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from overlord.models import Observation, SessionCreate, observation_adapter

# Ordered migrations run atomically with user_version; never edit an applied migration.
MIGRATIONS = (
    (
        "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, document TEXT NOT NULL)",
        """CREATE TABLE observations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL REFERENCES sessions(session_id),
            document TEXT NOT NULL,
            received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""",
        "CREATE INDEX observations_session ON observations(session_id, sequence)",
    ),
    (
        "CREATE TABLE response_control (session_id TEXT PRIMARY KEY "
        "REFERENCES sessions(session_id), document TEXT NOT NULL, changed_at TEXT NOT NULL)",
        "CREATE TABLE responses (event_id TEXT PRIMARY KEY REFERENCES observations(event_id), "
        "session_id TEXT NOT NULL REFERENCES sessions(session_id), document TEXT NOT NULL)",
        "CREATE INDEX responses_session ON responses(session_id)",
    ),
)


class Conflict(Exception):
    pass


class UnknownSession(Exception):
    pass


class Store:
    def __init__(self, path: Path, cooldown: int = 15):
        self.path = path
        self.cooldown = cooldown

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > len(MIGRATIONS):
                raise RuntimeError("Database schema is newer than this service")
            for index in range(version, len(MIGRATIONS)):
                for statement in MIGRATIONS[index]:
                    conn.execute(statement)
                conn.execute(f"PRAGMA user_version = {index + 1}")

    def health(self) -> None:
        with self.connection() as conn:
            conn.execute("SELECT 1 FROM sessions LIMIT 1").fetchone()

    def create_session(self, session: SessionCreate) -> None:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT document FROM sessions WHERE session_id = ?", (str(session.session_id),)
            ).fetchone()
            if row:
                if SessionCreate.model_validate_json(row[0]) != session:
                    raise Conflict("Session ID already has different metadata")
                return
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?)",
                (str(session.session_id), session.model_dump_json()),
            )

    def sessions(self, limit: int) -> list[SessionCreate]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT document FROM sessions ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
            return [SessionCreate.model_validate_json(row[0]) for row in rows]

    def record(self, observation: Observation) -> bool:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", (str(observation.session_id),)
            ).fetchone():
                raise UnknownSession
            row = conn.execute(
                "SELECT document FROM observations WHERE event_id = ?", (str(observation.event_id),)
            ).fetchone()
            if row:
                if observation_adapter.validate_json(row[0]) != observation:
                    raise Conflict("Event ID already has different contents")
                return False
            conn.execute(
                "INSERT INTO observations (event_id, session_id, document) VALUES (?, ?, ?)",
                (
                    str(observation.event_id),
                    str(observation.session_id),
                    observation.model_dump_json(),
                ),
            )
            from overlord.response import decide

            decide(conn, observation, self.cooldown)
            return True

    def observations(self, session_id: UUID, after: int, limit: int) -> list[Observation]:
        with self.connection() as conn:
            if not conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", (str(session_id),)
            ).fetchone():
                raise UnknownSession
            rows = conn.execute(
                "SELECT document FROM observations WHERE session_id = ? "
                "ORDER BY sequence LIMIT ? OFFSET ?",
                (str(session_id), limit, after),
            ).fetchall()
            return [observation_adapter.validate_json(row[0]) for row in rows]
