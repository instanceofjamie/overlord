# SPDX-License-Identifier: Apache-2.0
"""One bounded reserve. All state transitions share SQLite's writer transaction."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from overlord.models import Acknowledgement, Command, Control, Observation, observation_adapter
from overlord.operation import progression
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


def mission_state(conn: sqlite3.Connection, session: str) -> dict[str, Any]:
    events = [
        observation_adapter.validate_json(r[0])
        for r in conn.execute(
            "SELECT document FROM observations WHERE session_id=? ORDER BY sequence", (session,)
        )
    ]
    return progression(events)


def report_lines(conn: sqlite3.Connection, session: str, result: list[dict[str, Any]]) -> list[str]:
    progress = mission_state(conn, session)
    counts = {
        state: sum(r["state"] == state for r in result)
        for state in (
            "proposed",
            "approved",
            "issued",
            "executed",
            "rejected",
            "expired",
            "failed",
            "uncertain",
            "no_action",
        )
    }
    mode, _ = control(conn, session)
    name = (
        "observation only"
        if mode.observation_only
        else "recommendation only"
        if not mode.enabled
        else "execution automatic"
        if mode.automatic
        else "execution review"
    )
    return [
        "Director persisted snapshot; mode: " + name + ("; PAUSED" if mode.paused else ""),
        "Operation: " + progress["stage"],
        "Recon report recorded: " + str(progress["reconnaissance_reported"]),
        "Engagement recorded: " + str(progress["engagement_recorded"]),
        "Recommendations recorded: " + str(sum(bool(r["command"]) for r in result)),
        "Approvals recorded: " + str(sum(bool(r.get("approved_at")) for r in result)),
        "Responses (current lifecycle states): " + str(counts),
        "Latest reason: " + (result[-1]["reason"][:150] if result else "no attack decision"),
        "Movement applied is not arrival. Arrival is not tracked.",
    ]


def decide(conn: sqlite3.Connection, event: Observation, cooldown: int) -> None:
    # Called inside the ingestion transaction: replay cannot create another decision.
    if event.event_type == "operation_progress":
        if mission_state(conn, str(event.session_id))["outcome"] != "in_progress":
            for row in rows(conn, str(event.session_id)):
                if row["state"] in ("proposed", "approved"):
                    row.update(state="expired", reason="operation complete; no further dispatch")
                    save(conn, row)
        return
    if event.event_type != "checkpoint_attacked":
        return
    session = str(event.session_id)
    mode, changed = control(conn, session)
    previous = rows(conn, session)
    clock = now()
    expire(conn, previous, clock)
    reason = "Guard radio reports checkpoint harm; configured reserve response"
    state = "proposed"
    command = None
    if (
        event.payload.checkpoint_id != "checkpoint_alpha"
        or event.payload.attacking_side != "BLUFOR"
    ):
        reason = "unsuitable checkpoint or attacker (UNKNOWN is not hostile intent)"
    elif mission_state(conn, session)["outcome"] != "in_progress":
        reason = "operation complete"
    elif event.payload.report_channel != "guard_radio":
        reason = "no OPFOR report channel; director observation is not faction knowledge"
    elif not event.payload.reserve_available:
        reason = "mission reports reserve unavailable"
    elif mode.observation_only:
        reason = "observation only"
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
        if mode.enabled and mode.automatic:
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
        approved_at=clock.isoformat() if state == "approved" else None,
        approval_kind="enabled_rule" if state == "approved" else None,
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

    def approve(self, session: UUID, command_id: UUID) -> None:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            mode, changed = control(conn, str(session))
            result = rows(conn, str(session))
            expire(conn, result, now())
            if not mode.enabled or mode.paused or mode.observation_only:
                raise Conflict(
                    "Enable execution review first; paused/observation modes cannot approve"
                )
            if any(r["committed"] or r["state"] == "approved" for r in result):
                raise Conflict("Reserve already approved or committed")
            for row in result:
                if row["command"] and row["command"]["command_id"] == str(command_id):
                    if (
                        row["state"] != "proposed"
                        or datetime.fromisoformat(row["created_at"]) <= changed
                    ):
                        raise Conflict("Stale proposal; fresh attack required after enabling")
                    row.update(
                        state="approved",
                        reason="explicit operator approval of fresh guard report",
                        approved_at=now().isoformat(),
                        approval_kind="launch_operator",
                    )
                    save(conn, row)
                    return
            raise Conflict("Unknown recommendation")

    def inspect(self, session: UUID) -> dict[str, Any]:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            mode, _ = control(conn, str(session))
            result = rows(conn, str(session))
            expire(conn, result, now())
            return dict(control=mode.model_dump(), responses=result)

    def poll(self, session: UUID, include_report: bool = False) -> list[Any]:
        with self.store.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            mode, _ = control(conn, str(session))
            packet: list[Any] = ["1.0", str(session), mode.enabled, mode.paused, [], "no_action"]
            result = rows(conn, str(session))
            expire(conn, result, now())
            if result:
                packet[5] = result[-1]["state"]
            if include_report:
                packet.append(report_lines(conn, str(session), result))
            if (
                not mode.enabled
                or mode.paused
                or mode.observation_only
                or mission_state(conn, str(session))["outcome"] != "in_progress"
            ):
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
                row.update(
                    state="issued",
                    committed=True,
                    issued_at=row.get("issued_at") or now().isoformat(),
                )
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
                if include_report:
                    packet[6] = report_lines(conn, str(session), result)
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
                row.update(
                    state=ack.status, acknowledgement=document, ack_received_at=now().isoformat()
                )
                save(conn, row)
                return
            raise Conflict("Unknown command for session")
