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


## Documentation alignment — 2026-11-08

Updated README, architecture and FinOps transport wording on PR #24 after reading
the revised issues #2, #6, #11, #15, #22, #25, #26 and #27. Brought in the latest
`main` HostHavoc follow-up. Runtime code, schemas, migrations, dependencies, tests
and CI configuration are unchanged from the foundation implementation.

Checks run for this update:

- Existing regression suite: 22 passed on Linux / Python 3.12.3, with the same
  upstream Starlette/HTTPX TestClient deprecation warning. Run outside the sandbox
  because its threaded TestClient restriction was established previously.
- `ruff check .`, `ruff format --check .`, `mypy src/overlord` and
  `git diff --check` passed.
- Local Markdown link targets exist; newly referenced GitHub issue targets were
  fetched successfully. Checked fenced blocks and Mermaid structure, and manually
  reviewed candidate transport paths against the prose. No rendered Mermaid
  preview was run.
- Reviewed API, simulation and provider source against the demonstration wording:
  ingestion records observations; the client invokes the mock locally; mock output
  is not a stored decision or executable command.

The fresh installation, `pip check` and live HTTP simulation above are previously
reported evidence from 2026-11-07, not checks repeated for this documentation update.
No SITREP, provenance fields, faction reasoning, transport probe or game integration
was implemented or verified today. Native HTTP and DLL/HTTPS compatibility still
require #26/#22 evidence on the actual production server. No issues were closed.
