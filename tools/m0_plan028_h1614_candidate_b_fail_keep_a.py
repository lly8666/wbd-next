#!/usr/bin/env python3
"""Test-only source-locked negative generation-B fixture; product code is untouched."""
from pathlib import Path
import sys

SOURCE=Path("tools/m0-v4-public-real-linux-netns.sh")
def generate():
    s=SOURCE.read_text()
    def once(old,new):
        nonlocal s
        assert s.count(old)==1,("H1614 source fixture drift",old[:90],s.count(old))
        s=s.replace(old,new,1)

    once('if [[ "$PATH_SWITCH" == 1 ]];then ECHO_PACKETS=10;fi',
         'if [[ "$PATH_SWITCH" == 1 ]];then ECHO_PACKETS=11;fi')
    once('s.bind(("10.66.0.1",45901));s.settimeout(55 if os.environ.get("WBD_REAL_COUNT")=="10" else 28)',
         's.bind(("10.66.0.1",45901));s.settimeout(225)')
    before='  sudo -n ip -n "$NSC" addr add 10.25.0.3/24 dev wbdvc0'
    injection=r'''  # DROP ONLY proposed B source IPv4; old original A source .2 remains live.
  sudo -n ip netns exec "$NSC" iptables -I OUTPUT 1 -s 10.25.0.3 -p tcp --dport 443 -j DROP
  sudo -n ip netns exec "$NSS" iptables -I OUTPUT 1 -d 10.25.0.3 -p tcp --sport 443 -j DROP
  sudo -n ip netns exec "$NSC" iptables -nvxL OUTPUT >"$ART/h1614-b-candidate-client-firewall-before.txt"
  sudo -n kill -0 "$(cat "$TMP/client.pid")"
  sudo -n kill -0 "$(cat "$TMP/server.pid")"
'''
    once(before,injection+before)
    anchor='  path_ready=0\n  for i in {1..160};do'
    gate=r'''  # A real changed physical route starts B generation2, whose original
  # protected TLS must FAIL. Never declare B success from local client READY.
  fail_seen=0
  for i in {1..320};do
    if grep -E 'V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=2 class=.+ old_untouched=true superseded_by_new_OS_path=false' "$TMP/client.log" >/dev/null;then
      fail_seen=1;break
    fi
    sleep .25
  done
  if [[ "$fail_seen" != 1 ]];then
    echo H1614_FAILED_B_NOT_OBSERVED_KEEP_ORIGINAL_FAILURE >&2
    grep -E 'V4_PUBLIC_PATH_|V4_ORIGINAL_GO_.*READY' "$TMP/client.log" | tail -50 >&2 || true
    exit 1
  fi
  grep -Fq 'V4_PUBLIC_PATH_CANDIDATE role=client generation=2' "$TMP/client.log"
  if grep -Fq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2' "$TMP/client.log";then
    echo H1614_REJECT_MISTAKEN_FAILED_B_PROMOTION >&2;exit 1
  fi
  if grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log";then
    echo H1614_OLD_A_STOPPED_BEFORE_FAILED_B >&2;exit 1
  fi
  sudo -n kill -0 "$(cat "$TMP/client.pid")"
  sudo -n kill -0 "$(cat "$TMP/server.pid")"
  # Prove the B-specific filter matched actual kernel packets, not just
  # an arbitrary timeout. A remains reachable on its original source .2.
  sudo -n ip netns exec "$NSC" iptables -nvxL OUTPUT >"$ART/h1614-b-candidate-client-firewall-after.txt"
  python3 - "$ART/h1614-b-candidate-client-firewall-after.txt" <<'PY_CHECK'
import pathlib,re,sys
lines=pathlib.Path(sys.argv[1]).read_text().splitlines()
matches=[s for s in lines if 'DROP' in s and '10.25.0.3' in s and 'dpt:443' in s]
assert len(matches)==1,matches
packets=int(matches[0].split()[0])
assert packets>0,("B source rule did not drop real TCP segments",matches)
print("H1614_KERNEL_ONLY_B_TCP_BLOCK_CONFIRMED packets="+str(packets),flush=True)
PY_CHECK
  # Server's genuine UDP echo is still active, and the original same Go/Rust
  # generation A must deliver actual NEW TUN business while B has FAILED.
  sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45906))
s.settimeout(6)
data=b"WBD_REAL_V4_ORIGINAL_GO/H1614_FAILED_B_A_STILL_LIVE/"+bytes([121])*64
assert s.sendto(data,("10.66.0.1",45901))==len(data)
reply,peer=s.recvfrom(8192)
assert reply==b"V4_SERVER_APP_ECHO/"+data and peer[0]=="10.66.0.1",(reply,peer)
print("H1614_REAL_FAILED_B_OLD_A_KERNEL_UDP_PASS",flush=True)
s.close()
' >"$ART/h1614-old-a-business.log" 2>&1 || {
    cat "$ART/h1614-old-a-business.log" >&2;exit 1;
  }
  cat "$ART/h1614-old-a-business.log"
  if grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log";then
    echo H1614_OLD_A_STOPPED_WHILE_B_FAILED >&2;exit 1
  fi
  # Now permit ONLY the proposed physical B route to establish a new,
  # genuinely authenticated third generation, without restarting Go/Rust.
  sudo -n ip netns exec "$NSC" iptables -D OUTPUT -s 10.25.0.3 -p tcp --dport 443 -j DROP
  sudo -n ip netns exec "$NSS" iptables -D OUTPUT -d 10.25.0.3 -p tcp --sport 443 -j DROP
  ready_generation=3
  echo H1614_B_COLD_FAILED_BUT_A_RETAINED_AND_FIREWALL_RESTORED
  path_ready=0
  for i in {1..240};do'''
    once(anchor,gate)
    # The base fixture's Game condition is not used in this Normal scenario,
    # but both marker occurrences must become dynamically scoped to gen3.
    old="grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' \"$TMP/client.log\" &&"
    new='grep -q "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=$ready_generation old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1" "$TMP/client.log" &&'
    assert s.count(old)==2,("H1614 original generation marker count",s.count(old))
    s=s.replace(old,new)
    check='  test "$(grep -c \x27M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK\x27 "$ART/plan028-real-path-switched-business.log")" -eq 5'
    after=check+'''
  grep -Fq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' "$TMP/client.log"
  grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log"
  echo H1614_FAILED_B_NEW_GEN3_REAL_TLS_RUST_AND_EXACT_A_STOP_PASS'''
    once(check,after)
    # Copy ONLY allowlisted safe event metadata after both original owned Stop
    # and before EXIT deletes ephemeral TLS secrets and native raw logs.
    after_stop='# Sensitive logs contain NO TLS secret/cold/exporter keys. Persist only the'
    event=r'''if [[ "$PATH_SWITCH" == 1 ]];then
  grep -E 'V4_PUBLIC_PATH_|V4_ORIGINAL_GO_CLIENT_NATIVE_READY|V4_PUBLIC_LEASE_APPLIED|V4_PUBLIC_NATIVE_STOP_DRAINED' "$TMP/client.log" |
    tail -130 >"$ART/h1614-client-path-events.log" || true
fi
'''
    once(after_stop,event+after_stop)
    assert "H1614_REAL_FAILED_B_OLD_A_KERNEL_UDP_PASS" in s
    assert "H1614_FAILED_B_NEW_GEN3_REAL_TLS_RUST_AND_EXACT_A_STOP_PASS" in s
    return s

if len(sys.argv)==2 and sys.argv[1]=="--preflight":
    s=generate()
    assert "ECHO_PACKETS=11" in s and "s.settimeout(225)" in s
    assert s.count("H1614_REAL_FAILED_B_OLD_A_KERNEL_UDP_PASS")==1
    print("H1614_EXACT_ORIGINAL_NATIVE_BASE_NEGATIVE_FIXTURE_PREFLIGHT_PASS")
elif len(sys.argv)==2:
    dst=Path(sys.argv[1])
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(generate())
    dst.chmod(0o755)
    print("H1614_SOURCE_LOCKED_NEGATIVE_B_TEMP_FIXTURE_GENERATED")
else:
    raise SystemExit("expected --preflight or output path")
