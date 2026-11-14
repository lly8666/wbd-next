param([string]$LegacyRoot,[string]$OutputDirectory,[string]$SourceSHA,[string]$Version)
$ErrorActionPreference='Stop'
if($SourceSHA -notmatch '^[0-9a-f]{40}$' -or $Version -notmatch '^[A-Za-z0-9.-]+$'){throw 'invalid exact GUI build source/version'}
$root=[IO.Path]::GetFullPath($LegacyRoot)
$out=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force $out|Out-Null
$pf86=[Environment]::GetFolderPath('ProgramFilesX86')
$vswhere=Join-Path $pf86 'Microsoft Visual Studio/Installer/vswhere.exe'
if(-not(Test-Path $vswhere)){throw 'VM Visual Studio installer discovery missing'}
$vsroot=@(& $vswhere -latest -products '*' -property installationPath | Where-Object {$_ -and (Test-Path $_)}) | Select-Object -First 1
if(-not $vsroot){throw 'VM no installed Visual Studio'}
$cscCandidates=@((Join-Path $vsroot 'MSBuild/Current/Bin/Roslyn/csc.exe'),(Join-Path $vsroot 'MSBuild/15.0/Bin/Roslyn/csc.exe'))
$csc=@($cscCandidates|Where-Object {Test-Path $_}|Select-Object -First 1)
if(-not $csc){$csc=@(Get-ChildItem -Path $vsroot -Filter csc.exe -Recurse -File -ErrorAction SilentlyContinue |Where-Object {$_.FullName -match 'MSBuild.*Roslyn'}|Select-Object -First 1 -ExpandProperty FullName)}
if(-not $csc){throw 'VM no Roslyn csc.exe; no fake GUI pass'}
$csc=[IO.Path]::GetFullPath($csc[0])
$fx=Join-Path $pf86 'Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8'
if(-not(Test-Path (Join-Path $fx 'System.Windows.Forms.dll'))){throw 'VM missing .NET Framework 4.8 assemblies'}
$gen=Join-Path $out 'SourceInfo.cs'
$info='namespace Wbd.Gui {{ static class SourceInfo {{ public const string SHA = "{0}"; public const string Version = "{1}"; }} }}' -f $SourceSHA,$Version
[IO.File]::WriteAllText($gen,$info,[Text.UTF8Encoding]::new($false))
$refs=@('mscorlib','System','System.Core','System.Drawing','System.Windows.Forms','System.Web.Extensions','System.ServiceProcess')|ForEach-Object {'/reference:'+(Join-Path $fx ($_.ToString()+'.dll'))}
$source=@('Portable.cs','MainForm.cs','GuiTests.cs')|ForEach-Object {Join-Path $root ('windows/gui/'+$_)}
foreach($f in $source){if(-not(Test-Path $f)){throw "GUI source missing $f"}}
# PLAN029 own-source deterministic GUI presentation overlay. Never
# mutate the pinned original donor. Derived source is compiled once from
# the exact donor MainForm and source-locked updated Chinese CN semantics.
$originalMain=[IO.File]::ReadAllText($source[1],[Text.Encoding]::UTF8)
$oldChoice='new Choice("bypass-lan-cn", "局域网与中国 IPv4 直连")'
$newChoice='new Choice("bypass-lan-cn", "局域网、中国 IP 与域名并集直连")'
if(([regex]::Matches($originalMain,[regex]::Escape($oldChoice))).Count -ne 1){
  throw 'PLAN029 original GUI route-mode CN choice donor drift, no arbitrary patch'
}
$derivedMain=Join-Path $out 'MainForm-plan029-cn-domain.cs'
[IO.File]::WriteAllText($derivedMain,$originalMain.Replace($oldChoice,$newChoice),[Text.UTF8Encoding]::new($false))
$source[1]=$derivedMain
$originalFields=[IO.File]::ReadAllText((Join-Path $root 'windows/gui/fields.json'),[Text.Encoding]::UTF8)
$labelOld='"IPv4 分流"'
$labelNew='"中国 IP＋域名分流"'
$hintOld='"默认局域网与中国 IPv4 直连；DNS 劫持优先于分流"'
$hintNew='"中国域名、中国 IP、LAN、direct4 并集直连；普通 DNS 按 QNAME 选直连或隧道单上游；更改仅下次连接生效"'
foreach($old in @($labelOld,$hintOld)){
 if(([regex]::Matches($originalFields,[regex]::Escape($old))).Count -ne 1){
  throw 'PLAN029 original GUI route-mode field donor drift'
 }
}
$derivedFields=Join-Path $out 'gui-fields.json'
[IO.File]::WriteAllText($derivedFields,
  $originalFields.Replace($labelOld,$labelNew).Replace($hintOld,$hintNew),
  [Text.UTF8Encoding]::new($false))
$srcHash=(Get-FileHash $derivedMain -Algorithm SHA256).Hash.ToLowerInvariant()
$fieldsHash=(Get-FileHash $derivedFields -Algorithm SHA256).Hash.ToLowerInvariant()
[ordered]@{schema_version=1;source_sha=$SourceSHA;mode='PLAN029_CN_IP_DOMAIN_DISPLAY_ONLY';
  derived_mainform_sha256=$srcHash;derived_fields_sha256=$fieldsHash;
  original_go_donor_mutated=$false;os_applied='NOT_RUN'}|
  ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $out 'gui-overlay-source.json')
$manifest=Join-Path $root 'windows/gui/app.manifest'
if(-not(Test-Path $manifest)){throw 'GUI app.manifest absent'}
& $csc /nologo /noconfig /nostdlib+ /langversion:latest /target:winexe /platform:x64 /optimize+ /deterministic+ /utf8output /codepage:65001 ('/out:'+(Join-Path $out 'WBD.exe')) ('/win32manifest:'+$manifest) @refs @source $gen
if($LASTEXITCODE -ne 0){throw "source-locked WinForms C# compilation failed exit=$LASTEXITCODE"}
Remove-Item -LiteralPath $gen
Copy-Item -LiteralPath (Join-Path $root 'windows/gui/WBD.exe.config') -Destination $out
# Exact derived field catalog has already been written with the immutable
# source fingerprint; do NOT copy donor fields back over the 029 hints.
if(-not(Test-Path $derivedFields)){throw 'PLAN029 derived GUI fields absent'}
Copy-Item -LiteralPath (Join-Path $root 'docs/PARAMETERS.json') -Destination $out
[IO.File]::WriteAllText((Join-Path $out 'roslyn-path.txt'),$csc,[Text.UTF8Encoding]::new($false))
Write-Output "H1640_WIN_GUI_REAL_COMPILED_VS_DISCOVERED exact_source=$SourceSHA"
