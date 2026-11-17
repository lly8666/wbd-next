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
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY
