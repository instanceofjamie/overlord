// SPDX-License-Identifier: Apache-2.0
// Loaded only by initServer. No remoteExec and no client-supplied observations.
OL_fnc_uuid = {
    // Use OS GUIDs for delivered identities, independent of Eden's randomSeed.
    private _nativeId = "";
    if (missionNamespace getVariable ["OL_nativeIds", true]) then {
        private _result = "overlord_bridge" callExtension ["uuid", []];
        if (count (_result select 0) == 36) then {_nativeId = _result select 0; OL_nativeIds = true} else {
            OL_nativeIds = false;
        };
    };
    if (_nativeId != "") exitWith {_nativeId};
    // Missing DLL: still label debug detections, but no request can be delivered.
    private _chars = "0123456789abcdef";
    private _id = "";
    for "_i" from 0 to 35 do {
        _id = _id + (if (_i in [8,13,18,23]) then {"-"} else {
            if (_i == 14) then {"4"} else {
                _chars select [if (_i == 19) then {8 + floor random 4} else {floor random 16}, 1]
            }
        });
    };
    _id
};
OL_fnc_timestamp = {
    private _parts = systemTimeUTC;
    private _pad = { params ["_n"]; if (_n < 10) then {"0" + str _n} else {str _n} };
    format ["%1-%2-%3T%4:%5:%6Z", _parts select 0,
        [_parts select 1] call _pad, [_parts select 2] call _pad,
        [_parts select 3] call _pad, [_parts select 4] call _pad, [_parts select 5] call _pad]
};
OL_fnc_status = {
    params ["_message"];
    diag_log ("OVERLORD " + _message);
    private _history = missionNamespace getVariable ["OL_statusHistory", []];
    _history pushBack [call OL_fnc_uuid, "OVERLORD " + _message];
    if (count _history > 24) then {_history deleteAt 0};
    missionNamespace setVariable ["OL_statusHistory", _history, true];
};
OL_fnc_observe = {
    params ["_type", "_payload"];
    if (!isServer) exitWith {};
    private _id = call OL_fnc_uuid;
    private _body = format [
        "{""protocol_version"":""1.0"",""session_id"":""%1"",""event_id"":""%2"",""event_type"":""%3"",""timestamp"":""%4"",""payload"":%5}",
        OL_session, _id, _type, call OL_fnc_timestamp, _payload];
    // Bounded in-memory outbox. Report at most one attack per three seconds.
    if (_type == "checkpoint_attacked" && {count OL_outbox >= 24}) exitWith {["Offline attack buffer full; local mission progression remains available"] call OL_fnc_status};
    if (count OL_outbox >= 32) exitWith {["OUTBOX FULL: observation dropped"] call OL_fnc_status};
    OL_outbox pushBack [_id, "event", _body, _type];
    [format ["DETECTED %1 (event %2)", _type, _id]] call OL_fnc_status;
};
OL_fnc_checkpointHit = {
    params ["_unit", "_instigator"];
    if !([isServer, local _unit, diag_tickTime, OL_lastCheckpointReport, OL_stage] call OL_fnc_attackPolicy) exitWith {};
    // Throttle synchronously before scheduling/network; fresh attacks can follow operator enable.
    if (OL_stage in ["succeeded", "failed"]) exitWith {};
    if (!OL_checkpointReported) then {
        OL_localFacts pushBack ("checkpoint harm observed at " + call OL_fnc_timestamp);
        ["Checkpoint harm observed locally. A reserve response requires a surviving guard radio report and operator permission."] call OL_fnc_status;
    };
    OL_checkpointReported = true;
    OL_lastCheckpointReport = diag_tickTime;
    private _side = "UNKNOWN";
    if (!isNull _instigator && {_instigator isKindOf "CAManBase"}) then {
        _side = switch (side group _instigator) do {
            case west: {"BLUFOR"}; case east: {"OPFOR"}; case independent: {"INDEPENDENT"};
            default {"UNKNOWN"};
        };
    };
    // Minimal faction evidence: a surviving conscious checkpoint guard can radio the harm.
    // Recon reports alone never give OPFOR player knowledge. No player coordinates sent.
    private _channel = "none";
    if (({alive _x && {lifeState _x != "INCAPACITATED"}} count units group _unit) > 0) then {_channel = "guard_radio"};
    private _available = !isNull OL_reserveGroup && {({alive _x} count units OL_reserveGroup) > 0} && {OL_reserveGroup getVariable ["OL_owned", false]};
    ["checkpoint_attacked", format ["{""checkpoint_id"":""checkpoint_alpha"",""attacking_side"":""%1"",""report_channel"":""%2"",""reserve_available"":%3}", _side, _channel, if (_available) then {"true"} else {"false"}]] call OL_fnc_observe;
};
