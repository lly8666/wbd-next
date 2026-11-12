#!/usr/bin/env python3
"""H1197 x86 Normal fixed highest FEC2 profile6, original Go TLS/Rust M4
two real physical IP+MTU changes using qualified H1194 source-native fixture.
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-x86-normalauto-two-physical-handover-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=saved
s=out.read_text()
def one(old,new):
    global s
    assert s.count(old)==1,"qualified Normal real OS source anchor changed: "+old[:90]
    s=s.replace(old,new,1)
one("start_client \"$NSC\" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-auto '--record-cipher aes-128-gcm'",
    "start_client \"$NSC\" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-fixed '--fec-profile 6 --record-cipher aes-128-gcm'")
one('"V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto"',
    '"V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=fixed profile=6"')
one('"V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=auto"',
    '"V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=fixed"')
one('"normal-auto-AES128"','"normal-fixed6-AES128"')
s=s.replace("NORMAL_AUTO","NORMAL_FIXED6")
s=s.replace("normal_auto_authenticated_generations","normal_fixed6_authenticated_generations")
s=s.replace("plan028-h1192-normal-auto-two-source4.json","plan028-h1197-normal-fixed6-two-source4.json")
one("M0_PLAN028_H1192_X86_NORMAL_FIXED6_REAL_PHYSICAL_TWO_REAUTH_PASS",
    "M0_PLAN028_H1197_X86_NORMAL_FIXED6_REAL_PHYSICAL_TWO_REAUTH_PASS")
old='assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==3'
new=r'''assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==1
assert server.count("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server")>=2
assert server.count("V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=fixed profile=6")==3
effective_rows=re.findall(r'V4_PUBLIC_FEC2_READBACK role=client mode=fixed requested=\d+ applied=\d+ profile=(\d+) pending=false',normal)
assert effective_rows and all(int(x)==6 for x in effective_rows),effective_rows'''
# Original Go server emits one initial READY and two B_CLIENT_READY for
# authenticated generation2/3; never reinterpret candidate as three initial READY.
one(old,new)
assert s.count("PY_H1192")==2
# H1629: actual old-retire grace reached 18.82s (H1628) while the 32*0.4s
# sibling UDP generator finished in 12.8s. Lengthen real kernel payload
# coverage across the ENTIRE authenticated old-A exact Stop, not weaken oracle.
one("for i in $(seq 0 31);do","for i in $(seq 0 79);do")
one("assert len(t1)==32 and t1[0]<a<b<t1[-1]","assert len(t1)==80 and t1[0]<a<b<t1[-1]")
one("assert len(t2)==32 and t2[0]<c<d<t2[-1]","assert len(t2)==80 and t2[0]<c<d<t2[-1]")
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1198_X86_FIXED6_SERVER_THREE_CLIENT_FINAL_RUST_READBACK_FIXTURE_READY",flush=True)
