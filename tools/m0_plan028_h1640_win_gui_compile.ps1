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
$info='namespace Wbd.Gui { static class SourceInfo { public const string SHA = "{0}"; public const string Version = "{1}"; } }' -f $SourceSHA,$Version
[IO.File]::WriteAllText($gen,$info,[Text.UTF8Encoding]::new($false))
$refs=@('mscorlib','System','System.Core','System.Drawing','System.Windows.Forms','System.Web.Extensions','System.ServiceProcess')|ForEach-Object {'/reference:'+(Join-Path $fx ($_.ToString()+'.dll'))}
$source=@('Portable.cs','MainForm.cs','GuiTests.cs')|ForEach-Object {Join-Path $root ('windows/gui/'+$_)}
foreach($f in $source){if(-not(Test-Path $f)){throw "GUI source missing $f"}}
$manifest=Join-Path $root 'windows/gui/app.manifest'
if(-not(Test-Path $manifest)){throw 'GUI app.manifest absent'}
& $csc /nologo /noconfig /nostdlib+ /langversion:latest /target:winexe /platform:x64 /optimize+ /deterministic+ /utf8output /codepage:65001 ('/out:'+(Join-Path $out 'WBD.exe')) ('/win32manifest:'+$manifest) @refs @source $gen
if($LASTEXITCODE -ne 0){throw "source-locked WinForms C# compilation failed exit=$LASTEXITCODE"}
Remove-Item -LiteralPath $gen
Copy-Item -LiteralPath (Join-Path $root 'windows/gui/WBD.exe.config') -Destination $out
Copy-Item -LiteralPath (Join-Path $root 'windows/gui/fields.json') -Destination (Join-Path $out 'gui-fields.json')
Copy-Item -LiteralPath (Join-Path $root 'docs/PARAMETERS.json') -Destination $out
[IO.File]::WriteAllText((Join-Path $out 'roslyn-path.txt'),$csc,[Text.UTF8Encoding]::new($false))
Write-Output "H1640_WIN_GUI_REAL_COMPILED_VS_DISCOVERED exact_source=$SourceSHA"
