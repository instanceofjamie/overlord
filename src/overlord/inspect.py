# SPDX-License-Identifier: Apache-2.0
"""Read persisted observations; never invokes a provider or submits gameplay commands."""

import argparse
import json
from uuid import UUID

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect recorded mission observations")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--session", type=UUID)
    choice.add_argument("--latest", action="store_true", help="Most recently registered session")
    args = parser.parse_args()
    try:
        with httpx.Client(base_url=args.url, timeout=10, trust_env=False) as client:
            session_id = args.session
            if args.latest:
                response = client.get("/v1/sessions", params={"limit": 1})
                response.raise_for_status()
                sessions = response.json()
                if not sessions:
                    parser.exit(1, "No sessions recorded yet.\n")
                session_id = sessions[0]["session_id"]
            print(f"Session: {session_id}")
            offset = 0
            while True:
                response = client.get(
                    f"/v1/sessions/{session_id}/observations",
                    params={"offset": offset, "limit": 100},
                )
                response.raise_for_status()
                observations = response.json()
                for observation in observations:
                    print(json.dumps(observation, indent=2))
                offset += len(observations)
                if len(observations) < 100:
                    break
            print(f"Recorded observations: {offset}")
    except httpx.HTTPError as exc:
        parser.exit(1, f"Inspection failed: {exc}\n")


if __name__ == "__main__":
    main()
