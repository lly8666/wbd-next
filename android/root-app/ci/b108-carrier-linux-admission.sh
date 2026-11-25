#!/usr/bin/env bash
# Independent real kernel admission of the CI-only byte carrier.
# Three private namespaces, actual regular TCP on port443, no WBD claims.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD)" = "$GITHUB_SHA"
test "$(id -u)" = 0
out="$PWD/out/b108-carrier-host"
mkdir -p "$out"
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o "$out/relay" android/root-native/ci/b108-wire-relay.go
c="wbd108-c-$$";s="wbd108-s-$$";r="wbd108-r-$$"
pids=()
names=()
cleanup(){
 set +e
 for pid in "${pids[@]}";do kill "$pid" 2>/dev/null || true;done
 for pid in "${pids[@]}";do wait "$pid" 2>/dev/null || true;done
 for name in "${names[@]}";do ip netns del "$name";done
}
trap cleanup EXIT
for name in "$c" "$s" "$r";do ip netns add "$name";names+=("$name");ip -n "$name" link set lo up;done
ip link add wlan0 netns "$c" type veth peer name dead0 netns "$r"
ip link add wbdrg0 netns "$c" type veth peer name wbdrg1 netns "$r"
ip link add wbdrh0 netns "$s" type veth peer name wbdrh1 netns "$r"
ip -n "$c" link set wlan0 address 02:00:00:00:08:04
ip -n "$c" link set wbdrg0 address 02:00:00:00:08:04
ip -n "$r" link set dead0 address 02:00:00:00:08:05
ip -n "$r" link set wbdrg1 address 02:00:00:00:08:03
ip -n "$s" link set wbdrh0 address 02:00:00:00:08:01
ip -n "$r" link set wbdrh1 address 02:00:00:00:08:02
for dev in wlan0 wbdrg0;do ip -n "$c" link set "$dev" up;done
ip -n "$s" link set wbdrh0 up
for dev in dead0 wbdrg1 wbdrh1;do ip -n "$r" link set "$dev" up;done
ip -n "$r" link set wbdrg1 promisc on
# A real ordinary kernel TCP socket otherwise emits checksum/GSO offload
# descriptors instead of original IP bytes. The WBD RAW emitter does not
# require these changes; only this independent Linux carrier admission.
for pair in "$c wlan0" "$s wbdrh0";do
 read -r ns dev <<<"$pair"
 ip netns exec "$ns" ethtool -K "$dev" tx off tso off gso off gro off
done
ip -n "$c" addr add 10.0.2.15/32 dev wlan0
ip -n "$c" route add 10.0.2.2/32 dev wlan0 src 10.0.2.15
ip -n "$c" neigh add 10.0.2.2 lladdr 02:00:00:00:08:05 nud permanent dev wlan0
ip -n "$s" addr add 10.0.2.2/32 dev wbdrh0
ip -n "$s" route add 10.0.2.15/32 dev wbdrh0 src 10.0.2.2
ip -n "$s" neigh add 10.0.2.15 lladdr 02:00:00:00:08:02 nud permanent dev wbdrh0
ip netns exec "$c" tc qdisc add dev wlan0 clsact
ip netns exec "$c" tc qdisc add dev wbdrg0 clsact
ip netns exec "$c" tc filter add dev wlan0 egress protocol ip pref 49152 u32 match ip src 10.0.2.15/32 match ip dst 10.0.2.2/32 match ip protocol 6 0xff match ip dport 443 0xffff action mirred egress redirect dev wbdrg0
ip netns exec "$c" tc filter add dev wbdrg0 ingress protocol ip pref 49152 u32 match ip src 10.0.2.2/32 match ip dst 10.0.2.15/32 match ip protocol 6 0xff match ip sport 443 0xffff action mirred ingress redirect dev wlan0
ip netns exec "$r" "$out/relay" host wbdrh1 10.0.2.15 10.0.2.2 02:00:00:00:08:01 >"$out/host.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 30);do grep -Fq B108_RELAY_LISTENING "$out/host.log" && break;sleep .2;done
grep -Fq B108_RELAY_LISTENING "$out/host.log"
ip netns exec "$r" "$out/relay" guest wbdrg1 10.0.2.15 10.0.2.2 02:00:00:00:08:04 >"$out/guest.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 30);do grep -Fq B108_RELAY_CONNECTED "$out/guest.log" && break;sleep .2;done
grep -Fq B108_RELAY_CONNECTED "$out/guest.log"
ip netns exec "$s" python3 -u android/root-app/ci/traffic-fixture/server.py --bind 10.0.2.2 --port 443 >"$out/echo.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 30);do grep -Fq "WBD test echo TCP+UDP" "$out/echo.log" && break;sleep .2;done
grep -Fq "WBD test echo TCP+UDP" "$out/echo.log"
ip netns exec "$c" python3 - <<'PY'
import socket
data=bytes(range(256))*4096
with socket.create_connection(("10.0.2.2",443),timeout=8) as s:
    for at in range(0,len(data),16384):
        part=data[at:at+16384]
        s.sendall(part)
        result=bytearray()
        while len(result)<len(part):
            b=s.recv(len(part)-len(result))
            assert b,"premature EOF"
            result.extend(b)
        assert result==part
print("B108_LINUX_CARRIER_REAL_TCP_1MIB_BIDIRECTIONAL_PASS")
PY
for side in host guest;do
 grep -Fq "B108_RELAY_FIRST_TX $side" "$out/$side.log"
 grep -Fq "B108_RELAY_FIRST_RX $side" "$out/$side.log"
done
ip netns exec "$c" tc -s filter show dev wlan0 egress >"$out/egress.txt"
ip netns exec "$c" tc -s filter show dev wbdrg0 ingress >"$out/ingress.txt"
echo B108_LINUX_CARRIER_KERNEL_PASS | tee "$out/result.txt"
