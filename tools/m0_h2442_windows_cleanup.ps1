$ErrorActionPreference='Continue'
if(Test-Path h2442-out/windows-access.json){
 $r=Get-Content h2442-out/windows-access.json -Raw | ConvertFrom-Json
 Remove-NetRoute -DestinationPrefix $r.route -InterfaceIndex $r.index -NextHop $r.guest -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue
}
Remove-NetFirewallHyperVRule -Name ('WBD-H2442-'+$env:GITHUB_RUN_ID) -ErrorAction SilentlyContinue
& wsl.exe -d Ubuntu -u root -- tailscale logout
& wsl.exe -d Ubuntu -u root -- ip link del h228vc
& wsl.exe -d Ubuntu -u root -- ip link del h228bc
& ./tools/m0_wl_npcap_driver_ci.ps1 -Action Cleanup
