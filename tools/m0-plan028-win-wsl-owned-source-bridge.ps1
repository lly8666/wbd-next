$ErrorActionPreference='Stop'
$dir='result/plan028-win-wsl-owned'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$a='198.19.254.1'; $b='198.19.254.9'; $guest='198.19.254.2'
$ruleName='WBD-P028-WSL-'+$env:GITHUB_RUN_ID
$receipt=[ordered]@{scope='WINDOWS_WSL2_OWNED_IPv4_SOURCE_AND_REAL_UDP_PREPRODUCT';source_sha=$env:GITHUB_SHA;status='NOT_RUN';source_before=$null;source_after=$null;udp_before=$false;udp_after=$false;original_wsl_host_ipv4_untouched=$true;original_wsl_guest_ipv4_untouched=$true;runner_default_route_unchanged=$false;npcap_tls='NOT_RUN';wintun_rust='NOT_RUN';cpu_p99='NOT_MEASURED'}
$orig=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | ForEach-Object {"$($_.InterfaceIndex)|$($_.NextHop)|$($_.RouteMetric)"} | Sort-Object)
$idx=$null;$addedA=$false;$addedB=$false;$addedGuest=$false;$rule=$null;$process=$null
function Guest([string[]]$cmd) {
  & python tools/m0_wl_windows_bounded_cmd.py 40 wsl.exe -d Ubuntu -u root -- @cmd
  if($LASTEXITCODE -ne 0){throw ('WSL guest command failed: '+($cmd -join ' '))}
}
function RouteSource([string]$source,[uint32]$index){
  for($i=0;$i -lt 65;$i++){
    try {$match=@(Find-NetRoute -RemoteIPAddress '198.19.254.2' -ErrorAction Stop | Where-Object {$_.InterfaceIndex -eq $index -and $_.IPAddress -eq $source})}
    catch {$match=@();$receipt.last_transient_error=$_.Exception.Message}
    if($match.Count -gt 0){return $match[0]}
    Start-Sleep -Milliseconds 100
  }
  throw ('Windows selected WSL route did not use test-owned IPv4 '+$source)
}
function Echo([string]$source,[string]$label){
  $client=[Net.Sockets.UdpClient]::new([Net.IPEndPoint]::new([Net.IPAddress]::Parse($source),0))
  try {
    $client.Client.ReceiveTimeout=1100
    $msg=[Text.Encoding]::ASCII.GetBytes('WBD-PLAN028-REAL-'+$label)
    $expected='WBD-ECHO-WBD-PLAN028-REAL-'+$label
    for($i=0;$i -lt 35;$i++){
      [void]$client.Send($msg,$msg.Length,$guest,45941)
      try {
        $from=[Net.IPEndPoint]::new([Net.IPAddress]::Any,0)
        $reply=$client.Receive([ref]$from)
        if($from.Address.ToString() -eq $guest -and [Text.Encoding]::ASCII.GetString($reply) -eq $expected){return $true}
      }catch [Net.Sockets.SocketException]{}
      Start-Sleep -Milliseconds 150
    }
    throw ('Real native UDP through WSL2 not returned for '+$label)
  }finally{$client.Dispose()}
}
try {
  $nic=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.Name -match '^vEthernet \(WSL' -and $_.Status -eq 'Up'})
  if($nic.Count -ne 1){throw 'WSL2 host virtual network interface not unique/up'}
  $idx=[uint32]$nic[0].InterfaceIndex
  if(@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 | Where-Object {$_.InterfaceIndex -eq $idx}).Count -gt 0){throw 'Cannot alter runner management default route NIC'}
  $receipt.real_wsl_host_adapter=$nic[0].Name
  foreach($x in @($a,$b)){
    if(@(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $x -ErrorAction SilentlyContinue).Count){throw ('Owned host alias already exists: '+$x)}
  }
  $guestOrig=(Guest @('ip','-4','-o','addr','show','dev','eth0') | Out-String)
  if($guestOrig -match [regex]::Escape($guest)){throw 'Guest address occupied by foreign owner'}
  Guest @('ip','addr','add',($guest+'/24'),'dev','eth0') | Out-Null
  $addedGuest=$true
  New-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -IPAddress $a -PrefixLength 24 -SkipAsSource $false -ErrorAction Stop | Out-Null
  $addedA=$true
  $receipt.source_before=[string](RouteSource $a $idx).IPAddress
  $creator=@(Get-NetFirewallHyperVVMCreator -ErrorAction Stop | Where-Object {$_.FriendlyName -eq 'WSL'})
  if($creator.Count -ne 1){throw 'WSL HyperV firewall creator ambiguous'}
  if(Get-NetFirewallHyperVRule -Name $ruleName -ErrorAction SilentlyContinue){throw 'Foreign firewall rule name collision'}
  New-NetFirewallHyperVRule -Name $ruleName -DisplayName $ruleName -Direction Inbound -Action Allow -Enabled True -Profiles Any -VMCreatorId $creator[0].VMCreatorId -Protocol UDP -LocalAddresses $guest -RemoteAddresses @($a,$b) -LocalPorts 45941 -ErrorAction Stop | Out-Null
  $rule=$ruleName
  $py=Join-Path $dir 'echo-server.py'
  @'
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("198.19.254.2",45941))
s.settimeout(65)
try:
 for _ in range(30):
  b,src=s.recvfrom(2048)
  if b.startswith(b"WBD-PLAN028-REAL-"):
   s.sendto(b"WBD-ECHO-"+b,src)
finally:s.close()
'@ | Set-Content -Encoding utf8 $py
  $drive=$PWD.Path.Substring(0,1).ToLowerInvariant()
  $unix='/mnt/'+$drive+'/'+$PWD.Path.Substring(3).Replace('\','/')+'/'+$py.Replace('\','/')
  $process=Start-Process -FilePath wsl.exe -ArgumentList @('-d','Ubuntu','-u','root','--','python3','-u',$unix) -PassThru -RedirectStandardError (Join-Path $dir 'echo-error.log') -RedirectStandardOutput (Join-Path $dir 'echo-out.log')
  $receipt.udp_before=[bool](Echo $a 'BEFORE')
  $started=[DateTimeOffset]::UtcNow
  New-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -IPAddress $b -PrefixLength 24 -SkipAsSource $false -ErrorAction Stop | Out-Null
  $addedB=$true
  Set-NetIPAddress -InterfaceIndex $idx -IPAddress $a -SkipAsSource $true -ErrorAction Stop
  $receipt.source_after=[string](RouteSource $b $idx).IPAddress
  $receipt.udp_after=[bool](Echo $b 'AFTER')
  $receipt.mutation_to_OS_source_and_real_UDP_ms=[math]::Round(([DateTimeOffset]::UtcNow-$started).TotalMilliseconds,2)
  $receipt.status='PASS_TEST_OWNED_WINDOWS_WSL2_TWO_SOURCE_REAL_UDP_ONLY'
  Write-Output 'M0_PLAN028_WINDOWS_WSL2_TEST_OWNED_DUAL_SOURCE_REAL_UDP_PASS_NOT_NPCAP'
}catch{
  $receipt.status='FAIL_SCOPED_PREPRODUCT_WINDOWS_WSL2_UNDERLAY'
  $receipt.error=$_.Exception.Message
  throw
}finally{
  if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}
  if($rule){Remove-NetFirewallHyperVRule -Name $rule -ErrorAction SilentlyContinue}
  if($idx -and $addedB){Remove-NetIPAddress -InterfaceIndex $idx -IPAddress $b -Confirm:$false -ErrorAction SilentlyContinue}
  if($idx -and $addedA){Remove-NetIPAddress -InterfaceIndex $idx -IPAddress $a -Confirm:$false -ErrorAction SilentlyContinue}
  if($addedGuest){try {Guest @('ip','addr','del',($guest+'/24'),'dev','eth0') | Out-Null} catch {$receipt.guest_owned_cleanup_error=$_.Exception.Message}}
  $now=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | ForEach-Object {"$($_.InterfaceIndex)|$($_.NextHop)|$($_.RouteMetric)"} | Sort-Object)
  $receipt.runner_default_route_unchanged=($null -eq (Compare-Object -ReferenceObject $orig -DifferenceObject $now))
  $receipt.owned_cleanup_attempted=$true
  $receipt | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $dir 'dual-source-native.json')
  Get-Content (Join-Path $dir 'dual-source-native.json')
}
