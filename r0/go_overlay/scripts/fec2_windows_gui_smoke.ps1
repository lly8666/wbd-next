param([Parameter(Mandatory=$true)][string]$LegacyRoot,[Parameter(Mandatory=$true)][string]$OverlayRoot,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$legacy = [IO.Path]::GetFullPath($LegacyRoot)
$overlay = [IO.Path]::GetFullPath($OverlayRoot)
$out = [IO.Path]::GetFullPath($OutputDirectory)
$source = (git -C $overlay rev-parse HEAD).Trim()
if ($source -notmatch '^[0-9a-f]{40}$') { throw 'invalid exact overlay SOURCE' }
New-Item -ItemType Directory -Force $out | Out-Null
# Windows checkout filters can change the bytes of overlay FULL-FILE donor
# replacements. The main checkout repair restores original Go target blobs,
# but its replace branch does not restore the overlay sources themselves.
# Rematerialize exact pinned Git object bytes on this TEMP checkout only,
# before running the existing assembler. No fuzzy patch / hash bypass.
@'
import hashlib,json,pathlib,subprocess,sys
overlay=pathlib.Path(sys.argv[1]).resolve(strict=True)
expected=sys.argv[2]
assert subprocess.check_output(["git","-C",str(overlay),"rev-parse","HEAD"],text=True).strip()==expected
manifest=json.loads((overlay/"r0/go_overlay/assembly/manifest.json").read_text(encoding="utf-8"))
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
restored=0
for op in manifest["operations"]:
    name=op.get("overlay_path")
    if name is None:
        continue
    pure=pathlib.PurePosixPath(name)
    assert not pure.is_absolute() and all(x not in ("",".","..") for x in pure.parts) and "\\" not in name
    target=overlay.joinpath(*pure.parts)
    assert target.is_file() and not target.is_symlink()
    assert target.resolve().is_relative_to(overlay)
    raw=subprocess.check_output(["git","-C",str(overlay),"show",expected+":"+name])
    assert gitblob(raw)==op["result_blob"],"pinned overlay Git blob drift: "+name
    target.write_bytes(raw)
    restored+=1
assert restored>=18,("expected complete 016 overlay source files, got "+str(restored))
print("M4_PINNED_WINDOWS_OVERLAY_GIT_BYTES_RESTORED",restored)
'@ | python - $overlay $source
if ($LASTEXITCODE -ne 0) { throw 'exact Windows overlay Git objects cannot be materialized' }
# Compile original Go Windows executable after source-locked fail-closed overlay.
& python (Join-Path $overlay 'r0/go_overlay/scripts/fec2_assembly_smoke.py') --legacy-root $legacy --overlay-root $overlay --out (Join-Path $out 'go-build') --target windows-amd64
if ($LASTEXITCODE -ne 0) { throw 'exact assembly/Windows Go build failed' }
# Compile (do NOT execute) the entire original Windows native transaction
# package with the 12 pinned donor files. Hosted CI is not a network-isolated
# machine and must never exercise admin-owned WFP/routing mutations here.
Push-Location $legacy
try {
    $nativeTest=Join-Path $out 'native-windowsclient.test.exe'
    & go test -c -o $nativeTest ./internal/windowsclient
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $nativeTest)) {
        throw 'pinned original Go Windows native package compile failed'
    }
    $nativeRecoveryLog=Join-Path $out 'native-recover-test.log'
    & go test -count=1 -v -run '^TestPLAN010(OriginalNativeRecoveryNoShellOrLegacyFallback|NativeReadOnlyDiskStatusAndConflict)$' ./internal/windowsclient 2>&1 | Tee-Object -FilePath $nativeRecoveryLog
    if ($LASTEXITCODE -ne 0) { throw 'native original Go recovery/state read-only regression failed' }
    foreach ($named in @(
        'TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback',
        'TestPLAN010NativeReadOnlyDiskStatusAndConflict'
    )) {
        if (-not (Select-String -LiteralPath $nativeRecoveryLog -SimpleMatch ("--- PASS: " + $named) -Quiet)) {
            throw ("native Windows original Go test was NOT executed: " + $named)
        }
    }
    # The real original Windows CLI owns a named OS event shared by manual
    # native Recover and GUI Connect. Verify exclusivity, release/reclaim,
    # and a genuinely executed named Go test on the native Windows host.
    # Execute the FULL, exact-pinned original Windows Go CLI test package.
    # Three historical script tests are migrated to native-only owner/deny
    # semantics in the 31-op manifest. Never restore a shell runner to make
    # obsolete tests compile. None of these cases mutates machine routes.
    $ownerTestLog=Join-Path $out 'native-owner-slot-test.log'
    & go test -count=1 -v ./cmd/wbd-client 2>&1 | Tee-Object -FilePath $ownerTestLog
    if ($LASTEXITCODE -ne 0) { throw 'original Windows CLI native full test suite failed' }
    foreach ($named in @(
        'TestPLAN010OwnerSlotIsActuallyExclusive',
        'TestGUIClientSlotFencesUntilCleanupEnds',
        'TestN4WindowsEntryUsesSingleProtectedSenderAndNativeDirectIngress',
        'TestN4WindowsNativeGuardRefusesUnqualifiedCapture',
        'TestN4NativeApplyNeverFallsBackToPowerShell',
        'TestN4NativeCanceledApplyMustNotReportSuccess',
        'TestN4NativeRuntimeHasNoOldScriptCommandLauncher'
    )) {
        if (-not (Select-String -LiteralPath $ownerTestLog -SimpleMatch ("--- PASS: " + $named) -Quiet)) {
            throw ("original Windows CLI native test was not executed: " + $named)
        }
    }
} finally { Pop-Location }
$portable=Join-Path $out 'portable'
& (Join-Path $legacy 'scripts/build_windows_gui.ps1') -OutputDirectory $portable -SourceSHA $source -Version 'fec2-plan008'
if ($LASTEXITCODE -ne 0) { throw 'native WinForms compiler failed' }
Copy-Item (Join-Path $out 'go-build/wbd-client.exe') (Join-Path $portable 'wbd-client.exe')
# Runtime product must remain functional without shipping any .ps1 network
# script. Build/Actions may use PowerShell, never package it as fallback.
if (Test-Path -LiteralPath (Join-Path $portable 'windows_client_network.ps1')) {
    throw 'runtime PowerShell fallback leaked into portable product'
}
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
# Require new ORIGINAL WinForms -> ORIGINAL Go native status checks by exact
# receipt name, never accept an old GUI's generic PASS as this feature's PASS.
foreach ($name in @(
    'GUI original Go reports absent disk state, not network connected',
    'GUI original Go detects old script state without migration',
    'GUI original Go detects orphan intent and preserves it',
    'GUI rejects invalid WAL; not a fake safe or ready result'
)) {
    if ($report.checks -notcontains $name) {
        throw ("native GUI status regression NOT_RUN: " + $name)
    }
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
