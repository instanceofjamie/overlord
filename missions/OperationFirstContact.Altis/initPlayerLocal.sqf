// SPDX-License-Identifier: Apache-2.0
if (!hasInterface || {missionNamespace getVariable ["OL_clientInitialized", false]}) exitWith {};
OL_clientInitialized = true;
call compile preprocessFileLineNumbers "policy.sqf";
waitUntil {sleep 0.1; !isNull player && {count (missionNamespace getVariable ["OL_snapshot", []]) == 8} && {"recon_alpha" in allMapMarkers}};
player allowDamage true;
player enableAI "ALL";
player addWeapon "Binocular";
player createDiaryRecord ["Diary", ["Situation and intent", "HQ needs a report on a newly established OPFOR checkpoint near the airfield. Confirm its presence and return with your observations. This is reconnaissance, not checkpoint clearance. Remain covert if possible; engagement is your choice and is not required for success. Disengage and return alive."]];
player createDiaryRecord ["Diary", ["Operation First Contact", "A short reconnaissance patrol, approximately 10-15 minutes at a deliberate pace. Read the map, plan a covered route from friendly_base to recon_alpha, observe checkpoint_alpha through binoculars, then use Report checkpoint reconnaissance within 20m of recon_alpha. This is an explicit player report, not an automatic sighting. You may stay covert or engage. Return to extraction_alpha and use Extract and debrief. Success requires report plus live extraction; the last connected scout dying or a team abort is failure. No time limit and no automatic combat escalation. Essential tasks and debrief run locally if the director disconnects. Tasks and outcomes are shared. All living connected scouts must be at extraction. Disconnecting does not reset the operation."]];
player createDiaryRecord ["Diary", ["Director and human control", "Recommendation-only is the default. Use the private operator panel link printed when starting Overlord. Choose execution automatic or execution review before a fresh attack. Mode changes expire old proposals. The panel shows permissions and supports fresh recommendation approval and pause. Pause prevents new dispatch, not ongoing movement. Logged-in server admins may use Pause / take human control for a veto and ownership opt-out; Human override: hold reserve explicitly replaces its current movement order. No director acknowledgement proves physical arrival."]];

OL_fnc_sendProgress = {
    params ["_milestone"];
    private _session = (missionNamespace getVariable ["OL_snapshot", []]) param [0, ""];
    if (isServer) then {isNil {[_milestone, player] call OL_fnc_progress}} else {
        [_milestone, player, _session] remoteExecCall ["OL_fnc_requestProgress", 2];
    };
};
OL_fnc_sendTakeover = {
    params ["_action"];
    private _session = (missionNamespace getVariable ["OL_snapshot", []]) param [0, ""];
    if (isServer) then {[_action, player, _session] call OL_fnc_requestTakeover} else {
        [_action, player, _session] remoteExecCall ["OL_fnc_requestTakeover", 2];
    };
};
OL_fnc_localDebrief = {
    private _snapshot = missionNamespace getVariable ["OL_snapshot", []];
    if (count _snapshot != 8) exitWith {hint "Waiting for authoritative server mission state"};
    _snapshot params ["_session", "_stage", "_completed", "_facts", "_report", "_contact", "_results", "_veto"];
    private _connection = if (serverTime - _contact < 8) then {"Director snapshot recently received by the server"} else {"LOCAL FALLBACK: director unavailable or stale; director persistence unconfirmed"};
    private _acks = _results apply {format ["%1: %2 / %3 (server executor result; delivery is separate)", _x select 0, _x select 1, _x select 2]};
    private _body = format ["Session: %1<br/>Shared outcome/stage: %2<br/>%3<br/><br/>Server-observed milestones:<br/>%4<br/><br/>Last received director record (may be stale):<br/>%5<br/><br/>Server executor results:<br/>%6<br/>Reserve arrival: not tracked. Movement order applied is not arrival.<br/>Local veto: %7. Missing records are unknown, not success. The operator panel shows persisted evidence.", _session, _stage, _connection, _facts joinString "<br/>", _report joinString "<br/>", _acks joinString "<br/>", _veto];
    player createDiaryRecord ["Diary", ["After-action report", _body]];
    hint parseText _body;
};
player addAction ["Begin reconnaissance patrol", {["briefing_complete"] call OL_fnc_sendProgress}, nil, 2, true, true, "", "((missionNamespace getVariable ['OL_snapshot',[]]) param [1,'']) == 'briefing' && {player distance2D markerPos 'friendly_base' < 30}"];
player addAction ["Report checkpoint reconnaissance", {["recon_reported"] call OL_fnc_sendProgress}, nil, 2, true, true, "", "((missionNamespace getVariable ['OL_snapshot',[]]) param [1,'']) == 'recon' && {player distance2D markerPos 'recon_alpha' < 20}"];
player addAction ["Extract and debrief", {["extracted"] call OL_fnc_sendProgress; hint "Extraction requested. All living connected scouts must be within 30m of extraction."}, nil, 2, true, true, "", "((missionNamespace getVariable ['OL_snapshot',[]]) param [1,'']) == 'extraction' && {player distance2D markerPos 'extraction_alpha' < 30}"];
player addAction ["Abort patrol and debrief (team failure)", {["aborted"] call OL_fnc_sendProgress}, nil, 0, false, true, "", "((missionNamespace getVariable ['OL_snapshot',[]]) param [1,'']) in ['recon','extraction'] && {player distance2D markerPos 'extraction_alpha' < 30}"];
player addAction ["After-action report / director status", {call OL_fnc_localDebrief}];
player addAction ["Pause / take human control of reserve (admin)", {["takeover"] call OL_fnc_sendTakeover}, nil, 0, false, true, "", "isServer || {serverCommandAvailable '#kick'}"];
player addAction ["Human override: hold reserve (admin)", {["hold"] call OL_fnc_sendTakeover}, nil, 0, false, true, "", "isServer || {serverCommandAvailable '#kick'}"];
private _brief = player createSimpleTask ["Briefing"];
_brief setSimpleTaskDescription ["Read the diary and use Begin reconnaissance patrol at friendly_base.", "Briefing", "Briefing"];
_brief setSimpleTaskDestination markerPos "friendly_base";
private _recon = player createSimpleTask ["Reconnaissance"];
_recon setSimpleTaskDescription ["A scout must report within 20m of recon_alpha. Combat is optional. This report is shared.", "Report checkpoint reconnaissance", "Reconnaissance"];
_recon setSimpleTaskDestination markerPos "recon_alpha";
private _extract = player createSimpleTask ["Extraction"];
_extract setSimpleTaskDescription ["All living connected scouts return within 30m; one chooses Extract and debrief.", "Extract and debrief", "Extraction"];
_extract setSimpleTaskDestination markerPos "extraction_alpha";
[_brief, _recon, _extract] spawn {
    params ["_brief", "_recon", "_extract"];
    // JIP/reconnect get current state plus one summary, not historical radio replay.
    private _seen = (missionNamespace getVariable ["OL_statusHistory", []]) apply {_x select 0};
    private _lastStates = [];
    private _announcedTerminal = false;
    private _snapshot = missionNamespace getVariable ["OL_snapshot", []];
    systemChat format ["OVERLORD session %1; shared stage %2. Operator modes are controlled in the private director panel.", _snapshot select 0, _snapshot select 1];
    while {true} do {
        _snapshot = missionNamespace getVariable ["OL_snapshot", []];
        if (count _snapshot == 8) then {
            private _stage = _snapshot select 1;
            private _completed = _snapshot select 2;
            private _states = [_stage, _completed] call OL_fnc_taskStates;
            if !(_states isEqualTo _lastStates) then {
                {private _task = [_brief, _recon, _extract] select _forEachIndex; _task setTaskState _x; if (_x == "Assigned") then {player setCurrentTask _task}} forEach _states;
                _lastStates = +_states;
            };
            if (!_announcedTerminal && {_stage in ["succeeded", "failed"]}) then {_announcedTerminal = true; call OL_fnc_localDebrief};
        };
        {
            _x params ["_id", "_message"];
            if !(_id in _seen) then {
                _seen pushBack _id;
                if (count _seen > 64) then {_seen deleteAt 0};
                if ((_message find "DETECTED") < 0 && {(_message find "DELIVERY CONFIRMED") < 0}) then {systemChat _message};
            };
        } forEach (missionNamespace getVariable ["OL_statusHistory", []]);
        sleep 0.25;
    };
};
