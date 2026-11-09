// SPDX-License-Identifier: Apache-2.0
// Single-player local operation. No network dependency for essential progression.
call compile preprocessFileLineNumbers "flow.sqf";
OL_stage = "briefing";
OL_localFacts = [];
OL_directorReport = ["No director report received. Recommendations and persistence unknown."];
OL_lastDirectorContact = -100;
OL_fnc_progress = {
    params ["_milestone", "_caller"];
    if (!isServer || {isNull _caller} || {!local _caller} || {!(isPlayer [_caller])}) exitWith {};
    private _candidate = [OL_stage, _milestone] call OL_fnc_nextStage;
    if (_candidate == OL_stage) exitWith {};
    private _next = "";
    switch (_milestone) do {
        case "briefing_complete": {if (OL_stage == "briefing" && {alive _caller} && {_caller distance2D markerPos "friendly_base" < 30}) then {_next = "recon"}};
        case "recon_reported": {if (OL_stage == "recon" && {alive _caller} && {_caller distance2D markerPos "recon_alpha" < 20}) then {_next = "extraction"}};
        case "extracted": {if (OL_stage == "extraction" && {alive _caller} && {_caller distance2D markerPos "extraction_alpha" < 30}) then {_next = "succeeded"}};
        case "aborted": {if (OL_stage in ["recon", "extraction"] && {alive _caller} && {_caller distance2D markerPos "extraction_alpha" < 30}) then {_next = "failed"}};
        case "operator_killed": {if (!(OL_stage in ["succeeded", "failed"]) && {!alive _caller}) then {_next = "failed"}};
    };
    if (_next == "") exitWith {};
    OL_stage = _candidate;
    missionNamespace setVariable ["OL_stage", _next, true];
    private _fact = format ["%1 at %2", _milestone, call OL_fnc_timestamp];
    OL_localFacts pushBack _fact;
    ["operation_progress", format ["{""milestone"":""%1""}", _milestone]] call OL_fnc_observe;
    private _message = switch (_next) do {
        case "recon": {"HQ: Move to recon_alpha. Observe the checkpoint from cover, then use Report checkpoint reconnaissance. Engagement is optional."};
        case "extraction": {"HQ: Recon report received locally. Return to extraction_alpha and choose Extract and debrief. You may disengage without firing."};
        case "succeeded": {"HQ: Reconnaissance and extraction complete. Review After-action report in the action menu or diary. Director delivery may still be pending."};
        default {"HQ: Operation unsuccessful. Review the local after-action report; no missing director result is assumed."};
    };
    [_message] call OL_fnc_status;
};
