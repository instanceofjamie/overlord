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

## Local observation demo — 2026-11-08

Started from `27ae4d9` on main, after PR #24 merged. Read current issues #2, #4,
#6, #8, #11, #12, #25 and #26, plus prior repository documentation. No repository
AGENTS.md instructions were found. The local executable metadata and operator
confirmation both identify Arma 3 2.22; this is not a runtime networking probe.

Checks performed for this increment:

- Python 3.12 regression suite: **25 passed**, with the same upstream Starlette/
  HTTPX TestClient deprecation warning. Ruff lint/format, strict mypy (10 source
  modules) and `git diff --check` passed.
- New session-list API: empty state, registration ordering, bounds and restart
  persistence; inspector: pagination and empty state tested. Existing protocol
  validation/deduplication tests remain intact. No schema/migration change.
- Native queue test passed on Linux and Windows: capacity includes pending and unread results,
  duplicate enqueue does not add work, changed pending payload rejects, terminal
  polling consumes a result, and reset clears only completed entries.
- MinGW Windows x64 DLL and smoke harness built. PE exports were checked;
  imports are Windows system libraries (including WinHTTP and Ole32 for OS GUIDs) (no separate MinGW runtime).
- Executed the cross-compiled Windows harness via Windows PowerShell against an
  isolated real loopback FastAPI service: registration 201, mission_started 201,
  checkpoint_attacked 201, repeated attack 200. Inspector retrieved exactly two
  events, including UNKNOWN attribution. Enqueues measured 0ms in these samples.
  Stopped the director and observed result `[0]`, still with a 0ms enqueue. These
  were synthetic harness observations, **not an actual in-game attack**.
- Per-run/event UUIDs use Windows CoCreateGuid rather than Eden-seeded random values;
  Windows ABI harness checked distinct UUIDs. Missing UUID support disables delivery
  while detection/debug remain active. Installer copy and overwrite-refusal test passed
  against a disposable Windows game tree; the actual game was not modified.
- SQF-VM v2026.04.03-ed9f5f5 parsed all four SQF scripts, description.ext and
  mission.sqm. Configs were wrapped in a class for the parser's root restriction.
  This is syntax-only evidence; SQF-VM cannot validate game handlers, placement,
  locality, DLL loading or scheduling in Arma. Reproduce using
  `python tools/check_sqf.py PATH_TO_SQFVM`.

A Windows CI job builds with MSVC, runs the native queue test and a real DLL/API
smoke test (offline, online, retries, duplicate storage, invalid version, inspector
and stalled response), then packages the DLL and mission. Check its run conclusion
on the PR before using the artifact; local manual evidence above is separate.

Not verified here: interactive Eden/hosted multiplayer, actual projectile detection,
terrain placement, production native HTTP, BattlEye compatibility, headless-client
ownership migration, HostHavoc or remote HTTPS/authentication. No game commands,
inference, cloud resources or third-party integrations were added. The deterministic
SITREP remains deferred pending successful playable connection.

Follow [the Windows playtest](local-demo.md); report runtime productVersion, session
UUID, detection/delivery messages and inspector output. Keep broad issues open until
those acceptance criteria are actually met.

### First interactive feedback: Eden load warning

The operator reported “Error when loading the scenario” while opening the mission
in Eden, before Play. The flushed RPT contained no specific scenario-load diagnostic.
Review found missing EditorData ItemIDProvider and Camera metadata in the hand-written
SQM. Added nextID=2 (above entity IDs 0 and 1), an initial camera, and ScenarioData
author metadata. All six mission files still pass the syntax check. Updated both
installed profile copies with backups for the operator's retest. This is a candidate
fix; successful Eden reopening and actual observation delivery remain unconfirmed.
