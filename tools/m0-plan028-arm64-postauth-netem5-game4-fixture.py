#!/usr/bin/env python3
"""ARM64 hard physical link-down then authenticated M4 READY, only THEN real 5% netem."""
import runpy,sys,re
from pathlib import Path
out=Path(sys.argv[1]);original=sys.argv
sys.argv=["tools/m0-plan028-arm64-game4-link-down-before-reconnect-fixture.py",str(out)]
try:runpy.run_path(sys.argv[0],run_name="__main__")
finally:sys.argv=original
s=out.read_text()
src=Path("tools/m0-plan028-x86-game4-two-switch-netem5-fixture.py").read_text()
setup=re.search(r"setup=r'''(.*?)'''",src,re.S)
measure=re.search(r"measurement=r'''(.*?)'''",src,re.S)
assert setup and measure,"previous verified netem5 kernel + UDP measurement changed"
a,b=setup.group(1),measure.group(1)
a=a.replace("plan028-h1178","plan028-h1189")
b=b.replace("plan028-h1178","plan028-h1189")
b=b.replace("NATIVE_X86_X86_GAME4_FIXED6_TWO_PHYSICAL_CHANGES_REAL_TC_5PCT","NATIVE_ARM64_GAME4_HARD_DOWN_RECOVERY_POST_AUTH_TC_5PCT")
b=b.replace("M0_PLAN028_H1184_X86_NETEM5_200UDP_P99_NATIVE_DROP_AND_CLEAN_STOP_PROVEN","M0_PLAN028_H1189_ARM64_POSTAUTH_TRUE_NETEM5_200UDP_P99_PASS")
b=b.replace('"physical_qdisc_netem_loss_pct":5','"physical_qdisc_netem_loss_pct":5,\n "loss_injection_stage":"AFTER_GAME4_GEN2_AUTHENTICATED_M4"')
assert b.count("M0_PLAN028_H1189_ARM64_POSTAUTH_TRUE_NETEM5_200UDP_P99_PASS")==1
before='for i in range(160):'
assert s.count(before)==1,"native one443 UDP echo listener changed"
s=s.replace(before,'for i in range(480):',1)
mark='print("M0_PLAN028_H1171_ARM64_GAME4_LINK_DOWN_BEFORE_NEW_TLS_RECOVERY_PASS",flush=True)'+chr(10)+"PY_H1171"
assert s.count(mark)==1,"real link-DOWN and original TLS M4 receipt missing"
normal='send_udp "$NSC" "$IPC" NORMAL_AUTO_ARM_POSTAUTH_LOSS5 16 "$TMP/C-postauth-loss5.log" 0.2 &\nnormal_loss5_pid=$!\n'
finish='''wait "$normal_loss5_pid"
test "$(grep -c 'REAL_MIXED_UDP NORMAL_AUTO_ARM_POSTAUTH_LOSS5 .* ack_ns=' "$TMP/C-postauth-loss5.log")" -eq 16
python3 - "$ART/plan028-h1189-game4-netem5-rtt.json" <<'PY_ARM_NORMAL'
import pathlib,json,sys
p=pathlib.Path(sys.argv[1]);result=json.loads(p.read_text())
result["unaffected_normal_auto_udp_during_loss"]=16
p.write_text(json.dumps(result,indent=2)+chr(10))
PY_ARM_NORMAL
'''
s=s.replace(mark,mark+chr(10)+a+normal+b+finish,1)
assert s.count("PY_H1178_END")==0 and s.count("PY_ARM_NORMAL")==2
out.write_text(s);out.chmod(0o700)
print("M0_PLAN028_H1189_NATIVE_ARM64_POSTAUTH_NETEM5_FIXTURE_READY",flush=True)
