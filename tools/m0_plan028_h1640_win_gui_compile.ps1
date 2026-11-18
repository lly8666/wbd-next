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
# The original GUI cold eligibility guard was correct before PLAN029 H2202
# but is stale: the authenticated v2 extension now supports Normal Fixed/
# Auto and Game2/Game4 as well as Normal/off. Retain strict mode grammar and
# all other per-mode validation; remove ONLY this obsolete extra prohibition.
$portableText=[IO.File]::ReadAllText($source[0],[Text.Encoding]::UTF8)
$legacyPadGuard='(?m)^\s*if\(mode!=""&&mode!="off"&&\(nativeMode!="off"\|\|lanes!=1\)\)\r?\n\s*throw new InvalidDataException\("新流启动填充当前仅支持 Normal \+ FEC关闭。"\);'
if(([regex]::Matches($portableText,$legacyPadGuard)).Count -ne 1){
 throw 'H2204 GUI obsolete single-mode padding gate donor drift'
}
$portableText=[regex]::Replace($portableText,$legacyPadGuard,
 '                // H2202 strict TLS v2: the authenticated session owns padding mode.')
$portableDerived=Join-Path $out 'Portable-h2204-control-v2.cs'
[IO.File]::WriteAllText($portableDerived,$portableText,[Text.UTF8Encoding]::new($false))
$source[0]=$portableDerived
# H2204 GUI: the immutable donor predates encrypted V4 control v2.
# Derive a standalone presentation file; do not edit the pinned Go donor.
# Current original-Go assembly already registers these native V4v2
# selectors; adding another ComboBox list creates duplicate user choices.
$sourceText=[IO.File]::ReadAllText($derivedMain,[Text.Encoding]::UTF8)
foreach($key in @('startup-padding','fec.mode','fec.profile','fec.auto_policy','fec.auto_start_profile','outer-repair')){
 if(-not $sourceText.Contains('f.Key == "'+$key+'"')){
  throw "H2204 assembled WinForms selector missing: $key"
 }
}
$sourceText=$sourceText.Replace('仅TLS启动 · Normal','仅TLS启动 · 双端').Replace('所有TCP/UDP新流 · Normal','所有TCP/UDP新流 · 双端')
[IO.File]::WriteAllText($derivedMain,$sourceText,[Text.UTF8Encoding]::new($false))
# Run the source-donor GUI field-by-field / actual Go --check-config regression
# with the 029B/H2202 additions: stale test fixture must not be mistaken for
# a native product failure or be silently skipped.
$tests=[IO.File]::ReadAllText($source[2],[Text.Encoding]::UTF8)
$mutator='{"diagnostic-interval","2s"}'
if(([regex]::Matches($tests,[regex]::Escape($mutator))).Count -ne 1){throw 'H2204 GUI test mutator donor drift'}
# The assembled H2204 donor already has FEC2, outer-repair and TLS CA
# fields. The original GUI fixture should be enriched ONLY with absent
# parameters: duplicating a key in Dictionary<> is a real GUI self-test FAIL.
$mutStart=$tests.IndexOf('var mutations = new Dictionary<string, object> {')
if($mutStart -lt 0){throw 'H2204 GUI mutation dictionary donor drift'}
$mutEnd=$tests.IndexOf('};',$mutStart)
if($mutEnd -lt 0){throw 'H2204 GUI mutation dictionary terminator missing'}
$existingMutations=$tests.Substring($mutStart,$mutEnd-$mutStart)
$additional=@(
 @('startup-padding','"flows"'),@('fec.mode','"off"'),
 @('fec.profile','"strong"'),@('fec.auto_policy','"normal"'),
 @('fec.auto_start_profile','"strong"'),@('outer-repair','"on"'),
 @('dns.direct','"223.5.5.5"'),@('dns.tunnel','"1.1.1.1"'),
 @('direct-flow-hard','16384'),@('split-enable','false'),
 @('cn-domain-direct','false'),@('cn-rules-file','""'),
 @('health.keepalive_seconds','15'),@('health.dead_after_seconds','90'),
 @('health.idle_dormant_seconds','0'),@('tls-ca-pem','""')
)
$additions=@()
foreach($entry in $additional){
 $key=[string]$entry[0]
 $signature='{"'+$key+'",'
 if(-not $existingMutations.Contains($signature)){
  $additions+=('{"'+$key+'",'+[string]$entry[1]+'}')
 }
}
if($additions.Count -gt 0){
 $tests=$tests.Replace($mutator,$mutator+','+[string]::Join(',', $additions))
}

$derivedTests=Join-Path $out 'GuiTests-h2204-control-v2.cs'
[IO.File]::WriteAllText($derivedTests,$tests,[Text.UTF8Encoding]::new($false))
$source[2]=$derivedTests
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
# The old donor's 44-name catalogue is not the current original-Go native V4
# product. Every exposed GUI key MUST exist in actual --check-config; keep
# original legacy keys for safe migration and give new ones explicit defaults.
$fields=ConvertFrom-Json -InputObject ($originalFields.Replace($labelOld,$labelNew).Replace($hintOld,$hintNew)) -AsHashtable
$add=[ordered]@{
 'startup-padding'=@('传输','启动随机填充','off / tls / flows；客户端加密提出，服务端逐会话同步；与旧版 TLS 填充不要同时启用','String','"off"')
 'fec.mode'=@('传输','原生 FEC2 模式','off / fixed / auto（auto 只支持 Normal）','String','"off"')
 'fec.profile'=@('传输','原生固定 FEC2 档位','固定档：light、mild、medium、balanced、high、strong、maximum','String','"strong"')
 'fec.auto_policy'=@('传输','原生自动 FEC2 策略','normal 或 aggressive；仅 Normal','String','"normal"')
 'fec.auto_start_profile'=@('传输','原生自动起始 FEC2','默认 strong；重连才生效','String','"strong"')
 'outer-repair'=@('传输','外层重传','on / off；不改 FEC 与 Health','String','"on"')
 'dns.direct'=@('网络','物理网卡 DNS','一个 IPv4；仅物理侧冷启动解析','String','"223.5.5.5"')
 'dns.tunnel'=@('网络','隧道 DNS','一个 IPv4；DNS4 旧主备字段已退役','String','"1.1.1.1"')
 'direct-flow-hard'=@('网络','直连流数上限','直连独立保护阈值；默认 16384','Int','16384')
 'split-enable'=@('网络','高级分流开关','关闭时没有业务 Direct/FakeIP，基础 DNS/启动填充仍保留','Bool','false')
 'cn-domain-direct'=@('网络','CN 域名高级分流','仅与高级分流开启同时使用；需要可信域名规则','Bool','false')
 'cn-rules-file'=@('网络','CN 域名规则路径','填本地绝对路径；关闭高级分流时留空','String','""')
 'health.keepalive_seconds'=@('生命周期','原生 Health 心跳秒','默认 15，受保护的原生 Rust 计时','Uint','15')
 'health.dead_after_seconds'=@('生命周期','原生 Health 失活秒','默认 90；不得小于三倍心跳','Uint','90')
 'health.idle_dormant_seconds'=@('生命周期','原生 Health 闲置秒','默认 0 禁用；原生业务闲置','Uint','0')
 'tls-ca-pem'=@('服务器','TLS 服务端证书/CA','可选本地 PEM 绝对路径；未配置时使用系统可信根','String','""')
}
foreach($key in $add.Keys){
  if($fields.Contains($key) -and @($fields[$key]).Count -ne 3){throw "H2204 current GUI field metadata malformed: $key"}
  $fields[$key]=@($add[$key][0],$add[$key][1],$add[$key][2])
}
$fieldsJson=ConvertTo-Json -InputObject $fields -Depth 6
[IO.File]::WriteAllText($derivedFields,$fieldsJson,[Text.UTF8Encoding]::new($false))
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
$catalog=Get-Content -LiteralPath (Join-Path $root 'docs/PARAMETERS.json') -Raw | ConvertFrom-Json -AsHashtable
$cli=$catalog['targets']['client-windows']
# Real Go --check-config is authoritative; this catalogue extends only the
# independent WinForms UI to the currently installed native V4 flags.
$cli['dns4']['default_expression']='""'
$cli['mtu']['default_expression']='1460'
foreach($key in $add.Keys){
  if($cli.Contains($key) -and [string]$cli[$key]["type"] -ne [string]$add[$key][3]){throw "H2204 original catalogue key type drift: $key"}
  $cli[$key]=[ordered]@{
    type=$add[$key][3];default_expression=$add[$key][4];help=$add[$key][2];
    source='H2204 original-Go native V4 overlay';json=$true
  }
}
[IO.File]::WriteAllText((Join-Path $out 'PARAMETERS.json'),
  (ConvertTo-Json -InputObject $catalog -Depth 12),[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $out 'roslyn-path.txt'),$csc,[Text.UTF8Encoding]::new($false))
Write-Output "H1640_WIN_GUI_REAL_COMPILED_VS_DISCOVERED exact_source=$SourceSHA"
