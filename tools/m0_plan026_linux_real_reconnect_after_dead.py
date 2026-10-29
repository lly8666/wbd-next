#!/usr/bin/env python3
"""Genuine original Go TLS/Rust two-netns disconnect/reconnect product test.
Never manually kill/restart product or create TLS session in fixture.
"""
from pathlib import Path
import sys
if len(sys.argv)!=3: raise SystemExit("expected original.sh and generated.sh")
s=Path(sys.argv[1]).read_text()
def once(a,b):
    global s
    if s.count(a)!=1: raise SystemExit("source-locked original fixture anchor changed: "+a[:70])
    s=s.replace(a,b,1)
once('s.bind(("10.66.0.1",45901));s.settimeout(28)',
     's.bind(("10.66.0.1",45901));s.settimeout(225)')
once('env WBD_REAL_COUNT="$PACKETS" python3 -u -c \x27',
     'env WBD_REAL_COUNT="$((PACKETS+1))" python3 -u -c \x27')
anchor='if [[ "$PACKETS" == 5 || "$FEC" == 1 ]];then cat "$ART/public-v4-normal-business.log";fi'
inject=r'''[[ "$MODE" == fec-auto && "$FEC" == 1 && "$LOSS" == 0 ]] || exit 2
ORIG_CLIENT="$(cat "$TMP/client.pid")"
ORIG_SERVER="$(cat "$TMP/server.pid")"
test "$(grep -c 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log")" -eq 1
test "$(grep -c 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log")" -eq 1
# Real TCP+native Health control drop in BOTH underlay directions.
sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss 100%
sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss 100%
sleep 106
for role in client server;do
 grep -Fq 'WBD_M0_NATIVE_HEALTH_TIMEOUT side=tx reason=missing_authenticated_peer_dead_after_90s' "$TMP/$role.log" || {
 echo "M0_PLAN026_RECONNECT_DEAD_NOT_PROVEN role=$role" >&2;exit 1;
 }
done
sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 | grep -Eq 'dropped [1-9][0-9]*'
sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 | grep -Eq 'dropped [1-9][0-9]*'
sudo -n kill -0 "$ORIG_CLIENT"
sudo -n kill -0 "$ORIG_SERVER"
if grep -Ei 'DORMANT.*APPLIED|DORMANT.*PASS' "$TMP/client.log" "$TMP/server.log" >/dev/null;then
 echo 'M0_PLAN026_RECONNECT_FALSE_DORMANT' >&2;exit 1
fi
sudo -n ip netns exec "$NSC" tc qdisc del dev wbdvc0 root
sudo -n ip netns exec "$NSS" tc qdisc del dev wbdvs0 root
# The ONLY retry trigger is new real application packets into existing TUN.
# It may send multiple distinct first-source app packets while reconnecting.
sudo -n ip netns exec "$NSC" python3 -u -c '
import socket,time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.2",45903))
s.settimeout(.7)
until=time.monotonic()+48
found=False
n=0
while time.monotonic()<until and not found:
    msg=b"WBD_REAL_V4_ORIGINAL_GO/NEW_POST_DEAD_FLOW/"+str(n).encode()
    s.sendto(msg,("10.66.0.1",45901))
    try:
        data,source=s.recvfrom(8192)
        found=data==b"V4_SERVER_APP_ECHO/"+msg and source[0]=="10.66.0.1"
    except socket.timeout:pass
    n+=1
    time.sleep(.7)
assert found,"new app traffic did not recover authenticated product after 100pct underlay outage"
print("M0_PLAN026_RECONNECT_NEW_REAL_APP_UDP_PASS offered="+str(n),flush=True)
s.close()
' >"$ART/reconnect-new-flow.log" 2>&1 || {
  cat "$ART/reconnect-new-flow.log" >&2
  echo 'M0_PLAN026_RECONNECT_NEW_FLOW_FAILED_AFTER_TRUE_NATIVE_DEAD' >&2
  exit 1
}
# An echo from a still-existing process is NOT sufficient. A second actual
# original Go credential TLS and Rust handoff must be observed on both sides.
test "$(grep -c 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log")" -ge 2 || {
 echo 'M0_PLAN026_RECONNECT_NO_NEW_ORIGINAL_GO_TLS_CLIENT' >&2;exit 1;
}
test "$(grep -c 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log")" -ge 2 || {
 echo 'M0_PLAN026_RECONNECT_NO_NEW_ORIGINAL_GO_TLS_SERVER' >&2;exit 1;
}
sudo -n kill -0 "$ORIG_CLIENT"
sudo -n kill -0 "$ORIG_SERVER"
echo 'M0_PLAN026_LINUX_REAL_100PCT_DEAD_RESTORED_NEW_APP_AUTO_TLS_RUST_RECONNECT_PASS old_processes_preserved=1'
exit 0
'''
once(anchor,inject+anchor)
dst=Path(sys.argv[2]);dst.write_text(s);dst.chmod(0o755)
print("M0_PLAN026_RECONNECT_TEMP_FIXTURE_BYTE_ANCHORS_MATCH")
