#!/usr/bin/env python3
"""PLAN028 H1222: unchanged physical network, timer-triggered original TLS
generation handover while three authenticated devices run real UDP business.
Each Action matrix job is ONE native Linux x86_64/x86_64 scenario.
"""
from pathlib import Path
import sys

if len(sys.argv)!=3:
    raise SystemExit("usage: fixture.py OUTPUT {normal-auto|game2-off|game4-fixed6}")
out=Path(sys.argv[1])
scene=sys.argv[2]
target={
    "normal-auto":("carol", "mxc0"),
    "game2-off":("alice", "mxa0"),
    "game4-fixed6":("bob", "mxb0"),
}
if scene not in target:
    raise SystemExit("invalid mode scene")
who,nic=target[scene]
s=Path("tools/m0-plan028-mixed-normal-game-native.sh").read_text()
assert s.count("for i in range(160):")==1
s=s.replace("for i in range(160):","for i in range(4000):",1)
client={
    "normal-auto":'start_client "$NSC" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-auto \'--record-cipher aes-128-gcm\'',
    "game2-off":'start_client "$NSA" mxa0 10.25.0.2 mxa4 41031 alice alice-mixed-protected game2 \'--record-cipher chacha20-poly1305\'',
    "game4-fixed6":'start_client "$NSB" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 \'--game-fec fixed6 --record-cipher aes-256-gcm\'',
}[scene]
assert s.count(client)==1,"exact original client assembly changed"
s=s.replace(client,client.replace("--record-cipher","--rotation-interval 12s --record-cipher"),1)
if scene=="normal-auto":
    old='server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==1'
    assert s.count(old)==1
    s=s.replace(old,'server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")>=3',1)

anchor='wait "$PA" "$PB" "$PC"\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" "$TMP/bob.log"'
assert s.count(anchor)==1, "single traffic insertion anchor changed"
inject=r'''
# Native timing scenario: absolutely NO route, interface IPv4, or physical
# MTU mutation. One selected client rotates by an explicitly configured
# interval; other devices remain independently authenticated and sending.
ART="fixed-kernel-result"
TIMER_SCENE="@SCENE@"
TIMER_TARGET="@TARGET@"
TIMER_NIC="@NIC@"
route_snapshot(){
 local stamp="$1"
 for item in "alice $NSA mxa0" "bob $NSB mxb0" "carol $NSC mxc0";do
   read -r who ns nic <<<"$item"
   sudo -n ip -n "$ns" -j route get 10.25.0.1 >"$ART/timed-$stamp-$who-route.json"
   sudo -n ip -n "$ns" -j link show dev "$nic" >"$ART/timed-$stamp-$who-link.json"
 done
}
cpu_snapshot(){
 python3 - "$TMP" <<'PY_CPU'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); data={}
for who in ("server","alice","bob","carol"):
    pid=int((root/(who+".pid")).read_text())
    stat=(pathlib.Path("/proc")/str(pid)/"stat").read_text()
    tail=stat[stat.rfind(")")+2:].split()
    data[who]={"pid":pid,"utime_ticks":int(tail[11]),"stime_ticks":int(tail[12])}
print(json.dumps(data))
PY_CPU
}
route_snapshot before
cpu_snapshot >"$ART/timed-cpu-before.json"
cat >"$TMP/timed-stream.py" <<'PY_STREAM'
import json,math,os,socket,sys,time
src,tag,stopfile,out=sys.argv[1:]
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((src,0))
s.settimeout(.07)
start=time.monotonic()
seq=0;send_ns=[];recv_ns=[];rtts=[]
while not os.path.exists(stopfile) and time.monotonic()-start<70:
    payload=("WBD_MIXED443/TIMED_"+tag+"/"+str(seq)).encode()
    sent_at=time.monotonic()
    send_ns.append(time.time_ns())
    s.sendto(payload,("10.66.0.1",45901))
    try:
        reply,addr=s.recvfrom(4096)
        if reply==b"WBD_MIXED_ECHO/"+payload and addr[0]=="10.66.0.1":
            rtts.append((time.monotonic()-sent_at)*1000)
            recv_ns.append(time.time_ns())
    except socket.timeout:
        pass
    seq+=1
    time.sleep(.10)
s.close()
ordered=sorted(rtts)
p99=ordered[max(0,math.ceil(.99*len(ordered))-1)] if ordered else None
gaps=[(b-a)/1e6 for a,b in zip(recv_ns,recv_ns[1:])]
data={"device":tag,"physical_source":src,"sent":seq,"received":len(rtts),
      "no_application_retry":True,"received_only_rtt_p99_ms":p99,
      "max_successful_receipt_gap_ms":max(gaps,default=None),
      "first_send_unix_ns":send_ns[0] if send_ns else None,
      "last_receive_unix_ns":recv_ns[-1] if recv_ns else None,
      "receipts_unix_ns":recv_ns}
with open(out,"w") as f:json.dump(data,f)
print("TIMED_NATIVE_REAL_UDP "+tag+" "+str(seq)+"/"+str(len(rtts)),flush=True)
PY_STREAM
for item in "alice $NSA $IPA" "bob $NSB $IPB" "carol $NSC $IPC";do
 read -r who ns ip <<<"$item"
 sudo -n ip netns exec "$ns" python3 "$TMP/timed-stream.py" "$ip" "$who" \
   "$TMP/timed-finish" "$ART/timed-stream-$who.json" >"$TMP/timed-stream-$who.log" 2>&1 &
 case "$who" in
  alice) TS_A=$!;;
  bob) TS_B=$!;;
  carol) TS_C=$!;;
 esac
done
ready3=0
for _ in $(seq 1 280);do
  if grep -Fq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true' "$TMP/$TIMER_TARGET.log" &&
     grep -Fq 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2' "$TMP/$TIMER_TARGET.log" &&
     [[ "$(grep -c 'V4_PUBLIC_TIMER_ROTATION_DUE role=client' "$TMP/$TIMER_TARGET.log" || true)" -ge 2 ]];then
    ready3=1;break
  fi
  sleep .25
done
if [[ "$ready3" != 1 ]];then
  echo "TIMER_SCENE_FAILURE target=$TIMER_TARGET: two actual TLS/M4 rotations not ready" >&2
  touch "$TMP/timed-finish"
  wait "$TS_A" "$TS_B" "$TS_C" || true
  exit 1
fi
ready3_ns="$(date +%s%N)"
sleep 2
touch "$TMP/timed-finish"
wait "$TS_A" "$TS_B" "$TS_C"
cpu_snapshot >"$ART/timed-cpu-after.json"
route_snapshot after
python3 - "$TIMER_SCENE" "$TIMER_TARGET" "$ready3_ns" \
 "$TMP/alice.log" "$TMP/bob.log" "$TMP/carol.log" \
 "$ART/timed-evidence.json" <<'PY_ORACLE'
import json,pathlib,re,sys
scene,target,ready_ns=sys.argv[1],sys.argv[2],int(sys.argv[3])
logs=dict(zip(("alice","bob","carol"),[pathlib.Path(p).read_text() for p in sys.argv[4:7]]))
assert target in logs
target_log=logs[target]
gen=[int(x) for x in re.findall(r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)",target_log)]
old=[int(x) for x in re.findall(r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",target_log)]
timer=[x for x in target_log.splitlines() if "V4_PUBLIC_TIMER_ROTATION_DUE role=client" in x]
assert gen[:3]==[1,2,3] and old[:2]==[1,2],(gen,old)
assert len(timer)>=2 and all("same_physical_interface_ipv4=true" in x and "unchanged_path=true" in x for x in timer[:2]),timer
timer_due_unix_ms=[int(re.search(r"unix_ms=(\d+)",x).group(1)) for x in timer[:2]]
assert timer_due_unix_ms[0]<timer_due_unix_ms[1]
for who in ("alice","bob","carol"):
    before=json.loads(pathlib.Path(f"fixed-kernel-result/timed-before-{who}-route.json").read_text())[0]
    after=json.loads(pathlib.Path(f"fixed-kernel-result/timed-after-{who}-route.json").read_text())[0]
    for field in ("dev","prefsrc","src","gateway","mtu"):
        assert before.get(field)==after.get(field),(who,field,before,after)
    bi=json.loads(pathlib.Path(f"fixed-kernel-result/timed-before-{who}-link.json").read_text())[0]
    ai=json.loads(pathlib.Path(f"fixed-kernel-result/timed-after-{who}-link.json").read_text())[0]
    assert bi["ifindex"]==ai["ifindex"] and bi["mtu"]==ai["mtu"]==1500
    assert "V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client" not in logs[who],who
streams={who:json.loads(pathlib.Path(f"fixed-kernel-result/timed-stream-{who}.json").read_text())
         for who in ("alice","bob","carol")}
lease_receipts={}
for who in ("alice","bob","carol"):
    leases=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32",logs[who])
    lease_receipts[who]=leases
    assert len(leases)>=(3 if who==target else 1),(who,leases)
    assert set(leases)=={streams[who]["physical_source"]},(who,leases,streams[who]["physical_source"])
first_post_ready_echo_ms={}
for who,s in streams.items():
    next_reply=next((x for x in s["receipts_unix_ns"] if x>ready_ns),None)
    assert next_reply is not None,(who,"no real echo after authenticated M4 READY detection")
    first_post_ready_echo_ms[who]=round((next_reply-ready_ns)/1e6,3)
for who,s in streams.items():
    assert s["sent"]>=30 and s["received"]>=.70*s["sent"],(who,s)
    assert s["first_send_unix_ns"]<ready_ns<s["last_receive_unix_ns"],who
    if who!=target:
        assert s["received"]>=.85*s["sent"],(who,s)
    assert s["received_only_rtt_p99_ms"] is not None,who
cpu_before=json.loads(pathlib.Path("fixed-kernel-result/timed-cpu-before.json").read_text())
cpu_after=json.loads(pathlib.Path("fixed-kernel-result/timed-cpu-after.json").read_text())
cpu_ticks={who:sum(cpu_after[who][field]-cpu_before[who][field] for field in ("utime_ticks","stime_ticks"))
           for who in cpu_before}
assert all(v>=0 for v in cpu_ticks.values())
import os
ticks_per_second=os.sysconf("SC_CLK_TCK")
elapsed_s=(max(s["last_receive_unix_ns"] for s in streams.values())-
           min(s["first_send_unix_ns"] for s in streams.values()))/1e9
cpu_percent={who:round(100*(ticks/ticks_per_second)/elapsed_s,3)
             for who,ticks in cpu_ticks.items()}
result={"status":"PASS","source":"original Go TLS+Rust M4 native x86/x86",
        "mode_scene":scene,"timer_interval_seconds":12,"server_port":443,
        "physical_interface_ipv4_unchanged":True,"physical_mtu_unchanged":True,
        "target_authenticated_generations":gen[:3],"exact_old_stops":old[:2],
        "same_tunnel_ip":all(len(set(x))==1 for x in lease_receipts.values()),
        "actual_authenticated_lease_receipts":lease_receipts,
        "sibling_real_udp_live":True,
        "timer_due_unix_ms":timer_due_unix_ms,
        "second_timer_due_to_third_ready_detect_ms":round(ready_ns/1e6-timer_due_unix_ms[1],3),
        "native_READY_detect_to_first_real_echo_ms":first_post_ready_echo_ms,
        "streams":{w:{k:v for k,v in data.items() if k!="receipts_unix_ns"} for w,data in streams.items()},
        "cpu_process_ticks_during_scene":cpu_ticks,
        "cpu_process_percent_during_scene":cpu_percent,
        "cpu_causal_comparison":"NOT_MEASURED",
        "auth_to_first_packet_ms":"NOT_MEASURED",
        "old_027A_H998_live_same_socket_mtu":"FAIL_RETAINED",
        "remote_icmp_android":"NOT_RUN"}
pathlib.Path(sys.argv[7]).write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1222_TIMED_UNCHANGED_PATH_REAL_UDP_PASS "+scene,flush=True)
PY_ORACLE
'''
inject=inject.replace("@SCENE@",scene).replace("@TARGET@",who).replace("@NIC@",nic)
s=s.replace(anchor,'wait "$PA" "$PB" "$PC"\n'+inject+'\ngrep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" "$TMP/bob.log"',1)
# Preserve raw authenticated-generation logs before the base fixture's EXIT
# trap deletes its private namespace files. No secrets are emitted by client
# logs, and source-generated cert/key files remain confined to TMP.
final_anchor='echo "M0_PLAN028_H1151_NATIVE_X86_MIXED_ONE_PORT_ONE_RUST_TUN_PASS"'
assert s.count(final_anchor)==1
s=s.replace(final_anchor,
    'for who in server alice bob carol;do cp "$TMP/$who.log" "$ART/timed-runtime-$who.log";done\n'
    +final_anchor,1)
out.write_text(s)
out.chmod(0o700)
print("PLAN028 H1222 original TLS timer fixture generated:",scene)
