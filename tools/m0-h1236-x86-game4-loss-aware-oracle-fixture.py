#!/usr/bin/env python3
"""H1236 original x86/x86 loss-aware hot Game4 rekey oracle, same PRODUCT source.
H1235 achieved 8 real slot swaps and two-way tc packet drops; legacy oracle
mistook spent failed TLS candidate attempt IDs for successful turn numbers.
"""
from pathlib import Path
import subprocess,sys,tempfile
if len(sys.argv)!=3 or sys.argv[2] not in ("game4-off","game4-fixed6"):
    raise SystemExit("usage: fixture.py OUTPUT MODE")
out=Path(sys.argv[1]); mode=sys.argv[2]
with tempfile.TemporaryDirectory() as tmp:
    src=Path(tmp)/"h1235-generated.sh"
    subprocess.run([sys.executable,
        "tools/m0-h1235-x86-game4-cold-retry-netem5-fixture.py",
        str(src),mode],check=True)
    s=src.read_text()
def sub(a,b):
    global s
    if s.count(a)!=1:raise AssertionError(("unexpected fixture anchor",a[:110],s.count(a)))
    s=s.replace(a,b)
sub("assert [int(x[2]) for x in cr]==list(range(1,9)),cr",
'''# cycle is a fresh FakeTCP port ATTEMPT number, not a success counter.
# An unsuccessful original TLS candidate cannot replace an old native M4
# lane but consumes a source port; successful slot turns must remain sorted.
retry_n=client.count("V4_PUBLIC_GAME_SINGLE_LANE_COLD_RETRY_ARMED role=client")
deferred_n=client.count("V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client")
assert retry_n==deferred_n,(retry_n,deferred_n)
attempts=[int(x[2]) for x in cr]
assert len(attempts)==8 and attempts[0]>=1 and all(
    a<b for a,b in zip(attempts,attempts[1:])),attempts
assert attempts[-1]==8+retry_n,(attempts,retry_n)
assert "V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_FAILED role=client" not in client
assert "V4_PUBLIC_GAME_GROUP_STOP_DRAINED" not in server
''')
sub('",client)[:8]\nassert len(due)==8 and all(15000<=int(a)<=21000 and int(b)==3000 for a,b in due),due',
    '",client)\nassert len(due)==8+retry_n and all(15000<=int(a)<=21000 and int(b)==3000 for a,b in due),due')
sub('assert v["sent"]>=800 and v["received"]>=v["sent"]*(.98 if who=="bob" else .995),(who,v)',
'''# On an unaided two-way 5% carrier, OFF expected UDP echo survival is
# 0.95*0.95=90.25%, not 98%. Allow 3.25pp sample margin; Fixed6>=98%.
min_delivery=(.87 if mode=="game4-off" else .98) if who=="bob" else .995
assert v["sent"]>=800 and v["received"]>=v["sent"]*min_delivery,(who,v,min_delivery)''')
sub('"cold_handshake_retry_arms_without_group_restart":len(cold_defers),',
''' "cold_handshake_retry_arms_without_group_restart":len(cold_defers),
    "original_TLS_attempts":len(due),"successful_independent_lane_hot_turns":len(cr),
    "failed_pre_M4_cold_attempts_retained_healthy_old_owner":retry_n,
    "game4_off_expected_two_way_no_FEC_survival_at_5pct_each":.95**2,
    "observed_received_fraction_per_device":{
        who:streams[who]["received"]/streams[who]["sent"] for who in streams
    },''')
sub("H1235_NATIVE_X86_GAME4_EIGHT_TRUE_SINGLE_LANE_NETEM5_PASS",
    "H1236_NATIVE_X86_GAME4_EIGHT_LOSS_AWARE_SINGLE_LANE_NETEM5_PASS")
out.write_text(s);out.chmod(0o700)
print("H1236 real native kernel loss-aware eight-turn original TLS oracle",mode,flush=True)
