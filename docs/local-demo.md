<!-- SPDX-License-Identifier: Apache-2.0 -->
# Operation First Contact — Windows local reserve response demo

Target: **Arma 3 x64 2.22**, vanilla Altis, local Eden preview. The existing
checkpoint/observer/async DLL path is retained. One editor-placed OPFOR group
(`reserve_alpha`, leader `overlord_reserve_leader`) starts near `enemy_reserve`.
Only `response_alpha` at the checkpoint is a permitted destination. The reserve's
PATH AI starts disabled so recommendation-only tests leave it in place; execution
enables PATH once and assigns one MOVE waypoint. No units are spawned by commands.

The operator confirmed the previous observation/downtime demo on 2026-11-08.
**This new movement/executor behaviour still requires the playtest below.**
Automated checks cannot establish Arma movement, terrain or locality behaviour.
The existing inspector still prints stored observations; no SITREP formatter exists
on latest main, and none is introduced here.

## 1. Obtain/build and install

Use the new PR branch (or main once merged). Keep Arma closed during installation.
Choose either:

- **Prebuilt:** on the PR's Checks tab open the successful **Windows observation
  demo** run; download and extract `overlord-windows-observation-demo`. It contains
  the DLL in `@OVERLORD`, mission, installer, licence and SHA256 record. No PBO,
  Workshop download or third-party mod is required.
- **Build:** install Visual Studio 2022 Build Tools with **Desktop development with
  C++**, Windows SDK, and CMake. From the repository root in an x64 developer
  PowerShell:

  ```powershell
  cmake -S bridge -B build/windows -A x64
  cmake --build build/windows --config Release
  ctest --test-dir build/windows -C Release --output-on-failure
  ```

From the extracted artifact root or repository root, in PowerShell:

```powershell
# Adjust ArmaPath to your Steam installation.
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-demo.ps1 `
  -ArmaPath 'D:\Games\Steam\steamapps\common\Arma 3'
```

The installer copies the mission to the current Windows Documents folder's
`Arma 3\missions\OperationFirstContact.Altis` and the DLL to the game's
`@OVERLORD\overlord_bridge_x64.dll`. It refuses to overwrite existing destinations.
If using a custom Arma profile, specify its actual missions directory with
`-MissionsPath '...\Arma 3 - Other Profiles\YOUR_PROFILE\missions'`.
For a cross-compiled DLL in another location pass `-DllPath '...\overlord_bridge_x64.dll'`.
Manual installation uses exactly the same two locations. No administrator rights
should be necessary for a user-owned Steam library. Uninstall by removing only
those two copied directories while Arma is closed.

In the Arma Launcher:

1. Disable all other mods and **BattlEye** for this local test. This unsigned custom
   DLL is not BattlEye-whitelisted; do not use this configuration on public servers.
2. Select x64 and add `-mod=@OVERLORD` in Parameters → All Parameters → Advanced →
   Command line parameters (or launch `arma3_x64.exe -mod=@OVERLORD`). The folder is
   a DLL search path; it has no addon PBO. Do not copy the DLL inside the mission.
3. Launch Arma, open **Editor → Altis**, then **Scenario → Open → OperationFirstContact**.
   The scenario briefing name is Operation First Contact. Choose **Play Scenario**.
   For hosted multiplayer use Eden's **Play → Play in Multiplayer → Host** and take
   the NATO observer slot. Only the host needs the DLL. Dedicated/headless play is
   not validated in this PR; never transfer checkpoint ownership to a headless client.

The mission runs with a missing/blocked DLL too, but delivery will be unavailable.

## 2. Start the independent director

From a Windows clone of the same branch, use Python 3.12+ in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
Copy-Item .env.example .env  # first setup only; preserve an existing .env
.\.venv\Scripts\overlord.exe
```

Keep `OVERLORD_HOST=127.0.0.1`, `OVERLORD_PORT=8000`, and `OVERLORD_PROVIDER=mock`.
The demo DLL deliberately fixes this endpoint. No firewall inbound rule, port
forwarding, CORS change, AWS account or public binding is needed. Run both processes
on the Windows PC for the normal demo; a director on another PC is unsupported.
Do not bind this unauthenticated API publicly. Check
<http://127.0.0.1:8000/health> returns `{"status":"ok"}`.

## 3. Recommendation-only → explicit enable → fresh attack

Use the updated DLL **and** mission from this branch. With Arma closed, back up
and move the old installed `@OVERLORD` and mission directories before reinstalling;
the installer deliberately refuses overwrites. Restart Arma after updating the DLL.
Never resume a saved scenario: Play/Restart creates a new session with execution off.

1. Start Overlord using section 2, then load the mission in Eden and Play. Note the
   session UUID from OVERLORD statuses/RPT. Map: NATO start, checkpoint, reserve,
   response marker. Expect `DETECTED mission_started`, confirmed delivery and
   `execution enabled=false`. Do not shoot the reserve.
2. Shoot **one** checkpoint guard (leave the other alive). Expect checkpoint attack
   detection and delivery, then `RESPONSE proposed`. If the instigator was UNKNOWN,
   the deliberate outcome is `no_action`: inspect the event and try a fresh attack
   rather than treating unknown attribution as hostile knowledge. Inspect from a
   second PowerShell in the repository, using the exact UUID:

   ```powershell
   $session = 'COPY-SESSION-UUID-HERE'
   .\.venv\Scripts\python.exe -m overlord.inspect --session $session
   .\.venv\Scripts\python.exe -m overlord.control --session $session status
   ```

   The response view shows command proposal, event UUID, explanation, expiry and
   `committed=false`; execution remains disabled and the reserve stays put.
3. Explicitly enable **future** dispatches:

   ```powershell
   .\.venv\Scripts\python.exe -m overlord.control --session $session enable
   ```

   Old proposals become `expired` with a mode-change explanation. Enabling does
   not release them. Wait **at least 16 seconds** after the previous recommendation
   (default cooldown 15s), then shoot the remaining checkpoint guard. This must be
   a fresh, BLUFOR-attributed attack after enable. Hits are throttled to one report
   per 3s, while director cooldown and commitment are separate protections.
4. Observe `execution enabled=true`, `issued`, then `RESERVE executed:
   movement_order_assigned` and acknowledgement delivery. Inspect `status` again:
   the exact command and actual Arma acknowledgement are durable. Watch the reserve
   walk towards `response_alpha` (200m or so from its start). `executed` means the
   movement order was assigned, **not** physical arrival or tactical success.
5. Verify duplicate delivery. In Eden's Escape → Debug Console, execute **SERVER**
   (LOCAL in singleplayer) and note the waypoint count:

   ```sqf
   hint str count waypoints OL_reserveGroup;
   isNil {[OL_lastCommandPacket] call OL_fnc_receiveCommand};
   isNil {[OL_lastCommandPacket] call OL_fnc_receiveCommand};
   hint str count waypoints OL_reserveGroup;
   ```

   Count stays unchanged; the original acknowledgement is resent, no second order
   is assigned. `OL_lastCommandPacket` exists only after a command was received.
   Repeated attacks also produce `no_action` once committed. To report a debug
   attack after both guards died (this is synthetic, not projectile evidence):

   ```sqf
   ["checkpoint_attacked", "{""checkpoint_id"":""checkpoint_alpha"",""attacking_side"":""BLUFOR""}"] call OL_fnc_observe;
   ```

## 4. Pause, downtime, expiry and human override

Pause from PowerShell:

```powershell
.\.venv\Scripts\python.exe -m overlord.control --session $session pause
.\.venv\Scripts\python.exe -m overlord.control --session $session status
# When ready for future fresh attacks:
.\.venv\Scripts\python.exe -m overlord.control --session $session resume
# Return to recommendation-only:
.\.venv\Scripts\python.exe -m overlord.control --session $session disable
```

Pause prevents new retrieval/dispatch. It does not cancel a response already handed
to transport or an existing movement order. For an immediate game-side veto before
an in-flight command applies, run `OL_localPaused = true;` on SERVER in the debug
console. Restore with `OL_localPaused = false;`. A rejected issued command still
consumes the session's commitment. Resume/enable always requires fresh evidence;
mode transitions invalidate every undispatched proposal/approval. Idempotent repeat
control calls do not change its boundary. The director retains control mode in SQLite
across a service restart; a new mission session always defaults off.

Run separate **Restart** sessions for these tests (one commitment per session):

- **Offline observation:** stop Overlord with Ctrl-C before Play. Attack while it is
  down; gameplay and detection continue. Restart Overlord and verify retained IDs
  deliver once. Reports over 120s old deliberately produce `no_action`. No new order
  can be obtained while offline. The game outbox is memory-only until mission exit.
- **Offline after order:** after an executed command, stop/restart Overlord with the
  same database. Confirm the stored acknowledgement remains and no additional
  waypoint appears. If an ack is lost while the director is down, the game retains
  and retries it. If delivery stays unresolved beyond expiry, director status is
  `uncertain`, with commitment retained; a late actual ack can resolve it.
- **Paused:** fresh session, pause before attacking; expect `no_action` and no move.
  Resume, wait out cooldown if relevant, then attack afresh. For immediate local
  rejection, set `OL_localPaused=true` before an enabled fresh attack; expect
  `rejected/paused`, no waypoint, commitment consumed. Restart for another dispatch.
- **Human override:** after successful movement assignment, pause and run on SERVER:

  ```sqf
  OL_localPaused = true;
  OL_reserveGroup setVariable ["OL_owned", false];
  private _oldWaypoints = waypoints OL_reserveGroup;
  reverse _oldWaypoints;
  {deleteWaypoint _x} forEach _oldWaypoints;
  private _wp = OL_reserveGroup addWaypoint [[14650,16250,0],0];
  _wp setWaypointType "MOVE";
  OL_reserveGroup setCurrentWaypoint _wp;
  ```

  This explicit human order should take over. Replay `OL_lastCommandPacket` and
  inspect waypoints: the integration must not restore its old waypoint. Zeus can
  similarly take control; the demo adds no Zeus module. Before dispatch, revoke
  `OL_owned` to refuse integration orders. Do not transfer the reserve to a headless
  client: nonlocal groups are rejected rather than remotely commandeered.

Commands expire on a UTC minute boundary **60–120s** after creation. Keep Windows
clock correct; accelerated mission time is irrelevant. A pending command expires
without dispatch; an issued command with no ack becomes uncertain. An empty/new
SQLite database is **not** continuity evidence: the game latch still rejects a
second commitment, but the audit history is gone. Preserve the database; do not
reset it to bypass commitment. Save/load continuity is unsupported: restart the
scenario for a new session, never reset executor variables in an active mission.

Capture `productVersion`, session UUID, checkpoint events, response JSON, RPT statuses,
waypoint counts before/after retries, and observed movement/override. Automated
Python/native/ABI tests are distinct from this live evidence. Dedicated multiplayer,
HostHavoc and remote authentication remain subsequent work.
