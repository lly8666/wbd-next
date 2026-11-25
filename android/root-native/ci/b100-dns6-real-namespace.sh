#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
out=out/android-b100-dns6-host
mkdir -p "$out"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
export GO111MODULE=off GOTOOLCHAIN=local
go test -c -o "$out/rootjournal.test" ./r0/go_overlay/internal/v4productcli/rootjournal
ns="wbd-b100-$$"
sudo -n ip netns add "$ns"
trap 'sudo -n ip netns del "$ns"' EXIT
sudo -n ip netns exec "$ns" ip link set lo up
sudo -n ip netns exec "$ns" ip6tables -w 2 -t nat -S OUTPUT | tee "$out/nat6-baseline.txt"
sudo -n ip netns exec "$ns" env WBD_B100_REAL_NS=1 "$PWD/$out/rootjournal.test" -test.v -test.timeout=40s -test.run '^(TestB100IPv6SystemDNSRealNamespace|TestB120ManagedDNSRealNamespace|TestB120IPv6EntryRealNamespace) | tee "$out/test.log"
grep -Fq B100_HOST_IPV6_UID_MARK_UDP_TCP_REDIRECT_PASS "$out/test.log"
grep -Fq B100_HOST_IPV6_OWNER_STOP_PASS "$out/test.log"
 | tee "$out/test.log"
grep -Fq B100_HOST_IPV6_UID_MARK_UDP_TCP_REDIRECT_PASS "$out/test.log"
grep -Fq B100_HOST_IPV6_OWNER_STOP_PASS "$out/test.log"
grep -Fq B120_HOST_MANAGED_DNS6_UDP_TCP_ANY_MARK_PASS "$out/test.log"
grep -Fq B120_HOST_REAL_TUN_IPV6_ENTRY_AND_LOW_MTU_DROP_STOP_PASS "$out/test.log"
