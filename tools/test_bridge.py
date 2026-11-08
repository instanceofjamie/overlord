# SPDX-License-Identifier: Apache-2.0
"""Windows ABI + real HTTP regression check; requires port 8000 to be unused."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path, help="Directory containing DLL and extension_smoke.exe")
    args = parser.parse_args()
    build = args.build.resolve()
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("Port 8000 is in use; stop your local director before this test")
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        session = str(uuid4())
        data = {
            "session_id": session,
            "mission_name": "Operation First Contact",
            "map_name": "Altis",
        }

        def submit(identifier: str, kind: str, body: dict[str, object], expected: int) -> None:
            fixture = temp / "body.json"
            fixture.write_text(json.dumps(body), encoding="utf-8")
            subprocess.run(
                [
                    str(build / "extension_smoke.exe"),
                    str(build / "overlord_bridge_x64.dll"),
                    identifier,
                    kind,
                    str(fixture),
                    str(expected),
                ],
                check=True,
                timeout=15,
            )

        # Offline requests still enqueue promptly and complete with an error, never a false ack.
        submit(session, "session", data, 0)
        env = {
            **os.environ,
            "OVERLORD_DATABASE_PATH": str(temp / "test.sqlite3"),
            "OVERLORD_HOST": "127.0.0.1",
            "OVERLORD_PORT": "8000",
        }
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "overlord.api:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            env=env,
        )
        try:
            with httpx.Client(
                base_url="http://127.0.0.1:8000", trust_env=False, timeout=2
            ) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Director failed to start")
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Director startup timeout")
                submit(session, "session", data, 201)
                events = []
                for kind, payload in [
                    ("mission_started", {"player_count": 1}),
                    (
                        "checkpoint_attacked",
                        {"checkpoint_id": "checkpoint_alpha", "attacking_side": "UNKNOWN"},
                    ),
                ]:
                    event = {
                        "protocol_version": "1.0",
                        "session_id": session,
                        "event_id": str(uuid4()),
                        "event_type": kind,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": payload,
                    }
                    submit(str(event["event_id"]), "event", event, 201)
                    submit(str(event["event_id"]), "event", event, 200)
                    events.append(event)
                submit(
                    str(events[0]["event_id"]),
                    "event",
                    {**events[0], "protocol_version": "invalid"},
                    422,
                )
                stored = client.get(f"/v1/sessions/{session}/observations").json()
                assert [row["event_id"] for row in stored] == [row["event_id"] for row in events]
                assert stored[1]["payload"]["attacking_side"] == "UNKNOWN"
                subprocess.run(
                    [sys.executable, "-m", "overlord.inspect", "--latest"], check=True, timeout=10
                )
        finally:
            process.terminate()
            process.wait(timeout=10)
        submit(session, "session", data, 0)
        # Accept a request but never respond: exercise the worker's receive timeout.
        with socket.socket() as stalled:
            stalled.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            stalled.bind(("127.0.0.1", 8000))
            stalled.listen(1)

            def stall() -> None:
                connection, _ = stalled.accept()
                with connection:
                    connection.recv(4096)
                    time.sleep(4)

            thread = threading.Thread(target=stall, daemon=True)
            thread.start()
            submit(session, "session", data, 0)
            thread.join(timeout=6)
        print("Windows DLL: offline/online/duplicates/validation/inspection/timeout passed")


if __name__ == "__main__":
    main()
