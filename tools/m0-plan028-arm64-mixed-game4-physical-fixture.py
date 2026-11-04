#!/usr/bin/env python3
"""One genuine ARM64 shared443 mixed Normal/Game Game4 physical switch test.
Extend only the established mixed 48-UDP netns fixture; no product wire edit."""
from pathlib import Path
import sys

src=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
def change(old,new):
    global src
    if src.count(old)!=1:
        raise RuntimeError(f"mature mixed fixture changed: {old[:90]!r}; count={src.count(old)}")
    src=src.replace(old,new,1)

change('python3 - "$addr" "$tag" "$count" >"$log" <<\'PY\'',
       'python3 - "$addr" "$tag" "$count" "${6:-0}" >"$log" <<\'PY\'')
change("import socket,sys\nsrc,tag,count=sys.argv[1],sys.argv[2],int(sys.argv[3])",
       "import socket,sys,time\nsrc,tag,count=sys.argv[1],sys.argv[2],int(sys.argv[3])\ndelay=float(sys.argv[4])")
change('  print(f"REAL_MIXED_UDP {tag} {i}",flush=True)\ns.close()',
       '  print(f"REAL_MIXED_UDP {tag} {i} ack_ns={time.time_ns()}",flush=True)\n  if delay:time.sleep(delay)\ns.close()')

extra=r'''# Real physical Game4 source/MTU change while one unaffected Normal Auto
# client delivers replies throughout; no synthetic notifier or second TUN.
ART="fixed-kernel-result"
old_game="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
old_normal="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
send_udp "$NSC" "$IPC" NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH 48 "$TMP/C-live.log" 0.4 &
live=$!
for _ in {1..120};do
 grep -q 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH 0 ack_ns=' "$TMP/C-live.log" && break
 sleep .05
done
grep -q 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH 0 ack_ns=' "$TMP/C-live.log"
changed_ns="$(date +%s%N)"
sudo -n ip -n "$NSB" addr add 10.25.0.9/24 dev mxb0
sudo -n ip -n "$NSB" link set mxb0 mtu 1280
sudo -n ip -n "$NSB" route replace 10.25.0.1/32 dev mxb0 src 10.25.0.9
sudo -n ip -n "$NSB" -j route get 10.25.0.1 >"$ART/plan028-h1162-game4-os-route.json"
sudo -n ip -n "$NSB" -j link show mxb0 >"$ART/plan028-h1162-game4-os-link.json"
new_ready=0
for _ in {1..140};do
 if grep -q 'V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/bob.log";then
    new_ready=1;break
 fi
 sleep .25
done
[[ "$new_ready" == 1 ]] || { echo "H1162 missing true original Game4 TLS reauthentication and exact old Stop" >&2;exit 1; }
ready_ns="$(date +%s%N)"
wait "$live"
test "$(grep -c 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH .* ack_ns=' "$TMP/C-live.log")" -eq 48
send_udp "$NSB" "$IPB" GAME4_FIXED6_NEW_OS_SOURCE 32 "$TMP/B-new.log"
new_game="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
new_normal="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$old_game" == 1358 && "$new_game" == 1178 &&
   "$old_normal" == 1375 && "$new_normal" == 1375 ]] ||
 { echo "H1162 original owner cross-client MTU isolation mismatch" >&2;exit 1; }
python3 - "$TMP/bob.log" "$TMP/carol.log" "$TMP/C-live.log" \
 "$ART/plan028-h1162-game4-os-route.json" "$ART/plan028-h1162-game4-os-link.json" \
 "$changed_ns" "$ready_ns" "$old_game" "$new_game" "$old_normal" "$new_normal" \
 "$ART/plan028-h1162-mixed-game4-physical.json" <<'PY_H1162'
import json,pathlib,re,sys
bob,carol,live=(pathlib.Path(x).read_text() for x in sys.argv[1:4])
route=json.loads(pathlib.Path(sys.argv[4]).read_text())[0]
link=json.loads(pathlib.Path(sys.argv[5]).read_text())[0]
changed,ready=map(int,sys.argv[6:8])
old_g,new_g,old_n,new_n=map(int,sys.argv[8:12])
acks=[int(x) for x in re.findall(r'REAL_MIXED_UDP NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH \d+ ack_ns=(\d+)',live)]
assert len(acks)==48 and acks[0]<changed<ready<acks[-1],(len(acks),acks[:2],changed,ready,acks[-2:])
assert route["dev"]=="mxb0" and route["prefsrc"]=="10.25.0.9",route
assert link["mtu"]==1280,link
leases=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32',bob)
assert len(leases)>=2 and len(set(leases))==1,leases
assert bob.index("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2")<bob.index("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1")
assert 'V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6' in bob
assert 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client' not in carol
out={"scope":"NATIVE_ARM64_MIXED_NORMAL_GAME2_GAME4_PHYSICAL_REAUTH_SINGLE_SHARED_443",
 "source4_before":"10.25.0.3","source4_after":"10.25.0.9",
 "shared_port":443,"game4_lanes":4,"outer_user_ipv4_mtu":1460,"physical_new_mtu":1280,
 "game4_old_inner_os_mtu":old_g,"game4_new_inner_os_mtu":new_g,
 "normal_old_inner_os_mtu":old_n,"normal_new_inner_os_mtu":new_n,
 "game4_lease_preserved":leases[0],"normal_live_udp_echoes":48,
 "game4_new_udp_echoes":32,"new_tls_auth_ready":True,"old_exact_stop":True,
 "normal_not_reauthenticated":True,
 "physical_command_to_ready_ms":round((ready-changed)/1e6,2),
 "notifier_to_tls_start_ms":"NOT_MEASURED","auth_to_first_packet_ms":"NOT_MEASURED",
 "cpu_p99":"NOT_MEASURED"}
pathlib.Path(sys.argv[12]).write_text(json.dumps(out,indent=2)+"\n")
print("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS",flush=True)
PY_H1162
'''
change('wait "$PA" "$PB" "$PC"\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED',
       'wait "$PA" "$PB" "$PC"\n'+extra+'\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED')
out=Path(sys.argv[1])
out.write_text(src)
out.chmod(0o700)
print("M0_PLAN028_H1162_ARM64_MIXED_PHYSICAL_SOURCE4_FIXTURE_READY")
