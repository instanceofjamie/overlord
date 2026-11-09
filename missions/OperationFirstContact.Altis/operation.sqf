// SPDX-License-Identifier: Apache-2.0
// Server-owned shared operation. No director dependency for essential progression.
call compile preprocessFileLineNumbers "flow.sqf";
OL_stage = "briefing";
OL_completed = [];
OL_localFacts = [];
OL_directorReport = ["No director report received. Recommendations and persistence unknown."];
OL_lastDirectorContact = -100;
OL_fnc_progress = {
    params ["_milestone", "_caller"];
    if (!isServer || {isNull _caller} || {!([_caller] call OL_fnc_participant)}) exitWith {};
    private _candidate = [OL_stage, _milestone] call OL_fnc_nextStage;
    if (_candidate == OL_stage) exitWith {};
    private _living = (call OL_fnc_activeScouts) select {alive _x};
    private _allHome = count _living > 0 && {(_living findIf {_x distance2D markerPos "extraction_alpha" >= 30}) < 0};
    private _point = switch (_milestone) do {
        case "briefing_complete": {"friendly_base"};
        case "recon_reported": {"recon_alpha"};
        default {"extraction_alpha"};
    };
    private _near = _caller distance2D markerPos _point < (if (_milestone == "recon_reported") then {20} else {30});
    if !([_milestone, alive _caller, _near, count _living, _allHome] call OL_fnc_teamPolicy) exitWith {};
    private _next = _candidate;
    OL_stage = _candidate;
    missionNamespace setVariable ["OL_stage", _next, true];
    private _fact = format ["%1 at %2", _milestone, call OL_fnc_timestamp];
    OL_localFacts pushBack _fact;
    OL_completed pushBackUnique _milestone;
    ["operation_progress", format ["{""milestone"":""%1""}", _milestone]] call OL_fnc_observe;
    private _message = switch (_next) do {
        case "recon": {"HQ: Move to recon_alpha. Observe the checkpoint from cover, then use Report checkpoint reconnaissance. Engagement is optional."};
        case "extraction": {"HQ: Recon report received locally. Return to extraction_alpha and choose Extract and debrief. You may disengage without firing."};
        case "succeeded": {"HQ: Reconnaissance and extraction complete. Review After-action report in the action menu or diary. Director delivery may still be pending."};
        default {"HQ: Operation unsuccessful. Review the local after-action report; no missing director result is assumed."};
    };
    [_message] call OL_fnc_status;
    call OL_fnc_publish;
};
