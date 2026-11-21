# H2286 real Windows signed Npcap original Go/Rust FakeTCP single Windows WSL2 vEthernet owner.
# Only its one source/guest TCP443 tuple is allowed. Never disable firewall/default.
param([Parameter(Mandatory=$true)][ValidateSet("Install","Cleanup")][string]$Action,
      [string]$StatePath="h2286-out\windows-vethernet-owner.json")
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Clean {
    if(-not(Test-Path $StatePath)){Write-Output 'H2286_WSL_VETH_OWNER_NO_STATE';return}
    $s=Get-Content $StatePath -Raw | ConvertFrom-Json
    if($s.source_sha -ne $env:GITHUB_SHA -or $s.run_id -ne $env:GITHUB_RUN_ID -or $s.group -ne $env:GROUP){throw 'H2286_CLEAN_REFUSES_FOREIGN_OWNER'}
    if($s.neighbor_installed -eq $true){
        & netsh.exe interface ipv4 delete neighbors "interface=$($s.interface_index)" "address=$($s.guest_ip)" "store=active"
        if($LASTEXITCODE -ne 0){throw 'H2286_NEIGHBOR_DELETE_FAILED'}
    }
    if($s.hyperv_rule_installed -eq $true){
        Remove-NetFirewallHyperVRule -Name $s.rule_name -ErrorAction Stop
        if(Get-NetFirewallHyperVRule -Name $s.rule_name -ErrorAction SilentlyContinue){throw 'H2286_HYPERV_OWNED_RULE_SURVIVED'}
    }
    Remove-Item -LiteralPath $StatePath -Force
    Write-Output 'H2286_REAL_WSL2_ORIGINAL_NPCAP_HYPERV_AND_MAC_OWNER_CLEANED'
}
if($Action -eq "Cleanup"){Clean;exit 0}
if(Test-Path $StatePath){throw 'H2286_OWNER_EXISTS_REFUSE_OVERWRITE'}
$known=(& wsl.exe -d Ubuntu -u root -- ip -4 -o addr show dev eth0 | Out-String)
$m=[regex]::Match($known,'\binet\s+(\d{1,3}(?:\.\d{1,3}){3})/')
if(-not $m.Success){throw 'H2286_REAL_GUEST_IPV4_ABSENT'}
$guest=$m.Groups[1].Value
$nics=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object {$_.Name -match '^vEthernet \(WSL' -and $_.Status -eq 'Up'})
if($nics.Count -ne 1){throw 'H2286_REAL_WSL_VETHERNET_AMBIGUOUS'}
$nic=$nics[0]
$sources=@(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $nic.InterfaceIndex -ErrorAction Stop | Where-Object {$_.IPAddress -notmatch '^169\.254\.'})
if($sources.Count -ne 1){throw 'H2286_WINDOWS_REAL_VETH_IP_AMBIGUOUS'}
$hostIP=[string]$sources[0].IPAddress
$linuxMacInfo=@(& wsl.exe -d Ubuntu -u root -- ip -j link show dev eth0 | ConvertFrom-Json)
if($linuxMacInfo.Count -ne 1){throw 'H2286_REAL_LINUX_ETH0_MAC_MISSING'}
$mac=[string]$linuxMacInfo[0].address
if(@($mac.Split(':')).Count -ne 6){throw 'H2286_REAL_LINUX_ETH0_MAC_BAD'}
$existing=@(Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex $nic.InterfaceIndex -IPAddress $guest -ErrorAction SilentlyContinue)
if(@($existing | Where-Object {$_.State -eq 'Permanent'}).Count -gt 0){throw 'H2286_FOREIGN_PERMANENT_NEIGHBOR'}
$creator=@(Get-NetFirewallHyperVVMCreator -ErrorAction Stop | Where-Object {$_.FriendlyName -eq 'WSL'})
if($creator.Count -ne 1){throw 'H2286_WSL_HYPERV_CREATOR_NOT_UNIQUE'}
$name='WBD-H2286-'+$env:GITHUB_RUN_ID+'-'+$env:GROUP
if(Get-NetFirewallHyperVRule -Name $name -ErrorAction SilentlyContinue){throw 'H2286_FOREIGN_RULE_EXISTS'}
$state=[ordered]@{source_sha=$env:GITHUB_SHA;run_id=$env:GITHUB_RUN_ID;group=$env:GROUP;
  rule_name=$name;guest_ip=$guest;host_ip=$hostIP;guest_mac=$mac;
  interface_index=[int]$nic.InterfaceIndex;neighbor_installed=$false;hyperv_rule_installed=$false;
  scope='ORIGINAL_SIGNED_NPCAP_WINDOWS_ETHERNET_TO_WSL_KERNEL_FWD_TO_ARM'}
New-Item -ItemType Directory -Force (Split-Path $StatePath -Parent) | Out-Null
$state|ConvertTo-Json -Depth 4|Set-Content $StatePath
try{
    New-NetFirewallHyperVRule -Name $name -DisplayName $name -Direction Inbound -Action Allow -Enabled True -Profiles Any -VMCreatorId $creator[0].VMCreatorId -Protocol TCP -LocalAddresses $guest -RemoteAddresses $hostIP -LocalPorts 443 -RemotePorts 41031 -ErrorAction Stop | Out-Null
    $state.hyperv_rule_installed=$true
    $state|ConvertTo-Json -Depth 4|Set-Content $StatePath
    & netsh.exe interface ipv4 set neighbors "interface=$($nic.InterfaceIndex)" "address=$guest" "neighbor=$($mac.Replace(':','-'))" "store=active"
    if($LASTEXITCODE -ne 0){throw 'H2286_WSL_NEIGHBOR_OWNER_INSTALL_FAIL'}
    $state.neighbor_installed=$true
    $state|ConvertTo-Json -Depth 4|Set-Content $StatePath
    $neighbor=@(Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex $nic.InterfaceIndex -IPAddress $guest -ErrorAction Stop)
    if($neighbor.Count -ne 1 -or $neighbor[0].LinkLayerAddress.Replace('-',':') -ne $mac){throw 'H2286_WSL_NEIGHBOR_REAL_MAC_READBACK_MISMATCH'}
    $fire=Get-NetFirewallHyperVRule -Name $name -ErrorAction Stop
    if($fire.Direction -ne 'Inbound' -or $fire.Action -ne 'Allow'){throw 'H2286_REAL_HYPERV_443_RULE_READBACK_BAD'}
    Write-Output "H2286_REAL_NPCAP_WSL_GUEST_MAC_FIREWALL_OWNER_PASS host=$hostIP guest=$guest"
}catch{
    Clean
    throw
}
