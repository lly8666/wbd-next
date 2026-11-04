#!/usr/bin/env python3
"""H1199 genuine x86 original Go TLS/Rust Game2 fixed strongest FEC profile6
two physical underlay source-IP changes while Game4 and Normal remain healthy.
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);saved=sys.argv
sys.argv=["tools/m0-plan028-arm64-game2-off-two-physical-handover-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=saved
s=out.read_text()
def one(a,b):
    global s
    assert s.count(a)==1,"original native Game2 source anchor changed: "+a[:100]
    s=s.replace(a,b,1)
one("start_client \"$NSA\" mxa0 10.25.0.2 mxa4 41031 alice alice-mixed-protected game2 '--record-cipher chacha20-poly1305'",
    "start_client \"$NSA\" mxa0 10.25.0.2 mxa4 41031 alice alice-mixed-protected game2 '--game-fec fixed6 --record-cipher chacha20-poly1305'")
one('"game2-off-ChaCha"','"game2-fixed6-ChaCha"')
one('[[ "$a0" == 1373 && "$b0" == 1358 && "$c0" == 1375 ]]',
    '[[ "$a0" -ge 1100 && "$a0" -le 1373 && "$b0" == 1358 && "$c0" == 1375 ]]')
one('assert mtus[0]==1373 and','assert 1100<=mtus[0]<=1373 and')
s=s.replace("GAME2_OFF","GAME2_FIXED6")
s=s.replace("GAME2_OFF","GAME2_FIXED6")
s=s.replace("game2_off","game2_fixed6")
s=s.replace("plan028-h1193","plan028-h1199")
s=s.replace("H1193","H1199")
old='assert gen(alice)==[1,2,3] and stops==[1,2] and gen(bob)==[1] and gen(carol)==[1]'
new='''assert gen(alice)==[1,2,3] and stops==[1,2] and gen(bob)==[1] and gen(carol)==[1]
assert alice.count("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=fixed profile=6")==3'''
one(old,new)
old='assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=")>=2'
new='''assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=")>=2
assert server.count("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=2 mode=fixed profile=6")==3'''
one(old,new)
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1199_X86_GAME2_FIXED6_NATIVE_TEST_FIXTURE_READY",flush=True)
