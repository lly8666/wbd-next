#!/usr/bin/env python3
"""H1243 native ARM64 strict original Go TLS/Rust Game4:
in-flight lane rekey vs real source IPv4 and MTU physical path handover.
Guard against H1242 false PASS (Bob's last echo PRECEDED gen2 Ready).
"""
import pathlib,subprocess,sys,tempfile
if len(sys.argv)!=2:raise SystemExit("usage: H1243-fixture.py OUTPUT")
dest=pathlib.Path(sys.argv[1])
with tempfile.TemporaryDirectory() as td:
    p=pathlib.Path(td)/"old-generated-h1242.sh"
    subprocess.run([sys.executable,
      "tools/m0-h1241-arm64-game4-hotlane-physical-mtu-collision-fixture.py",
      str(p)],check=True)
    s=p.read_text()
def sub(old,new):
    global s
    count=s.count(old)
    if count!=1:raise AssertionError(("H1243 source fixture drift",old[:110],count))
    s=s.replace(old,new)
sub('assert "health90" not in server.lower(),server[-2500:]',
'''assert "health90" not in server.lower(),server[-2500:]
# The previous CI H1242 was falsely green: after a genuine first-slot
# rekey the server retired the whole old group BEFORE gen2 M4 READY.
# This failure is prohibited even when gen2 eventually re-authenticates.
assert "V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=one-lane-native-rekey-failed" not in server
assert "V4_PUBLIC_GAME_SINGLE_LANE_NATIVE_REKEY_FAILED" not in server
# New OS-source path is a WHOLE FOUR-lane original TLS cohort, not four
# independent hot swaps of the still-active same-epoch old group.
assert len(re.findall(
    r"V4_PUBLIC_GAME_PHYSICAL_GROUP_CANDIDATE role=server lane=[1-4]",server))>=4
ready_markers=[m.start() for m in re.finditer(
    r"V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4",server)]
assert len(ready_markers)==2,ready_markers
old_retirement=server.find("V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-new-generation")
assert old_retirement>ready_markers[1],(old_retirement,ready_markers)''')
sub('    assert v["real_no_retry_sent"]>=65,(who,v)',
'''    assert v["real_no_retry_sent"]>=(95 if who=="bob" else 65),(who,v)''')
sub('    assert v["real_correct_echoed"]>=v["real_no_retry_sent"]*(.70 if who=="bob" else .995),(who,v)',
'''    assert v["real_correct_echoed"]>=v["real_no_retry_sent"]*(.75 if who=="bob" else .995),(who,v)''')
sub('    assert v["max_successful_echo_gap_ms"]<12000,(who,v)',
'''    assert v["max_successful_echo_gap_ms"]<9000,(who,v)''')
sub('assert streams["bob"]["first_send_ns"]<changed<streams["bob"]["last_echo_ns"],streams',
'''# A passing trace MUST deliver actual Bob app UDP for at least 2s AFTER
# the next authenticated Go TLS and Rust M4 generation was Ready.
# H1242 Bob last real reply was BEFORE that Ready, not continuously live.
assert streams["bob"]["first_send_ns"]<changed<ready+2_000_000_000<streams["bob"]["last_echo_ns"],streams''')
sub('assert streams["carol"]["first_send_ns"]<changed<streams["carol"]["last_echo_ns"],streams',
'''assert streams["carol"]["first_send_ns"]<changed<ready+2_000_000_000<streams["carol"]["last_echo_ns"],streams''')
sub('    "lane_rekey_interrupt_outcome":"SUPERSEDED_BY_REAL_OS_PATH_CHANGE",',
'''    "lane_rekey_interrupt_outcome":"WHOLE_4_LANE_OS_REAUTH_ONLY_AFTER_AUTHENTIC_GEN2_M4_READY",
    "server_no_early_one_lane_native_rekey_failure":True,
    "bob_delivered_at_least_2s_after_gen2_ready":True,
    "server_full_group_staged_new_physical_tuple":True,''')
# H1244 native STRICT oracle printed its success marker, but wrote the
# immutable result under the previous H1241 basename. The H1243 CI runner
# correctly required h1243-* JSON and thus failed with FileNotFoundError.
# Fix the artifact contract (NOT the business gate) and keep the strict
# Bob last real echo > GEN2_READY+2s / no early M4 group Stop predicates.
sub('$ART/h1241-concurrent-physical-singlelane.json',
    '$ART/h1243-concurrent-physical-singlelane.json')
sub('M0_PLAN028_H1241_ARM64_REAL_GAME4_LANE_VS_PHYSICAL_SOURCE_MTU_OVERLAP_PASS',
    'M0_PLAN028_H1243_ARM64_GAME4_INFLIGHT_LANE_OS_MTU_STRICT_CONTINUITY_PASS')
# Test-only compile of every program embedded in the eventual shell.
for kind in ("PY_H1241_STREAM","PY_H1241_ORACLE","PY_H1162"):
    opening="<<'"+kind+"'\n"
    if s.count(opening)!=1:raise AssertionError(("missing nested Python",kind,s.count(opening)))
    body=s.split(opening,1)[1].split("\n"+kind,1)[0]
    compile(body,str(dest)+":"+kind,"exec")
dest.write_text(s);dest.chmod(0o700)
print("H1243_ARM64_STRICT_HOTLANE_VS_PHYSICAL_SOURCE_MTU_FIXTURE_COMPILED")
