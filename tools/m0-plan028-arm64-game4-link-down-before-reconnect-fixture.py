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
assert 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true' in bob
assert 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' in bob
out={"scope":"NATIVE_ARM64_GAME4_LINK_DOWN_BEFORE_NEW_TLS_RECOVERY_WITH_HEALTHY_NORMAL",
 "link_was_physically_down":True,"down_link_os_readback":down["operstate"],
 "down_interval_ms":gap,"old_link_was_up_before_new_auth":True,
 "new_original_TLS_generation2_ready":True,"first_physical_down_to_ready_ms":ready,
 "old_generation1_exact_stop":True,"no_dead_90_wait_observed":True,
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
s=s.replace(anchor,anchor+'\n'+extra,1)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1171_ARM64_LINK_DOWN_BEFORE_RECOVERY_GENERATOR_READY",flush=True)
