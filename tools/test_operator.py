# SPDX-License-Identifier: Apache-2.0
"""Optional browser regression against an owned temporary service, not the game director."""

import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from pydantic import SecretStr

from overlord.api import create_app
from overlord.config import Settings


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        settings = Settings(
            database_path=Path(directory) / "operator.db",
            port=8051,
            operator_token=SecretStr("browser-test-operator"),
            _env_file=None,
        )
        config = uvicorn.Config(
            create_app(settings), host="127.0.0.1", port=8051, log_level="warning"
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        # Test bind availability without contacting or changing an existing service.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 8051))
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("Temporary test service did not start")
            subprocess.run(
                ["node", str(Path(__file__).with_suffix(".cjs"))],
                env={**os.environ, "OVERLORD_TEST_URL": "http://127.0.0.1:8051"},
                check=True,
                timeout=90,
            )
        finally:
            server.should_exit = True
            thread.join(timeout=10)


if __name__ == "__main__":
    main()
