# SPDX-License-Identifier: Apache-2.0
"""Opt-in Windows/WSL headless engine probe. Own servers only; no human-client validation."""

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn
from fastapi.responses import JSONResponse
from pydantic import SecretStr

from overlord.api import create_app
from overlord.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arma-path", required=True, help="Windows path to existing game/server install"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    # Arma's profile/cache I/O needs a native Windows path, not a WSL UNC share.
    if os.name == "nt":
        runtime = Path(os.environ["LOCALAPPDATA"]) / "OVERLORD/dedicated"
    else:
        local = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[Environment]::GetFolderPath('LocalApplicationData')",
            ],
            text=True,
        ).strip()
        runtime = (
            Path(subprocess.check_output(["wslpath", "-u", local], text=True).strip())
            / "OVERLORD/dedicated"
        )
    runtime.mkdir(parents=True, exist_ok=True)
    evidence = {
        "scope": "Real dedicated engine; synthetic attack telemetry; no player clients connected",
        "tests": [],
        "sessions": [],
    }
    evidence["source_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "missions/OperationFirstContact.Altis").iterdir()
        if p.is_file()
    }
    token = secrets.token_urlsafe(32)
    database = runtime / ("probe-" + uuid4().hex + ".sqlite3")
    fault = {"block_ack": False, "packet": None}
    owned_pid = None
    server = None
    thread = None
    excluded_reports = set()

    def windows(path):
        if os.name == "nt":
            return str(path)
        return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()

    def ps(command):
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout

    def start_engine():
        nonlocal excluded_reports
        excluded_reports = set((runtime / "profiles").glob("*.rpt"))
        script = windows(root / "tools/start-dedicated.ps1")
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script,
                "-ArmaPath",
                args.arma_path,
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=True,
        )
        (runtime / "launch-private.txt").write_text(result.stdout)
        pid = int((runtime / "server.pid").read_text())
        print(f"Owned dedicated server started: PID {pid}", flush=True)
        return pid

    def stop_engine(pid):
        # Never use name-based shutdown or touch WSL/a client/any pre-existing process.
        ps(
            f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
            'if ($p) { if ($p.ProcessName -ne "arma3server_x64") '
            '{throw "Owned PID has unexpected process name"}; '
            "$p | Stop-Process; $p.WaitForExit(10000) | Out-Null }"
        )
        print(f"Owned dedicated server exited: PID {pid}", flush=True)

    def rpt():
        files = [p for p in (runtime / "profiles").glob("*.rpt") if p not in excluded_reports]
        return (
            max(files, key=lambda p: p.stat().st_mtime).read_text(errors="replace") if files else ""
        )

    def wait_for(predicate, label, seconds=90):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                print("Verified: " + label, flush=True)
                evidence["tests"].append({"name": label, "passed": True})
                return value
            time.sleep(0.5)
        raise RuntimeError("Timed out: " + label + "; inspect ignored var/dedicated/profiles RPT")

    def start_director():
        app = create_app(
            Settings(database_path=database, operator_token=SecretStr(token), _env_file=None)
        )

        @app.middleware("http")
        async def fault_boundary(request, call_next):
            if request.url.path == "/v1/acknowledgements" and fault["block_ack"]:
                return JSONResponse(
                    status_code=503, content={"detail": "Probe: deliberately lost ack"}
                )
            if request.url.path == "/v1/commands/poll" and fault["packet"]:
                return JSONResponse(content=fault["packet"])
            return await call_next(request)

        service = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
        )
        worker = threading.Thread(target=service.run, daemon=True)
        worker.start()
        wait_for(lambda: service.started, "owned director started", 10)
        return service, worker

    def stop_director():
        if server:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Owned director did not exit normally")

    # Fail rather than replace an existing listener, director or Arma server.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8000))
    try:
        owned_pid = start_engine()
        wait_for(
            lambda: "OVERLORD SESSION " in rpt(), "dedicated mission initialised without clients"
        )
        first_rpt = rpt()
        session = first_rpt.split("OVERLORD SESSION ")[-1].split(";")[0]
        wait_for(
            lambda: "DIRECTOR UNAVAILABLE" in rpt(),
            "director initially offline; server retains events",
            25,
        )
        server, thread = start_director()
        with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=3) as client:

            def events(sid):
                r = client.get(f"/v1/sessions/{sid}/observations")
                return r.json() if r.status_code == 200 else []

            wait_for(lambda: events(session), "startup event delivered after reconnect")
            assert events(session)[0]["payload"]["player_count"] == 0
            headers = {"Authorization": "Bearer " + token}
            path = f"/v1/sessions/{session}"
            assert client.put(path + "/control", json={"enabled": True}).status_code == 403
            client.put(
                path + "/control", json={"enabled": True}, headers=headers
            ).raise_for_status()
            time.sleep(1.1)
            fault["block_ack"] = True
            attack = dict(
                protocol_version="1.0",
                session_id=session,
                event_id=str(uuid4()),
                timestamp=datetime.now(UTC).isoformat(),
                event_type="checkpoint_attacked",
                payload=dict(
                    checkpoint_id="checkpoint_alpha",
                    attacking_side="BLUFOR",
                    report_channel="guard_radio",
                    reserve_available=True,
                ),
            )
            client.post("/v1/observations", json=attack).raise_for_status()
            packet = client.post("/v1/commands/poll", json={"session_id": session}).json()
            wait_for(
                lambda: "ORDER APPLIED " + packet[4][0] in rpt(),
                "real server-local movement order applied",
            )
            assert client.get(path + "/responses").json()["responses"][0]["acknowledgement"] is None
            stop_director()
            time.sleep(4)
            fault["block_ack"] = False
            server, thread = start_director()
            wait_for(
                lambda: client.get(path + "/responses").json()["responses"][0]["acknowledgement"],
                "actual ack retained through director restart",
            )
            fault["packet"] = packet
            wait_for(
                lambda: "CACHED RESULT " + packet[4][0] in rpt(),
                "forced duplicate delivery returns cached result",
            )
            fault["packet"] = None
            lines = [line for line in rpt().splitlines() if '"OVERLORD ' in line]
            assert sum("ORDER APPLIED " in line for line in lines) == 1
            evidence["sessions"].append(
                dict(
                    session_id=session,
                    observations=events(session),
                    responses=client.get(path + "/responses").json()["responses"],
                    rpt_lines=lines,
                )
            )
            stop_engine(owned_pid)
            owned_pid = None
            time.sleep(2)
            owned_pid = start_engine()
            wait_for(
                lambda: (
                    "OVERLORD SESSION " in rpt()
                    and session not in rpt().split("OVERLORD SESSION ")[-1].split(";")[0]
                ),
                "server restart creates a new mission session",
            )
            new_session = rpt().split("OVERLORD SESSION ")[-1].split(";")[0]
            wait_for(lambda: events(new_session), "new session registers independently")
            fault["packet"] = packet
            wait_for(
                lambda: "IGNORED PACKET: wrong mission/session" in rpt(),
                "previous-session command rejected by real engine",
            )
            fault["packet"] = None
            assert "ORDER APPLIED " not in rpt()
            assert not client.get(f"/v1/sessions/{new_session}/responses").json()["control"][
                "enabled"
            ]
            evidence["sessions"].append(
                dict(
                    session_id=new_session,
                    observations=events(new_session),
                    rpt_lines=[line for line in rpt().splitlines() if '"OVERLORD ' in line],
                )
            )
        evidence["result"] = "passed"
    finally:
        if owned_pid:
            stop_engine(owned_pid)
        stop_director()
        (runtime / "probe-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Headless dedicated probe passed. Two-player gameplay is NOT validated.", flush=True)


if __name__ == "__main__":
    main()
