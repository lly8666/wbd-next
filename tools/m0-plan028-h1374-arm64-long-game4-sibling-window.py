#!/usr/bin/env python3
"""H1374: exact H1373 original ARM64 product and physical-Normal fixture.
One fixture-only correction: live sibling 32*0.4s wallclock didn't cover
actual ~19s authenticated owner two-phase renewal. Extend 64*0.4s; do not
change product, packets, TLS, Rust, route, OS MTU or original markers.
"""
from pathlib import Path
import runpy,sys
assert len(sys.argv)==2,"one generated shell path required"
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-arm64-normaloff-two-physical-handover-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=saved
s=out.read_text()
def exactly(old,new):
 global s
 assert s.count(old)==1,(old,s.count(old))
 s=s.replace(old,new,1)
exactly('for i in $(seq 0 31);do','for i in $(seq 0 63);do')
exactly('assert len(t1)==32 and','assert len(t1)==64 and')
exactly('assert len(t2)==32 and','assert len(t2)==64 and')
out.write_text(s);out.chmod(0o700)
print("H1374_ARM64_64_PACED_NATIVE_GAME4_SIBLING_ENTIRE_COLD_AUTH_WINDOW_FIXTURE_READY")
