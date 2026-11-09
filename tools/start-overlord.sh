#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
if [[ ! -x .venv/bin/python ]]; then
    echo 'Project environment missing. Complete the one-time setup in docs/local-demo.md.' >&2
    exit 1
fi
exec .venv/bin/python -m overlord.cli
