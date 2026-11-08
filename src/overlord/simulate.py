# SPDX-License-Identifier: Apache-2.0
import argparse
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from overlord.models import observation_adapter
from overlord.providers import MockProvider


def simulate(base_url: str) -> list[dict[str, object]]:
    session_id = str(uuid4())
    now = datetime.now(UTC)
    with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as client:
        client.get("/health").raise_for_status()
        client.post(
            "/v1/sessions",
            json={
                "session_id": session_id,
                "mission_name": "Operation First Contact",
                "map_name": "Altis",
            },
        ).raise_for_status()
        for event_type, payload, timestamp in (
            ("mission_started", {"player_count": 4}, now),
            (
                "checkpoint_attacked",
                {"checkpoint_id": "checkpoint_alpha", "attacking_side": "BLUFOR"},
                now + timedelta(seconds=30),
            ),
        ):
            event = {
                "protocol_version": "1.0",
                "session_id": session_id,
                "event_id": str(uuid4()),
                "event_type": event_type,
                "timestamp": timestamp.isoformat(),
                "payload": payload,
            }
            client.post("/v1/observations", json=event).raise_for_status()
        response = client.get(f"/v1/sessions/{session_id}/observations")
        response.raise_for_status()
        observations: list[dict[str, object]] = response.json()
        if len(observations) != 2:
            raise RuntimeError("Expected two recorded observations")
        for recorded in observations:
            decision = MockProvider().deliberate(observation_adapter.validate_python(recorded))
            print(json.dumps({"observation": recorded, "mock_decision": decision.model_dump()}))
        return observations


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit sample observations to a running director")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        simulate(args.url)
    except (httpx.HTTPError, RuntimeError) as exc:
        parser.exit(1, f"Simulation failed: {exc}\nStart the service with: overlord\n")
