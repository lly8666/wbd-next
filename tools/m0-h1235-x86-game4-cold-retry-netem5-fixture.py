#!/usr/bin/env python3
"""H1235 native x86/x86: Game4 independent protected per-lane hot rekey
with REAL tc netem loss 5% in BOTH physical directions only on Bob veth.
Alice/Carol remain no-impairment live controls with their original M4 owners.
"""
import pathlib,sys,subprocess,tempfile
if len(sys.argv)!=3 or sys.argv[2] not in ("game4-off","game4-fixed6"):
    raise SystemExit("usage: x86-netem5-fixture.py OUTPUT game4-off|game4-fixed6")
out=pathlib.Path(sys.argv[1]);scene=sys.argv[2]
with tempfile.TemporaryDirectory() as d:
    original=pathlib.Path(d)/"h1231.sh"
    subprocess.run([sys.executable,
      "tools/m0-h1231-arm64-game4-real-single-lane-fixture.py",
      str(original),scene],check=True)
    s=original.read_text()
def sub(a,b,expected=1):
    global s
    actual=s.count(a)
    if actual!=expected:raise AssertionError((scene,a[:110],actual,expected))
    s=s.replace(a,b)

# Install one real Linux kernel network impairment per physical direction,
# with no extra proxy, signal/packet encoding, application replays or Go pump.
# Include each netem readback and counter as source-locked native evidence.
sub('snapshot before\ncat >"$TMP/hot-lane-stream.py"',
'''snapshot before
sudo -n tc qdisc replace dev mhb0 root netem loss 5%
sudo -n ip netns exec "$NSB" tc qdisc replace dev mxb0 root netem loss 5%
sudo -n tc -s qdisc show dev mhb0 >"$ART/netem-server-to-bob-before.txt"
sudo -n ip netns exec "$NSB" tc -s qdisc show dev mxb0 >"$ART/netem-bob-to-server-before.txt"
cat >"$TMP/hot-lane-stream.py"''')
sub('snapshot after\nfor who in server alice bob carol;',
'''snapshot after
sudo -n tc -s qdisc show dev mhb0 >"$ART/netem-server-to-bob-after.txt"
sudo -n ip netns exec "$NSB" tc -s qdisc show dev mxb0 >"$ART/netem-bob-to-server-after.txt"
# The two actual physical interfaces, not an application data simulator,
# were under netem during the full eight successive original TLS swaps.
sudo -n tc qdisc del dev mhb0 root
sudo -n ip netns exec "$NSB" tc qdisc del dev mxb0 root
for who in server alice bob carol;''')
sub('assert v["sent"]>=800 and v["received"]>=v["sent"]*.995,(who,v)',
'''assert v["sent"]>=800 and v["received"]>=v["sent"]*(.98 if who=="bob" else .995),(who,v)''')
sub('result={"result":"PASS","mode":mode,',
'''def netem_drops(name):
    raw=pathlib.Path("fixed-kernel-result/"+name).read_text()
    assert "netem" in raw and "loss 5%" in raw,(name,raw)
    m=re.search(r"dropped\s+(\d+)",raw)
    assert m,(name,raw)
    return int(m.group(1))
toward_bob=netem_drops("netem-server-to-bob-after.txt")
from_bob=netem_drops("netem-bob-to-server-after.txt")
assert toward_bob>=15 and from_bob>=15,(toward_bob,from_bob)
result={"result":"PASS","mode":mode,''')
sub('"other_clients_ongoing":True,\n    "outer_complete_ipv4_mtu_default":1460,',
'''"other_clients_ongoing":True,
    "physical_netem": {"device":"bob_only","loss_injected_each_direction_pct":5,
        "real_kernel_egress_dropped_server_to_bob":toward_bob,
        "real_kernel_egress_dropped_bob_to_server":from_bob,
        "all_other_client_veth_netem":"off"},
    "outer_complete_ipv4_mtu_default":1460,''')
sub('"platform":"original Go TLS/Rust ARM64+ARM64 native",',
    '"platform":"original Go TLS/Rust x86_64+x86_64 native",')
sub('H1231_NATIVE_ARM64_GAME4_EIGHT_TRUE_SINGLE_LANE_HOT_SWAPS_PASS',
    'H1235_NATIVE_X86_GAME4_EIGHT_TRUE_SINGLE_LANE_NETEM5_PASS')
# Keep genuine per-attempt authenticated retry timing inside a bounded
# long observation, so one 20s cold TLS timeout never gets confused with
# a permanently broken GameAdapter.
sub('time.time_ns()-first_send<230_000_000_000',
    'time.time_ns()-first_send<330_000_000_000')
sub('for _ in $(seq 1 1120);do','for _ in $(seq 1 1480);do')
# Keep the ACTUAL failing native witnesses instead of the inherited fixture's
# abbreviated server-only cleanup tail. A retry-worthy handshake failure
# must NOT kill the current healthy four-lane GameAdapter.
sub('if [[ "$rotated" != 1 ]];then\n echo "H1231_SINGLE_LANE_FAILURE: no eight authentic slot swaps" >&2',
'''if [[ "$rotated" != 1 ]];then
 echo "H1235_SINGLE_LANE_FAILURE: eight turns not completed" >&2
 for who in server alice bob carol;do
     if test -f "$TMP/$who.log";then
       cp "$TMP/$who.log" "$ART/hot-failed-runtime-$who.log"
     fi
 done
 sudo -n tc -s qdisc show dev mhb0 >"$ART/netem-server-to-bob-after.txt" || true
 sudo -n ip netns exec "$NSB" tc -s qdisc show dev mxb0 >"$ART/netem-bob-to-server-after.txt" || true''')
sub('  sleep .25\ndone\nif [[ "$rotated" != 1 ]];then',
'''  # Stop a genuine failed product cohort early, retain all four raw logs.
  if grep -Fq "V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_FAILED" "$TMP/bob.log";then
      break
  fi
  sleep .25
done
if [[ "$rotated" != 1 ]];then''')
sub('result={"result":"PASS","mode":mode,',
'''cold_defers=re.findall(r"V4_PUBLIC_GAME_SINGLE_LANE_COLD_RETRY_ARMED role=client",client)
result={"result":"PASS","mode":mode,''')
sub('"other_clients_ongoing":True,',
''' "cold_handshake_retry_arms_without_group_restart":len(cold_defers),
    "other_clients_ongoing":True,''')
out.write_text(s)
out.chmod(0o700)
print("H1235 native x86 Game4 scoped physical 5pct two-way netem generator",scene,flush=True)
