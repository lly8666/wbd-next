#!/usr/bin/env python3
"""H1130: adapt one frozen x86 timeline fixture to native ARM64 labels only."""
from pathlib import Path
import runpy
import sys

out=Path(sys.argv[1])
old_argv=sys.argv
try:
    sys.argv=["tools/m0-plan028-x86-auto-timeline-fixture.py",str(out)]
    runpy.run_path("tools/m0-plan028-x86-auto-timeline-fixture.py",run_name="__main__")
finally:
    sys.argv=old_argv
s=out.read_text()
for before,after in (
    ('"platform":"native_linux_x86_client_and_x86_server"',
     '"platform":"native_linux_arm64_client_and_arm64_server"'),
    ('M0_PLAN028_NATIVE_X86_PHASE_OBSERVATION_AND_128_REAL_UDP_CPU_P99_PASS',
     'M0_PLAN028_NATIVE_ARM64_PHASE_OBSERVATION_AND_128_REAL_UDP_CPU_P99_PASS'),
    ('plan028-x86-','plan028-arm64-'),
):
    if before not in s:
        raise RuntimeError("frozen x86 phase fixture changed: " + before)
    s=s.replace(before,after)
out.write_text(s)
out.chmod(0o700)
print("M0_PLAN028_H1130_ARM64_NATIVE_PHASE_FIXTURE_FROM_SAME_VERIFIED_GENERATOR_READY")
