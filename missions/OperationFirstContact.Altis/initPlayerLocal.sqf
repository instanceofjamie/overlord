// SPDX-License-Identifier: Apache-2.0
waitUntil { !isNull player };
player createDiaryRecord ["Diary", ["OVERLORD demo", "Attack a checkpoint guard at checkpoint_alpha, 100m north of the start. DETECTED means observed in-game; DELIVERY CONFIRMED means the API acknowledged persistence. DIRECTOR UNAVAILABLE never stops gameplay. Only one checkpoint_attacked event is recorded per run. Restart the scenario for another run."]];
// A bounded server-published history also works for local editor play and later JIP.
[] spawn {
    private _seen = [];
    while {true} do {
        {
            _x params ["_id", "_message"];
            if !(_id in _seen) then {
                _seen pushBack _id;
                if (count _seen > 24) then {_seen deleteAt 0};
                systemChat _message;
                hintSilent _message;
            };
        } forEach (missionNamespace getVariable ["OL_statusHistory", []]);
        sleep 0.25;
    };
};
