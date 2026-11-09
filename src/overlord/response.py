# SPDX-License-Identifier: Apache-2.0
"""One bounded reserve. All state transitions share SQLite's writer transaction."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from overlord.models import Acknowledgement, Command, Control, Observation
from overlord.storage import Conflict, Store, UnknownSession


def now() -> datetime:
    return datetime.now(UTC)


def rows(conn: sqlite3.Connection, session: str) -> list[dict[str, Any]]:
    return [
        json.loads(r[0])
        for r in conn.execute(
            "SELECT document FROM responses WHERE session_id=? ORDER BY rowid", (session,)
        )
    ]


def save(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE responses SET document=? WHERE event_id=?", (json.dumps(row), row["event_id"])
    )


def control(conn: sqlite3.Connection, session: str) -> tuple[Control, datetime]:
    row = conn.execute(
        "SELECT document, changed_at FROM response_control WHERE session_id=?", (session,)
    ).fetchone()
    if not conn.execute("SELECT 1 FROM sessions WHERE session_id=?", (session,)).fetchone():
        raise UnknownSession
    return (
        (Control.model_validate_json(row[0]), datetime.fromisoformat(row[1]))
        if row
        else (Control(), datetime.min.replace(tzinfo=UTC))
    )


def expire(conn: sqlite3.Connection, result: list[dict[str, Any]], clock: datetime) -> None:
    for row in result:
        if row["command"] and row["state"] in ("proposed", "approved", "issued"):
            if Command.model_validate(row["command"]).expires_at <= clock:
                row["state"] = "uncertain" if row["committed"] else "expired"
                row["reason"] = (
                    "expiry reached; issued order may have run"
                    if row["committed"]
                    else "command expired"
                )
                save(conn, row)


def decide(conn: sqlite3.Connection, event: Observation, cooldown: int) -> None:
    # Called inside the ingestion transaction: replay cannot create another decision.
    if event.event_type != "checkpoint_attacked":
        return
    session = str(event.session_id)
    mode, changed = control(conn, session)
    previous = rows(conn, session)
    clock = now()
    expire(conn, previous, clock)
    reason = "checkpoint_attack: configured reserve response"
    state = "proposed"
    command = None
    if (
        event.payload.checkpoint_id != "checkpoint_alpha"
        or event.payload.attacking_side != "BLUFOR"
    ):
        reason = "unsuitable checkpoint or attacker (UNKNOWN is not hostile intent)"
    elif any(r["committed"] for r in previous):
        reason = "reserve already committed; unresolved execution never permits replacement"
    elif mode.paused:
        reason = "director paused"
    elif event.timestamp < clock - timedelta(seconds=120) or event.timestamp > clock + timedelta(
        seconds=5
    ):
        reason = "stale or future attack report"
    elif mode.enabled and event.timestamp <= changed:
        reason = "attack predates operator enable; fresh evidence required"
    elif any(
        clock - datetime.fromisoformat(r["created_at"]) < timedelta(seconds=cooldown)
        for r in previous
        if r["command"]
    ):
        reason = "response cooldown"
    elif any(r["state"] == "approved" for r in previous):
        reason = "reserve response already approved"
    else:
        for old in previous:
            if old["state"] == "proposed":
                old.update(state="expired", reason="superseded by fresh recommendation")
                save(conn, old)
        identity = uuid5(event.session_id, "reserve_alpha:" + str(event.event_id))
        expiry = (clock + timedelta(seconds=120)).replace(second=0, microsecond=0)
        command = Command(
            session_id=event.session_id,
            command_id=identity,
            idempotency_key=identity,
            triggering_event=event.event_id,
            expires_at=expiry,
        ).model_dump(mode="json")
        if mode.enabled:
            state = "approved"
    if command is None:
        state = "no_action"
    row = dict(
        event_id=str(event.event_id),
        session_id=session,
        state=state,
        reason=reason,
        created_at=clock.isoformat(),
        command=command,
        committed=False,
        acknowledgement=None,
    )
    conn.execute(
        "INSERT INTO responses VALUES (?,?,?)", (row["event_id"], session, json.dumps(row))
    )


class Responses:
    def __init__(self, store: Store):
        self.store = store

    def set_control(self, session: UUID, mode: Control) -> Control:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            old, _ = control(conn, str(session))
            if old == mode:
                return mode
            # Every mode transition invalidates all undispatched proposals/approvals.
            for row in rows(conn, str(session)):
                if row["state"] in ("proposed", "approved"):
                    row.update(
                        state="expired", reason="operator mode changed; fresh attack required"
                    )
                    save(conn, row)
            conn.execute(
                "INSERT OR REPLACE INTO response_control VALUES (?,?,?)",
                (str(session), mode.model_dump_json(), now().isoformat()),
            )
        return mode

    def inspect(self, session: UUID) -> dict[str, Any]:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            mode, _ = control(conn, str(session))
            result = rows(conn, str(session))
            expire(conn, result, now())
            return dict(control=mode.model_dump(), responses=result)

    def poll(self, session: UUID) -> list[Any]:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            mode, _ = control(conn, str(session))
            packet: list[Any] = ["1.0", str(session), mode.enabled, mode.paused, [], "no_action"]
            result = rows(conn, str(session))
            expire(conn, result, now())
            if result:
                packet[5] = result[-1]["state"]
            if not mode.enabled or mode.paused:
                return packet
            for row in result:
                if row["state"] not in ("approved", "issued"):
                    continue
                cmd = Command.model_validate(row["command"])
                if cmd.expires_at <= now():
                    row.update(state="uncertain" if row["committed"] else "expired")
                    save(conn, row)
                    continue
                # Commit BEFORE transport. Lost response consumes the budget conservatively.
                row.update(state="issued", committed=True)
                save(conn, row)
                expiry = cmd.expires_at
                packet[4] = [
                    str(cmd.command_id),
                    str(cmd.idempotency_key),
                    cmd.action,
                    cmd.asset,
                    cmd.location,
                    [expiry.year, expiry.month, expiry.day, expiry.hour, expiry.minute],
                ]
                packet[5] = "issued"
                break
            return packet

    def acknowledge(self, ack: Acknowledgement) -> None:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            control(conn, str(ack.session_id))
            for row in rows(conn, str(ack.session_id)):
                if not row["command"] or row["command"]["command_id"] != str(ack.command_id):
                    continue
                if not row["committed"] or row["command"]["idempotency_key"] != str(
                    ack.idempotency_key
                ):
                    raise Conflict("Command was not issued or key differs")
                document = ack.model_dump(mode="json")
                if row["acknowledgement"]:
                    if row["acknowledgement"] != document:
                        raise Conflict("Conflicting acknowledgement")
                    return
                if (ack.status == "executed") != (ack.result == "movement_order_assigned"):
                    raise Conflict("Result does not match status")
                row.update(state=ack.status, acknowledgement=document)
                save(conn, row)
                return
            raise Conflict("Unknown command for session")
