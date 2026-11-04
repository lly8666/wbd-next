#!/usr/bin/env python3
"""Extend the already qualified one-scenario x86 genuine Rust M2 netns probe
for native ARM64 without changing the original product or test harness."""
from pathlib import Path
import runpy
import sys

out=Path(sys.argv[1])
original=sys.argv
try:
    sys.argv=["tools/m0-plan028-x86-shared-rust-m2-fixture.py",str(out)]
    runpy.run_path("tools/m0-plan028-x86-shared-rust-m2-fixture.py",run_name="__main__")
finally:
    sys.argv=original
text=out.read_text()
changes={
 "M0_PLAN028_H1137_X86_TWO_GENUINE_RUST_M2_READBACK_REBIND_AND_STOP_PASS":
 "M0_PLAN028_H1139_ARM64_TWO_GENUINE_RUST_M2_READBACK_REBIND_AND_STOP_PASS",
 "x86_64_client_and_x86_64_server":"arm64_client_and_arm64_server",
 "plan028-h1137-native-rust-m2.json":"plan028-h1139-native-rust-m2.json",
}
for src,dest in changes.items():
    if text.count(src)!=1:
        raise RuntimeError("source-frozen x86 probe changed unexpectedly: "+src)
    text=text.replace(src,dest)
out.write_text(text)
out.chmod(0o700)
print("M0_PLAN028_H1139_ARM64_TWO_GENUINE_RUST_M2_FIXTURE_READY product_unchanged=1")
