param([Parameter(Mandatory=$true)][string]$LegacyRoot,[Parameter(Mandatory=$true)][string]$OverlayRoot,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$legacy = [IO.Path]::GetFullPath($LegacyRoot)
$overlay = [IO.Path]::GetFullPath($OverlayRoot)
$out = [IO.Path]::GetFullPath($OutputDirectory)
$source = (git -C $overlay rev-parse HEAD).Trim()
if ($source -notmatch '^[0-9a-f]{40}$') { throw 'invalid exact overlay SOURCE' }
New-Item -ItemType Directory -Force $out | Out-Null
# Compile original Go Windows executable after source-locked fail-closed overlay.
& python (Join-Path $overlay 'r0/go_overlay/scripts/fec2_assembly_smoke.py') --legacy-root $legacy --overlay-root $overlay --out (Join-Path $out 'go-build') --target windows-amd64
if ($LASTEXITCODE -ne 0) { throw 'exact assembly/Windows Go build failed' }
$portable=Join-Path $out 'portable'
& (Join-Path $legacy 'scripts/build_windows_gui.ps1') -OutputDirectory $portable -SourceSHA $source -Version 'fec2-plan008'
if ($LASTEXITCODE -ne 0) { throw 'native WinForms compiler failed' }
Copy-Item (Join-Path $out 'go-build/wbd-client.exe') (Join-Path $portable 'wbd-client.exe')
Copy-Item (Join-Path $legacy 'scripts/windows_client_network.ps1') (Join-Path $portable 'windows_client_network.ps1')
if (-not (Test-Path (Join-Path $portable 'PARAMETERS.json')) -or -not (Test-Path (Join-Path $portable 'gui-fields.json')) -or -not (Test-Path (Join-Path $portable 'WBD.exe'))) {throw 'incomplete original portable GUI'}
# WBD.exe is a Windows GUI subsystem executable. Invoking it with &
# can return control before its self-test finishes. Wait for the REAL child
# process, not a time-based guess, and keep both failure and success receipts.
# FakeSession only simulates driver/Stop; native Go --check-config is real.
$receipt=Join-Path $portable 'gui-test-result.json'
if (Test-Path -LiteralPath $receipt) { throw 'stale GUI self-test receipt in fresh portable output' }
$guiPath=Join-Path $portable 'WBD.exe'
$guiProcess=Start-Process -FilePath $guiPath -ArgumentList @('--self-test') -WorkingDirectory $portable -PassThru -ErrorAction Stop
try {
    if (-not $guiProcess.WaitForExit(600000)) {
        try { $guiProcess.Kill() } catch { }
        throw 'native GUI self-test exceeded bounded 600s process timeout'
    }
    $guiProcess.Refresh()
    $guiExit=$guiProcess.ExitCode
} finally {
    $guiProcess.Dispose()
}
if (-not (Test-Path -LiteralPath $receipt)) {
    throw ("native GUI self-test produced no receipt after process exit code " + $guiExit)
}
$report=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
if ($report.result -ne 'PASS' -or $guiExit -ne 0) {
    $reason=if ($report.error) { [string]$report.error } else { 'no error detail in original GUI receipt' }
    throw ("native GUI self-test failed: exit=" + $guiExit + " result=" + $report.result + " reason=" + $reason)
}
$sourceInfo=@{
    result='PASS_SCOPED_WINFORMS_AND_ORIGINAL_GO_CONFIG'
    legacy_source=(git -C $legacy rev-parse HEAD).Trim()
    overlay_source=$source
    go_exe_sha256=(Get-FileHash (Join-Path $portable 'wbd-client.exe') -Algorithm SHA256).Hash.ToLower()
    gui_exe_sha256=(Get-FileHash (Join-Path $portable 'WBD.exe') -Algorithm SHA256).Hash.ToLower()
    gui_receipt_sha256=(Get-FileHash $receipt -Algorithm SHA256).Hash.ToLower()
    product_rust_native_loader='NOT_RUN'
    actual_fec2_applied='NOT_RUN'
    physical_driver='NOT_RUN'
}
$sourceInfo | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $out 'windows-product-result.json')
Write-Output 'FEC2_PLAN008_WINFORMS_NATIVE_CONFIG_PASS_NOT_PRODUCT_FEC2'
