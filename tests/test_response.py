# SPDX-License-Identifier: Apache-2.0
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_director import event

from overlord.api import create_app
from overlord.models import Acknowledgement, Control, SessionCreate, observation_adapter
from overlord.response import Responses
from overlord.storage import Conflict, Store


@pytest.fixture
def loop(tmp_path, monkeypatch):
    clock = [datetime(2026, 11, 9, 12, 0, 10, tzinfo=UTC)]
    monkeypatch.setattr("overlord.response.now", lambda: clock[0])
    store = Store(tmp_path / "loop.db", cooldown=15)
    store.initialize()
    session = uuid4()
    store.create_session(
        SessionCreate(session_id=session, mission_name="Operation First Contact", map_name="Altis")
    )
    return store, Responses(store), session, clock


def attack(loop, **payload):
    store, _, session, clock = loop
    data = event(str(session), "checkpoint_attacked")
    data["timestamp"] = clock[0].isoformat()
    data["payload"].update(payload)
    observation = observation_adapter.validate_python(data)
    store.record(observation)
    return observation


def test_recommend_only_stale_enable_and_cooldown(loop):
    store, responses, session, clock = loop
    observation = attack(loop)
    assert not store.record(observation)
    assert responses.inspect(session)["responses"][0]["state"] == "proposed"
    assert responses.poll(session)[4] == []
    responses.set_control(session, Control(enabled=True))
    assert responses.inspect(session)["responses"][0]["state"] == "expired"
    assert responses.poll(session)[4] == []
    clock[0] += timedelta(seconds=1)
    attack(loop)
    assert responses.inspect(session)["responses"][-1]["reason"] == "response cooldown"
    clock[0] += timedelta(seconds=16)
    attack(loop)
    command = responses.poll(session)[4]
    assert command[2:5] == ["dispatch_reserve", "reserve_alpha", "response_alpha"]
    assert responses.poll(session)[4] == command
    clock[0] += timedelta(seconds=20)
    attack(loop)
    assert responses.inspect(session)["responses"][-1]["state"] == "no_action"


@pytest.mark.parametrize(
    "status,result",
    [
        ("executed", "movement_order_assigned"),
        ("rejected", "reserve_ineligible"),
        ("expired", "expired"),
        ("failed", "uncertain"),
    ],
)
def test_ack_duplicate_conflict_and_restart(loop, status, result):
    store, responses, session, clock = loop
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=1)
    attack(loop)
    cmd = responses.poll(session)[4]
    # Lost poll/ack: reopen database, retrieve SAME identity, never mint a replacement.
    restarted = Responses(Store(store.path))
    assert restarted.poll(session)[4] == cmd
    ack = Acknowledgement(
        protocol_version="1.0",
        session_id=session,
        command_id=cmd[0],
        idempotency_key=cmd[1],
        status=status,
        result=result,
    )
    restarted.acknowledge(ack)
    restarted.acknowledge(ack)
    assert restarted.poll(session)[4] == []
    assert restarted.inspect(session)["responses"][0]["state"] == status
    with pytest.raises(Conflict):
        restarted.acknowledge(ack.model_copy(update={"result": "invalid_command"}))
    with pytest.raises(Conflict):
        restarted.acknowledge(ack.model_copy(update={"command_id": uuid4()}))
    clock[0] += timedelta(seconds=30)
    attack(loop)
    assert restarted.inspect(session)["responses"][-1]["state"] == "no_action"


def test_pause_disable_restart_and_expiry(loop):
    store, responses, session, clock = loop
    responses.set_control(session, Control(enabled=True, paused=True))
    clock[0] += timedelta(seconds=1)
    attack(loop)
    assert responses.poll(session)[4] == []
    assert responses.inspect(session)["responses"][-1]["reason"] == "director paused"
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=1)
    attack(loop)
    responses.set_control(session, Control())
    assert Responses(Store(store.path)).poll(session)[4] == []
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=20)
    attack(loop)
    clock[0] += timedelta(seconds=121)
    assert responses.poll(session)[4] == []
    assert responses.inspect(session)["responses"][-1]["state"] == "expired"
    attack(loop)
    issued = responses.poll(session)[4]
    assert issued
    responses.set_control(session, Control(enabled=True, paused=True))
    assert responses.poll(session)[4] == []
    clock[0] += timedelta(seconds=121)
    responses.set_control(session, Control(enabled=True))
    attack(loop)
    assert responses.poll(session)[4] == []
    assert responses.inspect(session)["responses"][-2]["state"] == "uncertain"


def test_unsuitable_stale_future_and_pre_enable_events(loop):
    store, responses, session, clock = loop
    attack(loop, attacking_side="UNKNOWN")
    attack(loop, checkpoint_id="elsewhere")
    old = event(str(session), "checkpoint_attacked")
    for delta in (-121, 10):
        old["event_id"] = str(uuid4())
        old["timestamp"] = (clock[0] + timedelta(seconds=delta)).isoformat()
        store.record(observation_adapter.validate_python(old))
    responses.set_control(session, Control(enabled=True))
    attack(loop)  # exactly at enable is unsuitable
    assert all(r["state"] == "no_action" for r in responses.inspect(session)["responses"])


def test_concurrent_approvals_only_one_identity(loop):
    store, responses, session, clock = loop
    store.cooldown = 0
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: attack(loop), range(8)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        deliveries = list(pool.map(lambda _: responses.poll(session)[4], range(8)))
    assert len({d[0] for d in deliveries}) == 1
    assert sum(r["committed"] for r in responses.inspect(session)["responses"]) == 1


def test_api_contract_and_session_isolation(loop):
    store, _, session, _ = loop
    from overlord.config import Settings

    with TestClient(create_app(Settings(database_path=store.path, _env_file=None))) as client:
        assert client.post("/v1/commands/poll", json={"session_id": str(session)}).json()[2:4] == [
            False,
            False,
        ]
        assert (
            client.post("/v1/commands/poll", json={"session_id": str(uuid4())}).status_code == 404
        )
        assert (
            client.put(
                f"/v1/sessions/{session}/control", json={"enabled": True, "sqf": "bad"}
            ).status_code
            == 422
        )
        ack = dict(
            protocol_version="1.0",
            session_id=str(session),
            command_id=str(uuid4()),
            idempotency_key=str(uuid4()),
            status="executed",
            result="movement_order_assigned",
        )
        assert client.post("/v1/acknowledgements", json=ack).status_code == 409
        ack["session_id"] = str(UUID(int=0))
        assert client.post("/v1/acknowledgements", json=ack).status_code == 404


def test_migrate_v1_preserves_observations(tmp_path):
    import sqlite3

    from overlord.storage import MIGRATIONS

    path = tmp_path / "legacy.db"
    session = uuid4()
    doc = SessionCreate(session_id=session, mission_name="legacy", map_name="Altis")
    observation = observation_adapter.validate_python(event(str(session)))
    with sqlite3.connect(path) as conn:
        for statement in MIGRATIONS[0]:
            conn.execute(statement)
        conn.execute("PRAGMA user_version = 1")
        conn.execute("INSERT INTO sessions VALUES (?,?)", (str(session), doc.model_dump_json()))
        conn.execute(
            "INSERT INTO observations(event_id,session_id,document) VALUES (?,?,?)",
            (str(observation.event_id), str(session), observation.model_dump_json()),
        )
    store = Store(path)
    store.initialize()
    store.initialize()
    assert store.observations(session, 0, 100) == [observation]
    assert Responses(store).inspect(session) == dict(control=Control().model_dump(), responses=[])


def test_ack_before_issue_wrong_key_and_inconsistent_result(loop):
    _, responses, session, clock = loop
    attack(loop)
    doc = responses.inspect(session)["responses"][0]["command"]
    ack = Acknowledgement(
        protocol_version="1.0",
        session_id=session,
        command_id=doc["command_id"],
        idempotency_key=doc["idempotency_key"],
        status="executed",
        result="movement_order_assigned",
    )
    with pytest.raises(Conflict):
        responses.acknowledge(ack)
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=20)
    attack(loop)
    cmd = responses.poll(session)[4]
    ack = ack.model_copy(update={"command_id": UUID(cmd[0]), "idempotency_key": uuid4()})
    with pytest.raises(Conflict):
        responses.acknowledge(ack)
    ack = ack.model_copy(update={"idempotency_key": UUID(cmd[1]), "result": "invalid_command"})
    with pytest.raises(Conflict):
        responses.acknowledge(ack)
