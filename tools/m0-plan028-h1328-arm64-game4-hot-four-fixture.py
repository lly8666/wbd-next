#!/usr/bin/env python3
"""PLAN028 test-only: original ARM64 Game4 Off hot-lane fixture.

Reuse mature original Go/Rust fixture, replace obsolete whole-group timer
oracle and its finite 4000-echo ceiling, not the product/data plane.
"""
import pathlib
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("usage: generator.py OUTPUT")
target = pathlib.Path(sys.argv[1])
with tempfile.TemporaryDirectory() as tmp:
    src = pathlib.Path(tmp) / "old-group.sh"
    subprocess.run([sys.executable, "tools/m0-plan028-x86-jittered-seven-modes-fixture.py",
                    str(src), "game4-off"], check=True)
    s = src.read_text()

def change(before, after):
    global s
    assert s.count(before) == 1, (before[:70], s.count(before))
    s = s.replace(before, after, 1)

# Actual prior native ARM64 185s: 36 warmup + 3964 stream replies = 4000.
# 3 * 10 UDP/s * 185s + 36 warmup < 6500 bounded echo receptions.
change("for i in range(4000):", "for i in range(6500):")
change('"last_receive_unix_ns":recv_ns[-1] if recv_ns else None,',
       '"last_receive_unix_ns":recv_ns[-1] if recv_ns else None,\n      "last_send_unix_ns":send_ns[-1] if send_ns else None,')

start = s.index("ready3=0\n")
sentinel = 'grep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0" "$TMP/bob.log"'
end = s.index(sentinel, start)
assert end > start
# The unchanged physical Game4 product intentionally replaces one M4 lane
# in the SAME group generation and never fires a full-group TIMER_DUE.
section = r'''ready4=0
for _ in $(seq 1 720);do
  if [[ "$(grep -c 'V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY role=client generation=1 lane=' "$TMP/bob.log" || true)" -ge 4 ]] &&
     [[ "$(grep -c 'V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=1 unchanged_path=1' "$TMP/bob.log" || true)" -ge 4 ]] &&
     [[ "$(grep -c 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=' "$TMP/server.log" || true)" -ge 4 ]];then
    ready4=1;break
  fi
  sleep .25
done
if [[ "$ready4" != 1 ]];then
  echo "M0_PLAN028_H1328_GAME4_HOT_FOUR_LANES_NOT_READY" >&2
  grep -E 'V4_PUBLIC_GAME_SINGLE_LANE_(READY|DUE|ROTATION_READY|COLD_RETRY_ARMED|ROTATION_FAILED)' "$TMP/bob.log" "$TMP/server.log" | tail -35 >&2 || true
  touch "$TMP/timed-finish"
  wait "$TS_A" "$TS_B" "$TS_C" || true
  exit 1
fi
ready4_ns="$(date +%s%N)"
sleep 4
touch "$TMP/timed-finish"
wait "$TS_A" "$TS_B" "$TS_C"
cpu_snapshot >"$ART/timed-cpu-after.json"
route_snapshot after
python3 - "$TMP" "$ART" "$ready4_ns" <<'PY_HOT'
import json,pathlib,re,sys
tmp,art,ready_ns=pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),int(sys.argv[3])
logs={n:(tmp/(n+".log")).read_text() for n in ("alice","bob","carol","server")}
bob,server=logs["bob"],logs["server"]
assert bob.count("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=1 old_generation=false")==1
assert "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2" not in bob
assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0" in bob
due=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=(\d+) unchanged_path=1 actual_delay_ms=(\d+) jitter_max_ms=(\d+)",bob)
client=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=(\d+) lane=(\d+) cycle=(\d+) old_client_port=(\d+) new_client_port=(\d+) unchanged_siblings=3 original_TLS_Rust_M4=1",bob)
owner=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY role=client generation=(\d+) lane=(\d+) new_client_port=(\d+) unaffected_sibling_lanes=3 original_TLS_Rust_M4=1",bob)
server_hot=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=(\d+) rotation=(\d+) client_port=(\d+) server_port=443 same_game_adapter=1 sibling_lane_restarts=0 original_TLS=1 Rust_M4=1",server)
assert len(due)>=4 and len(client)>=4 and len(owner)>=4 and len(server_hot)>=4,(due,client,owner,server_hot)
assert all(int(g)==1 and int(j)==3000 and 15000<=int(d)<=21000 for g,d,j in due[:4]),due[:4]
assert len(set(int(d) for g,d,j in due[:4]))>=2,due[:4]
assert [int(x[1]) for x in client[:4]]==[1,2,3,4],client[:4]
assert [int(x[1]) for x in owner[:4]]==[1,2,3,4],owner[:4]
assert [int(x[0]) for x in server_hot[:4]]==[1,2,3,4],server_hot[:4]
for c,o,s in zip(client[:4],owner[:4],server_hot[:4]):
    assert c[0]==o[0]=="1" and c[1]==o[1]==s[0] and c[4]==o[2]==s[2] and c[3]!=c[4]
    # Server counts first true hot association as rotation 1 (not 2).
    assert int(s[1])==1
initial=re.findall(r"V4_PUBLIC_GAME_GROUP_LANE_READY role=client group_generation=1 lane=(\d+) local_port=(\d+) server_port=443",bob)
assert len(initial)==4 and sorted(int(x[0]) for x in initial)==[1,2,3,4],initial
assert len({int(x[4]) for x in client[:4]}|{int(x[1]) for x in initial})==8
assert bob.count("V4_PUBLIC_GAME_OLD_COLD_TUPLE_RETIRE_SCHEDULED role=client lane=")>=4
streams={n:json.loads((art/("timed-stream-"+n+".json")).read_text()) for n in ("alice","bob","carol")}
leases={}
for n in ("alice","bob","carol"):
    lp=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32",logs[n])
    leases[n]=lp
    assert lp and len(set(lp))==1 and lp[0]==streams[n]["physical_source"],(n,lp)
    before=json.loads((art/("timed-before-"+n+"-route.json")).read_text())[0]
    after=json.loads((art/("timed-after-"+n+"-route.json")).read_text())[0]
    assert all(before.get(f)==after.get(f) for f in ("dev","prefsrc","src","gateway","mtu")),(n,before,after)
    b=json.loads((art/("timed-before-"+n+"-link.json")).read_text())[0]
    a=json.loads((art/("timed-after-"+n+"-link.json")).read_text())[0]
    assert a["ifindex"]==b["ifindex"] and a["mtu"]==b["mtu"]==1500
    assert "V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client" not in logs[n]
first_post={}
for n,v in streams.items():
    assert v["sent"]>=100 and v["received"]>=v["sent"]-max(3,int(.005*v["sent"])),(n,v["sent"],v["received"])
    assert v["received_only_rtt_p99_ms"] is not None
    assert v["max_successful_receipt_gap_ms"] is not None and v["max_successful_receipt_gap_ms"]<800,(n,v)
    assert v["last_send_unix_ns"] and v["last_receive_unix_ns"]
    assert v["last_send_unix_ns"]-v["last_receive_unix_ns"]<800_000_000,(n,"terminal_active_send_no_receive",v)
    assert v["first_send_unix_ns"]<ready_ns<v["last_receive_unix_ns"],n
    found=next((t for t in v["receipts_unix_ns"] if t>ready_ns),None)
    assert found is not None,(n,"no actual reply after fourth real native hot lane")
    first_post[n]=round((found-ready_ns)/1e6,3)
cpu_before=json.loads((art/"timed-cpu-before.json").read_text())
cpu_after=json.loads((art/"timed-cpu-after.json").read_text())
cpu={n:sum(cpu_after[n][f]-cpu_before[n][f] for f in ("utime_ticks","stime_ticks")) for n in cpu_before}
assert all(v>=0 for v in cpu.values())
sent=sum(v["sent"] for v in streams.values());recv=sum(v["received"] for v in streams.values())
assert recv>4000,(sent,recv,"old finite echo exhausted before four hot lanes")
result={"status":"PASS","mode_scene":"game4-off",
  "source":"original Go TLS+Rust M4 native aarch64/aarch64",
  "server_port":443,"target_authenticated_generations":[1],
  "four_live_individual_game4_hot_lane_rotations":True,
  "hot_lane_ids":[int(x[1]) for x in client[:4]],
  "native_server_matching_original_tls_ports":[int(x[2]) for x in server_hot[:4]],
  "same_game_adapter":True,"three_healthy_game4_siblings_unchanged":True,
  "server_independently_verified_hot_ports":True,
  "old_cold_lanes_retire_scheduled":True,
  "rotation_actual_armed_delays_ms":[int(x[1]) for x in due[:4]],
  "jitter_max_ms":3000,
  "real_udp_app_sent":sent,"real_udp_app_delivered":recv,
  "min_application_UDP_delivery_fraction":min(v["received"]/v["sent"] for v in streams.values()),
  "application_UDP_missed_by_device":{n:v["sent"]-v["received"] for n,v in streams.items()},
  "per_client_missing":{n:v["sent"]-v["received"] for n,v in streams.items()},
  "longest_interreceipt_gap_ms":max(v["max_successful_receipt_gap_ms"] for v in streams.values()),
  "terminal_active_send_no_receive_gap_ms":{n:max(0,round((v["last_send_unix_ns"]-v["last_receive_unix_ns"])/1e6,3)) for n,v in streams.items()},
  "native_ready_to_first_app_reply_ms":first_post,
  "physical_path_IP_MTU_unchanged":True,
  "physical_interface_ipv4_unchanged":True,"original_authenticated_IP_receipts":leases,
  "streams":{n:{k:v for k,v in p.items() if k!="receipts_unix_ns"} for n,p in streams.items()},
  "cpu_process_ticks":cpu,"cpu_causal_comparison":"NOT_MEASURED",
  "H998_original_same_socket_mtu":"HISTORIC_FAIL_RETAINED","L2_capacity":"NOT_MEASURED"}
(art/"timed-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1328_ARM64_GAME4_OFF_FOUR_HOT_LANES_REAL_UDP_PASS",recv,sent,flush=True)
PY_HOT
'''
s=s[:start]+section+s[end:]
target.write_text(s)
target.chmod(0o700)
print("H1328 exact original product ARM64 four separate Game4 hot lanes fixture",flush=True)
