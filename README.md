# OVERLORD

**An experimental AI-driven mission director for Arma 3.**

OVERLORD aims to direct the cooperative Arma 3 experience through intent, pacing, communication and bounded operational interventions. Arma and existing tactical or campaign systems retain their simulation responsibilities. Future action proposals must respect faction knowledge and be validated by the authoritative game server.

> **Status:** Local deterministic Operation First Contact: briefing, recon, optional combat, extraction and factual debrief. Prior transport/reserve playtests passed; the new playable flow awaits Eden testing.

## First playable target

**Operation First Contact** remains the immediate vanilla prototype target: a small co-op squad investigates an OPFOR checkpoint on Altis. Future interventions may include bounded reinforcements, radio updates, objective changes or deliberate restraint, subject to limited resources and faction knowledge. The local demo records real checkpoint events and defaults to recommendation-only. Explicit execution permission lets one preplaced reserve group receive one configured movement order per session.

## Roadmap

| Phase | Focus | Issues |
| --- | --- | --- |
| M0 — Foundations | Project conventions, architecture, scenario definition | [#1–#3](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M0) |
| M1 — Arma mission | Vanilla multiplayer mission, SQF actions, observations | [#4–#6](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M1) |
| M2 — Director | Python API, protocols, persistence, deterministic mock | [#7–#10](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M2) |
| M3 — Integration | Selected non-blocking transport, observations, validated command delivery | [#11–#13](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M3) |
| M4 — AI | LLM provider integration, bounded planning, faction intelligence | [#14–#16](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M4) |
| M5 — First release | Playable operation, documentation and diagnostics | [#17–#18](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M5) |

See the [issue tracker](https://github.com/instanceofjamie/overlord/issues) for the current implementation plan.

## Design principles

- **Arma remains authoritative.** AI proposals are not arbitrary SQF and cannot bypass validated server commands.
- **No simulation stalls.** LLM calls and external transport must not block the game thread.
- **Enemy knowledge is limited.** The director and in-game factions have different knowledge boundaries.
- **Restraint matters.** Good direction includes knowing when to do nothing.
- **Human override.** A human Zeus/admin should be able to pause, review or override AI actions.
- **Mock first.** The initial vertical slice works without an LLM, external service or paid credentials.

## Proposed technical direction

Arma 3 (SQF) ↔ local asynchronous x64 DLL ↔ independently deployed Python director (FastAPI, Pydantic, SQLite) ↔ optional model provider. [#26](https://github.com/instanceofjamie/overlord/issues/26) compares native `webRequest` with an asynchronous x64 extension before bridge implementation under [#11](https://github.com/instanceofjamie/overlord/issues/11). Native HTTP availability on the production server is unverified. The selected transport must be non-blocking and outbound, require no extra process on the managed game host, and pass HostHavoc validation under [#22](https://github.com/instanceofjamie/overlord/issues/22).

This is a provisional architecture; see [#2](https://github.com/instanceofjamie/overlord/issues/2) for design decisions.

## Experience-director modes

- **Observation-only:** collect and record events without issuing gameplay commands.
  The local recorder and demo SQF observer are implemented; the real in-game path
  was confirmed by the operator on 2026-11-08.
- **Recommendation-only (default):** record proposals, rationale, evidence and expected
  effects without dispatching commands; evaluate this before live execution under [#15](https://github.com/instanceofjamie/overlord/issues/15).
- **Authorised execution (bounded demo):** explicit operator configuration, capability and
  ownership checks, authoritative validation and human override gate any dispatch.

Future adapters must declare capabilities and ownership of units, objectives and
resources so OVERLORD cannot issue conflicting orders alongside another commander
([#2](https://github.com/instanceofjamie/overlord/issues/2)). Campaign memory, personality and third-party adapters remain future
work under [#27](https://github.com/instanceofjamie/overlord/issues/27); they are outside the vanilla prototype.

## Contributing and licensing

This project is being developed in the open; architecture and issue feedback are welcome. Contributor documentation is tracked in [#1](https://github.com/instanceofjamie/overlord/issues/1).

**Licence:** Original OVERLORD source and project documentation are made available under the [Apache License 2.0](LICENSE) (SPDX: `Apache-2.0`). This permits commercial use, modifications and redistribution subject to the licence conditions. Bohemia Interactive game content and third-party components remain subject to their own terms; do not assume they are included under Apache-2.0. See the [licensing record](docs/licensing-options.md) for the project policy.

OVERLORD is an independent community project, not affiliated with Bohemia Interactive.

## Play Operation First Contact

Follow [the Windows/Eden guide](docs/local-demo.md). Start the director with
`tools\start-overlord.cmd` (Windows clone) or `./tools/start-overlord.sh` (WSL).
Open its private operator-panel link, then load the matching mission in Eden.
The panel shows the active session, mode and approval permission; no development
task or console command is needed to enable execution or approve a fresh response.
Recommendation-only remains the default.

Read the briefing, use **Begin reconnaissance patrol**, reach **recon_alpha**,
observe the checkpoint and use **Report checkpoint reconnaissance**. Combat is
optional. Return alive to **extraction_alpha** and choose **Extract and debrief**.
The approximately 10–15 minute target includes a deliberate covered approach,
observation and return; no timer forces contact. One-player local preview is the
supported milestone; four-slot and dedicated-server acceptance remain open.

The operator may select observation, recommendation, execution with manual review,
or automatic bounded execution, and pause new dispatch. Mode changes expire old
proposals; fresh evidence is required after enabling. Pause does not cancel an
existing order. A surviving checkpoint guard's radio report is the narrow evidence
for a reserve response; recon reporting alone never informs OPFOR.

Essential tasks and a clearly labelled local debrief work during director downtime.
The panel displays persisted evidence and actual acknowledgements, with no claim
that assigning a movement order proves arrival. See [architecture](docs/architecture.md)
and [verification](docs/verification.md). No inference, spawning commands or new
gameplay command family was added.

## Local director quick start

Requires Python 3.12+ with pip and venv. No Arma, AWS account, cloud credentials or
LLM is needed. Run from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
cp .env.example .env
overlord
```

On Windows use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` in
PowerShell, then the same pip commands and `Copy-Item .env.example .env`.
The supplied lock records the tested development dependency versions. The package
metadata defines compatible dependency ranges; refresh the lock deliberately when
updating dependencies, then run all checks. The lock includes build tooling.

The service binds to `127.0.0.1:8000`. In another activated terminal:

```sh
overlord-simulate
# Or connect to another local port:
overlord-simulate --url http://127.0.0.1:8000
```

The simulation registers a fresh Operation First Contact session on Altis, submits
mission start and checkpoint attack observations, retrieves both and prints JSON
with `no_action` results from the deterministic mock invoked locally by the simulation
client. The API also records deterministic response decisions without invoking a model; default mode never dispatches.
The mock output is demonstration behaviour, not a persisted server decision or an
executable command. The client exits after retrieval; stop the service with Ctrl-C.
The observations remain in `var/overlord.sqlite3` across
service restarts. The printed session UUID can be used to read them again:

```sh
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/v1/sessions/SESSION_UUID/observations
```

Interactive API documentation is at <http://127.0.0.1:8000/docs>. Configure database
path, bind host/port and log level through `OVERLORD_*` variables or `.env` (see
[example](.env.example)); actual environment variables take precedence. Keep `.env`
untracked. Game transport is for a trusted local machine. Operator control mutations require
the private launch credential; remote hosting remains unsupported.

### Development checks

```sh
pytest
ruff check .
ruff format --check .
mypy src/overlord
```

Use feature branches and small issue-linked pull requests. Format changes with
`ruff format .`; production code uses strict mypy checks, Pydantic boundary
validation and pytest behavior tests. CI runs the same checks on Python 3.12.
See [architecture and protocol](docs/architecture.md) for components, retry and
ordering semantics, migrations, limitations and the local outbound-only game
bridge. The current slice adds local progression, authenticated operator controls and factual
debrief to the response loop. Broad mission, intelligence and dedicated multiplayer
acceptance criteria remain open.

### Subsequent milestones

Produce a bounded, deterministic structured SITREP from recorded observations under
[#6](https://github.com/instanceofjamie/overlord/issues/6), separating observed facts, inference and unknowns. SITREP formatting remains deferred until the playable connection is verified. Recommendation-only evaluation should precede live execution.
The implemented initial observation contract v1.0 retains its current schema and
version validation; ecosystem research under [#25](https://github.com/instanceofjamie/overlord/issues/25) and real SQF requirements
under [#6](https://github.com/instanceofjamie/overlord/issues/6)/[#8](https://github.com/instanceofjamie/overlord/issues/8) should inform its evolution before broader interfaces
are finalised. Complete [#26](https://github.com/instanceofjamie/overlord/issues/26) before selecting production transport.

`attacking_side` currently records a reported observation; it is not automatically
knowledge available to an enemy faction. Evidence provenance and faction-authorised
context must be addressed before enemy planning under [#16](https://github.com/instanceofjamie/overlord/issues/16). SITREPs,
provenance fields and faction reasoning are outside this PR.
