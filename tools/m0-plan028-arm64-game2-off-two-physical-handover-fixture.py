#!/usr/bin/env python3
"""H1193 native ARM64 Game2 off genuine two physical original TLS/Rust
replacements while independent Game4FEC6 and Normal Auto are live.
Same one443 original shared Rust TUN, no new packet handler or algorithm.
"""
from pathlib import Path
import sys
out=Path(sys.argv[1]);s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
assert s.count("for i in range(160):")==1
s=s.replace("for i in range(160):","for i in range(360):",1)
anchor='wait "$PA" "$PB" "$PC"'+chr(10)+'grep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4'
assert s.count(anchor)==1,"original mixed authenticated three-client anchor changed"
scene=r'''# Genuine Game2-off Alice with 2 lanes swaps physical mxa0 source4
# twice. No other client shares its logical lease or changes generation.
ART="fixed-kernel-result"
a0="$(sudo -n ip -n "$NSA" -j link show dev mxa4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
b0="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
c0="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$a0" == 1373 && "$b0" == 1358 && "$c0" == 1375 ]]
siblings(){
 local tag="$1" times="$2"
 for i in $(seq 0 23);do
  send_udp "$NSB" "$IPB" "$tag-GAME4-$i" 1 "$TMP/B-game2-sibling.log"
  send_udp "$NSC" "$IPC" "$tag-NORMAL-$i" 1 "$TMP/C-game2-sibling.log"
  date +%s%N >>"$times"
  sleep .4
 done
}
siblings GAME2_SWITCH1 "$TMP/A-siblings1-ns.txt" &
health1=$!
for _ in {1..120};do
 test -s "$TMP/A-siblings1-ns.txt" && break
 sleep .05
done
test -s "$TMP/A-siblings1-ns.txt"
changed1="$(date +%s%N)"
sudo -n ip -n "$NSA" addr add 10.25.0.9/24 dev mxa0
sudo -n ip -n "$NSA" link set mxa0 mtu 1280
sudo -n ip -n "$NSA" route replace 10.25.0.1/32 dev mxa0 src 10.25.0.9
sudo -n ip -n "$NSA" -j route get 10.25.0.1 >"$ART/plan028-h1193-game2-route-new.json"
ready1=0
for _ in {1..180};do
 if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/alice.log";then
  ready1=1;break
 fi
 sleep .25
done
[[ "$ready1" == 1 ]] || { echo "H1193 Game2 original TLS/Rust new gen2 or old1 Stop missing" >&2;exit 1; }
new1="$(date +%s%N)"
wait "$health1"
send_udp "$NSA" "$IPA" GAME2_OFF_AUTH_NEW_GEN2 16 "$TMP/A-game2-new2.log"
a1="$(sudo -n ip -n "$NSA" -j link show dev mxa4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$a1" -ge 1100 && "$a1" -lt "$a0" ]]
siblings GAME2_SWITCH2 "$TMP/A-siblings2-ns.txt" &
health2=$!
for _ in {1..120};do
 test -s "$TMP/A-siblings2-ns.txt" && break
 sleep .05
done
test -s "$TMP/A-siblings2-ns.txt"
changed2="$(date +%s%N)"
sudo -n ip -n "$NSA" link set mxa0 mtu 1500
sudo -n ip -n "$NSA" route replace 10.25.0.1/32 dev mxa0 src 10.25.0.2
sudo -n ip -n "$NSA" -j route get 10.25.0.1 >"$ART/plan028-h1193-game2-route-restored.json"
ready2=0
for _ in {1..180};do
 if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true' "$TMP/alice.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2' "$TMP/alice.log";then
  ready2=1;break
 fi
 sleep .25
done
[[ "$ready2" == 1 ]] || { echo "H1193 Game2 original TLS/Rust new gen3 or old2 Stop missing" >&2;exit 1; }
new2="$(date +%s%N)"
wait "$health2"
send_udp "$NSA" "$IPA" GAME2_OFF_AUTH_NEW_GEN3 16 "$TMP/A-game2-new3.log"
a2="$(sudo -n ip -n "$NSA" -j link show dev mxa4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
b2="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
c2="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
python3 - "$TMP/alice.log" "$TMP/bob.log" "$TMP/carol.log" \
 "$TMP/A-siblings1-ns.txt" "$TMP/A-siblings2-ns.txt" \
 "$ART/plan028-h1193-game2-route-new.json" "$ART/plan028-h1193-game2-route-restored.json" \
 "$IPA" "$changed1" "$new1" "$changed2" "$new2" "$a0" "$a1" "$a2" "$b2" "$c2" \
 "$ART/plan028-h1193-game2-two-physical.json" <<'PY_H1193'
import pathlib,json,re,sys
alice,bob,carol=[pathlib.Path(x).read_text() for x in sys.argv[1:4]]
t1,t2=([int(v) for v in pathlib.Path(x).read_text().splitlines()] for x in sys.argv[4:6])
route1,route2=(json.loads(pathlib.Path(x).read_text())[0] for x in sys.argv[6:8])
lease=sys.argv[8]
a,b,c,d=map(int,sys.argv[9:13])
mtus=list(map(int,sys.argv[13:18]))
assert len(t1)==24 and t1[0]<a<b<t1[-1],("first Game4/Normal live",len(t1),a,b)
assert len(t2)==24 and t2[0]<c<d<t2[-1],("second Game4/Normal live",len(t2),c,d)
assert route1["dev"]=="mxa0" and route1["prefsrc"]=="10.25.0.9",route1
assert route2["dev"]=="mxa0" and route2["prefsrc"]=="10.25.0.2",route2
gen=lambda text:[int(v) for v in re.findall(r'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)',text)]
stops=[int(v) for v in re.findall(r'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)',alice)]
assert gen(alice)==[1,2,3] and stops==[1,2] and gen(bob)==[1] and gen(carol)==[1]
leases=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32',alice)
assert len(leases)>=3 and set(leases)=={lease},leases
assert mtus[0]==1373 and 1100<=mtus[1]<mtus[0] and mtus[2]<=mtus[0] and mtus[3:]==[1358,1375]
result={"scope":"NATIVE_ARM64_GAME2_OFF_TWO_SOURCE_IP_REAUTH_WITH_GAME4_AND_NORMAL_HEALTHY",
 "physical_source4_sequence":["10.25.0.2","10.25.0.9","10.25.0.2"],
 "physical_mtu_sequence":[1500,1280,1500],"outer_user_mtu":1460,
 "game2_authenticated_generations":[1,2,3],"game2_exact_old_stops":stops,
 "game2_new_udp":[16,16],"tunnel_ip_preserved":True,"game2_lease":lease,
 "sibling_game4_stable":True,"sibling_normal_stable":True,
 "sibling_udp_each_switch":[[len(t1),len(t1)],[len(t2),len(t2)]],
 "game2_initial_inner_mtu":mtus[0],"game2_new_inner_mtu":mtus[1],
 "game2_restored_inner_mtu":mtus[2],"other_game4_inner_mtu":mtus[3],
 "other_normal_inner_mtu":mtus[4],"one_server_port":443,
 "command_to_ready_ms":[round((b-a)/1e6,2),round((d-c)/1e6,2)],
 "notifier_to_TLS":"NOT_MEASURED","auth_to_first_packet":"NOT_MEASURED",
 "CPU_causal":"NOT_MEASURED","loss5":"NOT_IN_THIS_SCENE"}
pathlib.Path(sys.argv[18]).write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1193_ARM64_GAME2_OFF_TWO_PHYSICAL_HEALTHY_SIBLINGS_PASS",flush=True)
PY_H1193
'''
s=s.replace(anchor,'wait "$PA" "$PB" "$PC"'+chr(10)+scene+'grep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4',1)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1193_ARM64_GAME2_TWO_PHYSICAL_FIXTURE_READY",flush=True)
