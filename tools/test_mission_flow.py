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
    script = (
        flow
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
        print("SQF runtime flow regression passed (7 assertions)")


if __name__ == "__main__":
    main()
