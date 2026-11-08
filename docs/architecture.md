<!-- SPDX-License-Identifier: Apache-2.0 -->
# Director foundation

Implemented in the first Python slice for #7; partial groundwork for #2, #8,
#9 and #10. This is an observation recorder, not a playable AI director.

```mermaid
flowchart LR
    CLI[Local simulation] -->|HTTP JSON| API[FastAPI validation]
    API --> DB[(SQLite sessions and observations)]
    API -->|Retrieve recorded observations| CLI
    CLI --> Mock[Deterministic no_action provider]
    SQF[Future authoritative SQF observer] -.-> Transport[Future transport selected under issue 26]
    Transport -.-> Native[Candidate native webRequest - unverified]
    Transport -.-> DLL[Candidate asynchronous x64 extension]
    Native -.->|Outbound HTTPS subject to issue 22| API
    DLL -.->|Outbound HTTPS subject to issue 22| API
```

## Implemented components

- `config.py`: Pydantic environment settings, `.env` support, mock-only provider.
- `models.py`: closed, discriminated observation schemas. Unknown fields are rejected.
- `api.py`: application factory and lifespan initialization, health/version, session
  registration, event ingestion and bounded observation retrieval. Synchronous
  endpoints run SQLite work in FastAPI's worker pool.
- `storage.py`: SQLite transactions, foreign keys, unique event IDs and receipt order.
  Each operation owns and closes its connection; writes use `BEGIN IMMEDIATE`
  and a five-second lock timeout. Storage errors return 503, not success.
- `providers.py`: typed provider interface and a pure deterministic no-op mock.
  Ingestion never invokes inference. The CLI calls the mock locally to demonstrate
  restraint; no decision is persisted or exposed as an executable command.
- `simulate.py`: finite HTTP client with timeouts and a fresh sample session per run.
- `logging.py`: JSON application logs with timestamp, level and event correlation
  IDs; payloads, prompts, environment and credentials are not logged. Validation
  errors do not echo submitted values. Uvicorn access logging is disabled.

Solid arrows describe today’s local demonstration; dotted arrows are future
candidates, not implemented integrations. All observation retrieval goes through
the API; the simulation has no direct database connection.

## Experience direction and operating modes

OVERLORD manages intent, pacing, communication and bounded operational interventions.
Arma and existing tactical or campaign systems retain their simulation responsibilities.
Future game adapters must declare capabilities and ownership of units, objectives and
resources; proposals outside those capabilities or conflicting with another commander
must be rejected ([#2](https://github.com/instanceofjamie/overlord/issues/2)). Game-specific adapters stay separate from director
logic without building a generic engine framework.

| Mode | Behaviour | Status |
| --- | --- | --- |
| Observation-only | Record events without spawning units, changing waypoints or issuing gameplay commands | Local API recorder exists; live SQF collection does not |
| Recommendation-only | Record proposals, rationale, evidence references and expected effects without dispatch | Planned evaluation under [#15](https://github.com/instanceofjamie/overlord/issues/15) before live execution |
| Authorised execution | Explicit operator configuration, capability/ownership checks, authoritative validation and human override gate dispatch | Future work; command lifecycle under [#13](https://github.com/instanceofjamie/overlord/issues/13) is required |

The API records observations without invoking a model or changing gameplay. The
simulation client retrieves them and invokes the deterministic mock locally. Its
`no_action` output demonstrates the provider interface; it is neither a persisted
server decision nor an executable command. These modes are direction, not a new
configuration switch in this PR.

The immediate target is the vanilla Operation First Contact prototype on Altis.
Campaign memory (distinct from the per-session event log), personality and third-party
adapters remain future work under [#27](https://github.com/instanceofjamie/overlord/issues/27).

## Implemented initial observation contract v1.0

The working schema and version validation remain unchanged. Ecosystem research under
[#25](https://github.com/instanceofjamie/overlord/issues/25) and actual SQF observation requirements under [#6](https://github.com/instanceofjamie/overlord/issues/6)/[#8](https://github.com/instanceofjamie/overlord/issues/8)
should inform its evolution before broader integration interfaces are finalised.

Register a UUID session via `POST /v1/sessions` with `mission_name` and `map_name`
(strings of 1–128 characters). Repeating identical registration is safe; changed
metadata under the same ID returns 409. Each mission run uses a new session UUID.

Submit `POST /v1/observations`:

```json
{
  "protocol_version": "1.0",
  "session_id": "f32b654e-7c36-42f0-8a77-d2411d1f488c",
  "event_id": "025670d7-9d6e-4913-b0e7-81f144e67322",
  "event_type": "checkpoint_attacked",
  "timestamp": "2026-11-07T11:00:00Z",
  "payload": {
    "checkpoint_id": "checkpoint_alpha",
    "attacking_side": "BLUFOR"
  }
}
```

Every envelope field is required. Timestamps require a timezone; they describe
reported occurrence time, not trusted server time. `mission_started` instead
requires payload `{"player_count": 4}` (strict integer 0–256). Checkpoint IDs
are 1–64 word/dot/hyphen characters. Sides are BLUFOR, OPFOR, INDEPENDENT or UNKNOWN.
Extra properties, arbitrary SQF, unsupported versions/types and mismatched payloads
return 422. The OpenAPI schema at `/openapi.json` is the machine-readable contract.

An unknown session returns 404. Successful recording returns 201 with event ID and
`recorded`; an identical validated event ID replay returns 200 and `duplicate`.
Event IDs are globally unique: reuse with different contents or session returns
409. Retrying an uncertain delivery must reuse the original ID and contents.
Transactions make concurrent retries safe. Events are append-only through the API.

`GET /v1/sessions/{session_id}/observations?offset=0&limit=100` returns receipt
order, with limit 1–100 and nonnegative offset. Delayed or out-of-order events are
accepted as reported observations; timestamps do not trigger actions, reorder receipts or establish
faction knowledge. A checkpoint event need not wait for mission_started delivery.

## Persistence and migrations

The default file is `var/overlord.sqlite3`. Startup applies ordered SQL migrations
inside one transaction using SQLite `user_version`; repeated startup is safe.
A newer schema fails startup rather than attempting a downgrade. Add migrations
instead of changing applied statements. Back up the database while the service is
stopped before upgrading; restore that backup to roll back. No automatic destructive
migration, deletion, compaction or retention schedule is implemented. Session and
event JSON and receipt timestamps persist across restart. Operators currently own
backup/retention and log rotation. No player identities or game assets are collected.
This is intended for one local service process and modest event volumes.

## Planned game boundary and trust

Arma remains authoritative. Future server-side SQF observes significant events;
execution and multiplayer locality stay on the authoritative server/owning machine.
The Python director deploys independently; no separate process may be required on
the managed HostHavoc game server. Transport selection remains open under
[#26](https://github.com/instanceofjamie/overlord/issues/26): compare native `webRequest` with an asynchronous x64 extension
before implementation under [#11](https://github.com/instanceofjamie/overlord/issues/11). Native HTTP availability and required
configuration on the production server are unverified. DLL permission in principle
does not prove loading or outbound HTTPS connectivity.

Either path must use non-blocking outbound communication, with no incoming connection
to the game server assumed. Submit events and eventually retrieve proposals over
authenticated HTTPS. Do not wait for network or inference round trips inside SQF;
if a DLL is selected, enqueue bounded work and return promptly from `callExtension`,
with waits on workers. Gameplay continues during director downtime.
[#22](https://github.com/instanceofjamie/overlord/issues/22) must validate the actual server version, selected transport availability,
authenticated outbound HTTPS, prompt return to SQF, response retrieval, retry safety
and disconnect/reconnect behaviour. The checklist in [FinOps](finops.md) must precede
real deployment.

The future bridge needs bounded queues, timeouts, backoff, stable IDs, expiry and
diagnostics. Its commands must be allowlisted typed proposals with bounded
arguments, idempotency keys, expiry, authoritative SQF validation and execution
acknowledgements (#8/#13). It must never accept arbitrary SQF. Human Zeus inspection,
pause, cancellation and override are required before autonomous execution. The
receipt log is an initial audit trail; command lifecycle and decisions are future work.

The director's observation log is not faction intelligence. A future deliberation
layer must select bounded, authorised faction knowledge rather than hand this
entire log to enemy planning ([#16](https://github.com/instanceofjamie/overlord/issues/16)). In particular, `attacking_side` is
currently a reported observation, not automatically knowledge available to an enemy
faction. Evidence provenance and faction-authorised context must be addressed before
enemy planning. This PR adds no provenance fields or faction reasoning.

If host transport is blocked, a trusted human Zeus client relay is a contingency,
requiring explicit server-side role/owner checks, CfgRemoteExec allowlisting,
schemas, cooldowns and idempotency. RCon alone is not a general SQF RPC interface.
These are design requirements, not implemented or verified game integrations.

This iteration has no authentication and binds to loopback by default. Remote
operation requires a separate authenticated HTTPS transport design before exposure;
the current API is for trusted local development. Body-level network quotas,
transport authentication and replay policy beyond ID deduplication remain open.

## Cost boundary and next increments

Only the mock is configurable; there is no AWS SDK, infrastructure or paid call.
Before adding a paid provider (#14/#19), implement per-session/month budgets,
conservative in-flight reservations, token/invocation accounting, cooldowns,
rate/concurrency bounds and deterministic fallback. The proposed £5/month target
in FinOps is not enforced by this recorder. Independent hosting and inference are
separate costs; no cloud standing resources are required.

Next: produce a bounded deterministic structured SITREP from recorded observations
under [#6](https://github.com/instanceofjamie/overlord/issues/6), separating observed facts, inference and unknowns. SITREPs are
not implemented in this PR. Evaluate recommendation-only behaviour under [#15](https://github.com/instanceofjamie/overlord/issues/15)
before live execution; command lifecycle under [#9](https://github.com/instanceofjamie/overlord/issues/9)/[#13](https://github.com/instanceofjamie/overlord/issues/13) remains a
later requirement for dispatch. Complete ecosystem research under [#25](https://github.com/instanceofjamie/overlord/issues/25)
before finalising broader interfaces or expanding the planner, and transport
selection under [#26](https://github.com/instanceofjamie/overlord/issues/26) before bridge implementation. Host compatibility
([#22](https://github.com/instanceofjamie/overlord/issues/22)) and mission acceptance ([#3](https://github.com/instanceofjamie/overlord/issues/3)) remain verification gates.
No Arma integration, bridge, Bedrock, dialogue, campaign, Antistasi, SaaS or billing is included.
