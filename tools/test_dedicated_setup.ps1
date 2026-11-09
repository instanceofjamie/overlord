# SPDX-License-Identifier: Apache-2.0
param([Parameter(Mandatory=$true)][string]$DllPath)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ('overlord-dedicated-' + [guid]::NewGuid())
try {
    $Game = Join-Path $TempRoot 'game'
    $Runtime = Join-Path $TempRoot 'runtime'
    New-Item -ItemType Directory -Force $Game | Out-Null
    New-Item -ItemType File (Join-Path $Game 'arma3server_x64.exe') | Out-Null
    & (Join-Path $Root 'tools/start-dedicated.ps1') -ArmaPath $Game -RuntimePath $Runtime -DllPath $DllPath -Port 26300 -PrepareOnly | Out-Null
    $Mission = Join-Path $Game 'MPMissions/OverlordLocal/OperationFirstContact.Altis'
    foreach ($Name in @('mission.sqm','description.ext','policy.sqf','network.sqf','operation.sqf','initPlayerLocal.sqf')) {
        if ((Get-FileHash (Join-Path $Mission $Name)).Hash -ne (Get-FileHash (Join-Path $Root "missions/OperationFirstContact.Altis/$Name")).Hash) { throw "Mission copy mismatch: $Name" }
    }
    $Config = [IO.File]::ReadAllText((Join-Path $Runtime 'server.cfg'))
    if ($Config.Contains('@JOIN_PASSWORD@') -or $Config.Contains('@ADMIN_PASSWORD@')) { throw 'Unexpanded secret placeholders' }
    $Passwords = [regex]::Matches($Config,'password(?:Admin)? = "([A-Za-z0-9_-]+)"')
    if ($Passwords.Count -ne 2 -or $Passwords[0].Groups[1].Value -eq $Passwords[1].Groups[1].Value) { throw 'Separate private join/admin credentials required' }
    if (Test-Path (Join-Path $Runtime 'server.pid')) { throw 'PrepareOnly unexpectedly started a process' }
    $Rejected = $false
    try { & (Join-Path $Root 'tools/start-dedicated.ps1') -ArmaPath $Game -RuntimePath $Runtime -BindAddress '0.0.0.0' -PrepareOnly | Out-Null }
    catch { $Rejected = $_.Exception.Message -like '*Public/wildcard*' }
    if (-not $Rejected) { throw 'Wildcard/public binding was not rejected' }
    Write-Output 'Dedicated setup: isolated files, private separate credentials, no process in PrepareOnly, public binding rejection passed'
} finally {
    if (Test-Path $TempRoot) { Remove-Item -LiteralPath $TempRoot -Recurse -Force }
}
