#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
out=out/android-b104-forwarding
mkdir -p "$out"
case "$1" in
 ipv4) filter=TestB104TetherIPv4RealDownstream;;
 ipv6) filter=TestB104IPv6CarrierRealDownstream;;
 *) exit 2;;
esac
export GO111MODULE=off GOTOOLCHAIN=local
python3 -m py_compile android/root-native/ci/b104-forwarding-sockets.py
go test -c -o "$out/rootjournal.test" ./r0/go_overlay/internal/v4productcli/rootjournal
# Only this isolated CI host. No host default route or global sysctl change.
if [[ "$1" == ipv6 ]];then sudo -n modprobe sit || true;fi
sudo -n env WBD_B104_REAL_NS=1 WBD_B104_SOCKET_FIXTURE="$PWD/android/root-native/ci/b104-forwarding-sockets.py" \
 "$PWD/$out/rootjournal.test" -test.v -test.timeout=90s -test.run "^$filter\$" | tee "$out/test.log"
grep -Fq -- '--- PASS: ' "$out/test.log"
if [[ "$1" == ipv4 ]];then
 grep -Fq B104_TETHER_IPV4_FORWARD_SNAT_DIRECT_DNS_PASS "$out/test.log"
 grep -Fq B104_TETHER_IPV4_STOP_RESTORED_PASS "$out/test.log"
else
 grep -Fq B104_IPV6_CARRIER_UID_DOWNSTREAM_DNS_PASS "$out/test.log"
 grep -Fq B104_IPV6_CARRIER_STOP_PASS "$out/test.log"
fi
