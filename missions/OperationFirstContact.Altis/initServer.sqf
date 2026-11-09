// SPDX-License-Identifier: Apache-2.0
if (!isServer || {missionNamespace getVariable ["OL_initialized", false]}) exitWith {};
OL_initialized = true;
call compile preprocessFileLineNumbers "observer.sqf";
OL_session = call OL_fnc_uuid;
OL_checkpointReported = false;
OL_lastCheckpointReport = -100;
call compile preprocessFileLineNumbers "executor.sqf";
OL_reserveGroup = group (missionNamespace getVariable ["overlord_reserve_leader", objNull]);
OL_reserveGroup setVariable ["OL_owned", true];
{_x disableAI "PATH"} forEach units OL_reserveGroup;
OL_outbox = [];
call compile preprocessFileLineNumbers "network.sqf";
call compile preprocessFileLineNumbers "operation.sqf";
OL_sessionBody = format ["{""session_id"":""%1"",""mission_name"":""Operation First Contact"",""map_name"":""Altis""}", OL_session];
OL_outbox pushBack [OL_session, "session", OL_sessionBody, "session"];
[format ["SESSION %1; productVersion %2; transport async x64 DLL", OL_session, productVersion]] call OL_fnc_status;
// Mission setup, not director commands. All checkpoint entities stay server-local.
{
    _x params ["_name", "_position", "_text", "_type", "_color"];
    private _marker = createMarker [_name, _position];
    _marker setMarkerType _type; _marker setMarkerColor _color; _marker setMarkerText _text;
} forEach [
    ["friendly_base", [13900,15700,0], "NATO start", "mil_start", "ColorWEST"],
    ["recon_alpha", [14280,15980,0], "Recon observation / report point", "mil_dot", "ColorWEST"],
    ["extraction_alpha", [13900,15700,0], "Extraction and debrief", "mil_end", "ColorWEST"],
    ["checkpoint_alpha", [14500,16100,0], "OPFOR checkpoint", "mil_objective", "ColorEAST"],
    ["response_alpha", [14500,16100,0], "Reserve response", "mil_dot", "ColorEAST"],
    ["enemy_reserve", [14600,16200,0], "OPFOR reserve", "mil_dot", "ColorEAST"]
];
createCenter east;
private _group = createGroup [east, true];
{
    private _guard = _group createUnit ["O_Soldier_F", _x, [], 0, "NONE"];
    _guard setPosATL _x;
    _guard setDir 180;
    _guard setSkill 0.2;
    _guard disableAI "PATH";
    _guard setUnitPos "MIDDLE";
    _guard addEventHandler ["Hit", {
        params ["_unit", "_source", "_damage", "_instigator"];
        if (_damage > 0) then {[_unit, _instigator] call OL_fnc_checkpointHit};
    }];
    // Fatal first hits may skip Hit; same shared latch prevents double reports.
    _guard addEventHandler ["Killed", {
        params ["_unit", "_killer", "_instigator"];
        [_unit, _instigator] call OL_fnc_checkpointHit;
    }];
} forEach [[14497,16100,0], [14503,16100,0]];
{
    private _barrier = createVehicle ["Land_BagFence_Long_F", _x, [], 0, "CAN_COLLIDE"];
    _barrier setPosATL _x;
} forEach [[14497,16098,0], [14503,16098,0]];
// Starting cover gives the observer time to read statuses and choose when to engage.
private _cover = createVehicle ["Land_HBarrier_3_F", [13900,15705,0], [], 0, "CAN_COLLIDE"];
_cover setPosATL [13900,15705,0];
[] spawn {
    waitUntil {sleep 0.1; time > 0};
    private _count = count (call OL_fnc_activeScouts);
    ["mission_started", format ["{""player_count"":%1}", _count min 256]] call OL_fnc_observe;
    [] execVM "transport.sqf";
};

private _reconCover = createVehicle ["Land_HBarrier_3_F", [14280,15985,0], [], 0, "CAN_COLLIDE"];
_reconCover setPosATL [14280,15985,0];

[format ["AUTHORITY dedicated=%1; reserve local=%2; reserve owner=%3; slots=4", isDedicated, local OL_reserveGroup, groupOwner OL_reserveGroup]] call OL_fnc_status;
call OL_fnc_publish;
// EntityKilled runs on the authoritative server even though player units are client-local.
addMissionEventHandler ["EntityKilled", {
    params ["_unit"];
    if (([_unit] call OL_fnc_participant) && {isPlayer [_unit]} && {!(_unit getVariable ["OL_parked", false])}) then {
        OL_localFacts pushBack ("A scout was killed at " + call OL_fnc_timestamp);
        ["operator_killed", _unit] call OL_fnc_progress;
        call OL_fnc_publish;
    };
}];

// Keep disconnected bodies/slots available; a disconnect is not a team death or reset.
addMissionEventHandler ["HandleDisconnect", {
    params ["_unit"];
    if ([_unit] call OL_fnc_participant) then {[_unit] call OL_fnc_parkSlot; true} else {false}
}];
[] spawn {
    while {true} do {
        private _active = call OL_fnc_activeScouts;
        {
            private _unit = missionNamespace getVariable [_x, objNull];
            if (!isNull _unit && {alive _unit}) then {
                if (_unit in _active) then {
                    if (_unit getVariable ["OL_parked", false]) then {
                        _unit hideObjectGlobal false;
                        _unit enableSimulationGlobal true;
                        if (local _unit) then {_unit allowDamage true; _unit enableAI "ALL"};
                        _unit setVariable ["OL_parked", false];
                    };
                } else {
                    if !(_unit getVariable ["OL_parked", false]) then {[_unit] call OL_fnc_parkSlot};
                };
            };
        } forEach OL_slotNames;
        sleep 0.5;
    };
};
