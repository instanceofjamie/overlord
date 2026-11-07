# OVERLORD

**An experimental AI-driven mission director for Arma 3.**

OVERLORD aims to bring a Zeus-like AI mission director to cooperative Arma 3. It observes significant in-game events, keeps a persistent model of the operation, and proposes bounded actions that the Arma server validates and executes. The long-term ambition is a responsive, believable mission director that can react to player choices without omniscient enemy cheating.

> **Status:** Pre-alpha Python observation recorder. There is no playable Arma release yet.

## First playable target

**Operation First Contact:** A small co-op squad investigates an OPFOR checkpoint on Altis. The director observes meaningful events and can decide whether to send reinforcements, issue radio updates, change objectives, or deliberately do nothing. Its decisions must respect limited resources and faction knowledge.

## Roadmap

| Phase | Focus | Issues |
| --- | --- | --- |
| M0 — Foundations | Project conventions, architecture, scenario definition | [#1–#3](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M0) |
| M1 — Arma mission | Vanilla multiplayer mission, SQF actions, observations | [#4–#6](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M1) |
| M2 — Director | Python API, protocols, persistence, deterministic mock | [#7–#10](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M2) |
| M3 — Integration | Async native bridge, observations, validated command delivery | [#11–#13](https://github.com/instanceofjamie/overlord/issues?q=is%3Aissue+is%3Aopen+M3) |
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

Arma 3 (SQF) ↔ non-blocking native extension ↔ Python director (FastAPI, Pydantic, SQLite) ↔ optional model provider (initially deterministic mock, later Amazon Bedrock).

This is a provisional architecture; see [#2](https://github.com/instanceofjamie/overlord/issues/2) for design decisions.

## Contributing and licensing

This project is being developed in the open; architecture and issue feedback are welcome. Contributor documentation is tracked in [#1](https://github.com/instanceofjamie/overlord/issues/1).

**Licence:** Original OVERLORD source and project documentation are made available under the [Apache License 2.0](LICENSE) (SPDX: `Apache-2.0`). This permits commercial use, modifications and redistribution subject to the licence conditions. Bohemia Interactive game content and third-party components remain subject to their own terms; do not assume they are included under Apache-2.0. See the [licensing record](docs/licensing-options.md) for the project policy.

OVERLORD is an independent community project, not affiliated with Bohemia Interactive.

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
with deterministic `no_action` mock results. It exits after retrieval; stop the
service with Ctrl-C. The observations remain in `var/overlord.sqlite3` across
service restarts. The printed session UUID can be used to read them again:

```sh
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/v1/sessions/SESSION_UUID/observations
```

Interactive API documentation is at <http://127.0.0.1:8000/docs>. Configure database
path, bind host/port and log level through `OVERLORD_*` variables or `.env` (see
[example](.env.example)); actual environment variables take precedence. Keep `.env`
untracked. This unauthenticated first slice is for trusted local development.

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
ordering semantics, migrations, limitations and the future outbound-only game
bridge. The current slice addresses #7 with partial groundwork for #2/#8/#9/#10;
it does not implement their full decision, command or game integration criteria.
