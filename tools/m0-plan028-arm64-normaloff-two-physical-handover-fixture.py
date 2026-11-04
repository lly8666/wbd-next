#!/usr/bin/env python3
"""PLAN028 H1198 native ARM64 Normal off two genuine original-Go TLS/Rust
physical changes, protected Game4 unaffected; reuse already-tested x86 shape.
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-x86-normalauto-two-physical-handover-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=saved
s=out.read_text()
def one(a,b):
    global s
    assert s.count(a)==1,"original Native Normal source changed: "+a[:110]
    s=s.replace(a,b,1)
one("start_client \"$NSC\" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-auto '--record-cipher aes-128-gcm'",
    "start_client \"$NSC\" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected normal '--record-cipher aes-128-gcm'")
one('"V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto"','"V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=off profile=0"')
one('"V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=auto"','"V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=off"')
one('"normal-auto-AES128"','"normal-off-AES128"')
one('[[ "$n0" == 1375 && "$g0" == 1358 ]]','[[ "$n0" == 1389 && "$g0" == 1358 ]]')
one('assert m0==1375 and','assert m0==1389 and')
s=s.replace("NORMAL_AUTO","NORMAL_OFF")
s=s.replace("normal_auto_authenticated_generations","normal_off_authenticated_generations")
s=s.replace("plan028-h1192-normal-auto-two-source4.json","plan028-h1198-normaloff-two-source4.json")
one("M0_PLAN028_H1192_X86_NORMAL_OFF_REAL_PHYSICAL_TWO_REAUTH_PASS",
    "M0_PLAN028_H1198_ARM64_NORMAL_OFF_TWO_PHYSICAL_M4_GAME4_HEALTH_PASS")
old='assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==3'
new='''assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==3
assert server.count("V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=off profile=0")==3
assert "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto" not in server'''
one(old,new)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1198_ARM_NORMAL_OFF_SOURCE_FIXTURE_READY",flush=True)
