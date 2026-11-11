#!/usr/bin/env python3
"""PLAN028 one real native failed-cold-rotation scenario; never changes shipping code."""
from pathlib import Path
import sys

ORIGINAL=Path("tools/m0-v4-public-real-linux-netns.sh")
def build():
    s=ORIGINAL.read_text()
    def once(old,new):
        nonlocal s
        assert s.count(old)==1,("H1615 frozen native fixture anchor drift",old[:100],s.count(old))
        s=s.replace(old,new,1)

    # Five initial, one while A remains live during blocked B, then five
    # after the successor becomes authentically READY and old A exactly Stops.
    once('ECHO_PACKETS="$PACKETS"','ECHO_PACKETS="$((PACKETS+6))"')
    once('s.bind(("10.66.0.1",45901));s.settimeout(55 if os.environ.get("WBD_REAL_COUNT")=="10" else 28)',
         's.bind(("10.66.0.1",45901));s.settimeout(225)')
    once('--mode "$MODE" --fec-profile 1 $GAME_FEC_ARG" >"$TMP/client.log" 2>&1 &',
         '--mode "$MODE" --fec-profile 1 $GAME_FEC_ARG --rotation-interval 5s" >"$TMP/client.log" 2>&1 &')
    before='# Startup uses exactly the production binaries and unmodified original Go'
    deny=r'''# Pure same-physical-network cold rotation: no NIC/IP/MTU/route change.
# Only the original A FakeTCP source port 41031 may traverse TLS443.
# Its successor ports (B2, B3,...) really hit netns iptables and fail.
# This preserves the OS path and the actual original-A Rust/Go owner.
sudo -n ip netns exec "$NSC" iptables -I OUTPUT 1 -p tcp --dport 443 ! --sport 41031 -j DROP
sudo -n ip netns exec "$NSS" iptables -I OUTPUT 1 -p tcp --sport 443 ! --dport 41031 -j DROP
'''
    once(before,deny+before)
    anchor='if [[ "$PACKETS" == 5 || "$FEC" == 1 ]];then cat "$ART/public-v4-normal-business.log";fi'
    experiment=r'''[[ "$MODE" == normal && "$AUTO_IP" == 1 && "$PATH_SWITCH" == 0 && "$FEC" == 0 && "$GAME" == 0 ]] || exit 2
pidc="$(cat "$TMP/client.pid")"
pids="$(cat "$TMP/server.pid")"
grep -Fq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=1 old_generation=false' "$TMP/client.log"
# Poll exact original supervisor: candidate B gen2 must fail via actual TLS
# cold path; never infer failure from an idle timeout or a local ACK.
failed=0
for i in {1..220};do
  if grep -E 'V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2 class=.+ old_untouched=true superseded_by_new_OS_path=false' "$TMP/client.log" >/dev/null;then
    failed=1;break
  fi
  sleep .25
done
if test "$failed" != 1;then
  echo H1615_AUTHENTIC_CANDIDATE_B2_FAILURE_NOT_OBSERVED >&2;exit 1
fi
if grep -Fq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true' "$TMP/client.log";then
  echo H1615_B2_WRONGLY_COMMITTED >&2;exit 1
fi
if grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log";then
  echo H1615_OLD_A_PREMATURELY_STOPPED >&2;exit 1
fi
sudo -n kill -0 "$pidc"
sudo -n kill -0 "$pids"
sudo -n ip netns exec "$NSC" iptables -nvxL OUTPUT >"$ART/h1615-b-real-kernel-drop.txt"
python3 - "$ART/h1615-b-real-kernel-drop.txt" <<'PY_B_DROP'
import pathlib,sys
rows=pathlib.Path(sys.argv[1]).read_text().splitlines()
matches=[r for r in rows if "DROP" in r and "dpt:443" in r]
assert len(matches)>=1,matches
drop=int(matches[0].split()[0])
assert drop>0,("no real B TCP packets dropped",matches)
print("H1615_SAME_ROUTE_COLD_B_GENUINE_TCP_KERNEL_DROP_PASS packets="+str(drop),flush=True)
PY_B_DROP
# With every B original TLS tuple still strictly dropped, send a FRESH
# unique kernel UDP datagram through the SAME original A M4 and echo server.
sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45906));s.settimeout(8)
data=b"WBD_REAL_V4_ORIGINAL_GO/H1615_FAILED_B_OLD_A_STILL_ACTIVE/"+bytes([119])*64
assert s.sendto(data,("10.66.0.1",45901))==len(data)
resp,peer=s.recvfrom(8192)
assert resp==b"V4_SERVER_APP_ECHO/"+data and peer[0]=="10.66.0.1",(resp,peer)
print("H1615_FAILED_B_OLD_A_NEW_TRUE_KERNEL_UDP_DELIVERED_PASS",flush=True)
s.close()
' >"$ART/h1615-original-a-live-udp.log" 2>&1 || {
  cat "$ART/h1615-original-a-live-udp.log" >&2;exit 1;
}
cat "$ART/h1615-original-a-live-udp.log"
if grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log";then
  echo H1615_A_STOPPED_DURING_BLOCKED_B >&2;exit 1
fi
# Remove ONLY fixture-owned B filters. Original Go still owns both PIDs,
# TUN, and finite 1/2/4/8s authenticated candidate retries.
sudo -n ip netns exec "$NSC" iptables -D OUTPUT -p tcp --dport 443 ! --sport 41031 -j DROP
sudo -n ip netns exec "$NSS" iptables -D OUTPUT -p tcp --sport 443 ! --dport 41031 -j DROP
ready=0
for i in {1..240};do
  if grep -Eq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=[3-9][0-9]* old_generation=true source=real_original_TLS_Rust_M4' "$TMP/client.log" &&
     grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log";then
    ready=1;break
  fi
  sleep .25
done
if test "$ready" != 1;then
  echo H1615_NEW_TLS_RUST_GENERATION_OR_OLD_A_EXACT_STOP_MISSING >&2;exit 1
fi
sudo -n kill -0 "$pidc"
sudo -n kill -0 "$pids"
sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45907));s.settimeout(10)
for i in range(205,210):
    data=b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i])*64
    assert s.sendto(data,("10.66.0.1",45901))==len(data)
    resp,peer=s.recvfrom(8192)
    assert resp==b"V4_SERVER_APP_ECHO/"+data and peer[0]=="10.66.0.1",(i,peer)
    print("H1615_NEW_POST_B_FAILURE_NATIVE_UDP_ECHO_PASS",i,flush=True)
s.close()
' >"$ART/h1615-new-original-tls-business.log" 2>&1 || {
  cat "$ART/h1615-new-original-tls-business.log" >&2;exit 1;
}
cat "$ART/h1615-new-original-tls-business.log"
test "$(grep -c 'H1615_NEW_POST_B_FAILURE_NATIVE_UDP_ECHO_PASS' "$ART/h1615-new-original-tls-business.log")" -eq 5
echo H1615_FAILED_CANDIDATE_KEPT_A_THEN_RECOVERED_REAL_TLS_RUST_PASS
'''
    once(anchor,anchor+'\n'+experiment)
    before_end='# Sensitive logs contain NO TLS secret/cold/exporter keys. Persist only the'
    capture=r'''# Save only source-locked native lifecycle metadata before TLS test files
# are deleted by the original owner cleanup; no private material leaves runner.
grep -E 'V4_PUBLIC_PATH_|V4_ORIGINAL_GO_CLIENT_NATIVE_READY|V4_PUBLIC_NATIVE_STOP_DRAINED|V4_PUBLIC_LEASE_APPLIED' "$TMP/client.log" |
  tail -150 >"$ART/h1615-original-client-events.log" || true
'''
    once(before_end,capture+before_end)
    assert s.count("H1615_FAILED_B_OLD_A_NEW_TRUE_KERNEL_UDP_DELIVERED_PASS")==1
    assert "rotation-interval 5s" in s
    return s

if len(sys.argv)==2 and sys.argv[1]=="--preflight":
    s=build()
    go=Path("r0/go_overlay/internal/v4productcli/path_supervisor_linux.go").read_text()
    assert '49152+(uint64(base)+seq*7919)%16383' in go
    assert s.count("ECHO_PACKETS=")>=2
    print("H1615_EXISTING_NATIVE_TIMER_ROTATION_SOURCE_EXACT_NEGATIVE_FIXTURE_PASS",flush=True)
elif len(sys.argv)==2:
    path=Path(sys.argv[1])
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(build())
    path.chmod(0o755)
    print("H1615_SAME_PHYSICAL_GO_RUST_NEGATIVE_TIMER_FIXTURE_READY",flush=True)
else:
    raise SystemExit("expected --preflight or output file")
