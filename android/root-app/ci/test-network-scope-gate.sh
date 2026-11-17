#!/usr/bin/env bash
# Pure Java session-decision test, NOT an Android Framework runtime gate.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/android-root-app/network-scope-test
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/NetworkScopeGate.java \
  android/root-app/ci/NetworkScopeGateTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.NetworkScopeGateTest
python3 - <<'PY'
from pathlib import Path
s=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
for method in ("registerNetworkCallback(", "unregisterNetworkCallback(",
 "onLost(", "onLinkPropertiesChanged(", "onCapabilitiesChanged(",
 "onBlockedStatusChanged("):
 assert method in s, method
assert "postDelayed(" not in s, "no 1-second steady Network watcher"
assert "getNetworkCapabilities(" not in s and "getLinkProperties(" not in s, "no synchronous ConnectivityManager lookup inside callback"
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY
