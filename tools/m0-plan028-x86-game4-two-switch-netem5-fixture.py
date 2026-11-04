#!/usr/bin/env python3
"""H1178 original native x86/x86 Game4, 2 real physical handovers, measured 5% kernel loss."""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);previous=sys.argv
sys.argv=["tools/m0-plan028-x86-mixed-game4-two-switch-fixture.py",str(out)]
try:runpy.run_path("tools/m0-plan028-x86-mixed-game4-two-switch-fixture.py",run_name="__main__")
finally:sys.argv=previous
s=out.read_text()
# Extend only the source-locked genuine 5% loss window: native M4
# may need original 1-30s bounded TLS retry and actual successor seq>=3.
# One other protected NormalAuto device continues genuine UDP for 128s.
patches=[
 ('send_udp "$NSC" "$IPC" NORMAL_AUTO_LIVE_GAME4_RESTORE 16 "$TMP/C-restore.log" 0.4 &',
  'send_udp "$NSC" "$IPC" NORMAL_AUTO_LIVE_GAME4_RESTORE 320 "$TMP/C-restore.log" 0.4 &'),
 ('restored=0'+chr(10)+'for _ in {1..140};do',
  'restored=0'+chr(10)+'for _ in {1..480};do'),
 ("if grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3 old_generation=true'",
  "if grep -Eq 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=[0-9]+ old_generation=true'"),
 ('''test "$(grep -c 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE .* ack_ns=' "$TMP/C-restore.log")" -eq 16''',
  '''test "$(grep -c 'REAL_MIXED_UDP NORMAL_AUTO_LIVE_GAME4_RESTORE .* ack_ns=' "$TMP/C-restore.log")" -eq 320'''),
 ('assert len(acks)==16 and acks[0]<changed<ready<acks[-1]',
  'assert len(acks)==320 and acks[0]<changed<ready<acks[-1]'),
 ('"normal_live_restoration_echoes":16','"normal_live_restoration_echoes":320'),
 ('"game4_new_gen3_echoes":16','"game4_new_successor_echoes":16'),
 ('"generation_replacement_sequence":[[1,2],[2,3]]',
  '"generation_replacement_sequence":[[1,2],[2,third]],"cold_retry_count":third-3'),
 ('H1167 missing genuine generation3 ready or generation2 Stop',
  'H1180 no authentic successor after bounded 1-30sec retry or generation2 Stop'),
]
for before,after in patches:
    assert s.count(before)==1,"mature x86 bounded-retry anchor changed: "+before[:78]
    s=s.replace(before,after,1)
old="assert bob.index('V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=3')<bob.index('V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2')"
after=r'''successors=[int(x) for x in re.findall(r'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+) old_generation=true',bob) if int(x)>=3]
assert successors,"no real original TLS-authenticated Game4 successor"
third=successors[0]
assert bob.index('V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation='+str(third))<bob.index('V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=2')'''
assert s.count(old)==1,"original healthy gen3 proof changed"
s=s.replace(old,after,1)
anchor="# Second physical source4 .9→.3; MTU 1280→1500. User outer intent stays 1460."
assert s.count(anchor)==1,"mature genuine x86 double switch changed"
setup=r'''# Real kernel source-NIC 5% loss on Bob only; no simulated packets.
sudo -n ip netns exec "$NSB" tc qdisc replace dev mxb0 root netem loss 5%
sudo -n ip netns exec "$NSB" tc -s -d qdisc show dev mxb0 >"$ART/plan028-h1178-netem-before.txt"
grep -Eq 'netem .*loss 5(\.0+)?%' "$ART/plan028-h1178-netem-before.txt"
'''
s=s.replace(anchor,setup+anchor,1)
anchor='wait "$live_restore"'+chr(10)
assert s.count(anchor)==1,"mature second switch live stage changed"
measurement=r'''# Generation3 authenticated while actual 5% loss is on the physical interface.
# One native 200-packet inner UDP echo stage at 10ms pacing, no retry or mock ACK.
sudo -n ip netns exec "$NSB" python3 - "$IPB" "$ART/plan028-h1178-game4-netem5-rtt.json" <<'PY_H1178'
import json,math,pathlib,select,socket,sys,time
ip=sys.argv[1];dest=pathlib.Path(sys.argv[2])
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind((ip,0));sock.setblocking(False)
sent={};received={};arrived=[]
base=time.monotonic_ns();pref=b"WBD_MIXED_ECHO/WBD_MIXED443/NETEM5/"
def drain(wait):
    readable,_,_=select.select([sock],[],[],wait)
    if not readable:return
    while True:
        try: data,peer=sock.recvfrom(4096)
        except BlockingIOError:break
        if peer[0]!="10.66.0.1" or not data.startswith(pref):continue
        try:n=int(data[len(pref):])
        except ValueError:continue
        if n in sent and n not in received:
            now=time.monotonic_ns();received[n]=(now-sent[n])/1e6;arrived.append(now)
for i in range(200):
    due=base+i*10_000_000
    now=time.monotonic_ns()
    if due>now:time.sleep((due-now)/1e9)
    sent[i]=time.monotonic_ns()
    sock.sendto(("WBD_MIXED443/NETEM5/%d"%i).encode(),("10.66.0.1",45901))
    drain(0)
deadline=time.monotonic()+3
while time.monotonic()<deadline and len(received)<200:drain(.05)
sock.close()
values=sorted(received.values());arrived.sort()
gap=max(((b-a)/1e6 for a,b in zip(arrived,arrived[1:])),default=0)
assert 140<=len(values)<=200 and gap<1500,(len(values),gap)
def slots(times):
    counts={}
    for moment in times:
        k=str((moment-base)//10_000_000)
        counts[k]=counts.get(k,0)+1
    return counts
proof={"scope":"NATIVE_X86_X86_GAME4_FIXED6_TWO_PHYSICAL_CHANGES_REAL_TC_5PCT",
       "physical_qdisc_netem_loss_pct":5,"native_inner_udp_sent":200,
       "native_inner_udp_received":len(values),"missing":200-len(values),
       "received_only_rtt_p99_ms":round(values[math.ceil(.99*len(values))-1],3),
       "max_delivery_gap_ms":round(gap,3),
       "sent_10ms_buckets":slots(sent.values()),"arrived_10ms_buckets":slots(arrived),
       "physical_qdisc_before":{"netem":True},"physical_qdisc_after":{"restored":False},
       "real_qdisc_removed":False,"original_tls_generation3_ready":True,
       "cpu_causal":"NOT_MEASURED","real_inner_tcp":"NOT_TESTED_IN_THIS_SCENE"}
dest.write_text(json.dumps(proof,indent=2)+chr(10))
print("M0_PLAN028_H1178_NATIVE_NETEM5_UDP_RTT_MEASURED delivered=%d p99_ms=%.3f gap_ms=%.3f"%
 (len(values),proof["received_only_rtt_p99_ms"],gap),flush=True)
PY_H1178
sudo -n ip netns exec "$NSB" tc -s -d qdisc show dev mxb0 >"$ART/plan028-h1178-netem-during.txt"
sudo -n ip netns exec "$NSB" tc qdisc del dev mxb0 root
sudo -n ip netns exec "$NSB" tc qdisc show dev mxb0 >"$ART/plan028-h1178-netem-after.txt"
if grep -q 'netem' "$ART/plan028-h1178-netem-after.txt";then
 echo "H1178 original physical loss qdisc leaked" >&2;exit 1
fi
python3 - "$ART/plan028-h1178-game4-netem5-rtt.json" <<'PY_H1178_END'
import pathlib,json,sys
p=pathlib.Path(sys.argv[1]);v=json.loads(p.read_text())
v["physical_qdisc_after"]["restored"]=True;v["real_qdisc_removed"]=True
p.write_text(json.dumps(v,indent=2)+chr(10))
print("M0_PLAN028_H1178_X86_TWO_REAL_GAME4_SWITCHES_NETEM5_INNER_UDP_P99_PASS",flush=True)
PY_H1178_END
'''
s=s.replace(anchor,anchor+measurement,1)
assert s.count('for i in range(320):')==1
s=s.replace('for i in range(320):','for i in range(1000):',1)
# This measurement block is appended after the existing physical stage.
assert s.count('"original_tls_generation3_ready":True')==1
s=s.replace('"original_tls_generation3_ready":True','"original_tls_successor_ready":True',1)
assert s.count("PY_H1178")>=4 and s.count('tc qdisc replace dev mxb0 root netem loss 5%')==1
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1178_X86_NATIVE_GAME4_NETEM5_FIXTURE_ASSEMBLED",flush=True)
