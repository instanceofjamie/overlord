# SPDX-License-Identifier: Apache-2.0
"""Optional syntax check with pinned SQF-VM; not an Arma runtime or locality test."""

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sqfvm", type=Path)
    args = parser.parse_args()
    mission = Path(__file__).resolve().parents[1] / "missions/OperationFirstContact.Altis"
    for path in sorted(mission.iterdir()):
        if path.suffix == ".sqf":
            source = ["--input-sqf", str(path)]
        elif path.suffix in {".ext", ".sqm"}:
            # SQF-VM's config parser requires a class root, unlike an Arma mission config.
            source = ["--config", "class SyntaxCheck {\n" + path.read_text() + "\n};"]
        else:
            continue
        result = subprocess.run(
            [str(args.sqfvm.resolve()), "-a", "--suppress-welcome", "--parse-only", *source],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode or "[ERR]" in result.stdout or "[FAT]" in result.stdout:
            raise RuntimeError(f"{path.name}: {result.stdout}\n{result.stderr}")
        print(f"Syntax parsed: {path.name}")


if __name__ == "__main__":
    main()
