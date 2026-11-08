// SPDX-License-Identifier: Apache-2.0
if (!isServer || {missionNamespace getVariable ["OL_initialized", false]}) exitWith {};
OL_initialized = true;
call compile preprocessFileLineNumbers "observer.sqf";
OL_session = call OL_fnc_uuid;
OL_checkpointReported = false;
OL_outbox = [];
OL_sessionBody = format ["{""session_id"":""%1"",""mission_name"":""Operation First Contact"",""map_name"":""Altis""}", OL_session];
OL_outbox pushBack [OL_session, "session", OL_sessionBody, "session"];
[format ["SESSION %1; productVersion %2; transport async x64 DLL", OL_session, productVersion]] call OL_fnc_status;
// Mission setup, not director commands. All checkpoint entities stay server-local.
{
    _x params ["_name", "_position", "_text", "_type", "_color"];
    private _marker = createMarker [_name, _position];
    _marker setMarkerType _type; _marker setMarkerColor _color; _marker setMarkerText _text;
} forEach [
    ["friendly_base", [14500,16000,0], "NATO start", "mil_start", "ColorWEST"],
    ["checkpoint_alpha", [14500,16100,0], "OPFOR checkpoint", "mil_objective", "ColorEAST"],
    ["enemy_reserve", [14600,16200,0], "Reserve location (unused)", "mil_dot", "ColorEAST"]
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
private _cover = createVehicle ["Land_HBarrier_3_F", [14500,16005,0], [], 0, "CAN_COLLIDE"];
_cover setPosATL [14500,16005,0];
[] spawn {
    waitUntil {sleep 0.1; time > 0};
    private _count = (count allPlayers) max 1;
    ["mission_started", format ["{""player_count"":%1}", _count min 256]] call OL_fnc_observe;
    [] execVM "transport.sqf";
};
