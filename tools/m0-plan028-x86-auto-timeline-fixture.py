#!/usr/bin/env python3
"""Only extend the already qualified temporary PLAN028 Normal Auto netns harness.
Never rewrite product Go/Rust or the mature source script.
"""
import pathlib
import runpy
import sys

out=pathlib.Path(sys.argv[1])
saved=sys.argv
sys.argv=["tools/m0-plan028-normal-fec-path-fixture.py",str(out)]
try:
    runpy.run_path("tools/m0-plan028-normal-fec-path-fixture.py",run_name="__main__")
finally:
    sys.argv=saved
s=out.read_text(encoding="utf-8")

def sub(a,b):
    global s
    if s.count(a)!=1:
        raise ValueError("frozen native fixture anchor mismatch: "+a[:95])
    s=s.replace(a,b,1)

sub("ECHO_PACKETS=$((PACKETS+5))","ECHO_PACKETS=$((PACKETS+128))")
sub("READER_MIN_PACKETS=$((PACKETS+5))","READER_MIN_PACKETS=$((PACKETS+128))")
sub("range(100,105)","range(100,228)")
sub('print("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",i,flush=True)',
    'print("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",i,flush=True)')
sub('test "$(grep -c \'M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK\' "$ART/plan028-real-path-switched-business.log")" -eq 5',
    'test "$(grep -c \'M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK\' "$ART/plan028-real-path-switched-business.log")" -eq 128')
sub("new_real_udp=5","new_real_udp=128")

observer=r'''
  phase_command_start_ns="$(date +%s%N)"
  python3 - "$TMP/client.log" "$ART/plan028-x86-phase-observer.json" "$phase_command_start_ns" <<'PY_OBSERVE' &
import json,pathlib,sys,time
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])
start=int(sys.argv[3])
marks={
 "path_effective":"V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback",
 "new_tls_candidate":"V4_PUBLIC_PATH_CANDIDATE role=client generation=2",
 "new_generation_ready":"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2",
 "old_exact_stop":"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1",
}
found={}
deadline=time.monotonic()+45
while time.monotonic()<deadline:
    data=p.read_text(errors="replace") if p.exists() else ""
    now=time.time_ns()
    for key,mark in marks.items():
        if key not in found and mark in data:
            found[key]=now
    if "protected_second_lease" not in found and data.count(
        "V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS")>=2:
        found["protected_second_lease"]=now
    if len(found)==len(marks)+1:break
    time.sleep(.01)
out.write_text(json.dumps({"observer_poll_interval_ms":10,
 "command_start_ns":start,"observed_marker_ns":found,
 "precision":"observer discovery only, not exact Go TLS timestamps",
 "missing_markers":sorted((set(marks)|{"protected_second_lease"})-set(found))},
 indent=2)+"\n")
PY_OBSERVE
  phase_observer_pid=$!
'''
sub('if [[ "$PATH_SWITCH" == 1 ]];then\n  # REAL physical interface/source IPv4 change',
    'if [[ "$PATH_SWITCH" == 1 ]];then\n'+observer+'  # REAL physical interface/source IPv4 change')
sub('  sudo -n ip netns exec "$NSC" ip -j link show dev wbdvc4 >"$ART/plan028-new-tun-mtu.json"',
    '  phase_ready_ns="$(date +%s%N)"\n  sudo -n ip netns exec "$NSC" ip -j link show dev wbdvc4 >"$ART/plan028-new-tun-mtu.json"')

sub('sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c \'\nimport os,socket\n',
    'sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" WBD_PHASE_STATS="$ART/plan028-x86-udp-stats.json" WBD_PHASE_CLIENT_PID="$(cat "$TMP/client.pid")" python3 -u -c \'\nimport os,socket,time,json,pathlib,math\n'
)
sub('s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45904));s.settimeout(12)\ntry:\n    for i in range(100,228):',
'''s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45904));s.settimeout(12)
def cpu_ticks():
    raw=pathlib.Path("/proc/"+os.environ["WBD_PHASE_CLIENT_PID"]+"/stat").read_text()
    fields=raw[raw.rfind(")")+2:].split()
    return int(fields[11])+int(fields[12])
time_start=time.perf_counter_ns();cpu_start=cpu_ticks()
samples=[];first_echo_wall_ns=None
try:
    for i in range(100,228):''')
sub('        assert s.sendto(data,("10.66.0.1",45901))==len(data)',
    '        sent_ns=time.perf_counter_ns()\n        assert s.sendto(data,("10.66.0.1",45901))==len(data)')
sub('        assert got==b"V4_SERVER_APP_ECHO/"+data and src[0]=="10.66.0.1",(i,src)\n        print("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",i,flush=True)',
'''        received_ns=time.perf_counter_ns()
        if first_echo_wall_ns is None:first_echo_wall_ns=time.time_ns()
        samples.append((received_ns-sent_ns)/1e6)
        assert got==b"V4_SERVER_APP_ECHO/"+data and src[0]=="10.66.0.1",(i,src)
        print("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",i,flush=True)''')
sub("finally:s.close()\n' >\"$ART/plan028-real-path-switched-business.log\" 2>&1",
'''finally:
    cpu_finish=cpu_ticks();wall_finish=time.perf_counter_ns()
    sorted_samples=sorted(samples)
    n=len(sorted_samples)
    stats={"real_udp_echo_count":n,
      "rtt_p99_ms":sorted_samples[math.ceil(.99*n)-1] if n else None,
      "rtt_median_ms":sorted_samples[n//2] if n else None,
      "first_echo_received_wall_ns":first_echo_wall_ns,
      "client_go_plus_linked_rust_process_cpu_pct_during_128_echo":
         round(100*(cpu_finish-cpu_start)/os.sysconf("SC_CLK_TCK")/
            max((wall_finish-time_start)/1e9,.001),2),
      "cpu_measurement_scope":"client process during 128 post-path UDP echoes only, NOT old/new causal comparison"}
    pathlib.Path(os.environ["WBD_PHASE_STATS"]).write_text(json.dumps(stats,indent=2))
    s.close()
' >"$ART/plan028-real-path-switched-business.log" 2>&1''')
# The existing 128 unique echo assertions and exact Stop remain unmodified.
sub('  if [[ "$GAME" != 0 ]];then\n    grep -q "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED',
'''  wait "$phase_observer_pid"
  python3 - "$ART/plan028-x86-phase-observer.json" "$ART/plan028-x86-udp-stats.json" "$ART/plan028-x86-timeline-summary.json" "$phase_ready_ns" <<'PY_PHASE_SUMMARY'
import json,pathlib,sys
observer=json.loads(pathlib.Path(sys.argv[1]).read_text())
stats=json.loads(pathlib.Path(sys.argv[2]).read_text())
ready=int(sys.argv[4]);events=observer["observed_marker_ns"]
get=lambda a,b:round((events[b]-events[a])/1e6,2) if a in events and b in events and events[b]>=events[a] else "NOT_MEASURED"
summary={"platform":"native_linux_x86_client_and_x86_server",
 "source_type":"frozen_original_Go_TLS_Rust",
 "outer_ipv4_user_intent":1460,"new_physical_ipv4_mtu":1280,
 "command_to_new_ready_ms":round((ready-observer["command_start_ns"])/1e6,2),
 "observed_path_log_to_new_tls_candidate_ms":get("path_effective","new_tls_candidate"),
 "observed_protected_lease_log_to_first_real_udp_ms":
     round((stats["first_echo_received_wall_ns"]-events["protected_second_lease"])/1e6,2)
     if stats["first_echo_received_wall_ns"] and "protected_second_lease" in events else "NOT_MEASURED",
 "actual_tls_auth_finished_to_first_udp_ms":"NOT_MEASURED",
 "actual_native_OS_notification_timestamp_to_TLS_ms":"NOT_MEASURED",
 "observer_resolution_ms":observer["observer_poll_interval_ms"],
 "observer_markers_missing":observer["missing_markers"],
 "real_udp_rtt_p99_ms":stats["rtt_p99_ms"],
 "real_udp_echo_count":stats["real_udp_echo_count"],
 "client_process_cpu_pct_post_switch":stats["client_go_plus_linked_rust_process_cpu_pct_during_128_echo"],
 "cpu_old_new_causality":"NOT_PROVEN"}
assert stats["real_udp_echo_count"]==128 and summary["command_to_new_ready_ms"]>=0
pathlib.Path(sys.argv[3]).write_text(json.dumps(summary,indent=2))
print("M0_PLAN028_NATIVE_X86_PHASE_OBSERVATION_AND_128_REAL_UDP_CPU_P99_PASS "+json.dumps(summary,sort_keys=True))
PY_PHASE_SUMMARY
  if [[ "$GAME" != 0 ]];then
    grep -q "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED''')
out.write_text(s,encoding="utf-8")
out.chmod(0o700)
print("M0_PLAN028_NATIVE_X86_AUTO_TIMELINE_EPHEMERAL_GENERATOR_READY product_unchanged=1",flush=True)
