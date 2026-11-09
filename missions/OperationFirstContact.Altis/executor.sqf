// SPDX-License-Identifier: Apache-2.0
// Loaded on server only. Wire arrays are parsed as data, never compiled.
OL_processed = createHashMap;
OL_reserveCommitted = false;
OL_localPaused = false;
OL_executionEnabled = false;
OL_directorPaused = false;
OL_lastResponseStatus = "";
OL_fnc_commandIdentity = {
    params ["_id"];
    if !(_id isEqualType "") exitWith {false};
    if (count _id != 36) exitWith {false};
    private _valid = true;
    {
        if (_forEachIndex in [8,13,18,23]) then {
            if (_x != 45) then {_valid = false};
        } else {
            if !(_x in toArray "0123456789abcdef") then {_valid = false};
        };
    } forEach toArray _id;
    _valid
};
OL_fnc_ackCommand = {
    params ["_id", "_key", "_state", "_result"];
    private _body = format ["{""protocol_version"":""1.0"",""session_id"":""%1"",""command_id"":""%2"",""idempotency_key"":""%3"",""status"":""%4"",""result"":""%5""}", OL_session, _id, _key, _state, _result];
    OL_processed set [_id, [_key, _state, _result]];
    // One command per session, so at most one retained acknowledgement.
    if ((OL_outbox findIf {(_x select 1) == "ack"}) < 0) then {
        OL_outbox pushBack [_id, "ack", _body, "reserve acknowledgement"];
    };
    [format ["RESERVE %1: %2 (%3)", _state, _result, _id]] call OL_fnc_status;
};
OL_fnc_receiveCommand = {
    params ["_packet"];
    if (!isServer || {!(_packet isEqualType [])} || {!(count _packet in [6,7])}) exitWith {};
    _packet params ["_version", "_session", "_enabled", "_paused", "_command", "_status"];
    if (_session != OL_session) exitWith {
        if (_session != (missionNamespace getVariable ["OL_lastIgnoredSession", ""])) then {
            OL_lastIgnoredSession = _session;
            diag_log "OVERLORD IGNORED PACKET: wrong mission/session";
        };
    };
    if (_version != "1.0" || {!(_enabled isEqualType true)} || {!(_paused isEqualType true)} || {!(_status isEqualType "")} || {!(_command isEqualType [])}) exitWith {};
    OL_lastDirectorContact = serverTime;
    if (count _packet == 7 && {(_packet select 6) isEqualType []}) then {OL_directorReport = _packet select 6};
    OL_executionEnabled = _enabled;
    OL_directorPaused = _paused;
    private _display = format ["RESPONSE %1; execution enabled=%2 paused=%3 (local veto=%4)", _status, _enabled, _paused, OL_localPaused];
    if (_display != OL_lastResponseStatus) then {[_display] call OL_fnc_status; OL_lastResponseStatus = _display};
    if (count _command == 0) exitWith {};
    if (count _command != 6) exitWith {["INVALID COMMAND SHAPE"] call OL_fnc_status};
    OL_lastCommandPacket = +_packet;
    _command params ["_id", "_key", "_action", "_asset", "_location", "_expiry"];
    if !(([_id] call OL_fnc_commandIdentity) && {[_key] call OL_fnc_commandIdentity}) exitWith {["INVALID COMMAND ID"] call OL_fnc_status};
    private _old = OL_processed getOrDefault [_id, []];
    if (count _old > 0) exitWith {
        diag_log format ["OVERLORD CACHED RESULT %1; waypoint count=%2", _id, count waypoints OL_reserveGroup];
        if ((_old select 0) == _key) then {[_id, _key, _old select 1, _old select 2] call OL_fnc_ackCommand};
    };
    private _result = "";
    private _state = "rejected";
    if (_id != _key || {_action != "dispatch_reserve"} || {_asset != "reserve_alpha"} || {_location != "response_alpha"}) then {_result = "invalid_command"};
    if !(_expiry isEqualType [] && {count _expiry == 5} && {(_expiry findIf {!(_x isEqualType 0)}) < 0}) then {_result = "invalid_command"};
    if (_result == "") then {
        private _bounds = [[2020,2100], [1,12], [1,31], [0,23], [0,59]];
        {
            private _range = _bounds select _forEachIndex;
            if (_x != floor _x || {_x < (_range select 0)} || {_x > (_range select 1)}) then {_result = "invalid_command"};
        } forEach _expiry;
    };
    if (_result == "") then {
        private _utc = systemTimeUTC;
        if ((_utc select 0) > (_expiry select 0) || {(_utc select 0) == (_expiry select 0) && {dateToNumber (_utc select [0,5]) >= dateToNumber _expiry}}) then {_result = "expired"; _state = "expired"};
    };
    if (_result == "" && {OL_stage in ["succeeded", "failed"]}) then {_result = "operation_complete"};
    if (_result == "" && {!OL_executionEnabled}) then {_result = "execution_disabled"};
    if (_result == "" && {OL_directorPaused || OL_localPaused}) then {_result = "paused"};
    if (_result == "" && {OL_reserveCommitted}) then {_result = "already_committed"};
    private _group = missionNamespace getVariable ["OL_reserveGroup", grpNull];
    if (_result == "" && {isNull _group || {!local _group} || {side _group != east} || {!(_group getVariable ["OL_owned", false])} || {({alive _x} count units _group) == 0} || {({isPlayer _x} count units _group) > 0} || {count waypoints _group > 1}}) then {_result = "reserve_ineligible"};
    if (_result == "" && {!("response_alpha" in allMapMarkers) || {markerPos "response_alpha" distance2D [14500,16100,0] > 1}}) then {_result = "invalid_location"};
    if (_result == "") then {
        // Latch BEFORE mutation, in one unscheduled call. Retries never recreate an order.
        OL_reserveCommitted = true;
        OL_processed set [_id, [_key, "failed", "uncertain"]];
        {_x enableAI "PATH"} forEach units _group;
        private _waypoint = _group addWaypoint [markerPos "response_alpha", 0];
        if (count _waypoint == 2 && {(_waypoint select 1) >= 0}) then {
            _waypoint setWaypointType "MOVE";
            _waypoint setWaypointSpeed "NORMAL";
            _group setCurrentWaypoint _waypoint;
            _state = "executed"; _result = "movement_order_assigned";
            diag_log format ["OVERLORD ORDER APPLIED %1; waypoint count=%2", _id, count waypoints _group];
        } else {_state = "failed"; _result = "assignment_failed"};
    };
    [_id, _key, _state, _result] call OL_fnc_ackCommand;
};
