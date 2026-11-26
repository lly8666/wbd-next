#!/usr/bin/env bash
# Actual CHR VM + native x86 server container + native Linux client + origin.
# One scenario per isolated Actions job; no physical deployment.
set -euo pipefail
case "${ROS_SCENE:?}" in routed|dnat|splice) ;; *) exit 2;; esac
name=wbd-ros
out="$PWD/ros-evidence"
bundle="$PWD/linux-plan029-public-bundle"
mkdir -p "$out"
work=$(mktemp -d)
client_pid= origin_pid= http_pid= capture_pid=
chr_started=0
export NO_COLOR=1 QUICKCHR_NO_PROMPT=1
ros() { quickchr exec "$name" -- "$1"; }
snapshot() {
  ros '/system/resource/print' >"$out/ros-resource.txt" 2>&1 || true
  ros '/system/package/print' >"$out/ros-packages.txt" 2>&1 || true
  ros '/system/license/print' >"$out/ros-license.txt" 2>&1 || true
  ros '/system/device-mode/print' >"$out/ros-device-mode.txt" 2>&1 || true
  ros '/interface/print detail' >"$out/ros-interfaces.txt" 2>&1 || true
  ros '/ip/address/print detail' >"$out/ros-addresses.txt" 2>&1 || true
  ros '/ip/route/print detail' >"$out/ros-routes.txt" 2>&1 || true
  ros '/ip/firewall/filter/print stats' >"$out/ros-filter.txt" 2>&1 || true
  ros '/ip/firewall/nat/print stats' >"$out/ros-nat.txt" 2>&1 || true
  ros '/container/print detail' >"$out/ros-container.txt" 2>&1 || true
  ros '/log/print where topics~"container"' >"$out/ros-container-log.txt" 2>&1 || true
}
cleanup() {
  rc=$?
  trap - EXIT
  set +e
  for p in "$client_pid" "$origin_pid" "$http_pid" "$capture_pid"; do
    if [ -n "$p" ]; then sudo kill -TERM "$p" 2>/dev/null; fi
  done
  if [ "$chr_started" = 1 ]; then snapshot; quickchr stop "$name" >"$out/chr-stop.txt" 2>&1; fi
  sudo ip netns del wbd-ros-client 2>/dev/null
  sudo ip link del wbd-ros-br 2>/dev/null
  sudo ip link del wbd-ros-wan 2>/dev/null
  sudo ip link del wbd-ros-origin 2>/dev/null
  rm -rf "$work"
  printf 'scene=%s exit=%s source=%s\n' "$ROS_SCENE" "$rc" "$GITHUB_SHA" >"$out/result.txt"
  exit "$rc"
}
trap cleanup EXIT
cp "$bundle/manifest.json" "$out/"
(cd "$bundle" && sha256sum -c SHA256SUMS) >"$out/hashes.txt"
uname -a >"$out/host.txt"
quickchr --version >>"$out/host.txt"
qemu-system-x86_64 --version >>"$out/host.txt"
test -w /dev/kvm && echo KVM_WRITABLE >>"$out/host.txt" || echo KVM_NOT_WRITABLE >>"$out/host.txt"
# Client and origin are on separate real L2 segments. SLIRP only provisions
# CHR, never carries WBD test traffic.
sudo ip link add wbd-ros-br type bridge
sudo ip tuntap add dev wbd-ros-wan mode tap user "$(id -u)"
sudo ip link set wbd-ros-wan master wbd-ros-br
sudo ip link set wbd-ros-wan up
sudo ip link set wbd-ros-br up
sudo ip netns add wbd-ros-client
sudo ip link add wbd-ros-veth type veth peer name wan0 netns wbd-ros-client
sudo ip link set wbd-ros-veth master wbd-ros-br
sudo ip link set wbd-ros-veth up
ns() { sudo ip netns exec wbd-ros-client "$@"; }
ns ip link set lo up
ns ip addr add 10.248.81.3/24 dev wan0
ns ip link set wan0 up
ns ip route add 10.248.82.0/24 via 10.248.81.2
ns iptables -A OUTPUT -o wan0 -p tcp --dport 443 --tcp-flags RST RST -j DROP
sudo ip tuntap add dev wbd-ros-origin mode tap user "$(id -u)"
sudo ip addr add 198.18.77.2/24 dev wbd-ros-origin
sudo ip link set wbd-ros-origin up
sudo ip route add 10.248.82.0/24 via 198.18.77.1 dev wbd-ros-origin
quickchr start --name "$name" --version 7.24.7 --arch x86 --cpu 2 --mem 2048 --boot-size 4G --add-network user --add-network tap:wbd-ros-wan --add-network tap:wbd-ros-origin --add-package container --device-mode-enable container --secure-login --timeout-extra 120
chr_started=1
ros '/system/package/print' | tee "$out/ros-packages.txt"
ros '/system/license/print' | tee "$out/ros-license.txt"
ros '/system/device-mode/print' | tee "$out/ros-device-mode.txt"
ros '/interface/ethernet/print detail' | tee "$out/ros-ethernet.txt"
ros '/ip/address/add address=10.248.81.2/24 interface=ether2'
ros '/ip/address/add address=198.18.77.1/24 interface=ether3'
ros '/interface/veth/add name=veth-wbd address=10.248.82.2/24 gateway=10.248.82.1'
ros '/interface/bridge/add name=br-wbd'
ros '/interface/bridge/port/add bridge=br-wbd interface=veth-wbd'
ros '/ip/address/add address=10.248.82.1/24 interface=br-wbd'
# Plain forward path first. Do not change the host/global firewall policy.
ros '/ip/firewall/filter/add chain=forward action=accept in-interface=ether2 out-interface=br-wbd dst-address=10.248.82.2 protocol=tcp dst-port=443 comment=wbd-lab-in'
ros '/ip/firewall/filter/add chain=forward action=accept in-interface=br-wbd out-interface=ether2 src-address=10.248.82.2 protocol=tcp src-port=443 comment=wbd-lab-return'
ros '/ip/firewall/filter/add chain=forward action=accept in-interface=br-wbd out-interface=ether3 src-address=10.248.82.2 comment=wbd-lab-origin'
ros '/ip/firewall/filter/add chain=forward action=accept in-interface=ether3 out-interface=br-wbd dst-address=10.248.82.2 comment=wbd-lab-origin-return'
peer=10.248.82.2
if [ "$ROS_SCENE" = dnat ]; then
  ros '/ip/firewall/nat/add chain=dstnat action=dst-nat in-interface=ether2 dst-address=10.248.81.2 protocol=tcp dst-port=443 to-addresses=10.248.82.2 to-ports=443 comment=wbd-lab-dnat'
  peer=10.248.81.2
fi
# Fresh run-only test credentials are never committed or uploaded.
mkdir -p "$work/image/fixture" "$work/http"
cp tools/routeros-server/{Dockerfile,entry.sh} "$work/image/"
cp "$bundle"/{wbd-v4-server,libwbd_engine.so} "$work/image/"
fixture="$work/image/fixture"
openssl rand -hex 32 >"$fixture/route-key.hex"
password=$(openssl rand -hex 16)
printf '{"bench":"%s"}\n' "$password" >"$fixture/users.json"
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes -keyout "$fixture/key.pem" -out "$fixture/cert.pem" -subj /CN=wbd-h2228.example.test -addext subjectAltName=DNS:wbd-h2228.example.test >"$out/cert-generation.txt" 2>&1
chmod 600 "$fixture"/{key.pem,users.json,route-key.hex}
cc=
if [ "$ROS_SCENE" = splice ]; then cc=cubic; fi
docker build --platform linux/amd64 --build-arg WBD_CC="$cc" -t wbd-ros-lab "$work/image" >"$out/image-build.txt" 2>&1
docker save wbd-ros-lab | gzip -1 >"$work/http/wbd.tar.gz"
python3 -m http.server 18080 --bind 127.0.0.1 --directory "$work/http" >"$out/http.log" 2>&1 &
http_pid=$!
ros '/tool/fetch url=http://10.0.2.2:18080/wbd.tar.gz dst-path=wbd.tar.gz' | tee "$out/ros-fetch.txt"
ros '/file/print detail where name=wbd.tar.gz' | tee "$out/ros-image-file.txt"
ros '/container/add name=wbd file=wbd.tar.gz interface=veth-wbd root-dir=wbd-root logging=yes stop-time=30s'
for i in $(seq 1 120); do
  ros '/container/print' >"$out/ros-extract.txt"
  if grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+S[[:space:]]+wbd([[:space:]]|$)' "$out/ros-extract.txt"; then break; fi
  if grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+F[[:space:]]+wbd([[:space:]]|$)' "$out/ros-extract.txt"; then exit 2; fi
  sleep 2
done
grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+S[[:space:]]+wbd([[:space:]]|$)' "$out/ros-extract.txt"
ros '/container/start [find where name=wbd]'
for i in $(seq 1 90); do
  ros '/log/print where topics~"container"' >"$out/ros-container-log.txt"
  if grep -q 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$out/ros-container-log.txt"; then break; fi
  sleep 2
done
grep -q 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$out/ros-container-log.txt"
if [ -n "$cc" ]; then grep -q 'WBD_TCP_SPLICE_READY tun=wbds0 port=46180 cc=cubic' "$out/ros-container-log.txt"; fi
# Verify the actual application with the H2429 finite duplex+half-close, scaled for CHR free,
# eight concurrent streams and UDP echo fixture, not just client READY.
sudo tcpdump -nn -l -c 80 -i wbd-ros-wan 'tcp port 443' >"$out/wire-headers.txt" 2>&1 &
capture_pid=$!
sudo ip netns exec wbd-ros-client env LD_LIBRARY_PATH="$bundle" "$bundle/wbd-v4-client" --raw-interface wan0 --local-ip 10.248.81.3 --local-port 44100 --peer-ip "$peer" --peer-port 443 --tun-name wbdc0 --server-name wbd-h2228.example.test --route-key-hex-file "$fixture/route-key.hex" --username bench --password "$password" --auto-ip --installation-id-file "$work/install" --mode normal --outer-repair on --outer-mtu 1460 >"$out/client.log" 2>&1 &
client_pid=$!
for i in $(seq 1 120); do
  kill -0 "$client_pid"
  if grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$out/client.log"; then break; fi
  sleep 1
done
grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$out/client.log"
ns ip route replace 198.18.77.2/32 dev wbdc0
ns ip route get 198.18.77.2 >"$out/client-route.txt"
python3 -u tools/routeros-server/app.py origin 5300 >"$out/origin.log" 2>&1 &
origin_pid=$!
for i in $(seq 1 20); do
  if ss -ltn | grep -q '198.18.77.2:5300'; then break; fi
  sleep 1
done
ss -ltn | grep '198.18.77.2:5300'
ns timeout 180 python3 -u tools/routeros-server/app.py client 5300 >"$out/application.json"
wait "$origin_pid"
origin_pid=
sudo kill -TERM "$client_pid"
wait "$client_pid"
client_pid=
grep -Eq 'V4_PUBLIC_SHARED_TUN_STOP|V4_PUBLIC_NATIVE_STOP_DRAINED' "$out/client.log"
ros '/container/stop [find where name=wbd]'
for i in $(seq 1 35); do
  ros '/log/print where topics~"container"' >"$out/ros-container-log.txt"
  if grep -q 'V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED' "$out/ros-container-log.txt"; then break; fi
  sleep 1
done
grep -q 'V4_PUBLIC_SHARED_TUN_STOP.*reader_joined=1' "$out/ros-container-log.txt"
grep -q 'V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED' "$out/ros-container-log.txt"
if [ -n "$cc" ]; then
  grep -q 'WBD_TCP_SPLICE_DONE.*target=198.18.77.2:5300' "$out/ros-container-log.txt"
  grep -q 'WBD_TCP_SPLICE_STOP error=<nil>' "$out/ros-container-log.txt"
fi
echo WBD_ROS_REAL_APPLICATION_AND_STOP_PASS
