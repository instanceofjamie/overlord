// SPDX-License-Identifier: Apache-2.0
// Loaded only by initServer. No remoteExec and no client-supplied observations.
OL_fnc_uuid = {
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
    // Only two events are possible in this scenario; extra guard protects later edits.
    if (count OL_outbox >= 4) exitWith {["OUTBOX FULL: observation dropped"] call OL_fnc_status};
    OL_outbox pushBack [_id, "event", _body, _type];
    [format ["DETECTED %1 (event %2)", _type, _id]] call OL_fnc_status;
};
OL_fnc_checkpointHit = {
    params ["_unit", "_instigator"];
    if (!isServer || {!local _unit} || {OL_checkpointReported}) exitWith {};
    // Set the shared latch synchronously before any scheduling/network operation.
    OL_checkpointReported = true;
    private _side = "UNKNOWN";
    if (!isNull _instigator && {_instigator isKindOf "CAManBase"}) then {
        _side = switch (side group _instigator) do {
            case west: {"BLUFOR"}; case east: {"OPFOR"}; case independent: {"INDEPENDENT"};
            default {"UNKNOWN"};
        };
    };
    ["checkpoint_attacked", format ["{""checkpoint_id"":""checkpoint_alpha"",""attacking_side"":""%1""}", _side]] call OL_fnc_observe;
};
