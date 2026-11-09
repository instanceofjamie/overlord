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


### Operator-confirmed local observation path

On 2026-11-08 the operator confirmed the Eden warning disappeared after the metadata
correction, then reported two recorded events after the firing playtest: mission
start and checkpoint attack (`mission_started` / `checkpoint_attacked` in the schema).
This is operator-reported real-game evidence on the previously confirmed vanilla
Arma 3 2.22 installation, distinct from the synthetic harness checks above.
The exact session UUID, raw JSON and RPT were not supplied with this confirmation.
Editor versus hosted-MP execution was not specified. Game downtime/recovery,
repeat-hit suppression, fatal-first-hit coverage and dedicated multiplayer remain
unconfirmed by this report. The local observation goal is demonstrated; broader
issues remain open and deterministic SITREP work remains a subsequent increment.


### Operator-confirmed director downtime and recovery

On 2026-11-08 the operator confirmed the follow-up test worked as expected:
start the scenario with Overlord stopped, detect mission start and checkpoint harm
inside Arma while gameplay continues, observe director-unavailable status, then
start Overlord without restarting the scenario and inspect exactly two delivered
events. This is operator-reported evidence of in-game buffering, retry/recovery
and acknowledged storage without duplicate records in that test. It is separate
from automated transport tests. No raw session UUID/JSON or frame-time measurement
was supplied. Repeat-hit and fatal-first-hit cases, dedicated/hosted multiplayer,
HostHavoc and remote authentication/HTTPS remain outside the confirmed evidence.
The requested local observation-and-recovery demonstration is complete; no broad
roadmap issue is closed on that basis.

## Bounded local reserve response — 2026-11-09

Started feature branch `feat/bounded-reserve-response` from latest fetched main
`292d0f8`, after reviewing merged PRs #24/#28, issues #2/#5/#8/#9/#10/#13 and
transport issue #26/comment plus `docs/transport-local.md`. No AGENTS.md was found.
The existing operator-confirmed asynchronous local transport and mission are reused.

Performed for this increment:

- Python 3.12: **36 tests passed**, including event replay, recommendation-only,
  enable invalidating proposals, cooldown, unsuitable/stale/future/pre-enable events,
  concurrent approvals/retrieval, pause/disable/resume, expiry, issue uncertainty,
  persisted restart identity and commitment, duplicate/conflicting/unknown/wrong-key
  acknowledgements, ack-before-issue, and v1→v2 migration preserving observations.
  Threaded tests ran outside the restricted sandbox. The existing upstream
  Starlette/HTTPX deprecation warning remains.
- Ruff lint/format and strict mypy (12 modules) passed; `git diff --check` passed.
  The installed Pydantic/mypy combination required an explicit typing cast
  at the existing discriminated-union TypeAdapter construction; runtime schema and
  observation validation tests remain unchanged.
- Linux native queue regression passed (CMake/CTest), including nested command
  response preservation and terminal consumption. MinGW x64 DLL and smoke harness
  built successfully. Existing asynchronous worker and finite queue remain in use.
- Executed Windows `extension_smoke.exe`/DLL via WSL against an isolated real
  loopback API/temporary database: session 201, disabled poll with empty command,
  enabled fresh attack 201, bounded command retrieval, identical command on retry,
  two identical synthetic acknowledgements 200, then empty poll with executed state.
  Sample enqueue latency was 0ms. This verifies Windows ABI/HTTP response retrieval
  and persistence, **not** game execution: the harness submitted the success ack.
- SQF-VM v2026.04.03-ed9f5f5 syntax parsed all five SQF scripts plus mission.sqm
  and description.ext. Syntax-only; not an engine/locality/terrain test.
- The broader existing offline/stalled-response harness was attempted through a
  temporary WSL path-translation wrapper, stalled without output and was terminated.
  Do not count that attempt as a pass. Windows CI runs the extended native harness
  directly, including offline/duplicates/invalid-version/timeout and new command/ack
  cases, plus installer regression. This direct Windows CI passed on implementation
  commit `bbf9fb7`: [run 42618815957](https://github.com/instanceofjamie/overlord/actions/runs/42618815957).
  The initial Python CI found an unused local typing suppression with its dependency
  versions; replaced it with an explicit cast in `6a00f6d` (local checks pass).

The updated Windows/Eden instructions in `docs/local-demo.md` cover recommendation
inspection, fresh attack after explicit enable, movement/ack, replay waypoint count,
separate sessions, pause/local veto, director outage and human order override.
These new Arma behaviours **still need operator playtest**; no movement or exactly-once
execution claim is made. The prior observation/downtime playtest remains historical
evidence for that earlier path. Dedicated multiplayer, HostHavoc, saved-game rollback,
remote authentication and production transport remain unverified and out of scope.
No paid inference, spawning commands, third-party integrations or infrastructure added.

## Local playable Operation First Contact — 2026-11-09

Started `feat/playable-first-contact` from fetched main `dc1ba18`, after merged
PRs #24/#28/#29 and current issues #3/#4/#6/#10/#13/#16/#17 were read. No applicable
AGENTS.md was present. Main was fetched again after the interrupted session and
remained `dc1ba18`. User reports confirm the previous reserve actually arrived in
Eden; that is prior-loop live evidence, not proof of this new operation's pacing.

Investigated actual approval friction using the previous logs and support exchange:
the 12:51 and 12:54 sessions had `enabled=false`, recommendations and no execution
ack. Session restart changed the UUID, and one enable attempt used `/usr/bin/python3`
outside the project environment. No missing application role existed in that old
unauthenticated local API. The new launcher/private operator panel supplies a normal
workflow and authenticates control/approval mutations rather than broadly granting
execution permission. The supported mission now defaults to recommendation-only.

Local checks performed:

- Python 3.12 regression suite: **49 tests passed**, including prior transport/
  lifecycle checks and new quiet recon success, overt harm, duplicate/out-of-order
  progress, death/abort terminal state, fresh reviewed approval, stale enable/expiry,
  observation/disabled/paused modes, missing/wrong credentials, foreign-origin denial,
  normal-launch credential creation/preservation, distinct faction reports, terminal
  dispatch suppression and factual bounded AAR snapshots. Existing upstream
  Starlette/HTTPX deprecation warning remains. Threaded API checks run outside the
  restricted sandbox; an in-sandbox attempt could not complete threaded TestClient.
- Ruff lint/format and strict mypy (13 modules); `git diff --check` passed.
- SQF-VM v2026.04.03-ed9f5f5 parsed seven SQF files, mission.sqm and description.ext.
  Final engine-API review changed the progression identity check to documented
  corpse-aware `isPlayer [unit]` (available since 2.06) for death reporting.
  Executed the mission's actual pure `flow.sqf` function with seven assertions for
  recon-only completion, duplicates, invalid extraction, attack restraint and failure
  terminal states. This does not emulate Arma's action UI, tasks, locality or terrain.
- Linux native queue CMake/CTest passed; MinGW x64 DLL and harness built. The worker
  is retained; only its bounded command response size increases to 2048 bytes.
- Headless Chromium/Playwright 1.60.0 against an isolated temporary director: plain
  visitor read-only, launch authentication, review mode, fresh approval, stable retry
  identity, synthetic acknowledgement, readable success/debrief, pause and unavailable
  status passed without page script errors. Screenshot reviewed. Its service used
  its own temporary database on port 8051 and exited normally; it did not stop WSL,
  an existing director or Arma. The synthetic ack is not game execution evidence.
- Built the Python wheel and confirmed `overlord/operator.html` is packaged.
- Direct Windows CI is configured to build/execute the DLL/API harness and installer,
  with the launch credential supplied only to operator control calls. Python CI also
  executes the pinned SQF checks and browser regression. PR CI results are separate
  from the local checks above and must be checked before using its artifact.

The working tree survived the reported WSL/PC restarts. No WSL shutdown, distribution
termination or existing game/director process termination was performed to resume it.
The new normal guide is `docs/local-demo.md`: project-aware launcher, permission
check, quiet and overt playthroughs, manual approval, pause/takeover and labelled local
fallback. The debug console is disabled for normal play. Game buffers are memory-only;
closing the scenario before delivery loses those unpersisted events, which the AAR
must not invent. Director restart with the same DB preserves mode and commitments.

Still requires operator Eden playtest: route/cover/visibility and the 10–15 minute
pacing target, covert viability, explicit action distances, task/radio presentation,
complete extraction/debrief, actual guard-report/reserve behaviour, human control and
outage fallback in the new mission. Single-player local preview only: four slots,
dedicated multiplayer, HostHavoc, realistic radio/delay/false intelligence and remote
transport authentication remain open. No LLM, paid inference, spawning command, new
gameplay action family, campaign, third-party integration, cloud deployment or billing.

### Operator-confirmed quiet and automatic-combat completions

The following live evidence was inspected on 2026-11-09, after installing the
Windows artifact for source commit `a30e141`. Selected game events, control metadata,
response/ack and correlated OVERLORD RPT lines are preserved in
[evidence/2026-11-09-first-contact.json](evidence/2026-11-09-first-contact.json).
Only the two relevant sessions are copied, not the full database or full RPT files;
there are no launch credentials or player identifiers in the snapshot.

| Approach | Session UUID | Recorded sequence (game UTC) | Result |
| --- | --- | --- | --- |
| Quiet recon | `4ce142e7-fb51-4461-8e5a-196a31823a66` | Start 16:50:46; begin 16:51:13; recon report 16:55:52; extraction 16:59:19 | Succeeded; no checkpoint attack or reserve decision |
| Automatic combat | `af1e472c-5a4f-4fa4-83c0-d32c18ae25be` | Start 17:34:43; begin 17:34:45; recon report 17:37:26; attack 17:39:10; extraction 17:42:46 | Succeeded; one reserve command and actual Arma acknowledgement |

The quiet-run operator feedback was “Recon only seems fine.” No response was
proposed or dispatched in that run. Its **final** stored mode is execution enabled,
but the control change was at 17:00:06 director UTC, **after** successful extraction.
Do not misrepresent it as an execution-enabled quiet approach throughout.

For the completed combat run, automatic execution was enabled at 17:35:17 director
UTC, before the attack. The event reported BLUFOR harm, a guard radio channel and an
available reserve. Command `c56a3955-0147-5734-aa04-1a124e159edf` was automatically
approved (`approval_kind=enabled_rule`), issued and acknowledged with
`executed / movement_order_assigned`. The game RPT confirms application and ack
delivery at 17:39:11; SQLite retains the same command/key and actual result.
The terminal outcome replays as `succeeded`, with all three progression milestones
accepted and no invalid progression events. No second reserve command is recorded.

Game timestamp and director receipt time differ slightly because they are separate
clocks; these records are not a precise latency benchmark. Order assignment is
confirmed; physical arrival remains untracked. The operator reported arrival for
the earlier response-loop milestone, but these new logs alone do not establish it.
A single applied command does not prove forced duplicate-delivery or exactly-once
semantics. The automatic branch has live evidence; manual review remains browser/
automated-tested rather than newly confirmed inside this mission.

Observed play durations were **8m33s quiet** and **8m03s combat**, measured from the
recorded mission-start event to extraction. Both approaches reach the recorded success condition,
but the intended 10–15 minute pacing is **not yet demonstrated**. Do not add forced
combat or a timer merely to stretch duration; route/briefing/observation pacing can
be refined from this feedback.

A separate unsuccessful combat session (`22dd886d-c0a5-4fa3-a6ac-b6a948be1de1`)
started with execution disabled while the earlier completed session was enabled.
Its eligible attacks produced proposals, and the operator later selected local
human takeover, which set the veto. Death then recorded terminal failure and expired
undispatched recommendations. The next successful response session confirmed the
correct fresh-session automatic setting. This is evidence that session selection
and takeover labels remain a usability concern, even though the gates behaved as
configured. Takeover is an opt-out, not permission for automatic execution.

Remaining live verification: explicit repeated-delivery waypoint-count test, new
mission outage/local-debrief recovery, actual human order replacement without
reapplication, detailed task/radio/AAR readability feedback and longer pacing.
Four slots, dedicated multiplayer and HostHavoc remain subsequent milestones. These
successful local completions do not close the broad roadmap acceptance criteria.
