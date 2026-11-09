# SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $Root '.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Python environment missing. Complete the one-time Windows setup in docs/local-demo.md, in the repository clone.' }
Set-Location $Root
& $Python -m overlord.cli
if ($LASTEXITCODE -ne 0) { throw 'OVERLORD stopped with an error. Check this terminal.' }
