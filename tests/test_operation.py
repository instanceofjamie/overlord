# SPDX-License-Identifier: Apache-2.0
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_director import event
from test_response import attack

from overlord.api import create_app
from overlord.config import Settings
from overlord.models import Control, SessionCreate, observation_adapter
from overlord.operation import debrief, progression
from overlord.storage import Conflict, Store


@pytest.fixture
def loop(tmp_path, monkeypatch):
    from overlord.response import Responses

    clock = [datetime(2026, 11, 9, 12, 0, 10, tzinfo=UTC)]
    monkeypatch.setattr("overlord.response.now", lambda: clock[0])
    store = Store(tmp_path / "operation.db", cooldown=15)
    store.initialize()
    session = uuid4()
    store.create_session(
        SessionCreate(session_id=session, mission_name="Operation First Contact", map_name="Altis")
    )
    return store, Responses(store), session, clock


def progress(session, milestone):
    data = event(str(session))
    data.update(event_type="operation_progress", payload={"milestone": milestone})
    return observation_adapter.validate_python(data)


def test_recon_only_and_duplicate_out_of_order_progress():
    session = uuid4()
    premature = progress(session, "extracted")
    brief = progress(session, "briefing_complete")
    recon = progress(session, "recon_reported")
    extract = progress(session, "extracted")
    report = debrief(
        [premature, brief, brief, recon, extract, progress(session, "operator_killed")], []
    )
    assert report["outcome"] == "succeeded"
    assert report["reconnaissance_reported"]
    assert not report["engagement_recorded"]
    assert len(report["accepted_progress_events"]) == 3
    assert len(report["ignored_progress_events"]) == 3
    assert "not tracked" in report["reserve_arrival"]


@pytest.mark.parametrize("milestone", ["aborted", "operator_killed"])
def test_failure_is_terminal(milestone):
    session = uuid4()
    report = progression(
        [
            progress(session, "briefing_complete"),
            progress(session, milestone),
            progress(session, "recon_reported"),
            progress(session, "extracted"),
        ]
    )
    assert report["outcome"] == "failed"
    assert not report["reconnaissance_reported"]


def test_minimal_faction_evidence_and_reserve_unavailable(loop):
    store, responses, session, clock = loop
    attack(loop, report_channel="none")
    attack(loop, report_channel="legacy_unverified")
    attack(loop, reserve_available=False)
    store.record(progress(session, "briefing_complete"))
    store.record(progress(session, "recon_reported"))
    assert responses.poll(session)[4] == []
    assert all(r["state"] == "no_action" for r in responses.inspect(session)["responses"])
    assert len(responses.inspect(session)["responses"]) == 3  # recon never triggers reserve
    clock[0] += timedelta(seconds=20)
    attack(loop)
    assert responses.inspect(session)["responses"][-1]["state"] == "proposed"


def test_fresh_manual_approval_and_terminal_stop(loop):
    store, responses, session, clock = loop
    attack(loop)
    stale = responses.inspect(session)["responses"][0]["command"]["command_id"]
    responses.set_control(session, Control(enabled=True, automatic=False))
    with pytest.raises(Conflict):
        responses.approve(session, stale)
    clock[0] += timedelta(seconds=20)
    attack(loop)
    command = responses.inspect(session)["responses"][-1]["command"]["command_id"]
    assert responses.poll(session)[4] == []
    from uuid import UUID

    responses.approve(session, UUID(command))
    row = responses.inspect(session)["responses"][-1]
    assert row["approval_kind"] == "launch_operator" and row["approved_at"]
    assert responses.poll(session)[4][0] == command
    for step in ("briefing_complete", "recon_reported", "extracted"):
        store.record(progress(session, step))
    assert responses.poll(session)[4] == []  # no new orders after completion
    clock[0] += timedelta(seconds=20)
    attack(loop)
    assert responses.inspect(session)["responses"][-1]["reason"] == "operation complete"


def test_disabled_pause_observation_and_expired_approval(loop):
    _, responses, session, clock = loop
    for mode in [
        Control(),
        Control(enabled=True, paused=True),
        Control(enabled=True, observation_only=True),
    ]:
        responses.set_control(session, mode)
        clock[0] += timedelta(seconds=20)
        attack(loop)
        with pytest.raises(Conflict):
            responses.approve(session, uuid4())
        assert responses.poll(session)[4] == []
    responses.set_control(session, Control(enabled=True, automatic=False))
    clock[0] += timedelta(seconds=20)
    attack(loop)
    command = responses.inspect(session)["responses"][-1]["command"]["command_id"]
    clock[0] += timedelta(seconds=121)
    from uuid import UUID

    with pytest.raises(Conflict):
        responses.approve(session, UUID(command))
    assert responses.poll(session)[4] == []


@pytest.mark.parametrize("credential", [None, "launch-test"])
def test_operator_permission_boundary_and_explanation(tmp_path, credential):
    settings = Settings(
        database_path=tmp_path / "auth.db",
        operator_token=SecretStr(credential) if credential else None,
        _env_file=None,
    )
    with TestClient(create_app(settings)) as client:
        session = str(uuid4())
        client.post(
            "/v1/sessions",
            json=dict(session_id=session, mission_name="Operation First Contact", map_name="Altis"),
        )
        path = f"/v1/sessions/{session}"
        status = client.get(path + "/operator-status").json()
        assert not status["permission"]["can_approve"]
        assert status["mode"] == "recommendation"
        assert client.get("/operator").headers["referrer-policy"] == "no-referrer"
        assert "launch-test" not in client.get("/operator").text
        expected = 403 if credential else 503
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            assert (
                client.put(path + "/control", json={"enabled": True}, headers=headers).status_code
                == expected
            )
            assert (
                client.post(
                    path + "/approve", json={"command_id": str(uuid4())}, headers=headers
                ).status_code
                == expected
            )
        assert not client.get(path + "/responses").json()["control"]["enabled"]
        if credential:
            headers = {"Authorization": "Bearer launch-test"}
            assert client.get(path + "/operator-status", headers=headers).json()["permission"][
                "can_approve"
            ]
            assert (
                client.put(
                    path + "/control",
                    json={"enabled": True},
                    headers={**headers, "Origin": "https://untrusted.example"},
                ).status_code
                == 403
            )
            assert (
                client.put(path + "/control", json={"enabled": True}, headers=headers).status_code
                == 200
            )


def test_persisted_debrief_overt_and_disconnect_recovery(loop):
    store, responses, session, _ = loop
    for step in ("briefing_complete", "recon_reported", "extracted"):
        store.record(progress(session, step))
    attack(loop)
    events = store.observations(session, 0, 100)
    report = debrief(events, responses.inspect(session)["responses"])
    assert report["engagement_recorded"] and report["outcome"] == "succeeded"
    assert report["responses"][0]["state"] == "no_action"
    assert report["responses"][0]["acknowledgement"] is None
    assert "missing events are unknown" in report["source"]


@pytest.mark.parametrize("configured", [False, True])
def test_normal_launcher_supplies_operator_credential(tmp_path, monkeypatch, capsys, configured):
    from overlord import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OVERLORD_OPERATOR_TOKEN", raising=False)
    if configured:
        monkeypatch.setenv("OVERLORD_OPERATOR_TOKEN", "configured-operator")
    monkeypatch.setattr(cli.secrets, "token_urlsafe", lambda _: "generated-operator")
    launches = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: launches.append((args, kwargs)))
    cli.main()
    expected = "configured-operator" if configured else "generated-operator"
    assert "#token=" + expected in capsys.readouterr().out
    assert Settings(_env_file=None).operator_token.get_secret_value() == expected
    assert launches[0][0] == ("overlord.api:create_app",)
    assert launches[0][1]["host"] == "127.0.0.1"


def test_faction_evidence_separate_from_player_progress(loop):
    store, responses, session, _ = loop
    store.record(progress(session, "briefing_complete"))
    store.record(progress(session, "recon_reported"))
    report = debrief(store.observations(session, 0, 100), responses.inspect(session)["responses"])
    assert report["reconnaissance_reported"] and report["faction_reports"] == []
    attack(loop)
    report = debrief(store.observations(session, 0, 100), responses.inspect(session)["responses"])
    assert len(report["faction_reports"]) == 1
    assert report["faction_reports"][0]["player_position"] == "not supplied"
    assert report["faction_reports"][0]["source"] == "guard_radio"


def test_report_snapshot_matches_issue_and_never_invents_arrival(loop):
    _, responses, session, clock = loop
    responses.set_control(session, Control(enabled=True))
    clock[0] += timedelta(seconds=1)
    attack(loop)
    packet = responses.poll(session, include_report=True)
    assert len(packet) == 7 and packet[5] == "issued"
    assert "'issued': 1" in packet[6][-3]
    import json

    assert len(json.dumps(packet).encode()) < 2048
    assert "Arrival is not tracked" in packet[6][-1]
    assert len(responses.poll(session)) == 6  # original clients retain the old wire shape
