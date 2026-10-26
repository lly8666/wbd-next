#!/usr/bin/env python3
"""Bounded real WSL2 guest/kernel preflight; never substitutes for the native product."""
import json
import os
import pathlib
import subprocess
import sys
import time

root = pathlib.Path("result/wl-public")
root.mkdir(parents=True, exist_ok=True)
args = [
    "wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "sh", "-c",
    'test -c /dev/net/tun && command -v ip && command -v openssl && command -v python3 && test "$(uname -s)" = Linux',
]
start = time.monotonic()
receipt = {
    "phase": "real_wsl2_guest_kernel_preflight",
    "harness_source": os.environ.get("GITHUB_SHA"),
    "linux_binary_source": os.environ.get("LINUX_BINARY_SRC"),
    "product": "NOT_RUN",
}
try:
    process = subprocess.run(args, capture_output=True, text=True, timeout=90, check=False)
    receipt["exit_code"] = process.returncode
    receipt["stdout_tail"] = process.stdout[-160:]
    receipt["stderr_tail"] = process.stderr[-160:]
    if process.returncode != 0:
        receipt["result"] = "ENVIRONMENT_BLOCKED_NATIVE_PREREQUISITE"
    else:
        receipt["result"] = "PASS_GENUINE_WSL2_GUEST_PRECONDITION_ONLY"
except subprocess.TimeoutExpired:
    receipt["result"] = "ENVIRONMENT_BLOCKED_NATIVE_WSL2_BOOT_TIMEOUT"
finally:
    receipt["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    (root / "wsl2-real-guest-probe.json").write_text(json.dumps(receipt, indent=2) + "\n")
if receipt["result"] != "PASS_GENUINE_WSL2_GUEST_PRECONDITION_ONLY":
    print("WL_REAL_WSL2_GUEST_BOOT_ENVIRONMENT_BLOCKED " + json.dumps(receipt), file=sys.stderr, flush=True)
    sys.exit(1)
print("WL_REAL_WSL2_GUEST_KERNEL_TUN_BOOT_PASS_PRECONDITION_ONLY", flush=True)
