#!/usr/bin/env python3
"""One-shot scoped outer native WSL2 execution watchdog.

Never a product test, PASS or timeout policy for normal user traffic.
If the owning PowerShell test step is still alive after bounded wall time,
force-terminate its Windows process tree. This protects against wsl.exe,
PowerShell cleanup and nested process hangs that Python mode timeouts cannot
interrupt. A sentinel created by the step disables the guard on normal exit.
"""
import os
import pathlib
import subprocess
import sys
import time

if len(sys.argv)!=4:
    raise SystemExit("usage: watchdog.py <owning-win-pid> <seconds> <done-marker>")
pid=int(sys.argv[1])
seconds=int(sys.argv[2])
sentinel=pathlib.Path(sys.argv[3])
assert 30<=seconds<=1500 and pid>4
deadline=time.monotonic()+seconds
while time.monotonic()<deadline:
    if sentinel.exists():
        print("WL_WSL2_OUTER_WATCHDOG_DISARMED owner_pid="+str(pid),flush=True)
        sys.exit(0)
    time.sleep(1)
if sentinel.exists():
    sys.exit(0)
print("WL_WSL2_OUTER_WATCHDOG_KILL reason=whole_native_step_deadline owner_pid="+str(pid)+" seconds="+str(seconds),file=sys.stderr,flush=True)
try:
    subprocess.run(["taskkill.exe","/PID",str(pid),"/T","/F"],
                   timeout=18,check=False,capture_output=True)
except (OSError,subprocess.TimeoutExpired) as exc:
    print("WL_WSL2_OUTER_WATCHDOG_TASKKILL_ERROR "+type(exc).__name__,file=sys.stderr,flush=True)
sys.exit(124)
