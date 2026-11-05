#!/usr/bin/env python3
"""PLAN028 H1226: seven protected original-TLS modes, 4 jittered native
generation changes with 3 real application peers. Game4 checks all four
independently authenticated per-generation physical lanes, and records that
a grouped Rust M4 commit is NOT an independent one-lane hot replacement.
"""
import pathlib
import subprocess
import sys
import tempfile

MODES={
  "normal-off":("normal-auto","normal",""),
  "normal-fixed6":("normal-auto","fec-fixed","--fec-profile 6"),
  "normal-auto":("normal-auto","fec-auto",""),
  "game2-off":("game2-off","game2",""),
  "game2-fixed6":("game2-off","game2","--game-fec fixed6"),
  "game4-off":("game4-fixed6","game4",""),
  "game4-fixed6":("game4-fixed6","game4","--game-fec fixed6"),
}
if len(sys.argv)!=3 or sys.argv[2] not in MODES:
    raise SystemExit("usage: fixture.py OUTPUT "+str(tuple(MODES)))
output=pathlib.Path(sys.argv[1])
scene=sys.argv[2]
base,mode,additional=MODES[scene]
with tempfile.TemporaryDirectory() as td:
    temp=pathlib.Path(td)/"base.sh"
    subprocess.run([sys.executable,"tools/m0-plan028-x86-same-path-timed-rotation-fixture.py",str(temp),base],check=True)
    s=temp.read_text()

def sub(a,b,expected=1):
    global s
    if s.count(a)!=expected:
        raise AssertionError((scene,a[:100],s.count(a),expected))
    s=s.replace(a,b)

# Original fixture's selected client contains the exact timer and one mode.
sub("--rotation-interval 12s --record-cipher",
    "--rotation-interval 18s --rotation-jitter 3s --record-cipher")
if mode!="fec-auto":
    if base=="normal-auto":
        sub("carol carol-mixed-protected fec-auto '--rotation-interval",
            "carol carol-mixed-protected "+mode+" '"+(additional+" ").replace("  "," ")+"--rotation-interval")
    elif base=="game2-off" and mode=="game2":
        if additional:
            sub("alice alice-mixed-protected game2 '--rotation-interval",
                "alice alice-mixed-protected game2 '"+additional+" --rotation-interval")
    elif base=="game4-fixed6":
        if not additional:
            sub("bob bob-mixed-protected game4 '--game-fec fixed6 --rotation-interval",
                "bob bob-mixed-protected game4 '--rotation-interval")
else:
    assert scene=="normal-auto"
# All four cold groups after first, not only the first two.
sub("time.monotonic()-start<70","time.monotonic()-start<185")
sub("for _ in $(seq 1 280);do","for _ in $(seq 1 720);do")
sub("generation=3 old_generation=true","generation=5 old_generation=true")
sub("generation=2' \"$TMP/$TIMER_TARGET.log\"","generation=4' \"$TMP/$TIMER_TARGET.log\"")
sub("\" -ge 2 ]];then","\" -ge 4 ]];then")
sub("two actual TLS/M4 rotations not ready","four actual TLS/M4 rotations not ready")
sub("gen[:3]==[1,2,3] and old[:2]==[1,2]","gen[:5]==[1,2,3,4,5] and old[:4]==[1,2,3,4]")
sub("len(timer)>=2","len(timer)>=4")
sub("timer[:2]","timer[:4]",2)
sub("lease_receipts={}","lease_receipts={}")
sub("(3 if who==target else 1)","(5 if who==target else 1)")
sub("\"timer_interval_seconds\":12","\"timer_interval_seconds\":18,\"rotation_jitter_max_seconds\":3")
sub("gen[:3],\"exact_old_stops\":old[:2]","gen[:5],\"exact_old_stops\":old[:4]")
sub("s[\"received\"]>=.70*s[\"sent\"]","s[\"received\"]==s[\"sent\"]")
sub("s[\"received\"]>=.85*s[\"sent\"]","s[\"received\"]==s[\"sent\"]")
sub("sleep 2\ntouch \"$TMP/timed-finish\"","sleep 4\ntouch \"$TMP/timed-finish\"")
# The source variation is evaluated by the actual arms logged before each due.
anchor='for who,s in streams.items():\n    assert s["sent"]>=30'
check=r'''delays=[int(re.search(r"actual_delay_ms=(\d+)",x).group(1)) for x in timer[:4]]
assert len(delays)==4 and all(15000<=x<=21000 for x in delays),delays
assert len(set(delays))>=3,delays
for a,b in zip(timer_due_unix_ms,timer_due_unix_ms[1:]):
    assert 15000<=b-a<=33000,("unexpected schedule/in-flight cold delay",a,b)
'''
sub(anchor,check+anchor)
# The original base requires auto/fixed6 in permanent assertions; the scene
# where that specific client is changed must use the truthful policy receipt.
if scene.startswith("normal-"):
    sub('server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")>=3',
        'server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")>=5')
    if scene!="normal-auto":
        sub('assert "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto" in server',
            'assert "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" in server')
        sub('assert "V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=auto" in server',
            'assert "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" in server')
if scene=="game4-off":
    sub('V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6',
        'V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0',2)
# For each fresh 4-lane cohort, require 4 authenticated original TLS tuples
# on client and server, and four NEW local ports, no omitted sibling lane.
# This does NOT claim independent lane-at-a-time Rust M4 handover.
lane_check=r'''if scene.startswith("game"):
    n=4 if scene.startswith("game4") else 2
    observed=re.findall(
        r"V4_PUBLIC_GAME_GROUP_LANE_READY role=client group_generation=(\d+) lane=(\d+) local_port=(\d+) server_port=(\d+)",target_log)
    grouped={}
    for gen_id,lane_id,source_port,dest_port in observed:
        grouped.setdefault(int(gen_id),{})[int(lane_id)]=(int(source_port),int(dest_port))
    assert set(grouped)>=set(range(1,6)),grouped
    for gen_id in range(1,6):
        assert set(grouped[gen_id])==set(range(1,n+1)),(gen_id,grouped)
    physical_ports={port for gen_id in range(1,6)
                    for port,dest in grouped[gen_id].values() if dest==443}
    assert len(physical_ports)==n*5,(scene,physical_ports)
    server_log=(pathlib.Path(sys.argv[4]).parent/"server.log").read_text()
    server_lanes=re.findall(
        r"V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=(\d+) lane=(\d+) client_port=(\d+) server_port=(\d+)",server_log)
    server_set={(int(n),int(lane),int(port),int(dest)) for n,lane,port,dest in server_lanes}
    for gen_id in range(1,6):
        for lane_id,(port,dest) in grouped[gen_id].items():
            assert (n,lane_id,port,dest) in server_set,(scene,gen_id,lane_id,port)
    result["all_game_lanes_original_TLS_M4_group_handoff"]={
        "per_generation_authenticated_local_ports":grouped,
        "server_all_original_authenticated_lane_tuples_match":True,
        "each_lane_new_tuple_every_group_generation":True,
        "individual_lane_without_sibling_restart":"NOT_IMPLEMENTED_OR_TESTED",
        "real_witness_type":"GROUPED_NATIVE_RUST_GAME_M4_4_LANES_AT_ONCE",
    }
result["rotation_delays_ms"]=delays
result["four_live_cold_group_rotations"]=True
'''
sub('pathlib.Path(sys.argv[7]).write_text(json.dumps(result,indent=2)+"\\n")',
    lane_check+'pathlib.Path(sys.argv[7]).write_text(json.dumps(result,indent=2)+"\\n")')
sub('"mode_scene":scene','"mode_scene":"'+scene+'"')
sub('M0_PLAN028_H1222_TIMED_UNCHANGED_PATH_REAL_UDP_PASS',
    'M0_PLAN028_H1226_JITTERED_ALL_MODES_REAL_UDP_PASS')
# Scene-specific echo thread and original script at 30Hz over ~100s remains
# below 4,000 messages; 3 native peers are alive throughout all four swaps.
output.write_text(s)
output.chmod(0o700)
print("H1226 7-mode jittered genuine native generator:",scene,flush=True)
