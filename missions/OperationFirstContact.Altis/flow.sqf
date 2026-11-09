// SPDX-License-Identifier: Apache-2.0
// Pure transition function shared by runtime progression and SQF-VM regression tests.
OL_fnc_nextStage = {
    params ["_stage", "_milestone"];
    if (_stage in ["succeeded", "failed"]) exitWith {_stage};
    if (_milestone == "operator_killed") exitWith {"failed"};
    if (_milestone == "aborted" && {_stage in ["recon", "extraction"]}) exitWith {"failed"};
    if (_stage == "briefing" && {_milestone == "briefing_complete"}) exitWith {"recon"};
    if (_stage == "recon" && {_milestone == "recon_reported"}) exitWith {"extraction"};
    if (_stage == "extraction" && {_milestone == "extracted"}) exitWith {"succeeded"};
    _stage
};
