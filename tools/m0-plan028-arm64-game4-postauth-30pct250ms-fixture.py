#!/usr/bin/env python3
"""H1203 original ARM64 Game4FEC6 auth link-down then true post-auth kernel
30% physical loss + 250ms delay; reuse native H1191 5pct original product.
"""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1]);orig=sys.argv
sys.argv=["tools/m0-plan028-arm64-postauth-netem5-game4-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=orig
s=out.read_text()
def one(a,b):
    global s
    assert s.count(a)==1,"actual native source changed "+a[:90]
    s=s.replace(a,b,1)
one("tc qdisc replace dev mxb0 root netem loss 5%","tc qdisc replace dev mxb0 root netem loss 30% delay 250ms")
one("grep -Eq 'netem .*loss 5(\\.0+)?%'","grep -Eq 'netem .*loss 30(\\.0+)?%'")
one('assert 140<=len(values)<=200 and gap<1500','assert 90<=len(values)<=200 and gap<3000')
one('deadline=time.monotonic()+3','deadline=time.monotonic()+8')
one('"physical_qdisc_netem_loss_pct":5,','"physical_qdisc_netem_loss_pct":30,\n       "physical_qdisc_delay_ms":250,')
one('"original_tls_generation3_ready":True','"original_tls_generation2_ready":True')
one("NATIVE_ARM64_GAME4_HARD_DOWN_RECOVERY_POST_AUTH_TC_5PCT","NATIVE_ARM64_GAME4_HARD_DOWN_RECOVERY_POST_AUTH_TC_30PCT_DELAY250")
s=s.replace("plan028-h1189","plan028-h1203").replace("game4-netem5-rtt","game4-netem30delay250-rtt")
s=s.replace("netem5","netem30delay250").replace("NETEM5","NETEM30_DELAY250").replace("LOSS5","LOSS30").replace("loss5","loss30").replace("H1189","H1203")
one("H1178 original physical loss qdisc leaked","H1203 physical loss qdisc leaked")
one("5pct physical kernel qdisc","30pct physical kernel qdisc")
assert s.count('tc qdisc replace dev mxb0 root netem loss 30% delay 250ms')==1
assert s.count('"physical_qdisc_delay_ms":250')==1
assert s.count('M0_PLAN028_H1203_ARM64_POSTAUTH_TRUE_NETEM30_DELAY250_200UDP_P99_PASS')==1
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1203_ARM64_POSTAUTH_NETEM30_DELAY250_FIXTURE_READY",flush=True)
