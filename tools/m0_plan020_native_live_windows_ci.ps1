$ErrorActionPreference='Stop'
# Uses only original pinned Go and SAME source Rust DLL/official signed
# Wintun already produced by the immediately preceding workflow steps.
# No global WFP, /1 capture routes, or false production ON.
New-Item -ItemType Directory -Force -Path result | Out-Null
@'
import os,pathlib,subprocess
root=pathlib.Path.cwd()
dest=root/"legacy/internal/windowsownerlease"
sha=os.environ["GITHUB_SHA"]
for name in ("created_wintun_windows_test.go","original_go_tls_join_windows_test.go","original_go_tls_fec2_windows_test.go","original_go_tls_game_windows_test.go"):
    src="r0/go_overlay/internal/windowsownerlease/"+name
    target=dest/name
    assert not target.exists(),"foreign original-Go test collision "+src
    raw=subprocess.check_output(["git","show",sha+":"+src])
    assert raw.startswith(b"//go:build windows")
    target.write_bytes(raw)
print("M0_PLAN020_SAME_SOURCE_TRUE_ORIGINAL_GO_TLS_RUST_WINTUN_TEST_COPY_PASS")
'@ | python -
if ($LASTEXITCODE -ne 0) {throw 'source-locked native Rust/Go original TLS test staging FAILED'}
$env:WBD_M0_WIN_OWNER_DLL=(Resolve-Path 'target/release/wbd_engine.dll').Path
$env:WBD_M0_TRY_SCOPED_NATIVE_WINTUN='1'
Push-Location legacy
try {
  & go test -c -tags wbd_v4_embedded_go -o ../result/wintun-release/m0-original-peer-real.exe ./internal/windowsownerlease
  if ($LASTEXITCODE -ne 0) {throw 'real original TLS Rust Wintun native owner compile FAIL'}
} finally {Pop-Location}
& ./result/wintun-release/m0-original-peer-real.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestM0WindowsRealOriginalGoTLSRustM4CreatedWintunSameGeneration$' 2>&1 | Tee-Object -FilePath result/m0-original-rust-wintun-kernel-actual.log
if ($LASTEXITCODE -ne 0) {throw 'actual original-Go TLS Rust M3 two-way signed Wintun kernel test FAIL'}
$wire=Get-Content result/m0-original-rust-wintun-kernel-actual.log -Raw
foreach ($marker in @(
'M0_PLAN020_REAL_ORIGINAL_GO_TLS_RUST_M3_PEER_DECRYPT_AFTER_SIGNED_WINTUN_KERNEL_UDP_APP_FIRST_DELIVERY_PASS',
'M0_PLAN020_REAL_ORIGINAL_GO_TLS_DUAL_RUST_M3_AEAD_SIGNED_WINTUN_KERNEL_UDP_APP_BOTH_DIRECTIONS_PASS',
'M0_PLAN020_REAL_TLS_BOUND_SIGNED_WINTUN_RUST_M3_RECV_ABI_NEGATIVES_PASS',
'M0_PLAN020_REAL_TLS_RUST_M3_RECEIVE_AFTER_NATIVE_WINTUN_QUIESCE_DENIED')) {
  if (!$wire.Contains($marker)) {throw ('original credential TLS Rust Win32 Wintun kernel marker NOT_RUN: '+$marker)}
}
if ($wire -match 'UNSUPPORTED|--- SKIP:') {throw 'real signed Wintun original TLS/Rust test was skipped'}
Write-Output 'M0_PLAN020_SAME_SOURCE_REAL_GO_TLS_RUST_M3_WINTUN_KERNEL_APP_FIRST_REVERSE_PASS_SCOPED'
# PLAN024: one source-locked Windows2022 runner, actual original-Go
# credential TLS FEC2 fixed AND auto, real Rust kind2 M3 AEAD, signed
# Wintun -> real UDP application first/reverse, genuine Stop. The
# authenticated SetTxFec M2 Applied/Auto revision remains NOT_RUN.
& ./result/wintun-release/m0-original-peer-real.exe '-test.v=true' '-test.timeout=6m' '-test.run=^TestM0PLAN024WindowsRealOriginalGoFEC2FixedAutoSignedWintunFirstReverse

# M0-only exact SOURCE post-donor test override. This does not change the
# 12 pinned Windows donor paths nor any production implementation. Check
# full original Git donor SHA BEFORE replacing only the isolated TEST file.
@'
import os,pathlib,subprocess,hashlib
root=pathlib.Path.cwd()
sha=os.environ["GITHUB_SHA"]
destination=root/"legacy/internal/windowsclient/native_admin_preroute_real_crash_windows_test.go"
source="r0/go_overlay/ci/native_admin_preroute_real_crash_windows_test.go"
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
old=destination.read_bytes()
assert blob(old)=="18876a185c2d1504379e81f9e5622dfbdf6f367a","exact pinned donor altered"
patch=subprocess.check_output(["git","show",sha+":"+source])
assert blob(patch)=="672c9ee126899f2300f161560c2cd91f5fbb55f2","new M0 test fixture source SHA drift"
assert b"n4RetirePinnedGhostPreRouteWAL" in patch
destination.write_bytes(patch)
assert blob(destination.read_bytes())==blob(patch)
print("M0_PLAN020_EXACT_M0_NATIVE_CRASH_TEST_SOURCE_POST_PINNED_DONOR_PASS")
'@ | python -
if ($LASTEXITCODE -ne 0) {throw 'exact M0 post-donor native crash test SOURCE rejected'}

Push-Location legacy
try {
  & go test -c -o ../result/wintun-release/m0-actual-ip-mtu-dns.exe ./internal/windowsclient
  if ($LASTEXITCODE -ne 0) {throw 'real native OS WAL test compilation FAIL'}
} finally {Pop-Location}
$env:WBD_N4_ADMIN_UNIFIED_WAL='1'
$env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT=(Join-Path (Resolve-Path result).Path 'real-ip-mtu-dns-wal.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedUnifiedWALRealLeaseMTUDNS$' 2>&1 | Tee-Object -FilePath result/m0-real-native-wal-apply-recover.log
if ($LASTEXITCODE -ne 0) {throw 'native real IP/MTU/DNS WAL Apply Recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT)) {throw 'missing actual OS Apply Recover readback report'}
$wal=Get-Content $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT -Raw | ConvertFrom-Json
if ($wal.source_sha -ne $env:GITHUB_SHA -or $wal.result -ne 'SCOPED_REAL_WINTUN_NATIVE_WAL_APPLY_RECOVER_PASS') {
  throw ('real IP/MTU/DNS WAL Apply Recover NOT_RUN or failed: '+$wal.result)
}
foreach ($field in @('lease','mtu','dns')) {
  if ($wal.$field -notlike 'PASS_*') {throw ('real native OS WAL stage missing '+$field)}
}
if ($wal.guard -ne 'TEST_ONLY_FAKE_NOT_PRODUCTION_WFP' -or $wal.routes -ne 'TEST_ONLY_FAKE_NO_CAPTURE_ROUTES') {
  throw 'native OS receipt falsely claims real host-global WFP or two /1 capture routes'
}
Write-Output 'M0_PLAN020_SAME_SOURCE_REAL_WIN_NATIVE_IP_MTU_DNS_WAL_APPLY_RECOVER_STOP_PASS_SCOPED_WFP_ROUTES_NOT_RUN'

$env:WBD_N4_ADMIN_PREROUTE_CRASH_PROBE='1'
$env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT=(Join-Path (Resolve-Path result).Path 'real-native-process-crash.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedRealPreRouteIPCrashWAL$' 2>&1 | Tee-Object -FilePath result/m0-real-process-crash-wal.log
if ($LASTEXITCODE -ne 0) {throw 'real child TerminateProcess and native WAL recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT)) {throw 'missing real child crash native OS WAL report'}
$crash=Get-Content $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT -Raw | ConvertFrom-Json
if ($crash.source_sha -ne $env:GITHUB_SHA -or $crash.result -like 'UNSUPPORTED*' -or $crash.result -eq 'FAIL_UNFINISHED') {
  throw ('real child crash OS WAL Recover NOT qualified: '+$crash.result)
}
if ($crash.wfp -ne 'FAKE_ONLY' -or $crash.routes -ne 'NOT_RUN') {
  throw 'real child crash falsely qualified global WFP /1 default routes'
}
Write-Output ('M0_PLAN020_REAL_WINDOWS_CHILD_CRASH_NATIVE_OS_WAL_RESULT='+$crash.result)
 2>&1 | Tee-Object -FilePath result/m0-original-fec2-rust-wintun-kernel-actual.log
if ($LASTEXITCODE -ne 0) {throw 'real original-Go Windows FEC2 Fixed Auto TLS Rust signed Wintun test FAIL'}
$fec=(Get-Content result/m0-original-fec2-rust-wintun-kernel-actual.log -Raw)
foreach($mode in @('fixed','auto')){
  if (!$fec.Contains('M0_PLAN024_ORIGINAL_GO_TLS_WINDOWS_FEC2_'+$mode+'_RUST_M3_SIGNED_WINTUN_KERNEL_UDP_APP_FIRST_REVERSE_PASS_SCOPED')){
    throw ('real FEC2 original TLS app marker not run: '+$mode)
  }
}
if ($fec -match 'UNSUPPORTED|--- SKIP:') {throw 'real original-Go FEC2 TLS native Wintun app positive test skipped'}
Write-Output 'M0_PLAN024_WINDOWS_REAL_ORIGINAL_GO_FEC2_FIXED_AUTO_NATIVE_TLS_RUST_WINTUN_FIRST_REVERSE_PASS_SCOPED'
# PLAN024: REAL original Go credential TLS on 2/4 independent FakeTCP
# lanes, Rust GameAdapter unique AEAD/PN, original authenticated Stop and
# signed Wintun -> real UDP app; the first native lane is deliberately lost.
& ./result/wintun-release/m0-original-peer-real.exe '-test.v=true' '-test.timeout=8m' '-test.run=^TestM0PLAN024WindowsRealOriginalGoGame2Game4SignedWintunFirstReverse


# M0-only exact SOURCE post-donor test override. This does not change the
# 12 pinned Windows donor paths nor any production implementation. Check
# full original Git donor SHA BEFORE replacing only the isolated TEST file.
@'
import os,pathlib,subprocess,hashlib
root=pathlib.Path.cwd()
sha=os.environ["GITHUB_SHA"]
destination=root/"legacy/internal/windowsclient/native_admin_preroute_real_crash_windows_test.go"
source="r0/go_overlay/ci/native_admin_preroute_real_crash_windows_test.go"
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
old=destination.read_bytes()
assert blob(old)=="18876a185c2d1504379e81f9e5622dfbdf6f367a","exact pinned donor altered"
patch=subprocess.check_output(["git","show",sha+":"+source])
assert blob(patch)=="672c9ee126899f2300f161560c2cd91f5fbb55f2","new M0 test fixture source SHA drift"
assert b"n4RetirePinnedGhostPreRouteWAL" in patch
destination.write_bytes(patch)
assert blob(destination.read_bytes())==blob(patch)
print("M0_PLAN020_EXACT_M0_NATIVE_CRASH_TEST_SOURCE_POST_PINNED_DONOR_PASS")
'@ | python -
if ($LASTEXITCODE -ne 0) {throw 'exact M0 post-donor native crash test SOURCE rejected'}

Push-Location legacy
try {
  & go test -c -o ../result/wintun-release/m0-actual-ip-mtu-dns.exe ./internal/windowsclient
  if ($LASTEXITCODE -ne 0) {throw 'real native OS WAL test compilation FAIL'}
} finally {Pop-Location}
$env:WBD_N4_ADMIN_UNIFIED_WAL='1'
$env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT=(Join-Path (Resolve-Path result).Path 'real-ip-mtu-dns-wal.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedUnifiedWALRealLeaseMTUDNS$' 2>&1 | Tee-Object -FilePath result/m0-real-native-wal-apply-recover.log
if ($LASTEXITCODE -ne 0) {throw 'native real IP/MTU/DNS WAL Apply Recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT)) {throw 'missing actual OS Apply Recover readback report'}
$wal=Get-Content $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT -Raw | ConvertFrom-Json
if ($wal.source_sha -ne $env:GITHUB_SHA -or $wal.result -ne 'SCOPED_REAL_WINTUN_NATIVE_WAL_APPLY_RECOVER_PASS') {
  throw ('real IP/MTU/DNS WAL Apply Recover NOT_RUN or failed: '+$wal.result)
}
foreach ($field in @('lease','mtu','dns')) {
  if ($wal.$field -notlike 'PASS_*') {throw ('real native OS WAL stage missing '+$field)}
}
if ($wal.guard -ne 'TEST_ONLY_FAKE_NOT_PRODUCTION_WFP' -or $wal.routes -ne 'TEST_ONLY_FAKE_NO_CAPTURE_ROUTES') {
  throw 'native OS receipt falsely claims real host-global WFP or two /1 capture routes'
}
Write-Output 'M0_PLAN020_SAME_SOURCE_REAL_WIN_NATIVE_IP_MTU_DNS_WAL_APPLY_RECOVER_STOP_PASS_SCOPED_WFP_ROUTES_NOT_RUN'

$env:WBD_N4_ADMIN_PREROUTE_CRASH_PROBE='1'
$env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT=(Join-Path (Resolve-Path result).Path 'real-native-process-crash.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedRealPreRouteIPCrashWAL$' 2>&1 | Tee-Object -FilePath result/m0-real-process-crash-wal.log
if ($LASTEXITCODE -ne 0) {throw 'real child TerminateProcess and native WAL recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT)) {throw 'missing real child crash native OS WAL report'}
$crash=Get-Content $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT -Raw | ConvertFrom-Json
if ($crash.source_sha -ne $env:GITHUB_SHA -or $crash.result -like 'UNSUPPORTED*' -or $crash.result -eq 'FAIL_UNFINISHED') {
  throw ('real child crash OS WAL Recover NOT qualified: '+$crash.result)
}
if ($crash.wfp -ne 'FAKE_ONLY' -or $crash.routes -ne 'NOT_RUN') {
  throw 'real child crash falsely qualified global WFP /1 default routes'
}
Write-Output ('M0_PLAN020_REAL_WINDOWS_CHILD_CRASH_NATIVE_OS_WAL_RESULT='+$crash.result)
 2>&1 | Tee-Object -FilePath result/m0-original-game-rust-wintun-kernel-actual.log
if ($LASTEXITCODE -ne 0) {throw 'real original-Go Windows Game2/4 TLS Rust native signed Wintun first/reverse noHOL test FAIL'}
$game=(Get-Content result/m0-original-game-rust-wintun-kernel-actual.log -Raw)
foreach($lane in @(2,4)){
 if (!$game.Contains('M0_PLAN024_ORIGINAL_GO_TLS_WINDOWS_GAME'+$lane+'_NATIVE_RUST_M4_SIGNED_WINTUN_KERNEL_APP_LANE1_BLOCKED_FIRST_REVERSE_NO_HOL_STOP_PASS_SCOPED')){
   throw ('native original TLS Game group app marker NOT_RUN lanes='+$lane)
 }
}
if ($game -match 'UNSUPPORTED|--- SKIP:') {throw 'real original Go Game2/4 signed Wintun test skipped'}
Write-Output 'M0_PLAN024_WINDOWS_REAL_ORIGINAL_GO_GAME2_GAME4_NATIVE_TLS_RUST_WINTUN_FIRST_REVERSE_NOHOL_PASS_SCOPED'



# M0-only exact SOURCE post-donor test override. This does not change the
# 12 pinned Windows donor paths nor any production implementation. Check
# full original Git donor SHA BEFORE replacing only the isolated TEST file.
@'
import os,pathlib,subprocess,hashlib
root=pathlib.Path.cwd()
sha=os.environ["GITHUB_SHA"]
destination=root/"legacy/internal/windowsclient/native_admin_preroute_real_crash_windows_test.go"
source="r0/go_overlay/ci/native_admin_preroute_real_crash_windows_test.go"
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
old=destination.read_bytes()
assert blob(old)=="18876a185c2d1504379e81f9e5622dfbdf6f367a","exact pinned donor altered"
patch=subprocess.check_output(["git","show",sha+":"+source])
assert blob(patch)=="672c9ee126899f2300f161560c2cd91f5fbb55f2","new M0 test fixture source SHA drift"
assert b"n4RetirePinnedGhostPreRouteWAL" in patch
destination.write_bytes(patch)
assert blob(destination.read_bytes())==blob(patch)
print("M0_PLAN020_EXACT_M0_NATIVE_CRASH_TEST_SOURCE_POST_PINNED_DONOR_PASS")
'@ | python -
if ($LASTEXITCODE -ne 0) {throw 'exact M0 post-donor native crash test SOURCE rejected'}

Push-Location legacy
try {
  & go test -c -o ../result/wintun-release/m0-actual-ip-mtu-dns.exe ./internal/windowsclient
  if ($LASTEXITCODE -ne 0) {throw 'real native OS WAL test compilation FAIL'}
} finally {Pop-Location}
$env:WBD_N4_ADMIN_UNIFIED_WAL='1'
$env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT=(Join-Path (Resolve-Path result).Path 'real-ip-mtu-dns-wal.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedUnifiedWALRealLeaseMTUDNS$' 2>&1 | Tee-Object -FilePath result/m0-real-native-wal-apply-recover.log
if ($LASTEXITCODE -ne 0) {throw 'native real IP/MTU/DNS WAL Apply Recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT)) {throw 'missing actual OS Apply Recover readback report'}
$wal=Get-Content $env:WBD_N4_ADMIN_UNIFIED_WAL_REPORT -Raw | ConvertFrom-Json
if ($wal.source_sha -ne $env:GITHUB_SHA -or $wal.result -ne 'SCOPED_REAL_WINTUN_NATIVE_WAL_APPLY_RECOVER_PASS') {
  throw ('real IP/MTU/DNS WAL Apply Recover NOT_RUN or failed: '+$wal.result)
}
foreach ($field in @('lease','mtu','dns')) {
  if ($wal.$field -notlike 'PASS_*') {throw ('real native OS WAL stage missing '+$field)}
}
if ($wal.guard -ne 'TEST_ONLY_FAKE_NOT_PRODUCTION_WFP' -or $wal.routes -ne 'TEST_ONLY_FAKE_NO_CAPTURE_ROUTES') {
  throw 'native OS receipt falsely claims real host-global WFP or two /1 capture routes'
}
Write-Output 'M0_PLAN020_SAME_SOURCE_REAL_WIN_NATIVE_IP_MTU_DNS_WAL_APPLY_RECOVER_STOP_PASS_SCOPED_WFP_ROUTES_NOT_RUN'

$env:WBD_N4_ADMIN_PREROUTE_CRASH_PROBE='1'
$env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT=(Join-Path (Resolve-Path result).Path 'real-native-process-crash.json')
& ./result/wintun-release/m0-actual-ip-mtu-dns.exe '-test.v=true' '-test.timeout=5m' '-test.run=^TestN4WindowsHostedRealPreRouteIPCrashWAL$' 2>&1 | Tee-Object -FilePath result/m0-real-process-crash-wal.log
if ($LASTEXITCODE -ne 0) {throw 'real child TerminateProcess and native WAL recover FAIL'}
if (!(Test-Path -LiteralPath $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT)) {throw 'missing real child crash native OS WAL report'}
$crash=Get-Content $env:WBD_N4_ADMIN_PREROUTE_CRASH_REPORT -Raw | ConvertFrom-Json
if ($crash.source_sha -ne $env:GITHUB_SHA -or $crash.result -like 'UNSUPPORTED*' -or $crash.result -eq 'FAIL_UNFINISHED') {
  throw ('real child crash OS WAL Recover NOT qualified: '+$crash.result)
}
if ($crash.wfp -ne 'FAKE_ONLY' -or $crash.routes -ne 'NOT_RUN') {
  throw 'real child crash falsely qualified global WFP /1 default routes'
}
Write-Output ('M0_PLAN020_REAL_WINDOWS_CHILD_CRASH_NATIVE_OS_WAL_RESULT='+$crash.result)
