#!/usr/bin/env bash
# Same original Go TLS/Rust native M1 on two ISAs, one real kernel.
# arm64 is QEMU-user; no ARM hardware, CPU/p99, Android, or PMTU claim.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${GITHUB_WORKSPACE:?}"
test "$(uname -m)" = x86_64
arm_role="${WBD_PLAN028_MIXED_ARM_ROLE:?client or server}"
case "$arm_role" in client|server);; *) echo invalid-mixed-ISA-role >&2;exit 2;;esac
root="$GITHUB_WORKSPACE/mixed-isa-build"
out="$GITHUB_WORKSPACE/mixed-isa-result-$arm_role"
mkdir -p "$out"
chmod 0755 "$root"/{amd64,arm64}/wbd-v4-{client,server}
(cd "$root/amd64" && sha256sum -c SHA256SUMS)
(cd "$root/arm64" && sha256sum -c SHA256SUMS)
python3 - "$root/manifest.json" "$GITHUB_SHA" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
assert m["source"]==sys.argv[2] and m["qualification"]=="BUILD_ONLY",m
for cpu,num in (("arm64",183),("amd64",62)):
    for kind in ("client","server"):
        assert m[cpu]["wbd-v4-"+kind]["elf_machine"]==num
PY
command -v qemu-aarch64-static >/dev/null
test -c /dev/net/tun
test -e /usr/aarch64-linux-gnu/lib/ld-linux-aarch64.so.1
client_cpu=amd64;server_cpu=amd64
if [[ "$arm_role" == client ]];then client_cpu=arm64;else server_cpu=arm64;fi
tag="$(printf %s "$GITHUB_RUN_ID" | tail -c 7)"
suffix=c;if [[ "$arm_role" == server ]];then suffix=s;fi
NC="wdmc$tag$suffix";NS="wdms$tag$suffix"
work="$RUNNER_TEMP/wbd-mixed-$tag-$arm_role";mkdir -m 0700 -p "$work";umask 077
cleanup(){
 set +e
 for ns in "$NC" "$NS";do
  for pid in $(sudo -n ip netns pids "$ns" 2>/dev/null||true);do sudo -n kill -TERM "$pid" 2>/dev/null||true;done
 done
 for ns in "$NC" "$NS";do sudo -n ip netns del "$ns" 2>/dev/null||true;done
 rm -rf "$work"
}
trap cleanup EXIT
for ns in "$NC" "$NS";do sudo -n ip netns add "$ns";sudo -n ip -n "$ns" link set lo up;done
sudo -n ip link add mxc0 type veth peer name mxs0
sudo -n ip link set mxc0 netns "$NC"
sudo -n ip link set mxs0 netns "$NS"
sudo -n ip -n "$NC" addr add 198.18.31.1/30 dev mxc0
sudo -n ip -n "$NS" addr add 198.18.31.2/30 dev mxs0
sudo -n ip -n "$NC" link set mxc0 up
sudo -n ip -n "$NS" link set mxs0 up
# Exact FakeTCP RST suppression only in these two ephemeral namespaces.
sudo -n ip netns exec "$NC" iptables -w -A OUTPUT -s 198.18.31.1 -d 198.18.31.2 -p tcp --sport 41031 --dport 443 --tcp-flags RST RST -j DROP
sudo -n ip netns exec "$NS" iptables -w -A OUTPUT -s 198.18.31.2 -d 198.18.31.1 -p tcp --sport 443 --dport 41031 --tcp-flags RST RST -j DROP
cat >"$work/users.json" <<'JSON'
{"alice":"cross-isa-protected-long-password-20261103"}
JSON
chmod 0600 "$work/users.json"
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 \
 -subj '/CN=wbd-v4.example.test' -addext 'subjectAltName=DNS:wbd-v4.example.test' \
 -keyout "$work/key.pem" -out "$work/cert.pem" >"$out/cert-create.log" 2>&1
chmod 0600 "$work/key.pem"
# Wrapper invokes only a real other-ISA binary, not a mock Go/Rust endpoint.
launch(){
 local ns="$1" cpu="$2" kind="$3" log="$4" pidfile="$5"
 shift 5
 local prefix=()
 if [[ "$cpu" == arm64 ]];then prefix=(qemu-aarch64-static -L /usr/aarch64-linux-gnu);fi
 sudo -n ip netns exec "$ns" bash -c 'echo $$ > "$1";shift;exec "$@"' bash "$pidfile" \
   env LD_LIBRARY_PATH="$root/$cpu" SSL_CERT_FILE="$work/cert.pem" \
   "${prefix[@]}" "$root/$cpu/wbd-v4-$kind" "$@" >"$out/$log" 2>&1 &
}
launch "$NS" "$server_cpu" server server.log "$work/server.pid" \
 --raw-interface mxs0 --local-ip 198.18.31.2 --local-port 443 \
 --tun-name wbdms1 --tun-ipv4 10.66.0.1/24 \
 --server-name wbd-v4.example.test --users-file "$work/users.json" \
 --lease-pool 10.66.0.128/25 --tls-cert "$work/cert.pem" --tls-key "$work/key.pem" \
 --mode normal --outer-mtu 1460
ready=0
for _ in {1..120};do
 if grep -q 'V4_PUBLIC_MULTI_SERVER_READY role=server port=443' "$out/server.log";then ready=1;break;fi
 if [[ -s "$work/server.pid" ]] && ! sudo -n kill -0 "$(cat "$work/server.pid")" 2>/dev/null;then break;fi
 sleep .25
done
if [[ "$ready" != 1 ]];then echo MIXED_ISA_SERVER_NOT_READY >&2;tail -35 "$out/server.log" >&2;exit 1;fi
# Go UDP server proves genuine Rust TUN ingress and egress, not just handshake.
sudo -n ip netns exec "$NS" python3 -u -c '
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(30)
try:
 for i in range(12):
  x,src=s.recvfrom(4096)
  assert x.startswith(b"WBD_MIXED_ISA/"),x
  s.sendto(b"WBD_MIXED_REPLY/"+x,src)
finally:s.close()
' >"$out/echo.log" 2>&1 &
launch "$NC" "$client_cpu" client client.log "$work/client.pid" \
 --raw-interface mxc0 --local-ip 198.18.31.1 --local-port 41031 \
 --peer-ip 198.18.31.2 --peer-port 443 --tun-name wbdmc1 \
 --server-name wbd-v4.example.test --username alice \
 --password cross-isa-protected-long-password-20261103 \
 --auto-ip --installation-id-file "$work/client-install" --mode normal --outer-mtu 1460
ready=0
for _ in {1..140};do
 if grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$out/client.log" && \
    grep -q 'V4_PUBLIC_MULTI_SESSION_READY role=server' "$out/server.log";then ready=1;break;fi
 if [[ -s "$work/client.pid" ]] && ! sudo -n kill -0 "$(cat "$work/client.pid")" 2>/dev/null;then break;fi
 sleep .25
done
if [[ "$ready" != 1 ]];then
 echo MIXED_ISA_AUTHENTICATED_TLS_OR_NATIVE_NOT_READY >&2
 tail -55 "$out/client.log" "$out/server.log" >&2
 exit 1
fi
for log in client server;do
 grep -q "V4_PUBLIC_ROUTE_PREHELLO role=$log mode=ephemeral_x25519" "$out/$log.log"
done
lease="$(python3 - "$out/client.log" <<'PY'
import ipaddress,pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text()
matches=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\\.66\\.0\\.[0-9]+)/32',s)
assert len(matches)==1,matches
addr=ipaddress.ip_address(matches[0])
assert addr in ipaddress.ip_network("10.66.0.128/25"),addr
print(addr)
PY
)"
sudo -n ip -n "$NC" route replace 10.66.0.1/32 dev wbdmc1
sudo -n ip -n "$NS" route replace "$lease/32" dev wbdms1
client_mtu="$(sudo -n ip -j -n "$NC" link show wbdmc1 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
server_mtu="$(sudo -n ip -j -n "$NS" link show wbdms1 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$client_mtu" -ge 576 && "$server_mtu" -ge 576 && "$client_mtu" -le 1460 && "$server_mtu" -le 1460 ]]
sudo -n ip netns exec "$NC" env WBD_ISA_SOURCE="$lease" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["WBD_ISA_SOURCE"],0));s.settimeout(12)
for i in range(10):
 x=b"WBD_MIXED_ISA/"+str(i).encode()
 assert s.sendto(x,("10.66.0.1",45901))==len(x)
 y,who=s.recvfrom(4096)
 assert y==b"WBD_MIXED_REPLY/"+x and who[0]=="10.66.0.1",(i,y,who)
print("M0_PLAN028_REAL_CROSS_ISA_UDP_ECHO_PASS packets=10",flush=True)
' >"$out/udp.log" 2>&1
grep -q 'M0_PLAN028_REAL_CROSS_ISA_UDP_ECHO_PASS packets=10' "$out/udp.log"
sudo -n kill -TERM "$(cat "$work/client.pid")"
for _ in {1..100};do
 if grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$out/client.log";then break;fi
 sleep .2
done
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$out/client.log"
sudo -n kill -TERM "$(cat "$work/server.pid")"
for _ in {1..100};do
 if grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$out/server.log";then break;fi
 sleep .2
done
grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$out/server.log"
python3 - "$root/manifest.json" "$out" "$arm_role" "$lease" "$client_mtu" "$server_mtu" <<'PY'
import hashlib,json,pathlib,sys
m=json.load(open(sys.argv[1]))
out=pathlib.Path(sys.argv[2]);arm=sys.argv[3]
j={"source":m["source"],"original_go_source":m["original_go_source"],"arm_role":arm,
 "client_cpu":"arm64" if arm=="client" else "amd64",
 "server_cpu":"arm64" if arm=="server" else "amd64",
 "qualification":"QEMU_USER_EMULATED_ARM64_REAL_KERNEL_NETNS_FUNCTIONAL_ONLY",
 "auth":"REAL_ORIGINAL_GO_TLS_X25519_PREHELLO_CERT_VERIFIED",
 "ipv4_lease":sys.argv[4],"client_inner_mtu_os":int(sys.argv[5]),
 "server_inner_mtu_os":int(sys.argv[6]),
 "udp_echoed":10,"owned_stop":"PASS_BOTH","single_server_port":443,
 "cpu_p99":"NOT_RUN","arm64_hardware":"NOT_RUN","android":"NOT_RUN",
 "binaries_manifest":m,
 "log_sha256":{f:hashlib.sha256((out/f).read_bytes()).hexdigest()
    for f in ("client.log","server.log","udp.log","echo.log")}}
(out/"receipt.json").write_text(json.dumps(j,indent=2))
print("M0_PLAN028_CROSS_ISA_ORIGINAL_GO_RUST_REAL_NETNS_PASS arm_role="+arm+
 " packets=10 server_port=443 owned_stop=1 qemu_arm64=1",flush=True)
PY
cleanup
trap - EXIT
