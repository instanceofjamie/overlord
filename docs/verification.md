<!-- SPDX-License-Identifier: Apache-2.0 -->
# Foundation verification — 2026-11-07

Verified on Linux with Python 3.12.3:

- Fresh virtual environment installation using `requirements-dev.lock`, editable
  install with `--no-deps --no-build-isolation`, and `pip check`.
- `pytest`: 22 passed. Covers the two event types, restart persistence, migrations,
  concurrent retries, conflict detection, invalid/mismatched/unbounded payloads,
  environment settings, deterministic no-op, pagination and storage failure.
- `ruff check .`, `ruff format --check .`, `mypy src/overlord`, `git diff --check`.
- Actual `overlord` HTTP server and `overlord-simulate` on loopback: both events
  submitted and retrieved, each displaying `no_action`; client exited zero and
  server shut down cleanly on Ctrl-C.

The installed Starlette emits one upstream deprecation warning about its HTTPX
TestClient adapter. Tests pass; migrating the test adapter can be evaluated in a
separate dependency update.

This execution environment restricts sockets and threaded TestClient execution;
network tests and the live HTTP smoke test were rerun outside that sandbox.
Windows instructions, other Python versions, Arma, HostHavoc DLL loading/outbound
HTTPS and any cloud deployment have not been tested. No AWS resources or paid
inference were used. The CLI connects to an already-running service; it does not
manage its lifecycle. Protocol commands, decisions/acknowledgements and faction
intelligence are intentionally absent.
