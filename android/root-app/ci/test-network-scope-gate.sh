#!/usr/bin/env bash
# Pure Java session-decision test, NOT an Android Framework runtime gate.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
# A34a: parse exact original Linux Oracle shell before expensive native builds.
bash -n android/root-native/ci/linux-original-oracle.sh
bash -n android/root-app/ci/x86-original-linux-server-prep.sh
mkdir -p out/android-root-app/network-scope-test
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/NetworkScopeGate.java \
  android/root-app/ci/NetworkScopeGateTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.NetworkScopeGateTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootStopCommand.java \
  android/root-app/ci/RootStopCommandTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootStopCommandTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java \
  android/root-app/src/org/wbdnext/rootclient/RootRecoveryCommand.java \
  android/root-app/ci/RootRecoveryCommandTest.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootRecoveryCommandTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/ci/InstalledAppTargetTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.InstalledAppTargetTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/ci/SelectedAppGroupTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.SelectedAppGroupTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/ci/AllAppUIDPolicyTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.AllAppUIDPolicyTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/ci/ServerAddressTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.ServerAddressTest
# Execute the EXACT production RootService original Go argv builder on the
# host JVM. No Android guest, fake Network, Root permission or packet I/O.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java \
  android/root-app/ci/OriginalGoCommandArgsTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.OriginalGoCommandArgsTest
# A32 real Host POSIX filesystem metadata test of the EXACT production
# Android pre-su 0600 credential policy (no guest, NIC, Root or fake TLS).
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialContract.java \
  android/root-app/ci/RootPrivateCredentialContractTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootPrivateCredentialContractTest
# Actual Lite v2 Java KDF + immutable cache HMAC, matched to main Go
# short_test.go vectors. Pure local JVM, no Root, server, network or fake TLS.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootRouteKeyV2.java \
  android/root-app/ci/RootRouteKeyV2Test.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootRouteKeyV2Test
# Exact production Root Service diagnostic writer, not a fabricated
# Android guest or Go/TLS success. Verify fixed enums, bounded retention,
# no untrusted metadata and Device acceptance report semantics.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/ci/RootDiagnosticReceiptTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDiagnosticReceiptTest
# Actual production report filtering and last-stage derivation; NEVER fake
# a Root device, fetch logcat, reveal source raw stdout or touch network.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java \
  android/root-app/ci/RootDiagnosticReportTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDiagnosticReportTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoMilestones.java \
  android/root-app/ci/OriginalGoMilestonesTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.OriginalGoMilestonesTest
PYTHONPATH=android/root-app/ci python3 -m unittest -v device_first_run_test
python3 android/root-app/ci/test-device-selftest-source.py
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootUidTunPacketScript.java \
  android/root-app/ci/RootUidTunPacketScriptTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootUidTunPacketScriptTest
python3 - <<'PY'
from pathlib import Path
s=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
for method in ("registerNetworkCallback(", "unregisterNetworkCallback(",
 "onLost(", "onLinkPropertiesChanged(", "onCapabilitiesChanged(",
 "onBlockedStatusChanged("):
 assert method in s, method
assert "postDelayed(" not in s, "no 1-second steady Network watcher"
assert "getNetworkCapabilities(" not in s and "getLinkProperties(" not in s, "no synchronous ConnectivityManager lookup inside callback"
assert 'read oldpid oldstart oldgeneration <' in s, "owner.pid has 3 fields; never fold generation into oldstart"
# A30: user's real Android API36 EXIT_1 PRE_TUN receipt must be
# classifiable only by actual fixed markers from the ROOT shell and
# original Go Bionic entry. Never capture native raw stdout in reports.
go_src=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
# A32 fixed-string checks use the same original Go parser source. Keep
# this alias before all credential gates, not below their first use.
cold=go_src
receipt=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
report=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
for marker in ["WBD_PUBLIC_ROOT_SHELL_ENTERED","WBD_PUBLIC_ROOT_UID_VERIFIED","WBD_PUBLIC_ROOT_PRIVATE_DIR_VERIFIED","WBD_PUBLIC_ROOT_OWNER_GUARD_PASSED","WBD_PUBLIC_ROOT_NATIVE_FILES_STAGED","WBD_PUBLIC_ROOT_OWNER_PID_WRITTEN","WBD_PUBLIC_ROOT_EXEC_ATTEMPTED"]:
 assert marker in s, "fixed Root shell stage missing: "+marker
for marker in ["V4_PUBLIC_ANDROID_GO_ENTRY role=client","V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client","V4_PUBLIC_ANDROID_GO_ARGS_ACCEPTED role=client","V4_PUBLIC_ANDROID_GO_INTERFACE_FOUND role=client","V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client","V4_PUBLIC_ANDROID_GO_TUN_OPENED role=client"]:
 assert marker in go_src and marker in s, "original Go stage not connected: "+marker
for event in ["START_DIAGNOSTIC_STAGES_V2","ROOT_PROCESS_EXIT_1","ROOT_SHELL_EXEC_ATTEMPTED","ORIGINAL_GO_ENTRY","ORIGINAL_GO_ARGS_REJECTED","ORIGINAL_GO_TUN_OPEN_ATTEMPTED"]:
 assert event in receipt, "diagnostic enum missing: "+event
assert 'if(has(session,"START_DIAGNOSTIC_STAGES_V2")' in report, "legacy receipts must not be misdiagnosed"
assert 'last_session_stage=' in report
assert 'OriginalGoMilestones.matches(line,' in s
assert 'echo WBD_PUBLIC_ROOT_EXEC_ATTEMPTED' in s
assert 'log.Print("V4_PUBLIC_ANDROID_GO_ENTRY role=client")' in go_src

assert s.count('InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)')>=2, "multi UID identity rechecked on Service and pre-su"
assert 'watchSelectedPackages(allApps?managerPackages:targetPackages)' in s and 'stopWatchingSelectedPackage()' in s, "withdraw selected group or manager exclusions on package events"
assert 'AllAppRouteScope.same(this,excludedAppIDs,managerPackages)' in s, "verify full-app owner+manager UID exclusions before su"
argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
assert 'OriginalGoCommandArgs.build(' in s, "production RootService must use host-tested original Go argv"
assert 'for(String a:args)quotedArgs.add(q(a))' in s, "every native argv token is shell quoted"
assert '"--android-route-all-apps"' in argv and '"--android-route-exclude-appids"' in argv, "original Go full-app CLI"
assert 'AllAppUIDPolicy.csv(excludedAppIDs)' in argv, "canonical app ID exclusions"
assert '"--android-route-uids"' in argv and '"--android-route-uid"' in argv, "original Go single and group UID flags"
assert 'ServerAddress.isIPv4Literal(peer)?"--peer-ip":"--peer-host"' in argv
assert 'ServerAddress.valid(peer)' in s
a=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'target_packages' in a and 'target_uids' in a
assert 'SelectedAppGroup.from(' in a and 'InstalledAppCatalog.stillSameGroup(' in a
assert 'Integer.parseInt(uid.getText()' not in a, "no arbitrary hand-entered UID"
assert 'CheckBox' in a and 'appChoices' in a, "real visible multi-App selections"
assert 'allAppsDefault.setChecked(true)' in a, "all ordinary Android applications are the product UI default"
assert 'AllAppRouteScope.snapshot(this)' in a and 'all_apps' in a, "default mode must pass verified scopes not fake overlay"

assert 'ServerAddress.valid(peer)' in a and 'Server underlay IPv4 or DNS name' in a
assert 'RootRouteKeyCache.resolve(this,sni,keyInput)' in a
assert 'privateText("wbd-route.secret",key+"\\n")' in a, "the original Go still reads only the canonical 32B hex secret file"
# Verified device bug: AOSP ContextImpl.MODE_PRIVATE can create 0660,
# original Go readPrivateArgFile intentionally rejects any group bits.
writer=Path("android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialFiles.java").read_text()
contract=Path("android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialContract.java").read_text()
assert 'RootPrivateCredentialFiles.write(this,file,text);' in a
assert 'openFileOutput(file,Context.MODE_PRIVATE)' not in a
for required in ('Os.open(path.getAbsolutePath()', 'OsConstants.O_NOFOLLOW',
  'OsConstants.O_CLOEXEC', 'Os.fchmod(fd,RootPrivateCredentialContract.OWNER_ONLY)',
  'verifyStat(Os.fstat(fd)', 'Os.lstat(', 'verifyAtStart(Context ctx,boolean hasCA)'):
 assert required in writer, required
assert '(mode&0777)==OWNER_ONLY' in contract and 'st.st_nlink' in writer
assert 'RootPrivateCredentialFiles.verifyAtStart(this,hasCA)' in s
assert 'APP_PRIVATE_CREDENTIALS_UNSAFE' in s
assert 'APP_PRIVATE_CREDENTIALS_0600_VERIFIED' in s
assert 'st.Mode().Perm()&0077!=0' in cold, "never relax original Go private read check"

assert 'String key=RootRouteKeyCache.resolve(this,sni,keyInput);' in a
assert 'RootRouteKeyV2.legacyHex(supplied)' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'file.readFully()' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'Os.chmod(destination.getAbsolutePath(),0600)' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'AtomicFile' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'PBKDF2WithHmacSHA256' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyV2.java").read_text()
cold=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
go=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
assert 'rootjournal.NewGroup(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uids=' in go
assert 'rootjournal.NewAllApps(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED mode=all_apps' in go
assert 'ServerIP:c.peerIP.String()' in go
assert 'V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client' in go
assert 'SERVER_PEER_THROW_PRIVATE_FIB_READBACK' in s
assert 'androidRouteAllApps' in cold and 'android-route-all-apps' in cold
# A31: original Go Run's parse rejection must emit only the fixed
# allowlisted category and never return dynamic error strings to the report.
assert 'originalAndroidColdParseClass(err)' in cold
assert 'V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s' in cold
assert 'log.Printf("V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s"' in cold
report=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
receipt=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
for field in (
  "FLAG_SYNTAX", "PASSWORD_FILE", "ROUTE_KEY_FILE", "ROUTE_KEY_VALUE",
  "INSTALLATION_ID", "CN_GEOSITE_FILE", "TLS_CA_FILE",
  "ALL_APP_EXCLUSIONS", "ANDROID_NETWORK_SCOPE", "PEER_ADDRESS",
  "REQUIRED_COLD_SETTINGS", "POLICY", "OTHER"):
 assert ("ORIGINAL_GO_PARSE_"+field) in s and ("ORIGINAL_GO_PARSE_"+field) in receipt
 assert ("ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_"+field) in report
assert "return \"ORIGINAL_GO_ARGUMENT_PARSE_REJECTED\";" in report

allapp=Path("r0/go_overlay/internal/v4productcli/rootjournal/allapps.go").read_text()
assert 'func NewAllApps(' in allapp and 'requireReady(original)' in allapp and 'readOwnedJournalVersion(' in allapp
assert 'AllAppIDMin = 10000' in allapp and 'AllAppIDMax = 19999' in allapp
assert 'allMaxUserProfiles = 20' in allapp and 'ExcludedAppIDs' in allapp
assert 'peerThrowArgs("add",original.ServerIP)' in allapp
assert 'peerThrowArgs("del",p.ServerIP)' in allapp
assert 'legacyAllAppsVersion = 3' in allapp
assert 'Intent.ACTION_CREATE_DOCUMENT' in a, "system SAF safe-report export"
assert 'RootDiagnosticReport.build(getFilesDir()' in a

j=Path("r0/go_overlay/internal/v4productcli/rootjournal/group.go").read_text()
assert 'func NewGroup(' in j and 'readOwnedJournalVersion(' in j and 'groupRuleState(' in j
# B2b source-lock: an actual signed asset is verified and handed as an
# app-private path to the ORIGINAL Go cold parser, not a Java fake packet
# handler or claimed Android DNS network state.
payload=Path("android/root-app/src/org/wbdnext/rootclient/NativePayload.java").read_text()
assert 'PINNED_CN_SHA256' in payload and 'cn-geosite-provenance.json' in payload
assert '"wbd-cn-geosite.txt",PINNED_CN_SHA256,6000000' in payload
assert 'new NativePayload(go,rust,cn,source,executable)' in payload
assert 'armAssets==x86Assets' in payload, 'only one signed ABI allowed'
assert '(!armAssets&&m.optBoolean("release",true))' in payload, 'x86 must be CI-only'
assert 'signed native ABI not supported by OS' in payload
assert 'libwbd_engine-' in payload and 'wbd-v4-client-' in payload, 'one original ABI-selected Go/Rust'
assert 'ownerExecutable=code.executableName' in s, 'exact original GO executable at Stop'
assert 'nativeCode.cnGeosite.getAbsolutePath()' in s and '"--android-cn-geosite-file"' in argv
cold=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
assert 'cnGeositeFile:=flags.String("android-cn-geosite-file"' in cold
assert 'dnsnative.ReadPinnedCNFile(*cnGeositeFile)' in cold
assert 'dns_capture=NOT_CONNECTED' in cold
assert 'peerHost:=flags.String("peer-host"' in cold
assert 'dnsnative.ResolveBootstrapIPv4(' in cold
assert 'V4_PUBLIC_ANDROID_SERVER_BOOTSTRAP_PHYSICAL_RESOLVED' in cold
typed=Path("r0/go_overlay/internal/v4productcli/dnsnative/cn_rules.go").read_text()
assert 'syscall.O_NOFOLLOW|syscall.O_NONBLOCK' in typed
assert 'st.Mode().Perm()!=0600' in typed
assert 'return ReadPinnedCN(f)' in typed
print("ANDROID_B2B_SIGNED_GEOSITE_TO_ORIGINAL_GO_COLD_SOURCE_GATE_PASS")
m=Path("android/root-app/AndroidManifest.xml").read_text()
assert '<queries>' in m and '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"' not in m, "narrow package visibility"
# The exact POSIX read arity must preserve kernel starttime for both
# existing old 2-field receipts and current 3-field receipts.
import subprocess,tempfile
with tempfile.TemporaryDirectory() as td:
    for payload,expected in (("123 9876","123|9876|"),
                             ("123 9876 abcdef","123|9876|abcdef")):
        p=Path(td)/"owner.pid"
        p.write_text(payload+chr(10))
        cmd='read pid start generation < "$1"; printf "%s|%s|%s" "$pid" "$start" "$generation"'
        result=subprocess.run(["sh","-c",cmd,"sh",str(p)],capture_output=True,text=True,check=True)
        assert result.stdout==expected,(payload,result.stdout)
print("ANDROID_ROOT_OWNED_PID_2_AND_3_FIELD_PARSE_PASS")
# Same-source fixed-enum, credential-free diagnostic receipts; never
# echo arbitrary native stdout and never count a Stop TERM as joined Stop.
assert 'OriginalGoMilestones.matches(' in s
assert 'ROOT_OR_NATIVE_EXIT_' in s and 'SYNACK_PRE_AUTH' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_KERNEL_CONFIGURED' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_RAW_SOCKET_READY' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN' in s
assert 'WBD_ROOT_DIAG' in s
assert 'RootDiagnosticReceipt.Event.NATIVE_M4_AND_UID_READY' in s
assert 'RootDiagnosticReceipt.Event.STOP_SIGNAL_ACCEPTED' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_RUST_STOP_JOINED' in s
assert 'RootDiagnosticReceipt.Event.AUTHENTICATED_LEASE_OS_READBACK' in s
assert 'RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED' in s
assert 'Log.i("WBD_ROOT_DIAG",event.name())' in s
accept=Path("android/root-app/ci/device_first_run.py").read_text()
assert '"real_android_linux_tls_and_data_e2e": "NOT_RUN"' in accept
assert '"original_go_rust_joined_stop":' in accept
assert '"ORIGINAL_GO_RUST_STOP_JOINED"' in accept
for cold_stage in ("ORIGINAL_GO_TUN_KERNEL_CONFIGURED",
                   "ORIGINAL_GO_RAW_SOCKET_READY",
                   "ORIGINAL_GO_TCP_SYNACK_SEEN"):
    assert cold_stage in accept, "first-run receipt must retain native cold-stage codes"
assert '"AUTHENTICATED_LEASE_OS_READBACK"' in accept
assert 'FIB table does not exist' in accept
assert '"wbdv40"' in accept
assert 'sudo' not in accept and 'pkill' not in accept
print("ANDROID_ROOT_DEVICE_DIAGNOSTIC_AND_OPERATOR_BUNDLE_HOST_PASS")

# A33 cold diagnostics must observe original stage sites, never fabricate TLS
# or promote a candidate SYNACK into an accepted FakeTCP association.
go_product=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
go_admission=Path("r0/go_overlay/internal/realityfront/admission_v4.go").read_text()
assert go_product.index('V4_PUBLIC_ANDROID_ORIGINAL_ASSOC_ESTABLISHED role=client') > go_product.index('waitForOriginalColdSYN(dialCtx,assoc)')
assert 'V4_PUBLIC_ANDROID_TLS_HANDSHAKE_ATTEMPTED role=client' in go_admission
assert go_admission.index('V4_PUBLIC_ANDROID_TLS_HANDSHAKE_VERIFIED role=client') > go_admission.index('handshakeClientConn(ctx,conn,tlsCfg)')
assert go_admission.index('V4_PUBLIC_ANDROID_PROTECTED_REPLY_PARSED role=client') > go_admission.index('v4ReadReply(client,req)')
assert go_admission.index('V4_PUBLIC_ANDROID_ADMISSION_VERIFIED role=client') > go_admission.index('v4ColdSnapshot(result,extension.Epoch')
assert 'v4AndroidColdFailureClass(err)' in go_admission
for event in ("ORIGINAL_GO_ASSOC_ESTABLISHED","ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED",
              "ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED","ORIGINAL_GO_ADMISSION_VERIFIED",
              "ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED"):
 assert event in s and event in receipt and event in report
assert 'SYNACK_CANDIDATE_ASSOC_NOT_PROVEN' in report
print("ANDROID_A33_ORIGINAL_COLD_TLS_NO_FAKE_WIRE_SOURCE_GATE_PASS")
# A34: actual original output/peer ingress, no fake ClientHello or no-TLS fallback.
assert 'observedEmit:=func(seg faketcp.Segment)error' in go_product
assert go_product.index('V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_OK role=client') > go_product.index('e:=emit(seg)')
assert 'firstPeerPayloadRX.CompareAndSwap(false,true)' in go_product
assert 'v4AndroidClassAtDeadline(err,guard.Remaining())' in go_admission
for ev in ("ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK",
           "ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX",
           "ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED",
           "ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER"):
 assert ev in s and ev in receipt
print("ANDROID_A34_ORIGINAL_TLS_WIRE_SOURCE_GATE_PASS")
# A35 exact 4-tuple RST suppression MUST only run on actual Android root,
# before the original SYN, with durable journal and exact Stop readback.
rst=Path("r0/go_overlay/internal/v4productcli/rstguard/guard.go").read_text()
test=Path("r0/go_overlay/internal/v4productcli/rstguard/guard_test.go").read_text()
assert go_product.index('V4_PUBLIC_ANDROID_COLD_RST_GUARD_READY role=client') < go_product.index('reauthAuthorized:=false')
assert go_product.index('reauthAuthorized:=false') < go_product.index('runClient(ctx,cfg,')
for required in ('--sport','--dport','--tcp-flags','--comment','-o','-s','-d',
                 'O_NOFOLLOW','O_EXCL','LOCK_NB','ErrCleanup','DropCounter'):
 assert required in rst
assert 'FakeTCP' in test or 'TestScopedRSTGuard' in test
for marker in ("ORIGINAL_GO_COLD_RST_GUARD_READY",
               "ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED",
               "ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE"):
 assert marker in s and marker in receipt and marker in report or marker.endswith("READY")
# Every original Android/Linux server assembly must copy the same pure-Go
# guard package. Missing x86 D2-S0 donor copy caused first A35 D2-S0 FAIL.
for assembler in ("android/root-native/build-source-locked.sh",
                  "android/root-native/ci/linux-original-oracle.sh",
                  "android/root-app/ci/x86-original-linux-server-prep.sh"):
    text=Path(assembler).read_text()
    assert 'cp r0/go_overlay/internal/v4productcli/rstguard/*.go legacy/internal/v4productcli/rstguard/' in text
    assert 'go test -count=1 ./internal/v4productcli/rstguard' in text
print("ANDROID_A35_THREE_ORIGINAL_GO_DONOR_ASSEMBLIES_SOURCE_LOCKED_PASS")
print("ANDROID_A35_SCOPED_RST_GUARD_NO_GLOBAL_FIREWALL_SOURCE_PASS")
# A36 Restore only runs source-locked original-Go exact journal cleanup.
assert 'RootClientService.RESTORE' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert '--android-recover-owned-root' in Path("android/root-app/src/org/wbdnext/rootclient/RootRecoveryCommand.java").read_text()
assert 'rootjournal.RecoverOwned(' in go_product and 'rstguard.RecoverOwned(' in go_product
assert 'VerifyServer:true' in go_product
assert 'v4AndroidCertFailureReason(err)' in go_admission
for e in ("ROOT_RESTORE_COMPLETE","ROOT_RESTORE_FAILED","ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH"):
 assert e in s and e in receipt and e in report
print("ANDROID_A36_APP_RESTORE_CERT_TRUST_SOURCE_GATE_PASS")
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY
