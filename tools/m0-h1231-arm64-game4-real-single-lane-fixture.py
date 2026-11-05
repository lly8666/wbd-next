#!/usr/bin/env python3
"""PLAN028 H1231 native ARM64: same-epoch single-lane TLS/Rust hot rotation,
Game4 lane1→2→3→4 twice; three continuous real inner UDP clients."""
from pathlib import Path
import sys
if len(sys.argv)!=3 or sys.argv[2] not in ("game4-off","game4-fixed6"):
    raise SystemExit("usage: fixture.py OUTPUT {game4-off|game4-fixed6}")
out=Path(sys.argv[1]); scene=sys.argv[2]
s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
def sub(a,b,count=1):
    global s
    if s.count(a)!=count:
        raise AssertionError((scene,"unexpected source fixture",a[:100],s.count(a),count))
    s=s.replace(a,b)
sub("for i in range(160):","for i in range(12000):")
original='start_client "$NSB" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 \'--game-fec fixed6 --record-cipher aes-256-gcm\''
extra="--rotation-interval 18s --rotation-jitter 3s --record-cipher aes-256-gcm"
if scene=="game4-fixed6":extra="--game-fec fixed6 "+extra
sub(original,'start_client "$NSB" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 \''+extra+'\'')
if scene=="game4-off":
    sub("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6",
        "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0",2)
anchor='wait "$PA" "$PB" "$PC"\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode='
inject=r'''
# Physical NIC/IP/MTU, original TLS route key and one server443 all fixed.
# Precisely 8 alternating one-lane A→B replacements, with all three
# original protected clients continuously sending TUN UDP with NO retry.
ART="fixed-kernel-result"
SINGLE_MODE="@SCENE@"
snapshot(){
 local when="$1"
 for item in "alice $NSA mxa0" "bob $NSB mxb0" "carol $NSC mxc0";do
   read -r who ns iface <<<"$item"
   sudo -n ip -n "$ns" -j route get 10.25.0.1 >"$ART/$when-$who-route.json"
   sudo -n ip -n "$ns" -j link show dev "$iface" >"$ART/$when-$who-link.json"
 done
}
snapshot before
cat >"$TMP/hot-lane-stream.py" <<'PY_STREAM'
import json,math,os,socket,sys,time
src,who,finish,out=sys.argv[1:]
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind((src,0));sock.settimeout(.08)
sent=0;got=0;rtts=[];recv=[];first_send=time.time_ns()
while not os.path.exists(finish) and time.time_ns()-first_send<230_000_000_000:
    payload=("WBD_MIXED443/HOT_"+who+"/"+str(sent)).encode()
    at=time.monotonic();sock.sendto(payload,("10.66.0.1",45901))
    sent+=1
    try:
        data,peer=sock.recvfrom(4096)
        if data==b"WBD_MIXED_ECHO/"+payload and peer[0]=="10.66.0.1":
            got+=1;rtts.append((time.monotonic()-at)*1000);recv.append(time.time_ns())
    except socket.timeout:pass
    time.sleep(.10)
sock.close()
rtts.sort()
v={"device":who,"source":src,"sent":sent,"received":got,"missed":sent-got,
   "rtt_p99_ms":rtts[max(0,math.ceil(.99*len(rtts))-1)] if rtts else None,
   "max_receipt_gap_ms":max(((b-a)/1e6 for a,b in zip(recv,recv[1:])),default=None),
   "first_send_ns":first_send,"last_recv_ns":recv[-1] if recv else None,
   "no_application_retries":True}
open(out,"w").write(json.dumps(v,indent=2)+"\n")
print("GAME4_LANE_HOT_REAL_UDP "+str(v),flush=True)
PY_STREAM
for item in "alice $NSA $IPA" "bob $NSB $IPB" "carol $NSC $IPC";do
 read -r who ns ip <<<"$item"
 sudo -n ip netns exec "$ns" python3 "$TMP/hot-lane-stream.py" "$ip" "$who" \
   "$TMP/hot-finish" "$ART/hot-stream-$who.json" >"$TMP/hot-stream-$who.log" 2>&1 &
 case "$who" in
  alice) HP_A=$!;;
  bob) HP_B=$!;;
  carol) HP_C=$!;;
 esac
done
rotated=0
for _ in $(seq 1 1120);do
  if [[ "$(grep -c 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client' "$TMP/bob.log" || true)" -ge 8 ]] &&
     [[ "$(grep -c 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=server' "$TMP/server.log" || true)" -ge 8 ]];then
    rotated=1;break
  fi
  sleep .25
done
if [[ "$rotated" != 1 ]];then
 echo "H1231_SINGLE_LANE_FAILURE: no eight authentic slot swaps" >&2
 touch "$TMP/hot-finish"
 wait "$HP_A" "$HP_B" "$HP_C" || true
 exit 1
fi
sleep 4
touch "$TMP/hot-finish"
wait "$HP_A" "$HP_B" "$HP_C"
snapshot after
for who in server alice bob carol;do cp "$TMP/$who.log" "$ART/hot-runtime-$who.log";done
python3 - "$SINGLE_MODE" "$TMP/bob.log" "$TMP/server.log" \
  "$ART/hot-native-evidence.json" <<'PY_ORACLE'
import json,pathlib,re,sys
mode,client_path,server_path,dest=sys.argv[1:]
client=pathlib.Path(client_path).read_text()
server=pathlib.Path(server_path).read_text()
cr=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=(\d+) lane=(\d+) cycle=(\d+) old_client_port=(\d+) new_client_port=(\d+) unchanged_siblings=3 original_TLS_Rust_M4=1",client)
sr=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=(\d+) rotation=(\d+) client_port=(\d+) server_port=(\d+) same_game_adapter=1 sibling_lane_restarts=0 original_TLS=1 Rust_M4=1",server)
assert len(cr)>=8 and len(sr)>=8,(len(cr),len(sr),client[-1500:],server[-1500:])
cr=cr[:8];sr=sr[:8]
assert [int(x[1]) for x in cr]==[1,2,3,4,1,2,3,4],cr
assert [int(x[0]) for x in sr]==[1,2,3,4,1,2,3,4],sr
assert [int(x[2]) for x in cr]==list(range(1,9)),cr
assert [int(x[1]) for x in sr]==[1,1,1,1,2,2,2,2],sr
assert [int(c[4]) for c in cr]==[int(s[2]) for s in sr],(cr,sr)
assert all(int(c[0])==1 for c in cr),cr
assert all(int(s[3])==443 for s in sr),sr
assert len({int(c[4]) for c in cr})==8
# One existing GameAdapter/group only; no 2nd global TLS cohort and no
# replacement native TUN reader or unrelated client restart.
assert client.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=4")==1
assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4")==1
assert client.count("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=1")==1
assert "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2" not in client
assert server.count("V4_PUBLIC_GAME_MULTI_GROUP_READY role=server")==2
assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==1
assert not re.search(r"V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=one-lane",server)
due=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=1 unchanged_path=1 actual_delay_ms=(\d+) jitter_max_ms=(\d+)",client)[:8]
assert len(due)==8 and all(15000<=int(a)<=21000 and int(b)==3000 for a,b in due),due
assert len(set(a for a,b in due))>=4,due
streams={}
for who in ("alice","bob","carol"):
    v=json.loads(pathlib.Path("fixed-kernel-result/hot-stream-"+who+".json").read_text())
    streams[who]=v
    assert v["sent"]>=800 and v["received"]>=v["sent"]*.995,(who,v)
    assert v["max_receipt_gap_ms"]<1000,(who,v)
    assert v["rtt_p99_ms"]<20,(who,v)
    before=json.loads(pathlib.Path("fixed-kernel-result/before-"+who+"-route.json").read_text())[0]
    after=json.loads(pathlib.Path("fixed-kernel-result/after-"+who+"-route.json").read_text())[0]
    assert all(before.get(f)==after.get(f) for f in ("dev","prefsrc","src","gateway","mtu")),who
    for part in ("link",):
        b=json.loads(pathlib.Path("fixed-kernel-result/before-"+who+"-"+part+".json").read_text())[0]
        a=json.loads(pathlib.Path("fixed-kernel-result/after-"+who+"-"+part+".json").read_text())[0]
        assert a["ifindex"]==b["ifindex"] and a["mtu"]==b["mtu"],who
result={"result":"PASS","mode":mode,"platform":"original Go TLS/Rust ARM64+ARM64 native",
    "server_port":443,"same_native_game_adapter":True,
    "game4_real_lane_sequence":[int(x[1]) for x in cr],
    "authenticated_server_client_single_lane_port_correspondence":True,
    "native_group_recreated_for_one_lane":False,
    "unaffected_three_lanes_not_reauthenticated_each_turn":True,
    "actual_random_delay_ms":[int(a) for a,b in due],
    "real_no_app_retry_three_client_udp":streams,
    "physical_route_interface_IP_MTU_unchanged":True,
    "other_clients_ongoing":True,
    "outer_complete_ipv4_mtu_default":1460,
    "H998_live_MTU_shrink":"FAIL_RETAINED"}
pathlib.Path(dest).write_text(json.dumps(result,indent=2)+"\n")
print("H1231_NATIVE_ARM64_GAME4_EIGHT_TRUE_SINGLE_LANE_HOT_SWAPS_PASS",mode,flush=True)
PY_ORACLE
'''
inject=inject.replace("@SCENE@",scene)
if s.count(anchor)!=1:raise AssertionError(("insertion mismatch",s.count(anchor)))
s=s.replace(anchor,'wait "$PA" "$PB" "$PC"\n'+inject+'\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=',1)
out.write_text(s);out.chmod(0o700)
print("H1231 native Game4 true eight single-lane turns:",scene)
