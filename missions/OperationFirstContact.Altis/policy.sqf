// SPDX-License-Identifier: Apache-2.0
// Pure predicates shared with executable SQF-VM regressions. Engine facts are gathered at the boundary.
OL_fnc_rpcPolicy = {
    params ["_server", "_known", "_player", "_expected", "_session", "_sender", "_owner", "_remote", "_jip", "_localHost", "_dedicated"];
    _server && {_known} && {_player} && {_session == _expected} && {!_jip} && {
        if (_remote) then {_sender > 2 && {_sender == _owner}} else {_localHost && {!_dedicated}}
    }
};
OL_fnc_adminPolicy = {
    params ["_multiplayer", "_dedicated", "_localCaller", "_admin"];
    !_multiplayer || {!_dedicated && {_localCaller}} || {_admin == 2}
};
OL_fnc_teamPolicy = {
    params ["_milestone", "_alive", "_near", "_livingCount", "_allHome"];
    if (_milestone == "operator_killed") exitWith {!_alive && {_livingCount == 0}};
    _alive && {_near} && {if (_milestone in ["extracted", "aborted"]) then {_allHome} else {true}}
};
OL_fnc_taskStates = {
    params ["_stage", "_completed"];
    private _states = ["Created", "Created", "Created"];
    if ("briefing_complete" in _completed) then {_states set [0, "Succeeded"]};
    if ("recon_reported" in _completed) then {_states set [1, "Succeeded"]};
    switch (_stage) do {
        case "briefing": {_states set [0, "Assigned"]};
        case "recon": {_states set [1, "Assigned"]};
        case "extraction": {_states set [2, "Assigned"]};
        case "succeeded": {_states = ["Succeeded", "Succeeded", "Succeeded"]};
        case "failed": {{if (_x != "Succeeded") then {_states set [_forEachIndex, "Failed"]}} forEach _states};
    };
    _states
};
OL_fnc_attackPolicy = {
    params ["_server", "_local", "_now", "_last", "_stage"];
    _server && {_local} && {_now - _last >= 3} && {!(_stage in ["succeeded", "failed"])}
};
