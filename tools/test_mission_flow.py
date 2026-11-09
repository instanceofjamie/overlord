# SPDX-License-Identifier: Apache-2.0
"""Execute the runtime's pure SQF state machine; not an Arma interaction/locality test."""

import argparse
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqfvm", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    flow = (root / "missions/OperationFirstContact.Altis/flow.sqf").read_text()
    policy = (root / "missions/OperationFirstContact.Altis/policy.sqf").read_text()
    script = (
        policy
        + flow
        + """
private _stage = "briefing";
{_stage = [_stage, _x] call OL_fnc_nextStage} forEach [
    "briefing_complete", "briefing_complete", "recon_reported", "recon_reported", "extracted"];
assert (_stage == "succeeded");
assert ((["succeeded", "operator_killed"] call OL_fnc_nextStage) == "succeeded");
assert ((["briefing", "extracted"] call OL_fnc_nextStage) == "briefing");
assert ((["recon", "checkpoint_attacked"] call OL_fnc_nextStage) == "recon");
assert ((["recon", "aborted"] call OL_fnc_nextStage) == "failed");
assert ((["extraction", "operator_killed"] call OL_fnc_nextStage) == "failed");
assert ((["failed", "extracted"] call OL_fnc_nextStage) == "failed");
assert ([true,true,true,"current","current",3,3,true,false,false,true] call OL_fnc_rpcPolicy);
assert (!([true,true,true,"current","current",4,3,true,false,false,true] call OL_fnc_rpcPolicy));
assert (!([true,true,true,"current","old",3,3,true,false,false,true] call OL_fnc_rpcPolicy));
assert (!([true,true,true,"current","current",3,3,true,true,false,true] call OL_fnc_rpcPolicy));
assert (!([true,true,true,"current","current",0,3,true,false,false,true] call OL_fnc_rpcPolicy));
assert (!([true,false,true,"current","current",3,3,true,false,false,true] call OL_fnc_rpcPolicy));
assert ([true,true,true,"current","current",0,2,false,false,true,false] call OL_fnc_rpcPolicy);
assert (!([true,true,true,"current","current",0,2,false,false,true,true] call OL_fnc_rpcPolicy));
assert ([true,true,false,2] call OL_fnc_adminPolicy);
assert (!([true,true,false,1] call OL_fnc_adminPolicy));
assert (!([true,true,false,0] call OL_fnc_adminPolicy));
assert ([false,false,true,0] call OL_fnc_adminPolicy);
assert (!(["extracted",true,true,2,false] call OL_fnc_teamPolicy));
assert (["extracted",true,true,2,true] call OL_fnc_teamPolicy);
assert (!(["operator_killed",false,false,1,false] call OL_fnc_teamPolicy));
assert (["operator_killed",false,false,0,false] call OL_fnc_teamPolicy);
assert ((["extraction",["briefing_complete","recon_reported"]] call OL_fnc_taskStates)
    isEqualTo ["Succeeded","Succeeded","Assigned"]);
assert ((["succeeded",[]] call OL_fnc_taskStates)
    isEqualTo ["Succeeded","Succeeded","Succeeded"]);
assert ((["failed",["briefing_complete","recon_reported"]] call OL_fnc_taskStates)
    isEqualTo ["Succeeded","Succeeded","Failed"]);
assert ([true,true,10,7,"recon"] call OL_fnc_attackPolicy);
assert (!([true,true,10,10,"recon"] call OL_fnc_attackPolicy));
assert (!([false,true,10,7,"recon"] call OL_fnc_attackPolicy));
assert (!([true,false,10,7,"recon"] call OL_fnc_attackPolicy));
assert (!([true,true,10,7,"succeeded"] call OL_fnc_attackPolicy));
diag_log "OVERLORD flow regression passed";
"""
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "flow_test.sqf"
        path.write_text(script)
        result = subprocess.run(
            [str(args.sqfvm.resolve()), "-a", "--suppress-welcome", "--input-sqf", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if (
            result.returncode
            or "[ERR]" in result.stdout
            or "[FAT]" in result.stdout
            or "OVERLORD flow regression passed" not in result.stdout
        ):
            raise RuntimeError(result.stdout + result.stderr)
        print("SQF runtime flow/MP policy regression passed (31 assertions)")


if __name__ == "__main__":
    main()
