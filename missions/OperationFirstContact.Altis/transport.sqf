// SPDX-License-Identifier: Apache-2.0
// One request at a time, fixed localhost DLL endpoint. Never waits for HTTP in callExtension.
if !(missionNamespace getVariable ["OL_nativeIds", false]) exitWith {
    ["DIRECTOR UNAVAILABLE: bridge UUID support missing. Detection remains active; install current DLL and restart Arma."] call OL_fnc_status;
};
private _ready = "overlord_bridge" callExtension ["reset", []];
if ((_ready select 0) != "ready") exitWith {
    ["DIRECTOR UNAVAILABLE: bridge missing/blocked. Detection remains active; restart after installation."] call OL_fnc_status;
};
private _registered = false;
private _unavailable = false;
private _lastPoll = -10;
while {true} do {
    if (_registered && {count OL_outbox == 0} && {diag_tickTime - _lastPoll >= 2}) then {
        OL_outbox pushBack [call OL_fnc_uuid, "command", format ["{""session_id"":""%1"",""include_report"":true}", OL_session], "command poll"];
        _lastPoll = diag_tickTime;
    };
    if (count OL_outbox > 0) then {
        private _item = OL_outbox select 0;
        _item params ["_id", "_kind", "_body", "_label"];
        private _submitted = "overlord_bridge" callExtension ["post", [_id, _kind, _body]];
        private _code = -1;
        private _reply = [];
        if ((_submitted select 0) == "queued") then {
            // Poll yields between frames. DLL has its own finite per-phase HTTP timeouts.
            // No new requests are submitted while this one remains in flight.
            private _started = diag_tickTime;
            private _warned = false;
            waitUntil {
                sleep 0.25;
                private _polled = "overlord_bridge" callExtension ["poll", [_id]];
                private _text = _polled select 0;
                if ((_text select [0,1]) == "[") then {_reply = parseSimpleArray _text; _code = _reply param [0,-1]};
                if (!_warned && {diag_tickTime - _started > 8}) then {
                    ["DIRECTOR UNAVAILABLE: request still pending; gameplay continues"] call OL_fnc_status;
                    _warned = true;
                };
                _code != -1
            };
        };
        if (_code in [200,201]) then {
            if (_kind == "session") then {_registered = true};
            if (_kind != "command") then {
                [format ["DELIVERY CONFIRMED %1 (%2), session %3", _label, _id, OL_session]] call OL_fnc_status;
            };
            OL_outbox deleteAt 0;
            if (_kind == "command" && {count _reply == 2}) then {
                // isNil code executes unscheduled: validation, latch and assignment cannot interleave.
                isNil {[_reply select 1] call OL_fnc_receiveCommand};
            };
            _unavailable = false;
        } else {
            if (!_unavailable) then {
                [format ["DIRECTOR UNAVAILABLE / delivery unconfirmed (HTTP %1). Retrying retained IDs.", _code]] call OL_fnc_status;
                _unavailable = true;
            };
            if (_code == 404 && {_registered}) then {
                // Director may have restarted with an empty database. Re-register same session.
                OL_outbox insert [0, [[OL_session, "session", OL_sessionBody, "session"]]];
                _registered = false;
            };
            if (_code in [400,409,422]) then {
                [format ["DELIVERY REJECTED %1: HTTP %2; inspect director logs. Automatic retries stopped.", _label, _code]] call OL_fnc_status;
                waitUntil {sleep 60; false};
            };
            sleep 3;
        };
    };
    sleep 0.25;
};
