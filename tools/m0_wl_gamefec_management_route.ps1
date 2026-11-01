# Only live GitHub runner management IPv4 peers, on their already-owned
# underlay. GameFEC test-only, NO product WAL, route table, or firewall cleanup.
param([Parameter(Mandatory=$true)][ValidateSet('Arm','Restore')][string]$Action,
      [string]$Receipt='result/wl-public/gamefec-management-route-lease.json')
$ErrorActionPreference='Stop'
if($env:WBD_WL_PUBLIC_MODES -notmatch '^game[24]-fec$'){throw 'GAMEFEC_ONLY'}
if($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows'){throw 'HOSTED_WINDOWS_ONLY'}
$owner="$($env:GITHUB_RUN_ID):$($env:GITHUB_RUN_ATTEMPT)"
if($owner -notmatch '^\d{8,15}:\d+$'){throw 'OWNER_ID_MISSING'}
$p=[IO.Path]::GetFullPath($Receipt)
function Save-Lease($v){
 New-Item -ItemType Directory -Force (Split-Path -Parent $p)|Out-Null
 $tmp="$p.tmp"
 [IO.File]::WriteAllText($tmp,($v|ConvertTo-Json -Depth 6))
 Move-Item -LiteralPath $tmp -Destination $p -Force
}
function Exact-Route($prefix,$idx,$gateway){
 return @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $prefix -ErrorAction SilentlyContinue | Where-Object {$_.InterfaceIndex -eq $idx -and $_.NextHop -eq $gateway})
}
function Undo-Lease($v){
 foreach($item in @($v.routes)){
  $prefix=[string]$item.prefix
  if($prefix -notmatch '^\d{1,3}(\.\d{1,3}){3}/32$'){throw 'BAD_HOST_ROUTE'}
  $found=Exact-Route $prefix ([int]$v.interface_index) ([string]$v.next_hop)
  $other=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $prefix -ErrorAction SilentlyContinue | Where-Object {$_.InterfaceIndex -ne [int]$v.interface_index -or $_.NextHop -ne [string]$v.next_hop})
  if($other.Count -or $found.Count -gt 1){throw 'FOREIGN_OR_AMBIGUOUS_HOST_ROUTE'}
  if($found.Count -eq 1){
   Remove-NetRoute -DestinationPrefix $prefix -InterfaceIndex ([int]$v.interface_index) -NextHop ([string]$v.next_hop) -Confirm:$false -ErrorAction Stop
   if((Exact-Route $prefix ([int]$v.interface_index) ([string]$v.next_hop)).Count){throw 'HOST_ROUTE_STILL_PRESENT'}
  }
 }
}
if($Action -eq 'Restore'){
 if(-not (Test-Path -LiteralPath $p)){Write-Output 'GAMEFEC_MGMT_ROUTE_NOT_ARMED';exit 0}
 $lease=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json
 if($lease.schema -ne 'm0-gamefec-management-peers/v1' -or $lease.owner -ne $owner -or $lease.source -ne $env:GITHUB_SHA){throw 'FOREIGN_MANAGEMENT_LEASE'}
 Undo-Lease $lease
 Remove-Item -LiteralPath $p -Force -ErrorAction Stop
 Write-Output 'GAMEFEC_MGMT_ROUTE_EXACT_RESTORE_PASS'
 exit 0
}
if(Test-Path -LiteralPath $p){throw 'EXISTING_MANAGEMENT_LEASE'}
$defaults=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop | Where-Object {$_.NextHop -ne '0.0.0.0' -and $_.InterfaceIndex -gt 0} | Sort-Object RouteMetric)
if($defaults.Count -ne 1){throw 'ORIGINAL_PHYSICAL_UNDERLAY_NOT_UNAMBIGUOUS'}
$d=$defaults[0]
$runner=@(Get-CimInstance Win32_Process -Filter "Name='Runner.Worker.exe' OR Name='Runner.Listener.exe'" | ForEach-Object {[uint32]$_.ProcessId})
if(-not $runner.Count){throw 'RUNNER_MANAGEMENT_PID_NOT_FOUND'}
$targets=@(Get-NetTCPConnection -State Established -ErrorAction Stop | Where-Object {$runner -contains [uint32]$_.OwningProcess} | ForEach-Object {$_.RemoteAddress} | Where-Object {$_ -match '^\d{1,3}(\.\d{1,3}){3}$' -and $_ -notmatch '^(127\.|169\.254\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|0\.)'} | Sort-Object -Unique)
if(-not $targets.Count){throw 'NO_ACTIVE_IPV4_GITHUB_RUNNER_MANAGEMENT'}
foreach($ip in $targets){
 if(@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "$ip/32" -ErrorAction SilentlyContinue).Count){throw 'PREEXISTING_SPECIFIC_HOST_ROUTE'}
}
$lease=[ordered]@{schema='m0-gamefec-management-peers/v1';owner=$owner;source=$env:GITHUB_SHA;interface_index=[int]$d.InterfaceIndex;next_hop=[string]$d.NextHop;routes=@()}
Save-Lease $lease
try{
 foreach($ip in $targets){
  $prefix="$ip/32"
  $lease.routes+=@([ordered]@{prefix=$prefix;state='intent'})
  Save-Lease $lease
  New-NetRoute -DestinationPrefix $prefix -InterfaceIndex ([int]$d.InterfaceIndex) -NextHop ([string]$d.NextHop) -RouteMetric 1 -PolicyStore ActiveStore -ErrorAction Stop|Out-Null
  if((Exact-Route $prefix ([int]$d.InterfaceIndex) ([string]$d.NextHop)).Count -ne 1){throw 'MANAGEMENT_HOST_ROUTE_READBACK_FAIL'}
  $lease.routes[-1].state='owned'
  Save-Lease $lease
 }
 Write-Output ('GAMEFEC_MGMT_PEERS_PINNED_UNDERLAY count='+$targets.Count)
}catch{
 try{Undo-Lease $lease;Remove-Item -LiteralPath $p -Force}
 catch{Write-Output 'GAMEFEC_MANAGEMENT_ROLLBACK_UNVERIFIED_RECEIPT_RETAINED'}
 throw
}
