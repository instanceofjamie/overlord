<!-- SPDX-License-Identifier: Apache-2.0 -->
# Local transport decision and evidence — 2026-11-08

Scope: the Windows local observation demo, not a production transport freeze.
Related issues: [#26](https://github.com/instanceofjamie/overlord/issues/26),
[#11](https://github.com/instanceofjamie/overlord/issues/11),
[#22](https://github.com/instanceofjamie/overlord/issues/22).

## Reserve-loop extension — 2026-11-09

The same DLL worker now also accepts `post [ticket, "command"|"ack", json]`.
Paths are fixed to `/v1/commands/poll` and `/v1/acknowledgements`. Command responses
are capped at 1024 bytes and terminal poll returns `[http_status, packet]`; all
other request types retain `[http_status]`. The response is data parsed with
`parseSimpleArray`, never executable SQF. Existing queue capacity, timeouts and
nonblocking entry points remain. The SQF loop polls every 2s when its outbox is
empty; events and retained acknowledgements take priority. Reset still clears only
completed DLL tickets, never the mission's commitment/processed-ID ledger.

See [current protocol and failure semantics](architecture.md) and the updated
[playtest](local-demo.md). The rest of this document records the **prior observation
milestone**, including its then-current limitations; command polling/ack support
supersedes those historical statements. Production selection is still open.

## Version and selection

The mounted Steam installation contains `arma3_x64.exe` and `arma3server_x64.exe`
reporting FileVersion **2.22**. The client PE fixed version tuple is
`(2, 22, 154, 89)`; Steam app 107410 manifest build ID is `25623484`, with no BetaKey.
The operator also confirmed version 2.22 and disabled other mods. These are installed
file/operator observations, not an in-game probe. The mission logs `productVersion`
in RPT and its initial status for runtime confirmation.

[Bohemia's webRequest reference](https://community.bistudio.com/wiki/webRequest)
currently marks the command as 2.24/development until release. Therefore this demo
uses an **asynchronous x64 DLL fallback**, not native HTTP on 2.22. We have not run
native HTTP in the game or claimed its availability. On an appropriate later build,
probe the command before changing transport; keep the current schema independent.

| Candidate | Local choice | Evidence and remaining questions |
| --- | --- | --- |
| Native `webRequest` | Not used for the installed 2.22 demo | Requires a supported build; fewer binaries, but actual availability/configuration must be probed |
| x64 extension worker | Implemented local fallback | Windows DLL ABI and HTTP path tested outside Arma; loader, game timing and detection still require playtest |

The [official WebAPI guide](https://community.bistudio.com/wiki/Arma_3:_WebAPI)
describes asynchronous handles/callbacks and mandatory preflight. A future native
adapter needs explicit origin/preflight support and response-status handling; this
PR adds neither WebAPI support nor permissive CORS to the Python service.

## Bridge contract (local only)

`overlord_bridge_x64.dll` exports `RVExtension`, `RVExtensionVersion` and
`RVExtensionArgs` according to the [extension ABI](https://community.bistudio.com/wiki/Extensions).
It accepts default SQF-escaped string arguments (unquotes/dedoubles them); the smoke
harness exercises this encoding. Arma calls `"overlord_bridge"`, without `_x64`.

- `uuid []`: creates an OS GUID without network I/O, independent of Eden random seeds.
- `post [ticket_uuid, "session"|"event", json]`: returns `queued`, `busy`, `full` or
  `invalid`; **queued is not delivered**. Payload bound: 2,048 bytes after decoding.
- `poll [ticket_uuid]`: returns `[-1]` while pending/lock busy, `[-2]` for an unknown
  ticket, `[0]` for transport failure, or `[http_status]`. A terminal poll consumes
  the result. HTTP 200/201 from the fixed API endpoints confirms persistence.
- `reset []`: discards completed results from previous missions. It does not cancel
  requests already in flight. Old-run requests may finish with their old session IDs.

Only `http://127.0.0.1:8000/v1/sessions` and `/v1/observations` are reachable. The DLL
has no configurable host, proxy, redirect following or gameplay function. It uses
WinHTTP on one background worker, with per-phase connect/resolve timeouts of 1s and
send/receive timeouts of 2s. These are per-phase bounds, not a promised total deadline.
No response body is downloaded. Network waits never occur inside `callExtension`.
SQF yields while polling; at 8s it reports pending delivery as unavailable without
submitting overlapping requests. Enqueue and poll use try-locks with immediate busy
results. A maximum of eight waiting/in-flight/unread results bounds DLL memory.
The mission has at most four retained requests and emits only two observations.

The worker is created on first use outside the loader entry point. The DLL pins
itself and retains one worker for the Arma process lifetime, avoiding unsafe thread
joins during DLL unload. Restart Arma to update the DLL. No second game-host process
is needed; the separately running director is independent.

SQF owns retry policy: 3s delay, stable session/event/ticket IDs and unchanged JSON,
registration before events, and recovery from a 404 after a database reset. HTTP
400/409/422 stops automatic delivery retries visibly; gameplay continues. Offline
buffers are in memory only and disappear on mission exit. No durable game-side
outbox, authentication, command polling, execution, or callback registration exists.

## Proportionate ecosystem review (#25)

References were read as architectural examples; no external implementation or game
asset was copied. Original bridge, SQF and Python changes use Apache-2.0. Repository
visibility is not a licence grant; copying code would require a separate review.

- [arma-gm](https://github.com/ViV99/arma-gm): its README separates SQF, an async Rust
  extension and a Python director, with shared JSON schemas, map graphs and operator
  controls. Adopt the separation and named locations conceptually. Implement this
  small observation path independently; omit its planners, map scanning and command
  executors. README claims are not tests of those components; deeper source fetching
  was unavailable during this review.
- [Clausewitz](https://github.com/underlines/reforger-clausewitz): Reforger, not Arma 3.
  Its documented sidecar, fake provider, SITREPs and fog-of-war direction support
  keeping inspection and inference separable. Do not transplant its game APIs or
  campaign machinery into this vanilla Arma 3 demo.
- [ALiVE OPCOM](https://www.alivemod.com/alive3/mil_opcom.htm) and its
  [scripting overview](https://www.alivemod.com/alive3/scripting_overview.htm): documented
  objective/profile ownership suggests future explicit adapter ownership. No ALiVE
  API is called or compatibility asserted here; the cited ALiVE 3 docs are in development.
- [AI Zeus mission-maker guide](https://clanofbrothers.com/AiZeus/mission-makers.php):
  documents controlled-side initialization and blacklist variables. Avoid co-owning
  its units; any adapter must opt in and declare boundaries. No integration tested.
- [HAL maintainer documentation](https://github.com/RockDood/NR6-HAL/wiki): warns about
  other systems changing group waypoints. Keep tactical command ownership out of
  this demo. No HAL interface or third-party scenario has been tested.

These findings support an initial observation adapter, not a final ecosystem API.
Full licence inventories, deeper interoperability research and interface decisions
remain open under #25/#2/#8 before broader planner/adapter expansion.

## Verification boundary and HostHavoc

Local Windows DLL smoke tests exercised the exported ABI, real API registration,
both event types, duplicate delivery and an offline endpoint. The cross-compiled
PE is x64; it imports Windows system DLLs only. Native queue tests and Python tests
are separate from the interactive game test. See [playtest](local-demo.md).

HostHavoc remains untested. Before selecting production transport under #26/#22:
record its server version, prove selected transport availability/loading, authenticated
outbound HTTPS, non-blocking response retrieval, disconnect recovery and deployment
policy. DLL permission in principle proves none of those. This local bridge deliberately
cannot target HostHavoc or a public endpoint; remote authentication/HTTPS needs a
separate design. No cloud resources or paid inference were used.
