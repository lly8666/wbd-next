#!/usr/bin/env python3
"""H1147: one ARM64+ARM64 source-locked TLS/Rust three-device scene,
checking that Normal fixed6 is selected from the existing protected
V4 record rather than a server process-global --fec-profile."""
from pathlib import Path
import runpy,sys

out=Path(sys.argv[1])
saved=sys.argv
try:
    sys.argv=["tools/m0-plan028-three-device-mixed-cipher-fixture.py",str(out)]
    runpy.run_path("tools/m0-plan028-three-device-mixed-cipher-fixture.py",run_name="__main__")
finally:
    sys.argv=saved
s=out.read_text()
def one(a,b):
    global s
    if s.count(a)!=1:
        raise RuntimeError(f"frozen H1146 cipher source fixture changed: {a[:115]!r} count={s.count(a)}")
    s=s.replace(a,b,1)
one("44031) fec_mode=fec-fixed;outer_arg='--outer-mtu 1280' ;;",
    "44031) fec_mode=fec-fixed;outer_arg='--outer-mtu 1280 --fec-profile 6' ;;")
one("assert [int(row[2]) for row in matches]==[1,2,3,1],[int(row[2]) for row in matches]",
    """assert [int(row[2]) for row in matches]==[1,2,3,1],[int(row[2]) for row in matches]
assert matches[2][0]=="fixed" and int(matches[2][1])==6,matches""")
one('assert server.count("V4_PUBLIC_M2_OUTER role=server")==4',
r'''assert server.count("V4_PUBLIC_M2_OUTER role=server")==4
effective=re.findall(r"V4_PUBLIC_MULTI_NATIVE_FEC_EFFECTIVE role=server mode=(auto|fixed) profile=(\d+) requested=(\d+) applied=(\d+) pending=(true|false)",server)
assert any(mode=="fixed" and int(profile)==6 and int(applied)>=1 for mode,profile,requested,applied,pending in effective),effective
assert re.search(r"V4_PUBLIC_FEC2_READBACK role=client mode=fixed requested=\d+ applied=[1-9]\d* profile=6",alice_d),alice_d[-2700:]''')
one('result["original_server_protected_rust_ciphers"]=[int(row[2]) for row in matches]',
    'result["original_server_protected_rust_ciphers"]=[int(row[2]) for row in matches]\nresult["original_authenticated_fixed6_profile"]=6\nresult["genuine_Rust_server_fixed6_readback"]=True')
one('print("M0_PLAN028_H1146_ONE_443_PER_CLIENT_OFF_AUTO_FIXED_PROTECTED_RUST_70_UDP_STOP_PASS",flush=True)',
    'print("M0_PLAN028_H1146_ONE_443_PER_CLIENT_OFF_AUTO_FIXED_PROTECTED_RUST_70_UDP_STOP_PASS",flush=True)\nprint("M0_PLAN028_H1147_PROTECTED_FIXED6_GENUINE_RUST_FEC_STRENGTH_AES1_2_3_70_UDP_STOP_PASS",flush=True)')
s=s.replace("H1146","H1147").replace("h1146","h1147")
out.write_text(s)
out.chmod(0o700)
print("M0_PLAN028_H1147_ARM64_PROTECTED_FIXED_STRENGTH_FIXTURE_READY",flush=True)
