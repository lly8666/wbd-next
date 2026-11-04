#!/usr/bin/env python3
"""PLAN028 x86/x86 two real native source IPv4/MTU replacements, same TLS/Rust products."""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-arm64-mixed-game4-physical-fixture.py",str(out)]
try:
    runpy.run_path("tools/m0-plan028-arm64-mixed-game4-physical-fixture.py",run_name="__main__")
finally:
    sys.argv=saved
s=out.read_text()
anchor='print("M0_PLAN028_H1162_ARM64_MIXED_NORMAL_LIVE48_GAME4_PHYSICAL_NEW32_STOP_PASS",flush=True)\nPY_H1162'
assert s.count(anchor)==1,"previous one-switch verified fixture changed"
second=r'''
# Second physical source4 .9→.3; MTU 1280→1500. User outer intent stays 1460.
send_udp "$NSC" "$IPC" NORMAL_AUTO_LIVE_GAME4_RESTORE 16 "$TMP/C-restore.log" 0.4 &
live_restore=$!
for _ in {1..120};do
 grep -q 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE 0 ack_ns=' "$TMP/C-restore.log" && break
 sleep .05
done
grep -q 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE 0 ack_ns=' "$TMP/C-restore.log"
changed_restore_ns="$(date +%s%N)"
sudo -n ip -n "$NSB" link set mxb0 mtu 1500
sudo -n ip -n "$NSB" route replace 10.25.0.1/32 dev mxb0 src 10.25.0.3
sudo -n ip -n "$NSB" -j route get 10.25.0.1 >"$ART/plan028-h1167-restored-os-route.json"
sudo -n ip -n "$NSB" -j link show mxb0 >"$ART/plan028-h1167-restored-os-link.json"
restored=0
for _ in {1..140};do
 if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true' "$TMP/bob.log" &&
    grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2' "$TMP/bob.log";then
    restored=1;break
 fi
 sleep .25
done
[[ "$restored" == 1 ]] || { echo "H1167 missing genuine generation3 ready or generation2 Stop" >&2;exit 1; }
ready_restore_ns="$(date +%s%N)"
wait "$live_restore"
test "$(grep -c 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE .* ack_ns=' "$TMP/C-restore.log")" -eq 16
send_udp "$NSB" "$IPB" GAME4_FIXED6_RESTORED_NEW_GEN3 16 "$TMP/B-restored.log"
new_restore_game="$(sudo -n ip -n "$NSB" -j link show dev mxb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
new_restore_normal="$(sudo -n ip -n "$NSC" -j link show dev mxc4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
[[ "$new_restore_game" == 1178 && "$new_restore_normal" == 1375 ]] ||
 { echo "H1167 overlap conservative MTU or other-client isolation mismatch" >&2;exit 1; }
python3 - "$TMP/bob.log" "$TMP/carol.log" "$TMP/C-restore.log" \
 "$ART/plan028-h1167-restored-os-route.json" "$ART/plan028-h1167-restored-os-link.json" \
 "$changed_restore_ns" "$ready_restore_ns" "$IPB" "$ART/plan028-h1167-two-physical-switch.json" <<'PY_H1167'
import json,pathlib,re,sys
bob,carol,live=(pathlib.Path(x).read_text() for x in sys.argv[1:4])
route=json.loads(pathlib.Path(sys.argv[4]).read_text())[0]
link=json.loads(pathlib.Path(sys.argv[5]).read_text())[0]
changed,ready=map(int,sys.argv[6:8])
acks=[int(x) for x in re.findall(r'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE \d+ ack_ns=(\d+)',live)]
assert len(acks)==16 and acks[0]<changed<ready<acks[-1],(len(acks),acks[:2],changed,ready,acks[-2:])
assert route["dev"]=="mxb0" and route["prefsrc"]=="10.25.0.3",route
assert link["mtu"]==1500,link
leases=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.\d+)/32',bob)
assert len(leases)>=3 and len(set(leases))==1 and leases[0]==sys.argv[8],leases
assert bob.index('V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3')<bob.index('V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2')
assert re.findall(r'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)',carol)==['1']
out={"scope":"NATIVE_X86_X86_MIXED443_GAME4_TWO_SOURCE4_AND_MTU_HANDOVERS",
 "one_server_port":443,"real_original_go_tls":True,"game4_lanes":4,"game4_fixed6":True,
 "source4_route_sequence":["10.25.0.3","10.25.0.9","10.25.0.3"],
 "physical_ipv4_mtu_sequence":[1500,1280,1500],"configured_outer_intent":1460,
 "os_mtu_first_generation":1358,"os_mtu_second_generation":1178,
 "os_mtu_third_generation_overlap_conservative":1178,"sibling_normal_os_mtu":1375,
 "generation_replacement_sequence":[[1,2],[2,3]],"game4_lease_preserved":leases[0],
 "normal_live_first_change_echoes":48,"normal_live_restoration_echoes":16,
 "game4_new_gen2_echoes":32,"game4_new_gen3_echoes":16,
 "old_generation1_exact_stop":True,"old_generation2_exact_stop":True,
 "normal_not_reauthenticated":True,
 "second_physical_command_to_ready_ms":round((ready-changed)/1e6,2),
 "notification_to_tls_start_ms":"NOT_MEASURED","tls_auth_to_first_business_ms":"NOT_MEASURED",
 "cpu_p99":"NOT_MEASURED","no_5percent_impairment_in_this_scene":True}
pathlib.Path(sys.argv[9]).write_text(json.dumps(out,indent=2)+"\n")
print("M0_PLAN028_H1167_NATIVE_X86_MIXED_GAME4_TWO_PHYSICAL_REAUTH_NORMAL_LIVE64_NEW48_PASS",flush=True)
PY_H1167
'''
s=s.replace(anchor,anchor+'\n'+second,1)
assert s.count('for i in range(160):')==1
s=s.replace('for i in range(160):','for i in range(320):',1)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1167_X86_TWO_PHYSICAL_GENERATOR_READY",flush=True)
