<!-- SPDX-License-Identifier: Apache-2.0 -->
# Operation First Contact — local playable operation

Supported target: **single-player Eden preview, vanilla Altis, Arma 3 x64 2.22**.
One playable NATO scout, two checkpoint guards and one editor-placed OPFOR reserve.
No extra mods, inference or spawning commands. Both quiet reconnaissance and automatic-combat runs now have successful local
Eden extraction records. The combat run has an actual movement-order acknowledgement.
Observed durations were about 8 minutes, below the 10–15 minute target. Detailed UI
readability, duplicate replay, human order replacement and new-mission outage fallback
remain to be tested; see [live evidence](verification.md#operator-confirmed-quiet-and-automatic-combat-completions).

## One-time installation / update

Use this PR's repository version and its successful **Windows observation demo**
artifact (`overlord-windows-observation-demo`), or main after merge. The artifact
contains the matching mission, DLL, installer and guides. The Python service runs
from the repository clone, not the extracted artifact's tools folder.

Close Arma before changing its installed DLL/mission. Back up your existing
`@OVERLORD` folder and `OperationFirstContact.Altis` mission folder by renaming them
outside the active mod/mission names. Do not overwrite Eden edits or saved games.
The installer deliberately refuses existing destinations. From the extracted
artifact directory in PowerShell (adjust your actual Steam/profile directories):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-demo.ps1 `
  -ArmaPath 'D:\Games\Steam\steamapps\common\Arma 3' `
  -MissionsPath 'C:\Users\j\Documents\Arma 3 - Other Profiles\instanceofjamie\missions'
```

Default `-MissionsPath` is Documents\Arma 3\missions. If you use both profiles,
install a matching mission into both. Never load a saved run to test an update.
Restart Arma after every DLL update. For a source build with Visual Studio C++ and
CMake, use `cmake -S bridge -B build/windows -A x64`, then
`cmake --build build/windows --config Release`; installer `-DllPath` accepts the DLL.

In a **Windows repository clone**, one-time Python 3.12 setup in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Keep host `127.0.0.1`, port `8000`. The existing DLL fixes this local endpoint.
Do not expose the API publicly: game ingestion/poll/ack still assume a trusted
local machine. Operator control mutations now require a separate launch credential.

## Normal startup and permission check — no development task required

1. In the repository clone, double-click **tools\start-overlord.cmd**. Keep its
   terminal open. It uses the project's Python automatically, avoiding the previous
   `/usr/bin/python3: No module named overlord` problem.
2. Open the **private operator panel link printed by that terminal**. It contains
   a launch credential in the URL fragment, which the panel removes from its URL
   and keeps in this tab's session storage. The server does not embed the credential
   in the page or send it to every visitor. Treat the launch link as a password.
   A service restart generates a new credential unless explicitly configured.
   Control mode and commitment for a still-running mission persist in the same
   SQLite database; credential rotation does not change that mode.
3. Launch Arma x64 with BattlEye and other mods off and `-mod=@OVERLORD`.
   Editor → Altis → Scenario → Open → OperationFirstContact → **Play Scenario**.
   This milestone disables the debug console; no console commands are needed.
4. The panel lists the new mission session. Confirm its UUID matches Arma's SESSION
   message. A newer scenario is announced with a **Switch to newest mission** button;
   a new session always starts recommendation-only, even if the last one was enabled.
5. Check **Current mode** and the access explanation. An authorised launch operator
   sees “approval and mode controls available”. A plain `/operator` visit is read-only
   unless this tab already holds a valid credential. Paste the current launch
   credential into its password field if necessary. If the service was started
   directly with uvicorn without a credential, the panel explains that approvals
   are unavailable: use the normal launcher. No machine/user role needs upgrading.

For an existing **Ubuntu/WSL** director checkout, run `./tools/start-overlord.sh`
from that repository instead. It chooses `.venv/bin/python` itself. Open the printed
loopback link in your Windows browser. This uses the same previously working WSL
loopback path; do not run two directors on port 8000. No WSL restart is required.

## What the previous “permission” problem actually was

The two logged sessions at 12:51 and 12:54 on 2026-11-09 both produced `proposed`
while `enabled=false`. Neither had an execution acknowledgement. Recommendation-only
was the intended default, but the only enable control was a session-specific CLI.
Ending/restarting the scenario invalidated the UUID being used, and a later CLI
attempt used system Python instead of the project environment. There was no missing
application role: the old service had no operator authentication at all.

This milestone adds a supported launch/panel workflow and a real limited control
boundary. Wrong/missing credentials cannot enable, pause or approve (403); a service
without an operator credential explains the configuration problem (503). Read-only
inspection stays available. Explicit `OVERLORD_OPERATOR_TOKEN` is supported for a
trusted local operator; keep it secret and out of source control. The old CLI now
also requires that credential in its environment; the normal panel is preferred.

## Playtest A — quiet reconnaissance, approximately 10–15 minutes

1. Leave **Recommendation only** selected. Read the diary/map briefing and use the
   scroll-wheel action **Begin reconnaissance patrol** at friendly_base.
2. Walk a deliberate covered route to **recon_alpha** (roughly 470m from start).
   Stop, observe checkpoint_alpha with binoculars (`B`), and identify the guards.
   There is no forced contact, combat objective or time-triggered reserve dispatch.
   The route/pacing target includes planning, observation and a cautious return;
   it is not an enforced minimum duration. The geometry needs your terrain playtest.
3. Within **20m of recon_alpha**, use **Report checkpoint reconnaissance**. This
   explicit player report completes the recon task and assigns extraction. A
   proximity crossing alone does not complete reconnaissance; the report is the
   player's assertion that observation is complete. There is no fragile visibility
   heuristic and this report grants OPFOR no knowledge.
4. Return alive to **extraction_alpha** (same location as friendly_base). Within
   **30m**, use **Extract and debrief**. Expect success, completed tasks and a readable
   after-action report. Open it again using **After-action report / director status**
   or Map → Diary → After-action report. The mission stays running so delivery can
   finish and the panel's persisted debrief can refresh.
5. In the panel expect recon and extraction recorded, success and no checkpoint
   intervention. Read “not recorded” as absence of evidence, not a claim that no
   unobserved event happened. Returning without reporting cannot succeed: **Abort
   patrol and debrief** is an explicit failure option at extraction. Death is failure;
   its persisted report is available in the panel if the death screen obscures diary.

## Playtest B — overt engagement with normal approval controls

Restart the scenario for a fresh session and select it in the panel. Keep that
same scenario running throughout permission selection and engagement.

1. Select **Execution with automatic bounded approval** and click **Apply mode**
   before attacking. Arma should report execution enabled after the next poll.
   Only a fresh eligible attack after enabling can respond. Mode changes expire
   all undispatched proposals; nothing stale is silently released.
2. Begin the patrol, complete the recon report, then optionally approach/attack the
   checkpoint. Leave a guard alive for a plausible report. A surviving conscious
   checkpoint guard radioing observed harm is the minimal OPFOR evidence channel.
   Kill both without any report, have UNKNOWN attribution or unavailable reserves,
   and deliberate no-action is appropriate. This is a bounded radio abstraction,
   not a simulation of radio range, jamming or delayed intelligence.
3. Expect a recommendation/approval, command issued, then **movement_order_assigned**
   if Arma accepts the order. The existing reserve can move to the checkpoint;
   no new units spawn. Its movement order is acknowledged, not its physical arrival.
4. Continue your own extraction route. Neither killing the checkpoint nor waiting
   for reserves to arrive is required for mission success. Debrief shows engagement,
   actual recommendation/approval and the real acknowledgement (or its absence).
   Repeated attacks must not cause a second reserve dispatch.

For **manual approval**, select **Execution with manual review** before a fresh
attack instead. It produces a fresh recommendation with an **Approve this fresh
recommendation** button in the panel. Click before expiry. Changing from default
recommendation-only to execution expires the old proposal: a fresh eligible attack
is required, after the 15s default cooldown. If both guards are dead, start a new
scenario rather than trying to reuse a stale recommendation. No session UUID typing
or ad hoc agent task is needed.

## Pause, human control and disconnection

- Panel **Pause new dispatch** stops retrieval/dispatch while paused. Resume requires
  fresh evidence for undispatched proposals. A command already handed to transport
  may still apply; an existing movement order continues.
- Mission action **Pause / take human control of reserve** immediately sets the
  local veto and relinquishes integration ownership. It does not magically stop
  an existing order. A human can replace that order in Eden/Zeus; retries never
  recreate it. The demo adds no Zeus module or third-party integration. This local
  takeover is deliberately not reset through the web panel; restart for another test.
- For an outage test, use a separate fresh scenario. Disconnect **your director's
  terminal** with Ctrl-C (never stop WSL), finish recon/extraction, and open the
  local AAR. It must say **LOCAL FALLBACK**, show local milestones/results and mark
  director records stale/unknown. No fabricated recommendation or ack is created.
  Restart the director with the normal launcher while the scenario remains running;
  retained events can deliver and the persisted report can catch up. Use the new
  launch link for approvals after the service restarts.
- Up to 32 game outbox entries are retained in memory. Attack entries stop at 24 to
  reserve room for essential progress and acks. Closing the scenario loses undelivered
  entries; the debrief must not claim they were persisted. Old buffered attacks
  (>120s or before enable) cannot authorize a response. Terminal operation progress
  expires undispatched proposals and prevents further command retrieval; a command
  already issued remains committed and any late ack is still accepted.
- One reserve commitment per session remains consumed even for rejected, failed or
  uncertain commands. Orders expire after 60–120s on a UTC minute boundary. An issued
  order without ack becomes **uncertain**, never a reason to create another order.

Record the two approach durations, task/radio clarity, whether covert play is viable,
reserve movement/actual acknowledgement, local versus persisted debrief and any RPT
errors. [Verification evidence](verification.md) separates automated checks from live
play. Dedicated multiplayer, four slots and HostHavoc remain subsequent milestones;
this local slice does not claim their acceptance criteria.
