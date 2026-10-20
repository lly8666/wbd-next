param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$out=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force $out | Out-Null

# No changes to host-wide default routes, DNS, IPv6 or production WFP guards.
# Only the GitHub-hosted ephemeral disposable Windows VM is allowed to run
# the isolated TEST-NET-3 native WFP/created-test-Wintun laboratory.
$receipt=@{
    schema='wbd-m4-plan013-hosted-native-lab/v1'
    runner_environment=$env:RUNNER_ENVIRONMENT
    wfp_testnet='NOT_RUN_NOT_DISPOSABLE_HOST'
    wintun_created='NOT_RUN_NOT_DISPOSABLE_HOST'
    native_ip_mtu_dns_route='NOT_RUN_NOT_DISPOSABLE_HOST'
    native_owned_wal='NOT_RUN_NOT_DISPOSABLE_HOST'
    production_wfp_capture='NOT_RUN'
    production_original_go_authenticated_stop='NOT_RUN'
}
$destination=Join-Path $out 'plan013-hosted-native-lab.json'
try {
    if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' -or
        $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
        Write-Output 'PLAN013 hosted native lab NOT_RUN (no disposable GitHub Windows runner)'
        return
    }
    $env:WBD_N4_WFP_ISOLATED_LAB='1'
    try {
        $wfpLog=Join-Path $out 'plan013-real-wfp-testnet.log'
        & go test -count=1 -timeout 2m -v -run '^(TestN4WindowsWFPPersistentFilterHostLab|TestN4WindowsWFPExactOwnedDeletePartialHostLab)$' ./internal/windowsclient 2>&1 | Tee-Object -FilePath $wfpLog
        if ($LASTEXITCODE -ne 0) {throw 'real narrow TEST-NET WFP native apply/delete failed'}
        foreach ($name in @('TestN4WindowsWFPPersistentFilterHostLab','TestN4WindowsWFPExactOwnedDeletePartialHostLab')) {
            if (-not (Select-String -LiteralPath $wfpLog -SimpleMatch ('--- PASS: '+$name+' ') -Quiet)) {
                throw ('WFP native positive test NOT_RUN: '+$name)
            }
        }
        $receipt.wfp_testnet='PASS_PERSISTENT_NATIVE_TESTNET_FILTER_REOPEN_EXACT_CAS_DELETE'
    } finally {
        Remove-Item Env:\WBD_N4_WFP_ISOLATED_LAB -ErrorAction SilentlyContinue
    }
    $labDir=Join-Path $env:RUNNER_TEMP ('wbd-plan013-wintun-'+$env:GITHUB_RUN_ID)
    New-Item -ItemType Directory -Force $labDir | Out-Null
    $archive=Join-Path $labDir 'wintun.zip'
    # Exactly the pinned official original-Go N4 Windows Actions dependency.
    Invoke-WebRequest -Uri 'https://www.wintun.net/builds/wintun-0.14.1.zip' -OutFile $archive -TimeoutSec 60
    $expected='07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51'
    if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {throw 'pinned official Wintun archive SHA256 mismatch'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $z=[IO.Compression.ZipFile]::OpenRead($archive)
    try {
        $entry=$z.GetEntry('wintun/bin/amd64/wintun.dll')
        if ($null -eq $entry) {throw 'pinned Win64 Wintun DLL missing'}
        $inputStream=$entry.Open()
        $outputStream=[IO.File]::Create((Join-Path $labDir 'wintun.dll'))
        try {$inputStream.CopyTo($outputStream)}
        finally {$outputStream.Dispose();$inputStream.Dispose()}
    } finally {$z.Dispose()}
    $labExe=Join-Path $labDir 'windowsclient.test.exe'
    & go test -mod=readonly -c -o $labExe ./internal/windowsclient
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $labExe)) {throw 'native Go test exe beside pinned official DLL failed'}
    $receipt.wintun_archive_sha256=$expected
    $env:WBD_N4_ADMIN_ISOLATED='1'
    $env:WBD_N4_ADMIN_PROBE_REPORT=Join-Path $out 'plan013-wintun-capability.json'
    try {
        $tunLog=Join-Path $out 'plan013-created-wintun.log'
        & $labExe '-test.v' '-test.run=^TestN4WindowsHostedCreatedWintunReadOnlyCapability$' '-test.timeout=2m' 2>&1 | Tee-Object -FilePath $tunLog
        if ($LASTEXITCODE -ne 0) {throw 'real isolated created-Wintun test failed'}
        if (-not (Test-Path -LiteralPath $env:WBD_N4_ADMIN_PROBE_REPORT)) {throw 'Wintun capability missing receipt'}
        $cap=Get-Content -LiteralPath $env:WBD_N4_ADMIN_PROBE_REPORT -Raw | ConvertFrom-Json
        if ($cap.Result -eq 'SCOPED_CREATED_WINTUN_READ_ONLY_PASS') {
            if (-not (Select-String -LiteralPath $tunLog -SimpleMatch '--- PASS: TestN4WindowsHostedCreatedWintunReadOnlyCapability ' -Quiet)) {throw 'Wintun PASS unverified'}
            $receipt.wintun_created='PASS_REAL_CREATED_WINTUN_LUID_IPHELPER_DNS'
        } elseif ($cap.Result -eq 'UNSUPPORTED') {
            if (-not (Select-String -LiteralPath $tunLog -SimpleMatch '--- SKIP: TestN4WindowsHostedCreatedWintunReadOnlyCapability ' -Quiet)) {throw 'Wintun unsupported claim lacks SKIP'}
            $receipt.wintun_created='UNSUPPORTED_DRIVER_DLL_ADMIN_OR_NATIVE_READ'
            $receipt.native_ip_mtu_dns_route='UNSUPPORTED_WINTUN_UNAVAILABLE'
            $receipt.native_owned_wal='UNSUPPORTED_WINTUN_UNAVAILABLE'
            return
        } else {
            throw ('Unexpected created-Wintun capability result '+$cap.Result)
        }
    } finally {
        Remove-Item Env:\WBD_N4_ADMIN_ISOLATED -ErrorAction SilentlyContinue
        Remove-Item Env:\WBD_N4_ADMIN_PROBE_REPORT -ErrorAction SilentlyContinue
    }
    $cases=@(
        @{name='TestN4WindowsHostedOwnedAdapterNativeIPWritesAndRestore'; enabled='WBD_N4_ADMIN_MUTATION'; report='WBD_N4_ADMIN_MUTATION_REPORT'; file='plan013-native-ip-writes.json'; success='SCOPED_ISOLATED_NATIVE_IP_WRITE_RESTORE_PASS'; field='native_ip_mtu_dns_route'},
        @{name='TestN4WindowsHostedUnifiedWALRealLeaseMTUDNS'; enabled='WBD_N4_ADMIN_UNIFIED_WAL'; report='WBD_N4_ADMIN_UNIFIED_WAL_REPORT'; file='plan013-native-owned-wal.json'; success='SCOPED_REAL_WINTUN_NATIVE_WAL_APPLY_RECOVER_PASS'; field='native_owned_wal'}
    )
    foreach ($case in $cases) {
        $path=Join-Path $out $case.file
        Set-Item -Path ('Env:'+$case.enabled) -Value '1'
        Set-Item -Path ('Env:'+$case.report) -Value $path
        try {
            $log=Join-Path $out ($case.name+'.log')
            & $labExe '-test.v' ('-test.run=^'+$case.name+'$') '-test.timeout=3m' 2>&1 | Tee-Object -FilePath $log
            if ($LASTEXITCODE -ne 0) {throw ('real native Win32 hosted adapter stage failed: '+$case.name)}
            if (-not (Test-Path -LiteralPath $path)) {throw ('native stage missing report: '+$case.name)}
            $result=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
            $passed=Select-String -LiteralPath $log -SimpleMatch ('--- PASS: '+$case.name+' ') -Quiet
            $skipped=Select-String -LiteralPath $log -SimpleMatch ('--- SKIP: '+$case.name+' ') -Quiet
            if ($result.result -eq $case.success -and $passed) {
                $receipt[$case.field]='PASS_REAL_TEST_ADAPTER_OWNED_OS_WRITE_READBACK_AND_ROLLBACK'
            } elseif ([string]$result.result -like 'UNSUPPORTED*' -and $skipped) {
                $receipt[$case.field]='UNSUPPORTED_'+[string]$result.result
            } else {throw ('native stage report contradicts actual Go PASS/SKIP: '+$case.name)}
        } finally {
            Remove-Item ('Env:'+$case.enabled) -ErrorAction SilentlyContinue
            Remove-Item ('Env:'+$case.report) -ErrorAction SilentlyContinue
        }
    }
} finally {
    if ($labDir -and (Test-Path -LiteralPath $labDir)) {Remove-Item -LiteralPath $labDir -Recurse -Force -ErrorAction SilentlyContinue}
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $destination
    Write-Output ('PLAN013_NATIVE_OS_LAB WFP='+$receipt.wfp_testnet+' WINTUN='+$receipt.wintun_created+' WAL='+$receipt.native_owned_wal)
}
