$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
New-Item -ItemType Directory -Force h2228-meta,h2442-out,h2228-peer | Out-Null
# WSL2 is a forwarding access router only. No WBD binary or TCP receiver in it.
& wsl.exe -d Ubuntu -u root -- bash -lc 'set -e; apt-get update -qq; apt-get install -y -qq curl ca-certificates iproute2 iptables; curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg; curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list; apt-get update -qq; apt-get install -y -qq tailscale; if ! tailscale status >/dev/null 2>&1; then nohup tailscaled --state=mem: >/tmp/h2442-tailscaled.log 2>&1 </dev/null & sleep 3; fi'
if($LASTEXITCODE -ne 0){throw 'WSL gateway tailscale install failed'}
$uri=$env:ACTIONS_ID_TOKEN_REQUEST_URL+'&audience='+[uri]::EscapeDataString($env:TS_AUD)
$jwt=(Invoke-RestMethod -Uri $uri -Headers @{Authorization=('Bearer '+$env:ACTIONS_ID_TOKEN_REQUEST_TOKEN)}).value
Write-Output "::add-mask::$jwt"
& wsl.exe -d Ubuntu -u root -- tailscale up "--client-id=$($env:TS_ID)?preauthorized=true&ephemeral=true" "--id-token=$jwt" --advertise-tags=tag:ci "--hostname=h2442-win-gateway-$env:GITHUB_RUN_ID" --accept-routes --timeout=90s
if($LASTEXITCODE -ne 0){throw 'WSL gateway OIDC tailnet failed'}
$jwt=$null
$guest=((& wsl.exe -d Ubuntu -u root -- ip -4 -o addr show dev eth0 | Out-String) -replace '[\x00]','')
$ip=[regex]::Match($guest,'\binet (\d+(?:\.\d+){3})/').Groups[1].Value
if(!$ip){throw 'WSL guest address unavailable'}
$route=Find-NetRoute -RemoteIPAddress $ip
$addr=@($route | Where-Object {$_.IPAddress -and $_.InterfaceIndex}) | Select-Object -First 1
if(!$addr -or $addr.IPAddress -eq $ip){throw 'Windows native access route missing'}
$hostip=$addr.IPAddress;$idx=$addr.InterfaceIndex
if(Get-NetRoute -DestinationPrefix '10.248.82.2/32' -ErrorAction SilentlyContinue){throw 'foreign exact route'}
New-NetRoute -DestinationPrefix '10.248.82.2/32' -InterfaceIndex $idx -NextHop $ip -PolicyStore ActiveStore | Out-Null
@{guest=$ip;host=$hostip;index=$idx;route='10.248.82.2/32'} | ConvertTo-Json | Set-Content -Encoding utf8 h2442-out/windows-access.json
$creator=@(Get-NetFirewallHyperVVMCreator -ErrorAction Stop | Where-Object {$_.FriendlyName -eq 'WSL'})
if($creator.Count -ne 1){throw 'WSL HyperV creator not uniquely owned'}
$name='WBD-H2442-'+$env:GITHUB_RUN_ID
New-NetFirewallHyperVRule -Name $name -DisplayName $name -Direction Inbound -Action Allow -Enabled True -Profiles Any -VMCreatorId $creator[0].VMCreatorId -Protocol TCP -RemoteAddresses @($hostip) -LocalAddresses @('10.248.82.2') -LocalPorts @('443','5202') -ErrorAction Stop | Out-Null
$path=((& wsl.exe -d Ubuntu -u root -- wslpath -a "$pwd" | Out-String).Trim())
& wsl.exe -d Ubuntu -u root -- env "GITHUB_SHA=$env:GITHUB_SHA" "GITHUB_RUN_ID=$env:GITHUB_RUN_ID" WBD_H2417_SPLICE=1 WBD_H2418_DIAG=1 WBD_H2442_ARM_SERVER=1 python3 "$path/tools/m0_h2442_topology.py" client-meta "$path/h2228-meta/client.json" $hostip
if($LASTEXITCODE -ne 0){throw 'actual Windows gateway metadata failed'}
Write-Output "H2442_WINDOWS_NATIVE_ACCESS_READY ifindex=$idx"
