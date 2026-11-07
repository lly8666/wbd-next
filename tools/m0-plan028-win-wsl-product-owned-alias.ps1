param(
 [Parameter(Mandatory=$true)][ValidateSet('Prepare','Switch','ShrinkMTU','Restore')][string]$Action,
 [string]$Receipt='result/wl-public/plan028-owned-alias.json'
)
$ErrorActionPreference='Stop'
$guest='198.19.254.2';$old='198.19.254.1';$new='198.19.254.9'
function Guest([string[]]$cmd) {
 & python tools/m0_wl_windows_bounded_cmd.py 35 wsl.exe -d Ubuntu -u root -- @cmd
 if($LASTEXITCODE -ne 0){throw ('real WSL2 native command failed: '+($cmd -join ' '))}
}
function Pick([uint32]$idx,[string]$want) {
 for($i=0;$i -lt 65;$i++) {
  try {$r=@(Find-NetRoute -RemoteIPAddress $guest -ErrorAction Stop | Where-Object {$_.InterfaceIndex -eq $idx -and $_.IPAddress -eq $want})}
  catch {$r=@()}
  if($r.Count -gt 0){return $r[0]}
  Start-Sleep -Milliseconds 100
 }
 throw ('original Windows GetBestRoute did not select owned '+$want)
}
function PhysicalMTU([uint32]$idx){
 $v=@(Get-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction Stop)
 if($v.Count -ne 1 -or [int]$v[0].NlMtuBytes -lt 576){throw 'real OS physical IPv4 NlMtu invalid'}
 return [int]$v[0].NlMtuBytes
}
function DefaultFingerprint(){
 return @((Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 -ErrorAction Stop |
   ForEach-Object {"$($_.InterfaceIndex)|$($_.NextHop)|$($_.RouteMetric)"} | Sort-Object))
}
if($Action -eq 'Prepare') {
 if(Test-Path -LiteralPath $Receipt){throw 'duplicate owned alias receipt refused'}
 $nic=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.Name -match '^vEthernet \(WSL' -and $_.Status -eq 'Up'})
 if($nic.Count -ne 1){throw 'one genuine WSL underlay required'}
 $idx=[uint32]$nic[0].InterfaceIndex
 if(@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 | Where-Object {$_.InterfaceIndex -eq $idx}).Count){throw 'WSL underlay also management default NIC; refuse'}
 foreach($ip in @($guest,$old,$new)){
  if(@(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $ip -ErrorAction SilentlyContinue).Count){throw ('owned source already in use '+$ip)}
 }
 $before=(Guest @('ip','-4','-o','addr','show','dev','eth0') | Out-String)
 if($before -match [regex]::Escape($guest)){throw 'foreign guest IPv4 alias'}
 $originalMTU=PhysicalMTU $idx
 $data=[ordered]@{owner='PLAN028_TEST_ONLY';source_sha=$env:GITHUB_SHA;wsl_host_ifindex=$idx;guest4=$guest;host_source_old=$old;host_source_new=$new;default_before=(DefaultFingerprint);stage='INIT';guest_created=$false;old_created=$false;new_created=$false;physical_ipv4_mtu_original=$originalMTU;mtu_shrink_started=$false;mtu_original_restored=$false}
 $data|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
 try {
  Guest @('ip','addr','add',($guest+'/24'),'dev','eth0')|Out-Null
  $data.guest_created=$true
  $data|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
  New-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -IPAddress $old -PrefixLength 24 -SkipAsSource $false -ErrorAction Stop|Out-Null
  $data.old_created=$true
  [void](Pick $idx $old)
  $data.stage='PREPARED'
  $data|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
  Write-Output 'M0_PLAN028_OWNED_WINDOWS_WSL2_UNDERLAY_PREPARED_REAL_OS_SOURCE4'
 }catch {
  $data.stage='PREPARE_FAIL'
  $data|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
  throw
 }
 exit 0
}
if(-not(Test-Path -LiteralPath $Receipt)){throw 'missing owned session receipt'}
$d=Get-Content $Receipt -Raw|ConvertFrom-Json
if($d.owner -ne 'PLAN028_TEST_ONLY' -or $d.guest4 -ne $guest -or $d.host_source_old -ne $old -or $d.host_source_new -ne $new){throw 'foreign or corrupted source4 receipt'}
$idx=[uint32]$d.wsl_host_ifindex
if($Action -eq 'Switch'){
 if($d.stage -ne 'PREPARED'){throw 'physical source4 switch requires prepared owned route'}
 New-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -IPAddress $new -PrefixLength 24 -SkipAsSource $false -ErrorAction Stop|Out-Null
 $d.new_created=$true
 $d.stage='NEW_ADDRESS_ADDED'
 $d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
 $changed=[DateTimeOffset]::UtcNow
 Set-NetIPAddress -InterfaceIndex $idx -IPAddress $old -SkipAsSource $true -ErrorAction Stop
 [void](Pick $idx $new)
 $d.stage='SWITCHED'
 $d|Add-Member -NotePropertyName native_source4_after -NotePropertyValue $new -Force
 $d|Add-Member -NotePropertyName test_owned_source4_mutation_to_OS_selected_ms -NotePropertyValue ([math]::Round(([DateTimeOffset]::UtcNow-$changed).TotalMilliseconds,2)) -Force
 $d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
 Write-Output 'M0_PLAN028_WINDOWS_REAL_OWNED_WSL2_SOURCE4_CHANGED_AND_SELECTED'
 exit 0
}
if($Action -eq 'ShrinkMTU'){
 if($d.stage -ne 'PREPARED'){throw 'MTU-only event requires prepared owned Windows WSL2 underlay'}
 $iface=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop |
   Where-Object {$_.InterfaceIndex -eq $idx -and $_.Name -match '^vEthernet \(WSL' -and $_.Status -eq 'Up'})
 if($iface.Count -ne 1){throw 'physical WSL NIC changed before test-owned MTU event'}
 if(@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 |
   Where-Object {$_.InterfaceIndex -eq $idx}).Count){throw 'refuse MTU change on runner management default NIC'}
 $before=PhysicalMTU $idx
 if($before -ne [int]$d.physical_ipv4_mtu_original -or $before -ne 1500){
  throw ('owned Windows NIC baseline not 1500, host-dependent precondition: '+$before)
 }
 [void](Pick $idx $old)
 $d.mtu_shrink_started=$true
 $d.stage='MTU_SHRINK_ARMED'
 $d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
 $stamp=[DateTimeOffset]::UtcNow
 Set-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4 -NlMtuBytes 1280 -ErrorAction Stop
 $readback=PhysicalMTU $idx
 if($readback -ne 1280){throw ('real kernel MTU narrowing not applied; readback='+$readback)}
 [void](Pick $idx $old)
 $d.stage='MTU_SHRUNK'
 $d|Add-Member -NotePropertyName mtu_only_source4_after -NotePropertyValue $old -Force
 $d|Add-Member -NotePropertyName physical_ipv4_mtu_after -NotePropertyValue $readback -Force
 $d|Add-Member -NotePropertyName mutation_to_OS_mtu_readback_ms -NotePropertyValue ([math]::Round(([DateTimeOffset]::UtcNow-$stamp).TotalMilliseconds,2)) -Force
 $d|Add-Member -NotePropertyName OS_mtu_event_unix_ms -NotePropertyValue $stamp.ToUnixTimeMilliseconds() -Force
 $d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
 Write-Output 'M0_PLAN028_WINDOWS_REAL_OWNED_WSL2_SAME_IP_PHYSICAL_MTU_1500_TO_1280_OS_READBACK'
 exit 0
}
# Restore only our original two Windows addresses and one guest alias.
# No generic interface reset, no DNS changes or runner route mutation.
# Restore the recorded IPv4 NlMtu only for this exact owned WSL NIC,
# even if the native product exits unexpectedly.
if($d.mtu_shrink_started){
 $iface=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop |
   Where-Object {$_.InterfaceIndex -eq $idx -and $_.Name -match '^vEthernet \(WSL'})
 if($iface.Count -ne 1){throw 'owned MTU restoration refused: physical NIC identity changed'}
 $original=[int]$d.physical_ipv4_mtu_original
 if($original -ne 1500){throw 'owned MTU restoration refused: baseline was not 1500'}
 Set-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4 -NlMtuBytes $original -ErrorAction Stop
 if((PhysicalMTU $idx) -ne $original){throw 'Windows WSL original NlMtu restore readback failed'}
 $d.mtu_original_restored=$true
 $d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
}
if($d.new_created){Remove-NetIPAddress -InterfaceIndex $idx -IPAddress $new -Confirm:$false -ErrorAction SilentlyContinue}
if($d.old_created){Remove-NetIPAddress -InterfaceIndex $idx -IPAddress $old -Confirm:$false -ErrorAction SilentlyContinue}
if($d.guest_created){Guest @('ip','addr','del',($guest+'/24'),'dev','eth0')|Out-Null}
$now=DefaultFingerprint
if($null -ne (Compare-Object -ReferenceObject @($d.default_before) -DifferenceObject $now)){throw 'runner default route changed outside test-owned area'}
$d.stage='RESTORED'
$d|Add-Member -NotePropertyName test_owned_aliases_restored -NotePropertyValue $true -Force
$d|Add-Member -NotePropertyName runner_default_route_unchanged -NotePropertyValue $true -Force
$d|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $Receipt -Encoding utf8
Write-Output 'M0_PLAN028_WINDOWS_WSL2_TEST_OWNED_IPV4_ALIASES_CLEANED'
