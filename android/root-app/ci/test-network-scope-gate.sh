#!/usr/bin/env bash
# Pure Java session-decision test, NOT an Android Framework runtime gate.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
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
# Exact production Root Service diagnostic writer, not a fabricated
# Android guest or Go/TLS success. Verify fixed enums, bounded retention,
# no untrusted metadata and Device acceptance report semantics.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/ci/RootDiagnosticReceiptTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDiagnosticReceiptTest
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
assert s.count('InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)')>=2, "multi UID identity rechecked on Service and pre-su"
assert 'watchSelectedPackages(allApps?managerPackages:targetPackages)' in s and 'stopWatchingSelectedPackage()' in s, "withdraw selected group or manager exclusions on package events"
assert 'AllAppRouteScope.same(this,excludedAppIDs,managerPackages)' in s, "verify full-app owner+manager UID exclusions before su"
assert '"--android-route-all-apps"' in s and '"--android-route-exclude-appids"' in s, "production source-locked Go full-app routing"
assert 'AllAppUIDPolicy.csv(excludedAppIDs)' in s, "only canonical app ID exclusions"

assert '"--android-route-uids"' in s and '"--android-route-uid"' in s, "real original Go CLI group and one-UID flags"
assert 'ServerAddress.isIPv4Literal(peer)?"--peer-ip":"--peer-host"' in s
assert 'ServerAddress.valid(peer)' in s
a=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'target_packages' in a and 'target_uids' in a
assert 'SelectedAppGroup.from(' in a and 'InstalledAppCatalog.stillSameGroup(' in a
assert 'Integer.parseInt(uid.getText()' not in a, "no arbitrary hand-entered UID"
assert 'CheckBox' in a and 'appChoices' in a, "real visible multi-App selections"
assert 'allAppsDefault.setChecked(true)' in a, "all ordinary Android applications are the product UI default"
assert 'AllAppRouteScope.snapshot(this)' in a and 'all_apps' in a, "default mode must pass verified scopes not fake overlay"

assert 'ServerAddress.valid(peer)' in a and 'Server underlay IPv4 or DNS name' in a
cold=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
go=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
assert 'rootjournal.NewGroup(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uids=' in go
assert 'rootjournal.NewAllApps(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED mode=all_apps' in go
assert 'androidRouteAllApps' in cold and 'android-route-all-apps' in cold
allapp=Path("r0/go_overlay/internal/v4productcli/rootjournal/allapps.go").read_text()
assert 'func NewAllApps(' in allapp and 'requireReady(original)' in allapp and 'readOwnedJournalVersion(' in allapp
assert 'AllAppIDMin = 10000' in allapp and 'AllAppIDMax = 19999' in allapp
assert 'allMaxUserProfiles = 20' in allapp and 'ExcludedAppIDs' in allapp

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
assert '"--android-cn-geosite-file",nativeCode.cnGeosite.getAbsolutePath()' in s
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
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY
