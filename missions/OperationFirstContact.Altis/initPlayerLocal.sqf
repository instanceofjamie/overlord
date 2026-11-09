// SPDX-License-Identifier: Apache-2.0
waitUntil { !isNull player && {!isNil "OL_stage"} && {"recon_alpha" in allMapMarkers} };
player addWeapon "Binocular";
player createDiaryRecord ["Diary", ["Operation First Contact", "A short reconnaissance patrol, approximately 10-15 minutes at a deliberate pace. Read the map, plan a covered route from friendly_base to recon_alpha, observe checkpoint_alpha through binoculars, then use Report checkpoint reconnaissance within 20m of recon_alpha. This is an explicit player report, not an automatic sighting. You may stay covert or engage. Return to extraction_alpha and use Extract and debrief. Success requires report plus live extraction; death or Abort patrol is failure. No time limit and no automatic combat escalation. Essential tasks and debrief run locally if the director disconnects. Single-player Eden preview is the supported scope."]];
player createDiaryRecord ["Diary", ["Director and human control", "Recommendation-only is the default. Use the private operator panel link printed when starting Overlord. Choose execution automatic or execution review before a fresh attack. Mode changes expire old proposals. The panel shows permissions and supports fresh recommendation approval and pause. Pause prevents new dispatch, not ongoing movement. Use Pause / take human control in this action menu for an immediate local veto and reserve ownership opt-out. No director acknowledgement proves physical arrival."]];
OL_fnc_localDebrief = {
    private _connection = if (diag_tickTime - OL_lastDirectorContact < 8) then {"Director snapshot recently received"} else {"LOCAL FALLBACK: director unavailable or snapshot stale; persistence unconfirmed"};
    private _facts = OL_localFacts joinString "<br/>";
    private _acks = [];
    {private _r = OL_processed get _x; _acks pushBack format ["%1: %2 / %3 (actual local executor result; delivery separately acknowledged)", _x, _r select 1, _r select 2]} forEach keys OL_processed;
    private _body = format ["Outcome/stage: %1<br/>%2<br/><br/>Local observed milestones:<br/>%3<br/><br/>Latest received director record (may be stale):<br/>%4<br/><br/>Local executor results:<br/>%5<br/>Reserve arrival: not tracked. Movement order applied is not arrival.<br/>Open the operator panel for persisted event and acknowledgement details. Missing records are unknown, not success.", OL_stage, _connection, _facts, OL_directorReport joinString "<br/>", _acks joinString "<br/>"];
    player createDiaryRecord ["Diary", ["After-action report", _body]];
    hint parseText _body;
};
player addAction ["Begin reconnaissance patrol", {isNil {["briefing_complete", player] call OL_fnc_progress}}, nil, 2, true, true, "", "isServer && {OL_stage == 'briefing'} && {player distance2D markerPos 'friendly_base' < 30}"];
player addAction ["Report checkpoint reconnaissance", {isNil {["recon_reported", player] call OL_fnc_progress}}, nil, 2, true, true, "", "isServer && {OL_stage == 'recon'} && {player distance2D markerPos 'recon_alpha' < 20}"];
player addAction ["Extract and debrief", {isNil {["extracted", player] call OL_fnc_progress}; call OL_fnc_localDebrief}, nil, 2, true, true, "", "isServer && {OL_stage == 'extraction'} && {player distance2D markerPos 'extraction_alpha' < 30}"];
player addAction ["Abort patrol and debrief (failure)", {isNil {["aborted", player] call OL_fnc_progress}; call OL_fnc_localDebrief}, nil, 0, false, true, "", "isServer && {OL_stage in ['recon','extraction']} && {player distance2D markerPos 'extraction_alpha' < 30}"];
player addAction ["After-action report / director status", {call OL_fnc_localDebrief}];
player addAction ["Pause / take human control of reserve", {
    if (!isServer) exitWith {};
    OL_localPaused = true;
    OL_reserveGroup setVariable ["OL_owned", false];
    ["LOCAL VETO ACTIVE; reserve ownership released. Existing movement continues until you replace its order. Director pause is also available in the operator panel."] call OL_fnc_status;
}];
player addEventHandler ["Killed", {params ["_unit"]; isNil {["operator_killed", _unit] call OL_fnc_progress}; call OL_fnc_localDebrief}];
private _brief = player createSimpleTask ["Briefing"];
_brief setSimpleTaskDescription ["Read the diary and plan your route. Use Begin reconnaissance patrol at friendly_base.", "Briefing", "Briefing"];
_brief setSimpleTaskDestination markerPos "friendly_base";
_brief setTaskState "Assigned";
player setCurrentTask _brief;
private _recon = player createSimpleTask ["Reconnaissance"];
_recon setSimpleTaskDescription ["Observe checkpoint_alpha from recon_alpha, then use Report checkpoint reconnaissance within 20m of the marker. Combat is optional.", "Report checkpoint reconnaissance", "Reconnaissance"];
_recon setSimpleTaskDestination markerPos "recon_alpha";
private _extract = player createSimpleTask ["Extraction"];
_extract setSimpleTaskDescription ["Return alive and use Extract and debrief within 30m of extraction_alpha.", "Extract and debrief", "Extraction"];
_extract setSimpleTaskDestination markerPos "extraction_alpha";
// Create each task once, update only on a state transition. Status lines are distinct IDs.
[_brief, _recon, _extract] spawn {
    params ["_brief", "_recon", "_extract"];
    private _seen = [];
    private _lastStage = "briefing";
    while {true} do {
        {
            _x params ["_id", "_message"];
            if !(_id in _seen) then {
                _seen pushBack _id;
                if (count _seen > 64) then {_seen deleteAt 0};
                if ((_message find "DETECTED") < 0 && {(_message find "DELIVERY CONFIRMED") < 0}) then {systemChat _message};
            };
        } forEach (missionNamespace getVariable ["OL_statusHistory", []]);
        if (OL_stage != _lastStage) then {
            _lastStage = OL_stage;
            switch (OL_stage) do {
                case "recon": {_brief setTaskState "Succeeded"; _recon setTaskState "Assigned"; player setCurrentTask _recon};
                case "extraction": {_recon setTaskState "Succeeded"; _extract setTaskState "Assigned"; player setCurrentTask _extract};
                case "succeeded": {_extract setTaskState "Succeeded"};
                case "failed": {{if !(taskState _x == "Succeeded") then {_x setTaskState "Failed"}} forEach [_brief, _recon, _extract]};
            };
        };
        sleep 0.25;
    };
};
