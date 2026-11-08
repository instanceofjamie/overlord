# SPDX-License-Identifier: Apache-2.0
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ArmaPath,
    [string]$MissionsPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Arma 3\missions'),
    [string]$DllPath = ''
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $ArmaPath 'arma3_x64.exe'))) { throw 'ArmaPath must contain arma3_x64.exe' }
if (-not $DllPath) {
    $DllPath = Join-Path $Root '@OVERLORD\overlord_bridge_x64.dll'
    if (-not (Test-Path $DllPath)) { $DllPath = Join-Path $Root 'build\windows\Release\overlord_bridge_x64.dll' }
}
if (-not (Test-Path $DllPath)) { throw 'Build the x64 DLL first, or use the Windows demo artifact.' }
$MissionTarget = Join-Path $MissionsPath 'OperationFirstContact.Altis'
$ModTarget = Join-Path $ArmaPath '@OVERLORD'
# Avoid silently overwriting an Eden-edited mission or an existing mod.
if ((Test-Path $MissionTarget) -or (Test-Path $ModTarget)) { throw 'Destination exists. Back it up and remove it, or choose another path before installing.' }
New-Item -ItemType Directory -Force -Path $MissionsPath | Out-Null
New-Item -ItemType Directory -Path $ModTarget | Out-Null
Copy-Item $DllPath (Join-Path $ModTarget 'overlord_bridge_x64.dll')
Copy-Item (Join-Path $Root 'missions\OperationFirstContact.Altis') $MissionTarget -Recurse
Write-Host "Mission installed: $MissionTarget"
Write-Host "Extension installed: $ModTarget"
Write-Host 'Start Arma x64 with BattlEye disabled and -mod=@OVERLORD. See docs/local-demo.md.'
