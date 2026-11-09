# SPDX-License-Identifier: Apache-2.0
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from overlord.api import create_app
from overlord.config import Settings
from overlord.logging import JsonFormatter
from overlord.models import observation_adapter
from overlord.providers import MockProvider
from overlord.storage import Store


@pytest.fixture
def settings(tmp_path):
    return Settings(database_path=tmp_path / "director.sqlite3", _env_file=None)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


def session(client):
    data = {
        "session_id": str(uuid4()),
        "mission_name": "Operation First Contact",
        "map_name": "Altis",
    }
    assert client.post("/v1/sessions", json=data).status_code == 201
    return data


def event(session_id, kind="mission_started"):
    return {
        "protocol_version": "1.0",
        "session_id": session_id,
        "event_id": str(uuid4()),
        "event_type": kind,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": {"player_count": 4}
        if kind == "mission_started"
        else {"checkpoint_id": "checkpoint_alpha", "attacking_side": "BLUFOR"},
    }


def test_health_version(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/version").json() == {
        "service": "overlord-director",
        "version": "0.1.0",
        "protocol_version": "1.0",
        "provider": "mock",
    }


def test_roundtrip_restart_and_order(client, settings):
    data = session(client)
    started = event(data["session_id"])
    attacked = event(data["session_id"], "checkpoint_attacked")
    # Receive attack before startup: preserve receipt order, do not infer chronology.
    for observation in [attacked, started]:
        assert client.post("/v1/observations", json=observation).status_code == 201
    path = f"/v1/sessions/{data['session_id']}/observations"
    with TestClient(create_app(settings)) as restarted:
        rows = restarted.get(path).json()
        assert [r["event_id"] for r in rows] == [attacked["event_id"], started["event_id"]]
        assert restarted.get(path, params={"offset": 1, "limit": 1}).json() == rows[1:]
    with sqlite3.connect(settings.database_path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM observations").fetchone()[0] == 2


def test_replays_and_conflicts(client):
    data = session(client)
    assert client.post("/v1/sessions", json=data).status_code == 201
    assert client.post("/v1/sessions", json={**data, "map_name": "Stratis"}).status_code == 409
    observation = event(data["session_id"])
    assert client.post("/v1/observations", json=observation).status_code == 201
    replay = client.post("/v1/observations", json=observation)
    assert replay.status_code == 200
    assert replay.json()["status"] == "duplicate"
    observation["payload"]["player_count"] = 3
    assert client.post("/v1/observations", json=observation).status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        {"protocol_version": "2.0"},
        {"event_type": "execute_sqf"},
        {"timestamp": "2026-11-07T12:00:00"},
        {"event_id": "bad"},
        {"sqf": "secret"},
        {"payload": {"player_count": 257}},
        {"payload": {"player_count": "4"}},
        {"payload": {"player_count": True}},
        {"payload": {"player_count": 4, "extra": "secret"}},
        {"event_type": "checkpoint_attacked", "payload": {"player_count": 4}},
        {
            "event_type": "checkpoint_attacked",
            "payload": {"checkpoint_id": "x" * 65, "attacking_side": "BLUFOR"},
        },
        {
            "event_type": "checkpoint_attacked",
            "payload": {"checkpoint_id": "alpha", "attacking_side": "CIVILIAN"},
        },
    ],
)
def test_invalid_events_not_persisted(client, change):
    data = session(client)
    response = client.post("/v1/observations", json={**event(data["session_id"]), **change})
    assert response.status_code == 422
    assert "secret" not in response.text
    assert client.get(f"/v1/sessions/{data['session_id']}/observations").json() == []


def test_unknown_session_and_pagination(client):
    unknown = str(uuid4())
    assert client.post("/v1/observations", json=event(unknown)).status_code == 404
    assert client.get(f"/v1/sessions/{unknown}/observations").status_code == 404
    known = session(client)["session_id"]
    assert client.get(f"/v1/sessions/{known}/observations?limit=101").status_code == 422
    assert client.get(f"/v1/sessions/{known}/observations?offset=-1").status_code == 422


def test_concurrent_replays(settings):
    store = Store(settings.database_path)
    store.initialize()
    from overlord.models import SessionCreate

    data = SessionCreate(session_id=uuid4(), mission_name="First Contact", map_name="Altis")
    store.create_session(data)
    observation = observation_adapter.validate_python(event(str(data.session_id)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.record(observation), range(8)))
    assert results.count(True) == 1
    assert len(store.observations(data.session_id, 0, 100)) == 1


def test_migration_rejects_newer_schema(settings):
    store = Store(settings.database_path)
    store.initialize()
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("PRAGMA user_version = 99")
    with pytest.raises(RuntimeError, match="newer"):
        store.initialize()


def test_settings_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("OVERLORD_DATABASE_PATH", str(tmp_path / "other.sqlite3"))
    monkeypatch.setenv("OVERLORD_PORT", "8100")
    assert Settings(_env_file=None).port == 8100
    assert Settings(_env_file=None).database_path == tmp_path / "other.sqlite3"
    monkeypatch.setenv("OVERLORD_PROVIDER", "bedrock")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_mock_is_deterministic():
    observation = observation_adapter.validate_python(event(str(uuid4())))
    provider = MockProvider()
    assert provider.deliberate(observation) == provider.deliberate(observation)
    assert provider.deliberate(observation).action == "no_action"


def test_structured_logs():
    import logging

    record = logging.LogRecord(
        "overlord.api", logging.INFO, "", 0, "observation_ingested", (), None
    )
    record.event_id = "test-id"
    data = json.loads(JsonFormatter().format(record))
    assert data["event"] == "observation_ingested"
    assert data["event_id"] == "test-id"


def test_storage_failure_is_503(client, settings):
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("DROP TABLE observations")
        conn.execute("DROP TABLE sessions")
    assert client.get("/health").status_code == 503


def test_session_inspection(client, settings):
    assert client.get("/v1/sessions").json() == []
    first = session(client)
    second = session(client)
    assert client.post("/v1/sessions", json=first).status_code == 201
    assert client.get("/v1/sessions?limit=1").json() == [second]
    assert client.get("/v1/sessions?limit=101").status_code == 422
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/v1/sessions").json() == [second, first]
