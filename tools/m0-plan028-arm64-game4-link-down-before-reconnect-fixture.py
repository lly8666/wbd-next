#!/usr/bin/env python3
"""PLAN028 H1171 separate native ARM64 physical link-down-before-reconnect scene.
Inherit qualified original-Go TLS/Rust three-client session and mutate only one
real netns physical outage (not an artificial callback, no new wire).
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-arm64-mixed-game4-physical-fixture.py",str(out)]
try:
    runpy.run_path("tools/m0-plan028-arm64-mixed-game4-physical-fixture.py",run_name="__main__")
finally:
    sys.argv=saved
s=out.read_text()
old='changed_ns="$(date +%s%N)"\nsudo -n ip -n "$NSB" addr add 10.25.0.9/24 dev mxb0\nsudo -n ip -n "$NSB" link set mxb0 mtu 1280\nsudo -n ip -n "$NSB" route replace 10.25.0.1/32 dev mxb0 src 10.25.0.9'
new=r'''changed_ns="$(date +%s%N)"
sudo -n ip -n "$NSB" link set mxb0 down
down_ns="$(date +%s%N)"
sudo -n ip -n "$NSB" -j link show mxb0 >"$ART/plan028-h1171-link-broken-os.json"
sleep 1.30
sudo -n ip -n "$NSB" addr add 10.25.0.9/24 dev mxb0
sudo -n ip -n "$NSB" link set mxb0 mtu 1280
sudo -n ip -n "$NSB" link set mxb0 up
up_ns="$(date +%s%N)"
sudo -n ip -n "$NSB" route replace 10.25.0.1/32 dev mxb0 src 10.25.0.9'''
assert s.count(old)==1,"mature first physical mutation anchor changed"
s=s.replace(old,new,1)
anchor='print("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS",flush=True)\nPY_H1162'
assert s.count(anchor)==1,"mature source-locked ARM proof anchor changed"

# Unlike healthy-link A→A+B→B, real physical link DOWN terminated
# generation1 BEFORE generation2 authentication. This is direct recovery,
# not a regression in the proven overlapping source-IP-change scenario.
check_old = "grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' \"$TMP/bob.log\" &&\n    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' \"$TMP/bob.log\""
check_new = "grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=false source=real_original_TLS_Rust_M4 os_path_authority=1' \"$TMP/bob.log\" &&\n    grep -q 'V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=1' \"$TMP/bob.log\""
assert s.count(check_old)==1,"overlap-only prerequisite changed"
s=s.replace(check_old,check_new,1)
old_order='assert bob.index("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2")<bob.index("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1")'
new_order='assert bob.index("V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=1")<bob.index("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2")\nassert "V4_PUBLIC_PATH_UNAVAILABLE role=client source=rtnetlink_os_readback" in bob'
assert s.count(old_order)==1,"original overlap-only Python proof changed"
s=s.replace(old_order,new_order,1)
old_result='"game4_new_udp_echoes":32,"new_tls_auth_ready":True,"old_exact_stop":True,'
new_result='"game4_new_udp_echoes":32,"new_tls_auth_ready":True,"old_disconnected_first":True,"old_exact_stop":False,'
assert s.count(old_result)==1,"original overlap-only result changed"
s=s.replace(old_result,new_result,1)
old_text='H1162 missing true original Game4 TLS reauthentication and exact old Stop'
assert s.count(old_text)==1
s=s.replace(old_text,'H1172 missing true direct TLS Game4 recovery AFTER old physical link terminated',1)
old_marker='M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS'
new_marker='M0_PLAN028_H1172_ARM64_NORMAL_LIVE48_GAME4_DOWN_FIRST_DIRECT_RECOVERY_NEW32_PASS'
assert s.count(old_marker)==1,"original H1162 success marker not unique"
s=s.replace(old_marker,new_marker,1)

extra=r'''
python3 - "$ART/plan028-h1171-link-broken-os.json" "$TMP/bob.log" \
 "$down_ns" "$up_ns" "$changed_ns" "$ready_ns" \
 "$ART/plan028-h1171-link-down-first.json" <<'PY_H1171'
import json,pathlib,sys
down=json.loads(pathlib.Path(sys.argv[1]).read_text())[0]
bob=pathlib.Path(sys.argv[2]).read_text()
down_ns,up_ns,changed_ns,ready_ns=map(int,sys.argv[3:7])
assert "UP" not in down["flags"] and down["operstate"]=="DOWN",down
assert changed_ns<=down_ns<up_ns<ready_ns,(changed_ns,down_ns,up_ns,ready_ns)
gap=round((up_ns-down_ns)/1e6,2);ready=round((ready_ns-changed_ns)/1e6,2)
assert gap>=1200 and ready<20000,(gap,ready)
assert 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=false' in bob
assert 'V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=1' in bob
out={"scope":"NATIVE_ARM64_GAME4_LINK_DOWN_BEFORE_NEW_TLS_RECOVERY_WITH_HEALTHY_NORMAL",
 "link_was_physically_down":True,"down_link_os_readback":down["operstate"],
 "down_interval_ms":gap,"old_link_was_up_before_new_auth":True,
 "new_original_TLS_generation2_ready":True,"first_physical_down_to_ready_ms":ready,
 "old_generation1_terminated_before_new_TLS":True,"old_generation1_exact_stop":False,"no_dead_90_wait_observed":True,
 "physical_old_source":"10.25.0.3","new_source":"10.25.0.9",
 "new_physical_mtu":1280,"new_inner_os_mtu":1178,"original_client_outer1460":True,
 "unchanged_other_normal_48_echoes":True,"new_game4_udp32":True,
 "unavailable_path_log_observed":'V4_PUBLIC_PATH_UNAVAILABLE role=client' in bob,
 "limitation":"Old address still configured while link returns; 1.3s real physical outage is not a permanent dead-lane disqualification or WAN/WiFi test.",
 "notifier_to_tls_start_ms":"NOT_MEASURED",
 "tls_auth_to_first_packet_ms":"NOT_MEASURED","cpu_p99":"NOT_MEASURED"}
pathlib.Path(sys.argv[7]).write_text(json.dumps(out,indent=2)+"\n")
print("M0_PLAN028_H1171_ARM64_GAME4_LINK_DOWN_BEFORE_NEW_TLS_RECOVERY_PASS",flush=True)
PY_H1171
'''
# The direct-recovery path above deliberately renamed the inherited H1162
# success token; append AFTER the resulting marker, not the stale original.
completed_marker='print("M0_PLAN028_H1172_ARM64_NORMAL_LIVE48_GAME4_DOWN_FIRST_DIRECT_RECOVERY_NEW32_PASS",flush=True)\\nPY_H1162'.replace('\\\\n','\\n')
assert s.count(completed_marker)==1,"direct recovery success token missing after staging"
s=s.replace(completed_marker,completed_marker+'\\n'+extra,1)
assert s.count("PY_H1171")==2,"link-down timing and kernel-readback proof was not installed"
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1171_ARM64_LINK_DOWN_BEFORE_RECOVERY_GENERATOR_READY",flush=True)
