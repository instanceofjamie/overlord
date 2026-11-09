# SPDX-License-Identifier: Apache-2.0
# Exercise installation against a disposable fake game tree, never the real game.
param([Parameter(Mandatory=$true)][string]$DllPath)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ('overlord-install-' + [guid]::NewGuid())
try {
    $Game = Join-Path $TempRoot 'game'
    $Missions = Join-Path $TempRoot 'missions'
    New-Item -ItemType Directory -Path $Game | Out-Null
    New-Item -ItemType File -Path (Join-Path $Game 'arma3_x64.exe') | Out-Null
    & (Join-Path $Root 'tools/install-demo.ps1') -ArmaPath $Game -MissionsPath $Missions -DllPath $DllPath
    $Installed = Join-Path $Game '@OVERLORD/overlord_bridge_x64.dll'
    if ((Get-FileHash $Installed).Hash -ne (Get-FileHash $DllPath).Hash) { throw 'DLL copy differs' }
    foreach ($Name in @('mission.sqm','description.ext','initServer.sqf','initPlayerLocal.sqf','observer.sqf','transport.sqf','executor.sqf')) {
        if (-not (Test-Path (Join-Path $Missions "OperationFirstContact.Altis/$Name"))) { throw "Missing $Name" }
    }
    $Refused = $false
    try { & (Join-Path $Root 'tools/install-demo.ps1') -ArmaPath $Game -MissionsPath $Missions -DllPath $DllPath }
    catch { $Refused = $_.Exception.Message -like 'Destination exists*' }
    if (-not $Refused) { throw 'Installer did not refuse overwrite' }
    Write-Output 'Installer copy and overwrite refusal passed'
} finally {
    if (Test-Path $TempRoot) { Remove-Item -LiteralPath $TempRoot -Recurse -Force }
}
