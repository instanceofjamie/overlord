# OVERLORD

**An experimental AI-driven mission director for Arma 3.**

OVERLORD aims to bring a Zeus-like AI mission director to cooperative Arma 3. It observes significant in-game events, keeps a persistent model of the operation, and proposes bounded actions that the Arma server validates and executes. The long-term ambition is a responsive, believable mission director that can react to player choices without omniscient enemy cheating.

> **Status:** Planning / pre-alpha. There is no playable release yet.

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

This project is being developed in the open; architecture and issue feedback are welcome. Contributor documentation and an explicit software licence are tracked in [#1](https://github.com/instanceofjamie/overlord/issues/1).

**No open-source licence has been selected yet.** A public repository does not automatically grant reuse or redistribution rights.

OVERLORD is an independent community project, not affiliated with Bohemia Interactive.
