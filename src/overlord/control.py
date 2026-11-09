# SPDX-License-Identifier: Apache-2.0
"""Explicit session-scoped local operator control and inspection."""

import argparse
import json
from uuid import UUID

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, type=UUID)
    parser.add_argument("operation", choices=["status", "enable", "disable", "pause", "resume"])
    args = parser.parse_args()
    try:
        with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=10) as client:
            path = f"/v1/sessions/{args.session}"
            response = client.get(path + "/responses")
            response.raise_for_status()
            mode = response.json()["control"]
            if args.operation != "status":
                field = "enabled" if args.operation in ("enable", "disable") else "paused"
                mode[field] = args.operation in ("enable", "pause")
                response = client.put(path + "/control", json=mode)
                response.raise_for_status()
            response = client.get(path + "/responses")
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))
    except httpx.HTTPError as exc:
        parser.exit(1, f"Operator request failed: {exc}\n")


if __name__ == "__main__":
    main()
