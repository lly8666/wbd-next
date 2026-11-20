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
# A38 actual production AES-GCM record codec with standard JVM cipher;
# AndroidKeyStore adapter source is separately compiled by signed SDK36 APK.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootSavedCredentialRecord.java \
  android/root-app/ci/RootSavedCredentialRecordTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootSavedCredentialRecordTest
# The same production optional save wrapper used by the on-device START.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootStartCredentialSave.java \
  android/root-app/ci/RootStartCredentialSaveTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootStartCredentialSaveTest
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
assert 'flags.Bool("tls-verify-server",false' in go_product
assert 'VerifyServer:c.tlsVerifyServer' in go_product
assert 'c.tlsVerifyServer=role=="client"&&*verifyTLS' in go_product
assert 'tlsVerifyServer.setChecked(false)' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'request.putExtra("tls_verify_server",verifyTLS)' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'args.add("--tls-verify-server")' in argv
for ev in ("ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED","ORIGINAL_GO_TLS_CERT_VERIFY_ENABLED"):
 assert ev in s and ev in receipt
print("ANDROID_A37_MAIN_DEFAULT_TLS_CERT_VERIFY_OFF_SOURCE_PASS")
# A38: prove no second forced verify in the REAL protected admission;
# the user's A37 device showed disabled at parse but unknown CA at TLS.
assert 'tlsCfg.VerifyServer=true' not in go_admission
assert 'tlsCfg:=cfg.TLS' in go_admission
assert 'V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_EFFECTIVE role=client class=DISABLED' in go_admission
for ev in ('ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED',
           'ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_ENABLED'):
 assert ev in s and ev in receipt
print("ANDROID_A38_NO_ORIGINAL_ADMISSION_CERT_OVERRIDE_SOURCE_GATE_PASS")
# UI plaintext secrets never go to SharedPreferences, Intent or logging.
store=Path("android/root-app/src/org/wbdnext/rootclient/RootEncryptedCredentialStore.java").read_text()
codec=Path("android/root-app/src/org/wbdnext/rootclient/RootSavedCredentialRecord.java").read_text()
for token in ('AndroidKeyStore','KeyGenParameterSpec','KeyProperties.BLOCK_MODE_GCM',
              'getNoBackupFilesDir()','AtomicFile','Os.fchmod','0600'):
 assert token in store
for token in ('AES/GCM/NoPadding','updateAAD(AAD)','cipher.doFinal','Arrays.fill'):
 assert token in codec
assert 'RootEncryptedCredentialStore.save(this,secret,keyInput)' in a
assert 'RootStartCredentialSave.attempt(' in a
assert 'UI_START_TAPPED' in a and 'UI_START_DISPATCHED' in a
assert 'UI_START_VALIDATION_REJECTED' in a and 'UI_START_DISPATCH_FAILED' in a
assert 'UI_CREDENTIAL_SAVE_FAILED' in a
assert 'RootEncryptedCredentialStore.load(this)' in a
assert 'RootEncryptedCredentialStore.clear(this)' in a
assert 'password.setText("")' in a and 'routeKey.setText("")' in a
assert 'request.putExtra("password"' not in a and 'request.putExtra("route_key"' not in a
assert 'cipher.init(Cipher.ENCRYPT_MODE,key);' in codec
assert 'cipher.getIV()' in codec
assert 'cipher.init(Cipher.ENCRYPT_MODE,key,new GCMParameterSpec' not in codec
# A40 real original post-auth transitions, not a synthetic lease.
postauth=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
androidbridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
for stage in ("COLD_OK","DETACH_OK","NATIVE_COMMIT_OK","LEASE_FIELD_OK","LEASE_OS_OK","NATIVE_IP_BOUND","UNDERLAY_OK","RAW_ATTACHED","TUN_ATTACHED","M4_STARTED","COLD_FAILED","DETACH_FAILED","NATIVE_PREPARE_FAILED","NATIVE_COMMIT_FAILED","NATIVE_OTHER_FAILED","LEASE_FIELD_FAILED","LEASE_ADD_FAILED","LEASE_DEL_FAILED","LEASE_READBACK_FAILED","LEASE_MISMATCH","LEASE_OS_FAILED","NATIVE_IP_BIND_FAILED","MTU_FAILED","UNDERLAY_FAILED","RAW_FAILED","TUN_FAILED","HEALTH_FAILED","M4_START_FAILED","UID_ROUTE_FAILED"):
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in s
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in receipt
 assert f'"{stage}"' in (postauth+go_product)
assert 'Operation:"original_native_prepare"' in androidbridge
assert 'Operation:"original_native_commit"' in androidbridge
assert 'V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s' in postauth
assert 'V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s' in go_product
# A41 Android native kernel lease readback uses the same getifaddrs
# interface API already proven on real device physical Network. This
# avoids Android-only external ip JSON "addr" parsing after successful add/del.
assert 'if runtime.GOOS=="android"{\n        iface,err:=net.InterfaceByName(name)' in go_product
assert 'addrs,err:=iface.Addrs()' in go_product
assert 'return originalV4OwnedTunIPv4FromNativeAddrs(addrs)' in go_product
assert 'func originalV4OwnedTunIPv4FromNativeAddrs(addrs []net.Addr)' in go_product
assert 'TestA41AndroidOriginalOwnedTunIPv4NativeGetifaddrs' in Path("r0/go_overlay/internal/v4productcli/android_native_tun_lease_readback_linux_test.go").read_text()
assert 'ANDROID_A41_ORIGINAL_ANDROID_GETIFADDRS_LEASE32_REAL_GO_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
# A42 original-Go Android post-M4 branches; no wire or sender change.
for stage in ("COLD_RTO_STOP_FAILED","DETACH_STATE_FAILED","GO_RX_FILTER_FAILED",
              "GO_RX_FILTER_OK","GO_RX_HANDOFF_OK","UID_ROUTE_ENTERED"):
 assert f'originalAndroidPostauthGo("{stage}")' in go_product
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in s
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in receipt
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in report
# A43: only original Android client Go's obsolete RX FD is retired.
raw_owner=Path("r0/go_overlay/internal/faketcp/raw_detached_data_linux.go").read_text()
raw_test=Path("r0/go_overlay/internal/faketcp/raw_detached_data_linux_test.go").read_text()
assert 'func (e *RawIPv4Endpoint) QuiesceDetachedClientReceive() error {' in raw_owner
assert 'Code: unix.BPF_RET | unix.BPF_K, K: 0' in raw_owner
assert 'return unix.SetsockoptSockFprog(e.recvFD,' in raw_owner
assert 'raw.QuiesceDetachedClientReceive()' in go_product
assert 'raw.ExcludeDetachedData(flow.PeerIP,flow.PeerPort)' in go_product
assert 'TestA43OriginalAndroidDetachedClientRXKernelQuiesce' in raw_test
assert 'ANDROID_A43_ORIGINAL_GO_CLIENT_RX_REAL_KERNEL_QUIESCE_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
# A44 original real M4 worker business counters + non-mutating UID route-get.
rust=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
aroute=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
parser=Path("r0/go_overlay/internal/v4productcli/rootjournal/effective_route.go").read_text()
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_loop_business_receipts(' in rust
assert 'originalAndroidBusinessReceipts()' in bridge
assert 'wbd_m0_embedded_go_loop_dns_ingress_observed' in bridge
for x in ('tun_ipv4_admitted.fetch_add(1','tun_ipv4_rejected.fetch_add(1',
          'business_raw_copied.fetch_add(1','business_reverse_tun.fetch_add(u64::from(delivered)'):
 assert x in rust,x
for x in ("TUN_IPV4_SEEN","TUN_IPV4_REJECTED","APP_RAW_TX_COPIED",
          "APP_REVERSE_TUN_WRITTEN","DNS_UDP53_TUN_SEEN","DNS_TCP53_TUN_SEEN"):
 assert f'ORIGINAL_RUST_{x}' in s and f'ORIGINAL_RUST_{x}' in receipt
 assert f'V4_PUBLIC_ANDROID_BUSINESS role=client class={x}' in s
for x in ("MATCHED_TUN","MISMATCH","UNAVAILABLE"):
 assert f'ORIGINAL_GO_UID_ROUTE_GET_{x}' in s and f'ORIGINAL_GO_UID_ROUTE_GET_{x}' in receipt
 assert f'V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class={x}' in s
assert 'originalAndroidSelectedUIDRouteGet(runner,' in aroute
assert 'SelectedUIDRouteGetUsesTun(out,tun)' in aroute
assert 'func SelectedUIDRouteGetUsesTun(' in parser
assert 'TestA44OriginalUIDEffectiveRouteGetParser' in Path("r0/go_overlay/internal/v4productcli/rootjournal/effective_route_test.go").read_text()
assert 'TestA44OriginalAndroidBusinessReceiptClasses' in Path("r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'ANDROID_A44_ORIGINAL_RUST_BUSINESS_WITNESS_CLASSIFIER_REAL_GO_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'wbd_m0_embedded_go_loop_business_receipts' in Path("android/root-native/build-source-locked.sh").read_text()
# A45: do not mistake second-app ICMP outside selected UIDs for data-plane FAIL.
# Android original Rust callback is an actual read-only M4 worker counter,
# never shell ping, Go per-packet processing, fabricated server or UI READY.
native=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
adapter=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
builder=Path("android/root-native/build-source-locked.sh").read_text()
goproduct=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
gotest=Path("r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'fn wbd_m0_embedded_go_loop_return_path_receipts(' in native
assert 'originalAndroidReturnPathReceipts()' in adapter
assert 'wbd_m0_embedded_go_loop_return_path_receipts' in builder
assert 'stats.raw_poll_ready.fetch_add(1' in native
assert 'stats.raw_parse_failed.fetch_add(1' in native
assert 'stats.raw_authenticated.fetch_add(1' in native
assert 'stats.raw_auth_rejected.fetch_add(' in native
assert 'stats.reverse_tun_write_failed.fetch_add(' in native
assert 'match head[9]' in native
for field in ('tun_icmp.fetch_add(1','tun_tcp.fetch_add(1','tun_udp.fetch_add(1'):
 assert field in native,field
assert 'TestA45OriginalAndroidReturnPathReceiptClasses' in gotest
assert 'ANDROID_A45_ORIGINAL_RETURN_PATH_AND_ICMP_CLASSIFIER_GO_HOST_PASS' in Path('android/root-native/ci/linux-original-oracle.sh').read_text()
for name in ("RAW_SOCKET_READABLE","RAW_PARSE_FAILED","RAW_PARSED",
             "RAW_AUTHENTICATED","RAW_AUTH_REJECTED","REVERSE_TUN_WRITE_FAILED",
             "TUN_ICMP_SEEN","TUN_TCP_SEEN","TUN_UDP_SEEN"):
 assert f'ORIGINAL_RUST_{name}' in s and f'ORIGINAL_RUST_{name}' in receipt
 assert f'V4_PUBLIC_ANDROID_BUSINESS role=client class={name}' in s
 assert f'"{name}"' in goproduct
# A46: copy EXACT main's already-landed Windows H2216 Linux/Android
# shared Rust parser. No new TTL interpretation and no M3 bypass.
main_ttl=Path("crates/wbd-platform/src/rx_ipv4_tcp.rs").read_text()
android_io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
linux_io=Path("crates/wbd-platform/src/linux_raw_carrier.rs").read_text()
assert 'if packet[8] == 0 { return Err(RxError::WrongIpHeader); }' in main_ttl
assert 'if packet[8]==0{return Err(RxError::WrongIpHeader)}' in main_ttl
assert 'if packet[8] != trusted.persona.ttl()' not in main_ttl
assert 'if packet[8]!=trusted.persona.ttl()' not in main_ttl
assert 'fn h2216_original_windows_128_to_116_client_public_nat_data_and_ack()' in main_ttl
assert 'PacketPersona::Windows11, 116u8' in main_ttl
assert 'PacketPersona::Legacy, 52u8' in main_ttl
assert 'RxError::IpChecksum' in main_ttl
assert 'crate::rx_ipv4_tcp::parse_data_packet(' in android_io
# main Linux single kernel raw / multi-buffer receive both call the
# H2216 shared parser; n and len are distinct source-local variable names.
assert 'parse_data_packet(&slot[..n],trusted)' in linux_io
assert 'parse_ack_packet(&slot[..n],trusted,false)' in linux_io
assert 'parse_data_packet(&slot[..len],TrustedRx{' in linux_io
assert 'parse_ack_packet(&slot[..len],TrustedRx{' in linux_io
assert 'ANDROID_A46_MAIN_WINDOWS_H2216_ROUTED_TTL_DATA_ACK_RUST_HOST_PASS' in Path('android/root-native/ci/linux-original-oracle.sh').read_text()
# A47 actual same-socket RAW recv metadata, precise rejection buckets,
# seq/owner handoff outcomes; 4-second cumulative Go snapshots survive
# the Java APK file/report boundary via a strict numeric-only allowlist.
nativeio=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
nativeworker=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
gobridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
appwrite=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
appreport=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
for name in ("RX_DATA_OK","RX_PURE_ACK","RX_TUPLE_BAD","RX_IP_CHECKSUM_BAD",
             "RX_TCP_CHECKSUM_BAD","RX_FLAGS_BAD","RX_LENGTH_BAD",
             "RX_OPTIONS_BAD","RX_SEQ_BAD","RX_OWNER_OFFER_BAD",
             "RX_LAST_SRC_IP","RX_LAST_DST_IP","RX_LAST_FLAGS"):
 assert name in nativeio,name
assert 'read_original_record(' in nativeio
assert 'parse_ack_packet(' in nativeio
assert 'driver.record_seq_reject()' in owner
assert 'driver.record_owner_offer_reject()' in owner
assert 'fn wbd_m0_embedded_go_loop_raw_rx_debug(' in nativeworker
assert 'C.wbd_m0_embedded_go_loop_raw_rx_debug(' in gobridge
assert 'wbd_m0_embedded_go_loop_raw_rx_debug' in Path("android/root-native/build-source-locked.sh").read_text()
assert 'originalAndroidM4RxSnapshot(' in go_product
assert 'originalAndroidM4OwnerSnapshot(' in go_product
assert 'TestA47OriginalNumericNativeM4Snapshots' in Path(
 "r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'ANDROID_A47_REAL_ORIGINAL_GO_NUMERIC_M4_SNAPSHOT_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'diagnostics.recordNativeSnapshot(line.substring(forensic))' in s
assert 'static boolean safeNativeSnapshot(String raw)' in appwrite
assert 'native_m4_numeric_debug_samples:' in appreport
assert 'ANDROID_A47_NATIVE_NUMERIC_M4_REAL_APK_REPORT_HOST_PASS' in Path(
 "android/root-app/ci/RootDiagnosticReportTest.java").read_text()
# A48: API36 source-locked physical handset actually returned 114
# original Rust RAW RX packets: 113 strict TCP checksum mismatches, zero
# tuple/IP/flags/length mismatches; normal M3 never saw them. Preserve
# strict Windows/Linux parser; ONLY Android Bionic may supply an untrusted
# candidate when every other original IPv4/TCP check has passed.
parser=Path("crates/wbd-platform/src/rx_ipv4_tcp.rs").read_text()
android_io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
linux_io=Path("crates/wbd-platform/src/linux_raw_carrier.rs").read_text()
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
assert 'parse_data_packet_checked(packet,trusted,true)' in parser
assert 'fn parse_data_packet_android_m3_pending' in parser
assert '#[cfg(any(target_os="android",test))]' in parser
assert 'parse_data_packet_checked(packet,trusted,false)' in parser
assert 'if require_tcp_checksum {' in parser
assert 'if require_tcp_checksum && !checksum_is_valid(sum)' not in parser
assert 'sum = add_bytes(sum, tcp);' in parser
assert 'a48_android_m3_pending_accepts_only_tcp_checksum_drift_as_untrusted' in parser
assert 'let parsed=match crate::rx_ipv4_tcp::parse_data_packet_android_m3_pending(' in android_io
assert 'if (observed&127)==0' in android_io
assert 'self.debug[RX_TCP_CHECKSUM_BAD].fetch_add(1' in android_io
assert 'self.debug[RX_DATA_OK].fetch_add(1' in android_io
assert 'Err(crate::rx_ipv4_tcp::RxError::TcpChecksum)=>{' not in android_io
assert 'a49_single_pass_matches_a48_two_pass_android_admission' in parser
assert 'ProtectedCryptoError::AndroidWouldBlock' in nativeworker
assert 'Err(err) if err.kind()==std::io::ErrorKind::WouldBlock' in owner
assert 'if error.kind()!=io::ErrorKind::WouldBlock' in android_io
assert 'wait_readable(raw.readiness_fd(),0)' not in nativeworker
assert 'wait_readable(tun.readiness_fd(),0)' not in nativeworker
assert 'parse_data_packet_android_m3_pending' not in linux_io
assert 'parse_data_packet(&slot[..n],trusted)' in linux_io
assert 'parse_data_packet(&slot[..len],TrustedRx{' in linux_io
assert 'self.offer_after_active(slab,0..len,absolute,now)' in owner
assert 'ANDROID_A48_ANDROID_BIONIC_TCP_CHECKSUM_ONLY_M3_PENDING_HOST_PASS' in Path(
    "android/root-native/ci/linux-original-oracle.sh").read_text()
print("ANDROID_A49_SINGLE_PASS_AND_BOUNDED_NONBLOCKING_DRAIN_SOURCE_PASS")
print("ANDROID_A48_EXACT_ANDROID_ONLY_CHECKSUM_GATE_M3_AUTH_STILL_REQUIRED_SOURCE_PASS")
print("ANDROID_A47_ORIGINAL_RUST_RAW_NUMERIC_AND_GO_JAVA_FORENSICS_SOURCE_PASS")
print("ANDROID_A46_EXACT_MAIN_WINDOWS_H2216_TTL_ANDROID_LINUX_SOURCE_GATE_PASS")
print("ANDROID_A45_ORIGINAL_M4_RETURN_PATH_ICMP_SOURCE_GATE_PASS")
print("ANDROID_A44_ORIGINAL_M4_APP_BUSINESS_AND_UID_ROUTE_GET_SOURCE_PASS")
print("ANDROID_A43_ORIGINAL_GO_CLIENT_RX_QUIESCE_SOURCE_GATE_PASS")
print("ANDROID_A42_ORIGINAL_M4_POST_START_HANDOFF_SOURCE_GATE_PASS")
print("ANDROID_A41_ANDROID_TUN_LEASE32_NATIVE_GETIFADDRS_SOURCE_PASS")
print("ANDROID_A40_ORIGINAL_GO_RUST_POSTAUTH_STAGE_HOST_SOURCE_PASS")
print("ANDROID_A39_ANDROID_KEYSTORE_PROVIDER_IV_AND_START_NONBLOCKING_SOURCE_PASS")
print("ANDROID_A38_KEYSTORE_ENCRYPTED_SECRET_AUTOFILL_SOURCE_GATE_PASS")
assert 'v4AndroidCertFailureReason(err)' in go_admission
for e in ("ROOT_RESTORE_COMPLETE","ROOT_RESTORE_FAILED"):
 assert e in s and e in receipt and e in report
# Certificate subtypes need to be recognized in the native stdout parser
# and the fixed Event enum. The existing report emits validated events
# generically; it correctly does NOT hardcode every certificate subtype.
assert "ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH" in s
assert "ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH" in receipt
assert "RootDiagnosticReceipt.safeEventToken(event)" in report
print("ANDROID_A36_APP_RESTORE_CERT_TRUST_SOURCE_GATE_PASS")
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY
