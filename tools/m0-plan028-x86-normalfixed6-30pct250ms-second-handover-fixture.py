#!/usr/bin/env python3
"""H1204 x86 original Go TLS/Rust Normal fixed highest6: true second
physical IP change DURING native kernel tc loss30 delay250; Game4 healthy.
Test-only reuse of qualified H1197 original native M4 A-B-A and H1186 tc.
"""
from pathlib import Path
import runpy,re,sys
out=Path(sys.argv[1]);prior=sys.argv
sys.argv=["tools/m0-plan028-x86-normalfixed6-two-physical-handover-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=prior
s=out.read_text()
def one(a,b):
    global s
    assert s.count(a)==1,"original native Normal highest source changed "+a[:100]
    s=s.replace(a,b,1)
one('for i in range(360):','for i in range(1000):')
one('local tag="$1" times="$2"','local tag="$1" times="$2" limit="$3"')
one('for i in $(seq 0 31);do','for i in $(seq 0 "$limit");do')
one('game_live GAME4_HEALTH_NORMAL_CHANGE1 "$TMP/B-game-live1-ns.txt" &',
    'game_live GAME4_HEALTH_NORMAL_CHANGE1 "$TMP/B-game-live1-ns.txt" 31 &')
one('game_live GAME4_HEALTH_NORMAL_CHANGE2 "$TMP/B-game-live2-ns.txt" &',
    'game_live GAME4_HEALTH_NORMAL_CHANGE2 "$TMP/B-game-live2-ns.txt" 319 &')
one('assert len(t2)==32 and t2[0]<c<d<t2[-1]',
    'assert len(t2)==320 and t2[0]<c<d<t2[-1]')
one('ready2=0\nfor _ in {1..180};do','ready2=0\nfor _ in {1..480};do')
one("grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true'",
    "grep -Eq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=[3-9][0-9]* old_generation=true'")
one('assert gn==[1,2,3] and old==[1,2] and gg==[1]',
    'assert gn[:2]==[1,2] and gn[-1]>=3 and old==[1,2] and gg==[1]')
one('for attempt in range(4):','for attempt in range(8):')
setup='''sudo -n ip netns exec "$NSC" tc qdisc replace dev mxc0 root netem loss 30% delay 250ms
sudo -n ip netns exec "$NSC" tc -s -d qdisc show dev mxc0 >"$ART/plan028-h1204-netem-before.txt"
grep -Eq 'netem .*loss 30(\\.0+)?%' "$ART/plan028-h1204-netem-before.txt"
grep -Fq 'delay 250ms' "$ART/plan028-h1204-netem-before.txt"
'''
one('changed2="$(date +%s%N)"',setup+'changed2="$(date +%s%N)"')
one("M0_PLAN028_H1197_X86_NORMAL_FIXED6_REAL_PHYSICAL_TWO_REAUTH_PASS",
    "M0_PLAN028_H1204_X86_NORMAL_FIXED6_REAL_TC30_SECOND_REAUTH_PASS")
one("plan028-h1197-normal-fixed6-two-source4.json",
    "plan028-h1204-normal-fixed6-two-source4.json")
one('"loss5":"NOT_IN_THIS_SCENE"',
    '"loss30":"REAL_OS_TC_DURING_SECOND_NORMAL_TLS","physical_qdisc_delay_ms":250')
old='print("M0_PLAN028_H1204_X86_NORMAL_FIXED6_REAL_TC30_SECOND_REAUTH_PASS",flush=True)'+chr(10)+'PY_H1192'
assert s.count(old)==1,"authentic second normal TLS scene changed"
src=Path("tools/m0-plan028-x86-game4-two-switch-netem5-fixture.py").read_text()
m=re.search(r"measurement=r'''(.*?)'''",src,re.S)
assert m,"qualified genuine kernel 200 UDP RTT measurement moved"
b=m.group(1)
b=b.replace("plan028-h1178","plan028-h1204")
b=b.replace("game4-netem5-rtt","normal-fixed6-netem30delay250-rtt")
b=b.replace('"$NSB"','"$NSC"').replace('"$IPB"','"$IPC"').replace("mxb0","mxc0")
b=b.replace("NETEM5","NETEM30").replace("netem5","netem30delay250")
b=b.replace('assert 140<=len(values)<=200 and gap<1500','assert 90<=len(values)<=200 and gap<3000')
b=b.replace('deadline=time.monotonic()+3','deadline=time.monotonic()+8')
b=b.replace('"physical_qdisc_netem_loss_pct":5,"native_inner_udp_sent":200',
            '"physical_qdisc_netem_loss_pct":30,"physical_qdisc_delay_ms":250,\n       "loss_injection_stage":"DURING_NORMAL_GEN3_TLS_REAUTH","native_inner_udp_sent":200')
b=b.replace("NATIVE_X86_X86_GAME4_FIXED6_TWO_PHYSICAL_CHANGES_REAL_TC_5PCT",
            "NATIVE_X86_X86_NORMAL_FIXED6_REAL_TLS_SECOND_SWAP_TC30_DELAY250")
b=b.replace('"original_tls_generation3_ready":True','"original_tls_successor_ready":True')
b=b.replace("PY_H1178_END","PY_NORMAL_HIGH30_END")
b=b.replace("H1178 original physical loss qdisc leaked","H1204 physical loss qdisc leaked")
b=b.replace("5pct physical kernel qdisc","30pct physical kernel qdisc")
b=b.replace("M0_PLAN028_H1184_X86_NETEM5_200UDP_P99_NATIVE_DROP_AND_CLEAN_STOP_PROVEN",
            "M0_PLAN028_H1204_X86_NORMAL_FIXED6_NETEM30_DELAY250_NATIVE_DROP_AND_CLEAN_STOP_PASS")
assert b.count("M0_PLAN028_H1204_X86_NORMAL_FIXED6_NETEM30_DELAY250_NATIVE_DROP_AND_CLEAN_STOP_PASS")==1
s=s.replace(old,old+chr(10)+b,1)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1204_X86_NORMAL_FIXED6_ORIGINAL_TLS_DURING_NETEM30_FIXTURE_READY",flush=True)
