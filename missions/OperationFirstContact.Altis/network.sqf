// SPDX-License-Identifier: Apache-2.0
call compile preprocessFileLineNumbers "policy.sqf";
// Server-only RPC boundary; no arbitrary code, coordinates or unit classes accepted.
OL_slotNames = ["overlord_player", "overlord_player_2", "overlord_player_3", "overlord_player_4"];
OL_fnc_participant = {
    params ["_unit"];
    !isNull _unit && {_unit in (OL_slotNames apply {missionNamespace getVariable [_x, objNull]})} && {!alive _unit || {side group _unit == west}}
};
OL_fnc_activeScouts = {
    private _players = +allPlayers;
    if (!isMultiplayer && {hasInterface} && {!isNull player}) then {_players pushBackUnique player};
    _players select {[_x] call OL_fnc_participant}
};
OL_fnc_parkSlot = {
    params ["_unit"];
    if (!isNull _unit && {alive _unit}) then {
        _unit hideObjectGlobal true;
        _unit enableSimulationGlobal false;
        if (local _unit) then {_unit allowDamage false; _unit disableAI "ALL"};
        _unit setVariable ["OL_parked", true];
    };
};
OL_fnc_requestAllowed = {
    params ["_caller", "_session", "_sender", "_remote", "_jip"];
    [isServer, [_caller] call OL_fnc_participant, isPlayer [_caller], OL_session, _session,
        _sender, owner _caller, _remote, _jip, local _caller, isDedicated] call OL_fnc_rpcPolicy
};
OL_fnc_publish = {
    if (!isServer) exitWith {};
    private _acks = [];
    {private _r = OL_processed get _x; _acks pushBack [_x, _r select 1, _r select 2]} forEach keys OL_processed;
    // One server-owned snapshot supplies initial state, JIP, reconnect, tasks and local AAR.
    missionNamespace setVariable ["OL_snapshot", [OL_session, OL_stage, +OL_completed,
        +OL_localFacts, +OL_directorReport, OL_lastDirectorContact, _acks, OL_localPaused], true];
};
OL_fnc_requestProgress = {
    if (!isServer) exitWith {};
    params [["_milestone", "", [""]], ["_caller", objNull, [objNull]], ["_session", "", [""]]];
    if !([_caller, _session, remoteExecutedOwner, isRemoteExecuted, isRemoteExecutedJIP] call OL_fnc_requestAllowed) exitWith {diag_log "OVERLORD denied progress RPC: owner/session/participant"};
    if !(_milestone in ["briefing_complete", "recon_reported", "extracted", "aborted"]) exitWith {};
    // remoteExecCall executes unscheduled. Validate and latch before any yielding operation.
    [_milestone, _caller] call OL_fnc_progress;
};
OL_fnc_requestTakeover = {
    if (!isServer) exitWith {};
    params [["_action", "", [""]], ["_caller", objNull, [objNull]], ["_session", "", [""]]];
    private _sender = remoteExecutedOwner;
    if !([_caller, _session, _sender, isRemoteExecuted, isRemoteExecutedJIP] call OL_fnc_requestAllowed) exitWith {diag_log "OVERLORD denied takeover RPC: owner/session/participant"};
    if !([isMultiplayer, isDedicated, local _caller, admin (owner _caller)] call OL_fnc_adminPolicy) exitWith {diag_log "OVERLORD denied takeover RPC: logged-in server admin required"};
    if !(_action in ["takeover", "hold"]) exitWith {};
    OL_localPaused = true;
    OL_reserveGroup setVariable ["OL_owned", false];
    if (_action == "hold" && {!isNull OL_reserveGroup} && {local OL_reserveGroup}) then {
        // Explicit human replacement order, not a director command or an execution ack.
        private _old = waypoints OL_reserveGroup;
        reverse _old;
        {deleteWaypoint _x} forEach _old;
        private _wp = OL_reserveGroup addWaypoint [getPosATL leader OL_reserveGroup, 0];
        _wp setWaypointType "HOLD";
        OL_reserveGroup setCurrentWaypoint _wp;
        OL_localFacts pushBack "Logged-in admin explicitly replaced reserve movement with HOLD";
    };
    ["LOCAL VETO ACTIVE; integration ownership released. Pause alone leaves existing movement running; explicit admin HOLD replaces it."] call OL_fnc_status;
    call OL_fnc_publish;
};
