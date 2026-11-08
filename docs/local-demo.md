<!-- SPDX-License-Identifier: Apache-2.0 -->
# Operation First Contact — Windows local observation demo

Target: **Arma 3 x64 2.22**, vanilla Altis. One playable NATO rifleman and two OPFOR
guards behind sandbags, 100m north of the start. The checkpoint and start are near
the Altis airfield. This demo only observes: no director orders, planning or model
calls. Scenario setup creates the guards and barriers locally on the server; these
are mission content, not remotely requested actions.

**Verification status:** automated Python and Windows DLL/API checks passed. On
2026-11-08 the operator confirmed that Eden opens without warning after the metadata
fix and that the firing playtest produced two recorded events: mission start and
checkpoint attack. This is operator-reported real-game evidence, not just the
transport harness. Interactive downtime/recovery and repeat-hit/fatal-hit cases
still need confirmation. The inspector prints recorded facts; SITREP formatting
remains a subsequent increment. See [dated evidence](verification.md).

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

## 3. Trigger and inspect (short playtest)

1. Start/restart the scenario, not a saved game. The server creates a new random
   UUID session for every run and logs it plus `productVersion`. Expect in-game
   **DETECTED mission_started**, then separate **DELIVERY CONFIRMED session** and
   **DELIVERY CONFIRMED mission_started** statuses. Initial delivery can take a few
   seconds. The same messages go to RPT prefixed `OVERLORD`.
2. Open the map (`M`): locate `checkpoint_alpha` north of `friendly_base`;
   `enemy_reserve` is a named, unused location. Step out from the starting H-barrier cover and shoot an OPFOR guard. Expect
   **DETECTED checkpoint_attacked** followed separately by **DELIVERY CONFIRMED
   checkpoint_attacked**. Further hits, including the second guard, produce no
   additional attack observations in this run.
3. In a second PowerShell at the repo root:

   ```powershell
   .\.venv\Scripts\overlord-inspect.exe --latest
   # Prefer the explicit session if other simulations have run:
   .\.venv\Scripts\overlord-inspect.exe --session 'UUID_FROM_GAME'
   ```

   Expect exactly two observations with `mission_started` and `checkpoint_attacked`,
   `checkpoint_id=checkpoint_alpha`, unique event UUIDs and UTC timestamps. Check
   that repeated hits leave the count at two. `--latest` means most recently
   registered, not necessarily the game if another simulator registered later.
   The same records are available at `/v1/sessions/UUID/observations` in API docs
   (<http://127.0.0.1:8000/docs>); `GET /v1/sessions` lists recent registrations.
4. Stop and restart the director with the same database path; inspect the same
   session UUID again. Records must persist.

## 4. Downtime and retry test

Start a **new scenario run** with the DLL installed but director stopped. Expect
**DETECTED mission_started** and **DIRECTOR UNAVAILABLE / delivery unconfirmed**.
Shoot a guard: detection must still appear and normal gameplay must continue.
Start the director while staying in the mission; within the next retry window it
should confirm the session and both observations. Inspect the session and confirm
only two events. Network failures retry after 3s, reusing the original event IDs and
JSON. There is no automatic inference or gameplay effect on reconnect.

Alternatively stop the director after mission-start delivery, shoot, then restart.
Do not exit/restart the scenario before retrying: the game-side buffer is memory-only.
A DLL install/update needs a full Arma restart. Missing DLL detection does not hot-retry
loading; install it, restart Arma and start a new scenario.

## Detection definition and limits

`checkpoint_attacked` means **the first positive Hit or a Killed event on either
registered checkpoint guard during this mission run**. It does not mean a shot
passed nearby or hit the sandbags. Local server-owned entity handlers share an
immediate one-shot latch; fatal-hit coverage and repeated/explosive handlers cannot
create an unlimited stream. This deliberately also covers noncombat injury/death;
it reports a guard being harmed, not proven hostile intent. Shoot the guard in the
playtest, rather than relying on suppression. Attribution uses only an available
`CAManBase` instigator's current group side; absent/unsupported evidence is UNKNOWN,
never a guess based on the nearest player or source vehicle.

The label and `attacking_side` remain **reported game observations**, not automatically
knowledge available to OPFOR. Confidence, provenance, intent and faction-authorised
context remain future work under #16. The v1.0 schema is unchanged; all payloads
remain bounded. UTC uses the game host's system clock, not the simulated 2035 date.

Server-only initialization, server-local guards and `isServer`/`local` checks keep
observation authority on the host. This is a path toward multiplayer, not tested
support for ownership migration, untrusted clients, persistence through save/load,
respawn or arbitrary mission editing. With one player slot and no HC it stays simple.

## If the test fails

- **No detection:** ensure the right scenario is loaded and shoot a guard, not terrain
  or cover. Inspect RPT for SQF errors. Press Esc for the debug console; use Local Exec
  on `copyToClipboard str productVersion` to capture the exact runtime version.
- **Detected but unavailable:** verify `/health`, port 8000, x64, BattlEye disabled,
  DLL at `@OVERLORD\overlord_bridge_x64.dll`, launcher parameter, and full game restart.
  Missing DLL/blocked loading produces a visible unavailable message.
- **HTTP 400/409/422:** delivery is rejected and retries stop visibly. Preserve the
  event/session IDs and RPT/director logs for a bug report; do not claim delivery.
- **Pending over 8s:** the mission warns without blocking gameplay or piling up requests.
  Check director health. The native worker's phase timeouts will eventually return a
  status; queueing alone never displays delivery success.

Report: exact runtime version, editor or hosted MP, session UUID, detection/delivery
messages, inspector output and any `OVERLORD`/SQF RPT errors. No broad issue should be
closed until the corresponding game/host acceptance tests genuinely pass.
