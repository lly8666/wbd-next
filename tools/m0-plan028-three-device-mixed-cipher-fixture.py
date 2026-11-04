#!/usr/bin/env python3
"""H1146: one genuine x86 Go TLS/Rust shared-443 scenario with
independent ChaCha, AES128, AES256 suites on distinct authenticated devices.
The existing native 70-UDP mixed Normal FEC fixture is source-frozen."""
from pathlib import Path
import runpy,sys
out=Path(sys.argv[1])
saved=sys.argv
try:
 sys.argv=["tools/m0-plan028-three-device-mixed-normal-fec-fixture.py",str(out)]
 runpy.run_path("tools/m0-plan028-three-device-mixed-normal-fec-fixture.py",run_name="__main__")
finally:
 sys.argv=saved
s=out.read_text()
def rep(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError("source-frozen native mixed Normal anchor changed "+a[:105])
 s=s.replace(a,b,1)
rep("  local pidfile=\"$1\" fec_mode=normal outer_arg=''",
    """  local pidfile="$1" fec_mode=normal outer_arg='' cipher_arg=''
  case "$port" in
    42031) cipher_arg='--record-cipher aes-128-gcm' ;;
    44031) cipher_arg='--record-cipher aes-256-gcm' ;;
  esac""")
rep("--mode '$fec_mode' $outer_arg\n","--mode '$fec_mode' $outer_arg $cipher_arg\n")
rep("assert all(int(row[2])==1 for row in matches)",
    "assert [int(row[2]) for row in matches]==[1,2,3,1],[int(row[2]) for row in matches]")
rep('result["original_server_protected_rust_modes"]=[row[0] for row in matches]',
    'result["original_server_protected_rust_modes"]=[row[0] for row in matches]\nresult["original_server_protected_rust_ciphers"]=[int(row[2]) for row in matches]')
s=s.replace("H1144","H1146").replace("h1144","h1146")
out.write_text(s)
out.chmod(0o700)
print("M0_PLAN028_H1146_NATIVE_MIXED_NORMAL_THREE_PROTECTED_RUST_AEAD_SUITE_FIXTURE_READY")
