#!/usr/bin/env bash
set -euo pipefail
scene=${BBR_SCENE:?}
name=wbd-bbr
out="$PWD/bbr-evidence"
mkdir -p "$out"
work=$(mktemp -d)
started=0; hp=
ros(){ quickchr exec "$name" -- "$1"; }
cleanup(){
 rc=$?; trap - EXIT;set +e
 if [ "$started" = 1 ]; then
   ros '/log/print where topics~"container"' >"$out/container.log" 2>&1
   ros '/container/print detail' >"$out/container.txt" 2>&1
   ros '/system/resource/print' >"$out/resource.txt" 2>&1
   ros '/system/license/print' >"$out/license.txt" 2>&1
   ros '/ip/route/print detail' >"$out/routes.txt" 2>&1
   quickchr stop "$name" >"$out/stop.txt" 2>&1
 fi
 [ -z "$hp" ] || kill "$hp" 2>/dev/null
 sudo tc -s qdisc show dev bbr-wan >"$out/qdisc.txt" 2>&1
 sudo tc -s qdisc show dev bbr-ifb >>"$out/qdisc.txt" 2>&1
 sudo ip link del bbr-ifb 2>/dev/null
 sudo ip link del bbr-wan 2>/dev/null
 rm -rf "$work"
 printf 'scene=%s exit=%s source=%s\n' "$scene" "$rc" "$GITHUB_SHA" >"$out/result.txt"
 exit "$rc"
}
trap cleanup EXIT
cc=kernel
if [ "$scene" != kernel ];then cc=${scene%%-*};fi
mkdir -p "$work/image/bin" "$work/http"
cp tools/routeros-bbr/{Dockerfile,entry.sh} "$work/image/"
gcc -O2 -Wall -Wextra -o "$work/image/kernel-probe" tools/routeros-bbr/kernel-probe.c
sudo "$work/image/kernel-probe" | tee "$out/native-linux-kernel-control.txt"
if [ "$cc" != kernel ];then cp bbr-reference/wbd-bbr-lab "$work/image/bin/"; sha256sum bbr-reference/wbd-bbr-lab >"$out/reference-sha256.txt";fi
docker build --build-arg BBR_LAB_CC="$cc" -t wbd-bbr-lab "$work/image" >"$out/image.log" 2>&1
docker save wbd-bbr-lab | gzip -1 >"$work/http/image.tar.gz"
python3 -m http.server 18080 --bind 127.0.0.1 --directory "$work/http" >"$out/http.log" 2>&1 & hp=$!
sudo ip tuntap add dev bbr-wan mode tap user "$(id -u)"
sudo ip addr add 198.18.77.2/24 dev bbr-wan
sudo ip link set bbr-wan up
sudo ip route add 10.249.90.0/24 via 198.18.77.1 dev bbr-wan
quickchr start --name "$name" --version 7.24.7 --arch x86 --cpu 2 --mem 2048 --boot-size 4G --add-network user --add-network tap:bbr-wan --add-package container --device-mode-enable container --secure-login --timeout-extra 120
started=1
ros '/ip/address/add address=198.18.77.1/24 interface=ether2'
ros '/interface/veth/add name=veth-bbr address=10.248.82.2/24 gateway=10.248.82.1'
ros '/interface/bridge/add name=br-bbr'
ros '/interface/bridge/port/add bridge=br-bbr interface=veth-bbr'
ros '/ip/address/add address=10.248.82.1/24 interface=br-bbr'
ros '/ip/route/add dst-address=10.249.90.0/24 gateway=10.248.82.2'
ros '/tool/fetch url=http://10.0.2.2:18080/image.tar.gz dst-path=image.tar.gz'
ros '/container/add name=bbr file=image.tar.gz interface=veth-bbr root-dir=bbr-root logging=yes'
for i in $(seq 1 120);do
 ros '/container/print' >"$out/extract.txt"
 if grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+S[[:space:]]+bbr([[:space:]]|$)' "$out/extract.txt";then break;fi
 sleep 2
done
grep -Eq '^[[:space:]]*[0-9]+[[:space:]]+S[[:space:]]+bbr([[:space:]]|$)' "$out/extract.txt"
ros '/container/start [find where name=bbr]'
for i in $(seq 1 60);do
 ros '/log/print where topics~"container"' >"$out/container.log"
 if [ "$cc" = kernel ];then
  if grep -q BBR_KERNEL_PROBE_COMPLETE "$out/container.log";then cat "$out/container.log";exit 0;fi
 else
  if grep -q "BBR_LAB_READY cc=$cc" "$out/container.log";then break;fi
 fi
 sleep 1
done
cat "$out/container.log"
grep -q "BBR_LAB_READY cc=$cc" "$out/container.log"
if [[ "$scene" == *-loss ]];then
 sudo modprobe ifb
 sudo ip link add bbr-ifb type ifb
 sudo ip link set bbr-ifb up
 sudo tc qdisc add dev bbr-wan root netem delay 200ms loss 5%
 sudo tc qdisc add dev bbr-wan ingress
 sudo tc filter add dev bbr-wan parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev bbr-ifb
 sudo tc qdisc add dev bbr-ifb root netem delay 200ms loss 5%
fi
python3 -u - <<'PY' | tee "$out/receipt.json"
import hashlib,json,socket,time
t=time.monotonic()
with socket.create_connection(("10.249.90.2",5300),timeout=40) as s:
 s.settimeout(120);s.sendall(b"x")
 h=hashlib.sha256();n=0
 while True:
  b=s.recv(65536)
  if not b:break
  h.update(b);n+=len(b)
 expected=hashlib.sha256(bytes((i*31+7)&255 for i in range(512*1024))).hexdigest()
 assert n==512*1024 and h.hexdigest()==expected,(n,h.hexdigest())
 s.sendall(h.hexdigest().encode())
 print(json.dumps({"bytes":n,"sha256":h.hexdigest(),"elapsed_s":time.monotonic()-t,"native_peer":True}))
PY
for i in $(seq 1 30);do
 ros '/log/print where topics~"container"' >"$out/container.log"
 if grep -q "BBR_LAB_REAL_TCP_PASS actual_cc=$cc" "$out/container.log";then break;fi
 sleep 1
done
cat "$out/container.log"
grep -q "BBR_LAB_REAL_TCP_PASS actual_cc=$cc" "$out/container.log"
