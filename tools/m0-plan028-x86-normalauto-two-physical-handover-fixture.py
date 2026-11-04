#!/usr/bin/env python3
"""H1192 original Go TLS/Rust Normal Auto two REAL physical source-IP switches.
Reuse one443 three-device native mixed fixture; no product or steady-wire edits.
"""
from pathlib import Path
import sys
out=Path(sys.argv[1])
s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
assert s.count("for i in range(160):")==1
s=s.replace("for i in range(160):","for i in range(360):",1)
anchor='wait "$PB" "$PC"'+chr(10)+'sudo -n kill -TERM "$(cat "$TMP/bob.pid")"'
assert s.count(anchor)==1,"original mixed native owned Stop anchor changed"
scene=r'''# Original Go TLS authenticated Carol Normal Auto, Bob Game4FEC6,
# Alice Game2 already precisely stopped. One native Rust shared TUN.
ART="fixed-kernel-result"
n0="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
g0="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$n0" == 1375 && "$g0" == 1358 ]]
game_live(){
  local tag="$1" times="$2"
  for i in $(seq 0 31);do
    send_udp "$NSB" "$IPB" "$tag-$i" 1 "$TMP/B-game-live.log"
    date +%s%N >>"$times"
    sleep 0.4
  done
}
game_live GAME4_HEALTH_NORMAL_CHANGE1 "$TMP/B-game-live1-ns.txt" &
game1_pid=$!
for _ in {1..120};do
 test -s "$TMP/B-game-live1-ns.txt" && break
 sleep 0.05
done
test -s "$TMP/B-game-live1-ns.txt"
changed1="$(date +%s%N)"
sudo -n ip -n "$NSC" addr add 10.25.0.9/24 dev mxc0
sudo -n ip -n "$NSC" link set mxc0 mtu 1280
sudo -n ip -n "$NSC" route replace 10.25.0.1/32 dev mxc0 src 10.25.0.9
sudo -n ip -n "$NSC" -j route get 10.25.0.1 >"$ART/plan028-h1192-normal-route-new.json"
ready1=0
for _ in {1..180};do
 if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true' "$TMP/carol.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/carol.log";then
  ready1=1;break
 fi
 sleep 0.25
done
[[ "$ready1" == 1 ]] || { echo "H1192 genuine Normal Auto new M4 gen2 or old gen1 Stop missing" >&2;exit 1; }
new1="$(date +%s%N)"
wait "$game1_pid"
send_udp "$NSC" "$IPC" NORMAL_AUTO_ACTUAL_NEW_GEN2 16 "$TMP/C-new2.log"
n1="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$n1" -ge 1100 && "$n1" -lt "$n0" ]]
game_live GAME4_HEALTH_NORMAL_CHANGE2 "$TMP/B-game-live2-ns.txt" &
game2_pid=$!
for _ in {1..120};do
 test -s "$TMP/B-game-live2-ns.txt" && break
 sleep 0.05
done
test -s "$TMP/B-game-live2-ns.txt"
changed2="$(date +%s%N)"
sudo -n ip -n "$NSC" link set mxc0 mtu 1500
sudo -n ip -n "$NSC" route replace 10.25.0.1/32 dev mxc0 src 10.25.0.4
sudo -n ip -n "$NSC" -j route get 10.25.0.1 >"$ART/plan028-h1192-normal-route-restored.json"
ready2=0
for _ in {1..180};do
 if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true' "$TMP/carol.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2' "$TMP/carol.log";then
  ready2=1;break
 fi
 sleep 0.25
done
[[ "$ready2" == 1 ]] || { echo "H1192 genuine Normal Auto new M4 gen3 or old gen2 Stop missing" >&2;exit 1; }
new2="$(date +%s%N)"
wait "$game2_pid"
send_udp "$NSC" "$IPC" NORMAL_AUTO_ACTUAL_NEW_GEN3 16 "$TMP/C-new3.log"
n2="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
g2="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
python3 - "$TMP/carol.log" "$TMP/bob.log" "$TMP/B-game-live1-ns.txt" "$TMP/B-game-live2-ns.txt" \
 "$ART/plan028-h1192-normal-route-new.json" "$ART/plan028-h1192-normal-route-restored.json" "$IPC" \
 "$changed1" "$new1" "$changed2" "$new2" "$n0" "$n1" "$n2" "$g2" \
 "$ART/plan028-h1192-normal-auto-two-source4.json" <<'PY_H1192'
import json,pathlib,re,sys
normal,game=(pathlib.Path(v).read_text() for v in sys.argv[1:3])
t1,t2=([int(x) for x in pathlib.Path(v).read_text().splitlines()] for v in sys.argv[3:5])
r1,r2=(json.loads(pathlib.Path(v).read_text())[0] for v in sys.argv[5:7])
lease=sys.argv[7]
a,b,c,d=map(int,sys.argv[8:12]);m0,m1,m2,g0=map(int,sys.argv[12:16])
assert len(t1)==32 and t1[0]<a<b<t1[-1],("Game4 first actual UDP",len(t1),a,b)
assert len(t2)==32 and t2[0]<c<d<t2[-1],("Game4 second actual UDP",len(t2),c,d)
assert r1["dev"]=="mxc0" and r1["prefsrc"]=="10.25.0.9",r1
assert r2["dev"]=="mxc0" and r2["prefsrc"]=="10.25.0.4",r2
gn=[int(v) for v in re.findall(r'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)',normal)]
gg=[int(v) for v in re.findall(r'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)',game)]
old=[int(v) for v in re.findall(r'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)',normal)]
leases=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32',normal)
assert gn==[1,2,3] and old==[1,2] and gg==[1],(gn,old,gg)
assert len(leases)>=3 and set(leases)=={lease},leases
assert m0==1375 and 1100<=m1<m0 and m2<=m0 and g0==1358
result={"scope":"REAL_X86_X86_NORMAL_AUTO_TWO_SOURCE_IP_HANDOVERS_WITH_HEALTHY_GAME4",
 "normal_auto_authenticated_generations":gn,"old_normal_exact_stops":old,
 "game4_generation_unchanged":gg==[1],"game4_live_UDP_during_both":[len(t1),len(t2)],
 "normal_new_generation_udp":[16,16],"one_server_port":443,
 "physical_source4_sequence":["10.25.0.4","10.25.0.9","10.25.0.4"],
 "physical_mtu_sequence":[1500,1280,1500],"outer_user_mtu":1460,
 "inner_mtu_original":m0,"inner_mtu_new":m1,"inner_mtu_restored_conservative":m2,
 "sibling_game4_inner_mtu":g0,"same_tunnel_IP":True,"normal_tunnel_IP":lease,
 "physical_command_to_ready_ms":[round((b-a)/1e6,2),round((d-c)/1e6,2)],
 "exact_event_to_TLS":"NOT_MEASURED","auth_to_first_packet":"NOT_MEASURED",
 "cpu_causal":"NOT_MEASURED","loss5":"NOT_IN_THIS_SCENE"}
pathlib.Path(sys.argv[16]).write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1192_X86_NORMAL_AUTO_REAL_PHYSICAL_TWO_REAUTH_PASS",flush=True)
PY_H1192
'''
s=s.replace(anchor,'wait "$PB" "$PC"'+chr(10)+scene+'sudo -n kill -TERM "$(cat "$TMP/bob.pid")"',1)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1192_X86_NORMAL_AUTO_PHYSICAL_FIXTURE_ASSEMBLED",flush=True)
