<!-- SPDX-License-Identifier: Apache-2.0 -->
# Local dedicated Operation First Contact

Target: installed Windows **Arma 3 x64/server 2.22.154089**, vanilla Altis. Preserve
the same operation and deterministic reserve response. This branch repairs dedicated
authority/state paths; it does **not yet claim two-player acceptance**. The real
headless server/executor probe passed with synthetic attack telemetry and no clients.
Two human-controlled clients must complete the matrix below.

## Processes and prerequisites

| Process | Responsibility | Installation/connectivity |
| --- | --- | --- |
| `arma3server_x64.exe` | One authoritative mission/session, guards, reserve, progress, snapshot, outbox, command validator | Existing game install; server alone loads `@OVERLORD` DLL; outbound loopback HTTP to port 8000 |
| Player clients | Input, action-menu requests, local task/diary rendering from server state | Four named playable slots; two required for acceptance; clients need no bridge/mod |
| Python director | Persist events, rules, authenticated operator panel, command lifecycle | Start independently on the server PC; keep `127.0.0.1:8000`; existing WSL loopback path is supported |

The inspected installation already contains both client and `arma3server_x64.exe`
plus the Altis assets. **No server package, DLC or Arma Tools download was needed.**
A second human-controlled client was not available to this automated probe. Do not
use headless clients as evidence of two players; they cannot impersonate scout slots.

First complete the existing [Python setup](local-demo.md). Use this branch's mission
and the tested x64 bridge (existing 2048-byte-response bridge is unchanged). Keep all
other mods/BattlEye off for this unsigned local DLL test. Public hosting is outside
scope: no router changes, UPnP, public HTTP or firewall changes are performed.

## Start services and load the mission

1. Start the director from the repository, either Windows `tools\start-overlord.cmd`
   or WSL `./tools/start-overlord.sh`. Open its private operator link. Do not run a
   second director on port 8000. Keep the SQLite file across interruptions.
2. From a PowerShell in the repository or matching extracted artifact:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start-dedicated.ps1 `
     -ArmaPath 'D:\Games\Steam\steamapps\common\Arma 3'
   ```

   The launcher reuses the installed DLL (or accepts `-DllPath`), installs only the
   scoped `MPMissions\OverlordLocal\OperationFirstContact.Altis` folder, backs up an
   older copy and loads it via `-mpmissions=MPMissions\OverlordLocal`. No PBO tooling
   is needed: the unpacked mission loaded successfully in the actual server probe.
   It refuses an existing server, occupied ports, a differing installed DLL, and
   public/wildcard bindings rather than stopping processes or overwriting mods.
3. Keep the PowerShell output private. It prints **separate random join and game
   admin passwords**, the server address and owned PID. Generated config/profiles/PID
   are under `%LOCALAPPDATA%\OVERLORD\dedicated`, outside the repository. The committed
   `configs/local-dedicated.cfg.example` has placeholders, not credentials.
   Do not point profiles/runtime at WSL UNC paths: actual Arma cache/config startup
   failed there; a native Windows path fixed startup. `-RuntimePath` can choose a
   different native Windows directory. `-PrepareOnly` copies/configures without launch.
4. The server starts the mission automatically without clients (`persistent=1`,
   `-autoInit`). Expect one `OVERLORD SESSION`, `dedicated=true; reserve local=true;
   reserve owner=2; slots=4`, and confirmed registration/mission-start delivery.
   Zero connected players is correctly recorded as zero, not an invented player.
5. Client: Multiplayer → Server Browser → Direct Connect → `127.0.0.1`, port `2302`,
   use the **join** password, select a NATO scout slot and continue. A second player
   selects a different slot. No `-mod=@OVERLORD` is required on clients.

Default binding/`loopback=1` is **same-machine testing only**. For a second physical
PC on your private LAN, start instead with `-BindAddress 'YOUR-SERVER-LAN-IP'`; only
private IPv4 addresses are accepted and loopback-only mode is disabled in that case.
The friend connects to that LAN address, not their own `127.0.0.1`. Do not expose the
Python director: its loopback endpoint remains on the server PC. No router mapping
is needed. If a demonstrated LAN connection failure is due to Windows Firewall,
allow only this executable/UDP server ports on the private profile for the friend's
address; obtain/confirm that local rule before changing it. The launcher makes none.

The documented Arma [startup parameters](https://community.bistudio.com/wiki/Arma_3:_Startup_Parameters)
and [server config](https://community.bistudio.com/wiki/Arma_3:_Server_Config_File)
explain `-ip`, `-mpmissions`, `persistent`, `loopback` and private `#login` administration.

## Shared progress and reconnect policy

- Server initialisation is guarded once per mission. Only server code creates the
  session/events and applies reserve orders; there is no per-client observer/bridge.
- Any living scout may begin or report reconnaissance at the original distances.
  One accepted report advances the **shared** operation. Overlapping requests become
  no-ops once that phase has advanced; they do not recreate tasks/events.
- **All living, currently connected scouts** must be within 30m of extraction when
  one requests extraction or team abort. A disconnected scout does not block the
  remaining team. One casualty does not fail a surviving team; the last connected
  scout being killed produces failure. Casualties are server-observed local AAR facts.
  Single-player still fails on its player's death. No resurrection/respawn is added.
- Four playable slots are retained with `disabledAI=0` because disabling AI while
  respawn is off prevents JIP into vacant slots. The server parks vacant/disconnected
  slots (hidden, simulation disabled, no AI patrol participation) and restores them
  on occupancy. A reconnect uses a surviving slot, never revives a dead slot or
  resets the operation. Dead/parked units do not count as living connected extractees.
- A JIP-compatible server snapshot supplies session, stage, completed milestones,
  facts, last director report/contact and real executor results. Clients create their
  three tasks once and reconstruct **all** task states from that snapshot, even when
  joining at extraction or after completion. They receive one current-stage summary
  rather than replaying historical radio lines. Reconnecting does not initialise the
  server again. Verify actual network delivery with two clients; pure rendering
  regressions are not that proof.
- Debrief/essential progression depend on the **game server**, not on the director.
  The same server-observed facts/results reach all clients. Server-synchronised time
  labels stale director snapshots as LOCAL FALLBACK. Nothing claims that undelivered
  events/acks are persisted or that a movement-order acknowledgement means arrival.

## Operator roles and human override

Director approval is through the **existing private web panel**, not an in-game
approval shortcut. Confirm the dedicated session UUID and mode; new sessions default
to recommendation-only. For automatic play choose automatic execution and Apply;
for review choose reviewed execution **before a fresh attack**, then approve its
fresh proposal. Missing/wrong credentials remain read-only/403, missing service
credentials explain configuration/503. Pause stops new dispatch, not an existing
movement order. Mode changes expire undispatched recommendations, never release
stale ones. Normal players do not receive the operator credential.

Game administration is separate. In chat, the operator may use the launcher's
private `#login ADMIN-PASSWORD`. Only a **logged-in** admin (not merely a voted admin)
may use the in-game takeover actions on a dedicated server:

- **Pause / take human control of reserve:** sets the local veto/releases ownership;
  existing movement continues.
- **Human override: hold reserve:** explicitly replaces existing waypoints with one
  HOLD at the reserve's current location, while keeping the veto. This is a bounded
  human replacement order, not a new director command family or fabricated ack.
  Subsequent retries return cached director results without restoring the old move.

The server validates owner, known scout object, session and admin role. Client-side
button visibility is not authority. Generic `call`, `execVM`, `spawn`, remote commands
and JIP RPC replay are not permitted. The two mission RPC names only target server 2;
[CfgRemoteExec](https://community.bistudio.com/wiki/CfgRemoteExec) and
[remoteExecutedOwner](https://community.bistudio.com/wiki/remoteExecutedOwner) are
used without changing HTTP operator permissions. Headless ownership migration is
unsupported: nonlocal reserve groups are still rejected, never commandeered.

Use admin `#restart` for an in-process mission restart, and `#shutdown`/the owned
server console to end this dedicated process. Never stop WSL to restart the mission.
A fresh mission has a new UUID/default mode; same-session director restart preserves
its mode, reserve commitment and unresolved IDs. Backups/profiles survive outside
mission state. Do not delete the SQLite database to reset a budget.

## Concise two-player matrix

Use fresh sessions for separate one-reserve tests. Capture session UUID, both clients'
task states/AAR, server RPT, panel decisions/acks, and duplicate waypoint diagnostics.
No second player has yet completed these rows on this branch.

| Case / steps | Expected | Actual evidence/status |
| --- | --- | --- |
| Two scouts quietly begin → recon report → both extract | Same tasks and success; no response | Prior Eden flow passed; MP policies/rendering automated; **two clients pending** |
| Enable auto, attack with two scouts | One eligible reserve commitment/order; same progression | Real dedicated executor passed with synthetic attack; **actual shots/two clients pending** |
| Recommendation-only, attack | Proposal only; reserve stays put | Existing rules/browser tests pass; **two-client run pending** |
| Reviewed execution, authorised approve; plain browser tries mutation | Fresh approval works; unauthorised request denied | Browser/API tests + real probe 403 pass; **live operator review pending** |
| Both click report / fire overlapping hits | One phase event; 3s shared harm throttle; at most one dispatch | Actual pure SQF policies + SQLite concurrency pass; **network overlap pending** |
| Join after recon report | Reconstructed briefing/recon success, extraction current; no old radio replay | Actual task-state function tested; **JIP network/UI pending** |
| Scout disconnects, rejoins surviving slot | Same UUID/phase; no reset; other player can continue | Code/policy review; **live reconnect/park/unpark pending** |
| Director down before mission/event, then start | No game wait; retained IDs deliver once | **Real headless startup/recovery passed**; client progression fallback pending |
| Stop director after issue; withhold ack; restart same DB | Issued/uncertain remains committed; same ack/ID resolves; no new order | **Real engine + deliberately failed ack/restart passed**; human gameplay continuity pending |
| Replay the applied command | Cached result, same waypoint count, no extra assignment | **Real dedicated forced duplicate passed**: one ORDER APPLIED, cached result, waypoint count 2 both times |
| Admin takeover/HOLD, then retry | New dispatch vetoed; human order remains; no reapply | Pure admin policy passes; **actual client-admin HOLD pending** |
| #restart same server process | New UUID/default mode; old packet ignored | Fresh-process restart + actual old-packet rejection passed; **in-process #restart pending** |
| Both view outcome/debrief after extraction or last-scout death | Shared success/failure and evidence; no arrival claim | Server snapshot/rendering policies tested; **two-client visual confirmation pending** |

Short human handoff: join two slots; complete a quiet run together, with one late
join/reconnect after recon. Restart; select the new session and enable automatic
execution, attack, interrupt/restart **only the director terminal**, then both extract
and compare AARs. In a separate session, log in as game admin, issue the reserve,
apply Human override: hold reserve, and verify retries do not undo it. Also run the
reviewed/recommendation modes and `#restart` row. Report failures with UUID/RPT and
both clients' task states, rather than changing permissions or resetting variables.

## Reproduce available automation (optional developer checks)

`python tools/test_mission_flow.py PATH_TO_SQFVM` executes the actual transition,
request-owner/session/admin, team-extraction and JIP task-state predicates (31
assertions). `python tools/check_sqf.py PATH_TO_SQFVM` is syntax-only.

The opt-in real-engine probe (Windows Python or this WSL checkout) is:

```powershell
python tools/test_live_dedicated.py --arma-path 'D:\Games\Steam\steamapps\common\Arma 3'
```

It requires port 8000 free, starts **its own** temporary director DB and dedicated
processes, injects explicitly synthetic attack telemetry, deliberately fails ack
delivery, restarts that owned director/server, forces duplicate/old-session packets,
and records `%LOCALAPPDATA%\OVERLORD\dedicated\probe-evidence.json`. It shuts down only
the server PIDs it created and its own test service; it never stops WSL, a player
client or an existing director/server. Its private launch transcript/config stay in
AppData and must not be committed. This is live headless-engine evidence, not two
players, a real projectile, mission progression under load or human UI evidence.
