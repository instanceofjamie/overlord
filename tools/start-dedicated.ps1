# SPDX-License-Identifier: Apache-2.0
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ArmaPath,
    [string]$BindAddress = '127.0.0.1',
    [ValidateRange(1024,65532)][int]$Port = 2402,
    [string]$DllPath = '',
    [string]$RuntimePath = '',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Server = Join-Path $ArmaPath 'arma3server_x64.exe'
if (-not (Test-Path $Server)) { throw 'Installed arma3server_x64.exe required; no download is performed.' }
$Address = [Net.IPAddress]::Parse($BindAddress)
$Bytes = $Address.GetAddressBytes()
$Private = $BindAddress -eq '127.0.0.1' -or $Bytes[0] -eq 10 -or ($Bytes[0] -eq 192 -and $Bytes[1] -eq 168) -or ($Bytes[0] -eq 172 -and $Bytes[1] -ge 16 -and $Bytes[1] -le 31)
if ($Bytes.Length -ne 4 -or -not $Private) { throw 'Choose loopback or your private LAN IPv4 address. Public/wildcard binding is outside this milestone.' }
# Refuse overlap instead of stopping any existing server or touching its files.
if (Get-Process arma3server* -ErrorAction SilentlyContinue) { throw 'An Arma server is already running. This launcher will not stop or modify it.' }
foreach ($Offset in @(0,1,2,3)) {
    $Probe = [Net.Sockets.UdpClient]::new()
    try { $Probe.ExclusiveAddressUse = $true; $Probe.Client.Bind([Net.IPEndPoint]::new($Address, $Port+$Offset)) }
    finally { $Probe.Dispose() }
}
$TargetMod = Join-Path $ArmaPath '@OVERLORD'
if (-not $DllPath) { $DllPath = Join-Path $TargetMod 'overlord_bridge_x64.dll' }
if (-not (Test-Path $DllPath)) { $DllPath = Join-Path $Root 'build/windows/Release/overlord_bridge_x64.dll' }
if (-not (Test-Path $DllPath)) { $DllPath = Join-Path $Root '@OVERLORD/overlord_bridge_x64.dll' }
if (-not (Test-Path $DllPath)) { throw 'Supply the tested x64 bridge DLL using -DllPath.' }
$InstalledDll = Join-Path $TargetMod 'overlord_bridge_x64.dll'
if ((Test-Path $InstalledDll) -and (Get-FileHash $InstalledDll).Hash -ne (Get-FileHash $DllPath).Hash) { throw 'Installed DLL differs. Back up/update it with Arma closed; launcher will not overwrite it.' }
New-Item -ItemType Directory -Force $TargetMod | Out-Null
if (-not (Test-Path $InstalledDll)) { Copy-Item $DllPath $InstalledDll }
$MissionRoot = Join-Path $ArmaPath 'MPMissions/OverlordLocal'
$TargetMission = Join-Path $MissionRoot 'OperationFirstContact.Altis'
if (Test-Path $TargetMission) { Move-Item $TargetMission ($TargetMission + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')) }
New-Item -ItemType Directory -Force $MissionRoot | Out-Null
Copy-Item (Join-Path $Root 'missions/OperationFirstContact.Altis') $TargetMission -Recurse
if (-not $RuntimePath) { $RuntimePath = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'OVERLORD/dedicated' }
if ($RuntimePath.StartsWith('\\')) { throw 'Use a native Windows runtime/profile path; Arma cache writes failed on a WSL UNC share.' }
$Runtime = $RuntimePath
New-Item -ItemType Directory -Force (Join-Path $Runtime 'profiles') | Out-Null
function New-LocalPassword {
    $Data = New-Object byte[] 24
    $Rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $Rng.GetBytes($Data) } finally { $Rng.Dispose() }
    return [Convert]::ToBase64String($Data).Replace('+','-').Replace('/','_').TrimEnd('=')
}
$JoinPassword = New-LocalPassword
$AdminPassword = New-LocalPassword
$Text = [IO.File]::ReadAllText((Join-Path $Root 'configs/local-dedicated.cfg.example'))
$Text = $Text.Replace('@JOIN_PASSWORD@',$JoinPassword).Replace('@ADMIN_PASSWORD@',$AdminPassword).Replace('@LOOPBACK@',$(if ($BindAddress -eq '127.0.0.1') {'1'} else {'0'}))
$Config = Join-Path $Runtime 'server.cfg'
[IO.File]::WriteAllText($Config,$Text)
Write-Host "Server: $BindAddress`:$Port"
if ($BindAddress -eq '127.0.0.1') {
    Write-Warning 'Loopback mode is for isolated headless probes; player discovery/connectivity is not verified. Use -BindAddress with your private LAN IPv4 address for playtests.'
}
Write-Host "Private join password: $JoinPassword"
Write-Host "Private game-admin login: #login $AdminPassword"
Write-Host 'Director approval is separate: use the private operator panel printed by start-overlord.'
Write-Host 'No router/firewall changes performed. Only the server requires the DLL.'
if ($PrepareOnly) { Write-Host 'Prepared; server not started.'; return }
$Arguments = @("-ip=$BindAddress", "-port=$Port", ('-config="' + $Config + '"'), ('-profiles="' + (Join-Path $Runtime 'profiles') + '"'), '-mpmissions=MPMissions\OverlordLocal', '-mod=@OVERLORD', '-autoInit', '-world=empty', '-noSound', '-limitFPS=30')
$Process = Start-Process -FilePath $Server -WorkingDirectory $ArmaPath -ArgumentList $Arguments -PassThru
Write-Host "Started owned dedicated server PID $($Process.Id). Use its console/admin #shutdown when finished; do not stop WSL."
[IO.File]::WriteAllText((Join-Path $Runtime 'server.pid'),[string]$Process.Id)
