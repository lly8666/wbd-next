#!/usr/bin/env python3
"""H1241: native ARM64 original Go TLS/Rust M4 Game4 selected lane rekey
IN-FLIGHT while actual OS physical IPv4 source+MTU path changes.
Reuse H1162 real source4 physical re-auth, do not add another controller.
One Game4 Fixed6 representative, not duplicate 7-mode matrix.
"""
from pathlib import Path
import subprocess,sys,tempfile
if len(sys.argv)!=2:raise SystemExit("usage: fixture.py OUTPUT")
dest=Path(sys.argv[1])
with tempfile.TemporaryDirectory() as td:
    generated=Path(td)/"h1162-physical.sh"
    subprocess.run([sys.executable,
        "tools/m0-plan028-arm64-mixed-game4-physical-fixture.py",
        str(generated)],check=True)
    s=generated.read_text()
def sub(old,new,count=1):
    global s
    if s.count(old)!=count:raise AssertionError(("fixture drift",old[:120],s.count(old),count))
    s=s.replace(old,new,count)
sub("for i in range(160):","for i in range(12000):")
sub('  rm -rf "$TMP"\\n}', '''  mkdir -p fixed-kernel-result
  for who in server alice bob carol echo;do
    if test -f "$TMP/$who.log";then
      cp "$TMP/$who.log" "fixed-kernel-result/h1241-real-runtime-$who.log"
    fi
  done
  for who in bob carol;do
    if test -f "$TMP/h1241-$who-stream.log";then
      cp "$TMP/h1241-$who-stream.log" "fixed-kernel-result/h1241-real-stream-$who.log"
    fi
  done
  rm -rf "$TMP"
}''')

sub("start_client \"$NSB\" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec fixed6 --record-cipher aes-256-gcm'",
    "start_client \"$NSB\" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec fixed6 --rotation-interval 18s --rotation-jitter 3s --record-cipher aes-256-gcm'")
sub('NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH 48 "$TMP/C-live.log" 0.4',
    'NORMAL_AUTO_LIVE_BOB_GAME4_REAUTH 96 "$TMP/C-live.log" 0.4')
sub(' -eq 48\nsend_udp "$NSB"',' -eq 96\nsend_udp "$NSB"')
sub('assert len(acks)==48 and acks[0]<changed<ready<acks[-1]',
    'assert len(acks)==96 and acks[0]<changed<ready<acks[-1]')
sub('"normal_live_udp_echoes":48','"normal_live_udp_echoes":96')
# Additional authentic no-retry UDP probes on rotating Game4 and unaffected
# Normal Auto, after original shared Go TLS+Rust M4 cold READY.
inject=r'''
# Small bilateral latency creates a measurable overlap window for the next
# original Go TLS/FakeTCP candidate. This remains REAL Linux kernel netem
# on Bob's PHYSICAL veth, not synthetic Go packet processing.
sudo -n tc qdisc replace dev mhb0 root netem delay 120ms
sudo -n ip netns exec "$NSB" tc qdisc replace dev mxb0 root netem delay 120ms
sudo -n tc -s qdisc show dev mhb0 >"$ART/h1241-bob-host-qdisc.txt"
sudo -n ip netns exec "$NSB" tc -s qdisc show dev mxb0 >"$ART/h1241-bob-client-qdisc.txt"
cat >"$TMP/h1241-no-retry.py" <<'PY_H1241_STREAM'
import json,math,os,socket,sys,time
src,who,finish,out=sys.argv[1:]
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind((src,0));sock.settimeout(.85)
sent=got=0;recv=[];rtt=[];first=time.time_ns()
while not os.path.exists(finish) and time.time_ns()-first<110_000_000_000:
    msg=("WBD_MIXED443/H1241_"+who+"/"+str(sent)).encode()
    at=time.monotonic();sock.sendto(msg,("10.66.0.1",45901));sent+=1
    try:
        answer,peer=sock.recvfrom(4096)
        if answer==b"WBD_MIXED_ECHO/"+msg and peer[0]=="10.66.0.1":
            got+=1;recv.append(time.time_ns());rtt.append((time.monotonic()-at)*1000)
    except socket.timeout:pass
    time.sleep(.10)
sock.close();rtt.sort()
res={"source":src,"device":who,"real_no_retry_sent":sent,"real_correct_echoed":got,
     "real_missing":sent-got,
     "p99_received_rtt_ms":rtt[max(0,math.ceil(.99*len(rtt))-1)] if rtt else None,
     "max_successful_echo_gap_ms":max(((b-a)/1e6 for a,b in zip(recv,recv[1:])),default=None),
     "first_send_ns":first,"last_echo_ns":recv[-1] if recv else None,
     "app_retries":0}
open(out,"w").write(json.dumps(res,indent=2)+"\n")
print("H1241_REAL_NO_RETRY_UDP "+str(res),flush=True)
PY_H1241_STREAM
sudo -n ip netns exec "$NSB" python3 "$TMP/h1241-no-retry.py" "$IPB" bob "$TMP/h1241-stream-finish" "$ART/h1241-bob-udp.json" >"$TMP/h1241-bob-stream.log" 2>&1 &
H1241_BOB=$!
sudo -n ip netns exec "$NSC" python3 "$TMP/h1241-no-retry.py" "$IPC" carol "$TMP/h1241-stream-finish" "$ART/h1241-carol-udp.json" >"$TMP/h1241-carol-stream.log" 2>&1 &
H1241_CAROL=$!
# REQUIRE in-flight Game4 lane rekey, not merely a path change close to
# a successfully finished scheduled lane switch.
due_seen=0
for _ in $(seq 1 3400);do
 if grep -Fq 'V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=1 unchanged_path=1' "$TMP/bob.log";then
     due_seen=1;break
 fi
 sleep .01
done
if [[ "$due_seen" != 1 ]];then
   echo 'H1241_COLLISION_FAILED: single-lane due missing before physical path mutation' >&2
   exit 1
fi
due_seen_ns="$(date +%s%N)"
if grep -Fq 'V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=1' "$TMP/bob.log";then
  echo 'H1241_COLLISION_FAILED: lane switch already finished before OS path change' >&2
  exit 1
fi
echo "H1241_REAL_GAME4_LANE_INFLIGHT_AT_OS_CHANGE due_seen_ns=$due_seen_ns"
'''
sub('changed_ns="$(date +%s%N)"',inject+'changed_ns="$(date +%s%N)"')
sub('wait "$live"\ntest "$(grep -c', '''wait "$live"
touch "$TMP/h1241-stream-finish"
wait "$H1241_BOB" "$H1241_CAROL"
test "$(grep -c''')
# Replace oracle assert to include independently genuine native OS path
# source and old/new Rust M4 ownership, app streams and overlap observables.
# Extra oracle executes AFTER original H1162 original authentic path evidence
# and before the final original 48-UDP multi-peer Stop/Health contracts.
oracle=r'''
python3 - "$ART/plan028-h1162-mixed-game4-physical.json" "$TMP/bob.log" \
  "$TMP/server.log" "$TMP/carol.log" "$due_seen_ns" "$changed_ns" "$ready_ns" \
  "$ART/h1241-concurrent-physical-singlelane.json" <<'PY_H1241_ORACLE'
import json,pathlib,re,sys
source,bobp,serverp,carolp,due,changed,ready,out=sys.argv[1:]
old=json.loads(pathlib.Path(source).read_text())
bob=pathlib.Path(bobp).read_text()
server=pathlib.Path(serverp).read_text()
carol=pathlib.Path(carolp).read_text()
due,changed,ready=map(int,(due,changed,ready))
assert due<changed<ready,(due,changed,ready)
assert "V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=1 unchanged_path=1" in bob
assert "V4_PUBLIC_PATH_GAME_OVERLAP_COMMIT role=client new_generation=2 old_generation=1" in bob
assert "V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1" in bob
assert "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2" in bob
assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" in bob
assert len(re.findall(r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=",bob))==2
assert "V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_FAILED role=client generation=2" not in bob
assert "health90" not in server.lower(),server[-2500:]
assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4")==2
# Final server close and native Stop are required by the mature base fixture later.
assert re.findall(r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)",carol)==['1']
assert old["game4_new_inner_os_mtu"]==1178 and old["game4_old_inner_os_mtu"]==1358
assert old["normal_old_inner_os_mtu"]==old["normal_new_inner_os_mtu"]==1375
assert old["normal_live_udp_echoes"]==96
assert old["source4_after"]=="10.25.0.9"
streams={}
for who in ("bob","carol"):
    v=json.loads(pathlib.Path("fixed-kernel-result/h1241-"+who+"-udp.json").read_text())
    streams[who]=v
    assert v["real_no_retry_sent"]>=65,(who,v)
    assert v["real_correct_echoed"]>=v["real_no_retry_sent"]*(.70 if who=="bob" else .995),(who,v)
    assert v["max_successful_echo_gap_ms"]<12000,(who,v)
assert streams["bob"]["first_send_ns"]<changed<streams["bob"]["last_echo_ns"],streams
assert streams["carol"]["first_send_ns"]<changed<streams["carol"]["last_echo_ns"],streams
res={"result":"PASS","platform":"native Linux ARM64 client + server",
    "full_original_TLS443_Rust_M4_game4_fixed6":True,
    "physical_underlay_change_while_game4_lane_attempt_inflight":True,
    "physical_source_ipv4_before_after":["10.25.0.3","10.25.0.9"],
    "physical_mtu_before_after":[1500,1280],"outer_ipv4_default_budget_bytes":1460,
    "inflight_due_seen_ns":due,"os_physical_change_command_ns":changed,
    "new_original_TLS_Rust_M4_ready_ns":ready,
    "command_to_ready_ms":round((ready-changed)/1e6,3),
    "new_authenticated_generation":2,"old_generation_exact_stop":1,
    "game4_inner_os_mtu_before_after":[1358,1178],
    "normal_unaffected_inner_os_mtu":1375,"normal_generation_unchanged":1,
    "real_no_retry_inner_udp":streams,"no_group_rust_health90":True,
    "lane_rekey_interrupt_outcome":"SUPERSEDED_BY_REAL_OS_PATH_CHANGE",
    "prior_H998_live_hot_same_socket_mtu_fail":"FAIL_RETAINED"}
pathlib.Path(out).write_text(json.dumps(res,indent=2)+"\n")
print("M0_PLAN028_H1241_ARM64_REAL_GAME4_LANE_VS_PHYSICAL_SOURCE_MTU_OVERLAP_PASS",flush=True)
PY_H1241_ORACLE
'''
# H1162 oracle runs before original final exact stop; append once
# immediately following its unique output marker and before final overall
# original shared-443 final Stop checks in mature base.
sub('print("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS",flush=True)',
    'print("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE96_GAME4_PHYSICAL_NEW32_STOP_PASS",flush=True)')
# The H1162 generator injects oracle before grep "V4_PUBLIC_GAME_FEC...",
# so place our own cross-check after H1162 Python heredoc terminator.
sub("PY_H1162\n\ngrep -Fq", "PY_H1162\n"+oracle+"\ngrep -Fq")
# Keep full device/process logs even when this scenario fails, for root cause.
sub('for f in server.log alice.log bob.log carol.log echo.log A-udp.log B-udp.log C-udp.log C-live.log B-new.log B-after.log C-after.log;do',
    'for f in server.log alice.log bob.log carol.log echo.log A-udp.log B-udp.log C-udp.log C-live.log B-new.log B-after.log C-after.log h1241-bob-stream.log h1241-carol-stream.log;do')
# Hard syntax checks of *both* generated nested Python programs occur now.
for marker in ("PY_H1241_STREAM","PY_H1241_ORACLE"):
    start="<<'"+marker+"'\n"
    assert s.count(start)==1,(marker,s.count(start))
    body=s.split(start,1)[1].split("\n"+marker,1)[0]
    compile(body,str(dest)+":"+marker,"exec")
dest.write_text(s)
dest.chmod(0o700)
print("H1241 candidate native ARM64 real physical source-IP MTU vs active Game4 lane TLS rekey fixture READY")
