param([string]$BuildRoot='xdp-build',[string]$LegacyRoot='legacy',[string]$SourceSHA=$env:GITHUB_SHA)
$ErrorActionPreference='Stop'
$build=[IO.Path]::GetFullPath($BuildRoot)
$portable=Join-Path $build 'portable'
New-Item -ItemType Directory -Force $portable,(Join-Path $portable 'drivers/winxdp'),(Join-Path $portable 'licenses') | Out-Null
$m=Get-Content (Join-Path $build 'manifest.json') -Raw | ConvertFrom-Json
if($m.source_sha -ne $SourceSHA){throw 'source identity'}
Copy-Item (Join-Path $build 'wbd-client-embedded.exe') (Join-Path $portable 'wbd-client.exe')
Copy-Item (Join-Path $build 'wbd_engine.dll') $portable
& "$PSScriptRoot/m0_plan028_h1640_win_gui_compile.ps1" -LegacyRoot $LegacyRoot -OutputDirectory $portable -SourceSHA $SourceSHA -Version 'WinXDP-1.4'
if($LASTEXITCODE -ne 0){throw 'GUI build failed'}
# Ship exact Microsoft MIT runtime; omit debug symbols, eBPF tools and PA setup.
nuget install Microsoft.XDP-for-Windows.Runtime.x64 -Version 1.4.0 -OutputDirectory xdp-release-deps -NonInteractive
if($LASTEXITCODE -ne 0){throw 'WinXDP 1.4 runtime unavailable'}
$runtime=(Get-ChildItem xdp-release-deps -Recurse -Filter xdp-setup.ps1 | Select-Object -First 1).Directory.FullName
foreach($name in @('xdp.inf','xdp.cat','xdp.sys','xdpapi.dll','xdppcw.man')){
  Copy-Item (Join-Path $runtime $name) (Join-Path $portable 'drivers/winxdp')
}
foreach($name in @('xdp.sys','xdp.cat')){
  if((Get-AuthenticodeSignature (Join-Path $runtime $name)).Status -ne 'Valid'){throw "official Microsoft driver signature unavailable: $name"}
}
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/microsoft/xdp-for-windows/v1.4.0/LICENSE' -OutFile (Join-Path $portable 'licenses/WinXDP-MIT.txt')
$wzip=Join-Path $env:RUNNER_TEMP 'wbd-release-wintun.zip'
$wdir=Join-Path $env:RUNNER_TEMP 'wbd-release-wintun'
Invoke-WebRequest -UseBasicParsing -Uri 'https://www.wintun.net/builds/wintun-0.14.1.zip' -OutFile $wzip -TimeoutSec 100
if((Get-FileHash $wzip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51'){throw 'official Wintun archive hash changed'}
Expand-Archive $wzip $wdir -Force
$dll=Join-Path $wdir 'wintun/bin/amd64/wintun.dll'
if((Get-AuthenticodeSignature $dll).Status -ne 'Valid'){throw 'official Wintun DLL signature unavailable'}
Copy-Item $dll $portable
$license=Get-ChildItem (Join-Path $wdir 'wintun') -File | Where-Object {$_.Name -match '^LICENSE'} | Select-Object -First 1
if(!$license){throw 'Wintun distribution license missing'}
Copy-Item $license.FullName (Join-Path $portable 'licenses/Wintun.txt')
# Compile helper output is evidence, not shipped product source.
foreach($f in (Get-ChildItem $portable -File | Where-Object {$_.Extension -eq '.cs' -or $_.Name -eq 'roslyn-path.txt'})){Remove-Item $f.FullName}
@'
WBD Windows x64 / WinXDP 1.4 + Wintun 0.14.1
首次使用：完整解压至可写本地目录，以管理员身份启动 WBD.exe。
在“便携与驱动”页点击 WinXDP 驱动安装及 Wintun 驱动安装，再重新检测。
也可在管理员终端执行 WBD.exe --install-drivers（结果写入 driver-install-result.txt）。
无需 Npcap。现有其他应用的驱动不会由 WBD 卸载。
更新：先断开连接并完成原生网络清理，保留 data 目录，替换程序文件。
删除便携目录前先断开；共享系统驱动不会随便携目录删除而卸载。
WinXDP API 就绪不等于当前物理网卡 Native 模式可用或业务已连通。
微软 WinXDP MIT、Wintun 官方分发许可见 licenses。
'@ | Set-Content -Encoding UTF8 (Join-Path $portable 'README-安装.txt')
$files=[ordered]@{}
Get-ChildItem $portable -File -Recurse | Sort-Object FullName | ForEach-Object {
 $key=[IO.Path]::GetRelativePath($portable,$_.FullName).Replace('\','/')
 $files[$key]=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
[ordered]@{source_sha=$SourceSHA;arch='windows-amd64';xdp_runtime='1.4.0';wintun='0.14.1';native_fec_acceleration=$true;files=$files} | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $portable 'package-manifest.json')
Compress-Archive -Path (Join-Path $portable '*') -DestinationPath (Join-Path $build 'WBD-Windows-amd64-WinXDP.zip') -Force
Write-Output 'WBD_WINXDP_PORTABLE_PACKAGE_BUILT'
