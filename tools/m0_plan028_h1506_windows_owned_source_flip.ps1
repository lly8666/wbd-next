param(
 [Parameter(Mandatory=$true)][ValidateSet('Flip')][string]$Action,
 [Parameter(Mandatory=$true)][string]$Receipt,
 [Parameter(Mandatory=$true)][ValidateSet('198.19.254.1','198.19.254.9')][string]$ExpectedCurrent
)
$ErrorActionPreference='Stop'
# Only original H1385/H1506 owned WSL vEthernet aliases after real
# Prepare+Switch. Flip is a GENUINE Windows kernel route/source change,
# not a simulated Rust callback, artificial M4 event or lane DATA copy.
$d=Get-Content -LiteralPath $Receipt -Raw|ConvertFrom-Json
if($d.owner -ne 'PLAN028_TEST_ONLY' -or $d.source_sha -ne $env:GITHUB_SHA -or
   $d.stage -ne 'SWITCHED' -or -not $d.new_created -or -not $d.old_created -or
   $d.host_source_old -ne '198.19.254.1' -or
   $d.host_source_new -ne '198.19.254.9' -or
   $d.guest4 -ne '198.19.254.2'){throw 'H1506 foreign/not fully owned physical alias scope'}
$idx=[uint32]$d.wsl_host_ifindex
$nic=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop |
  Where-Object {$_.InterfaceIndex -eq $idx -and $_.Name -match '^vEthernet \(WSL' -and $_.Status -eq 'Up'})
if($nic.Count -ne 1){throw 'H1506 native WSL source link identity changed'}
if(@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4|
    Where-Object {$_.InterfaceIndex -eq $idx}).Count){throw 'H1506 refuse runner management default NIC change'}
$expected=$ExpectedCurrent
$next=if($expected -eq '198.19.254.1'){'198.19.254.9'}else{'198.19.254.1'}
$before=@(Find-NetRoute -RemoteIPAddress $d.guest4 -ErrorAction Stop |
  Where-Object {$_.InterfaceIndex -eq $idx -and $_.IPAddress -eq $expected})
if($before.Count -lt 1){throw 'H1506 old physical source not actually selected'}
$begin=[DateTimeOffset]::UtcNow
Set-NetIPAddress -InterfaceIndex $idx -IPAddress $next -SkipAsSource $false -ErrorAction Stop
Set-NetIPAddress -InterfaceIndex $idx -IPAddress $expected -SkipAsSource $true -ErrorAction Stop
$selected=@()
for($i=0;$i -lt 80;$i++){
  $selected=@(Find-NetRoute -RemoteIPAddress $d.guest4 -ErrorAction SilentlyContinue |
    Where-Object {$_.InterfaceIndex -eq $idx -and $_.IPAddress -eq $next})
  if($selected.Count -ge 1){break}
  Start-Sleep -Milliseconds 100
}
if($selected.Count -lt 1){throw 'H1506 real Windows OS route failed to select new source'}
$d|Add-Member -NotePropertyName native_source4_after -NotePropertyValue $next -Force
$d|Add-Member -NotePropertyName last_h1506_actual_physical_rebound_unix_ms -NotePropertyValue ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) -Force
$d|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $Receipt -Encoding utf8
$elapsed=([DateTimeOffset]::UtcNow-$begin).TotalMilliseconds
Write-Output ('H1506_REAL_WINDOWS_OS_SOURCE_SELECTED path='+$expected+'->'+$next+' elapsed_ms='+[Math]::Round($elapsed,3))
