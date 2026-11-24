#!/usr/bin/env python3
"""Test-only Go 1.23.12 Android/arm64 NativeBridge MIDR fault isolation.

Do NOT modify the hosted Go installation, donor sources, or the production
Root APK. Copy pinned Go GOROOT, then alter one Android-only internal/cpu
condition in the test toolchain. This is a diagnostic of NativeBridge's
HWCAP_CPUID / unimplemented MRS MIDR_EL1, not an Android production patch.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path(os.environ["GITHUB_WORKSPACE"])
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == os.environ["GITHUB_SHA"]
goversion = subprocess.check_output(["go", "version"], text=True).strip()
assert goversion.startswith("go version go1.23.12 "), goversion
oldroot = Path(subprocess.check_output(["go", "env", "GOROOT"], text=True).strip())
target = root / "out/nativebridge-go-patched-goroot"
assert not target.exists(), "refuse reusing patched GOROOT from another generation"
original = oldroot / "src/internal/cpu/cpu_arm64_hwcap.go"
data = original.read_text()
needle = "if ARM64.HasCPUID {\n\t\tmidr := getMIDR()"
replace = 'if ARM64.HasCPUID && os != "android" {\n\t\tmidr := getMIDR()'
assert data.count(needle) == 1, "Go1.23.12 internal/cpu source differs: fail closed"
assert "hwcapInit(os string)" in data and "getMIDR()" in data
shutil.copytree(oldroot, target, symlinks=True)
dest = target / "src/internal/cpu/cpu_arm64_hwcap.go"
assert dest.read_text() == data
dest.write_text(data.replace(needle, replace, 1))
patched = dest.read_text()
assert patched.count(replace) == 1
assert data.replace(needle, replace, 1) == patched
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
receipt = {
  "schema": "wbd-ksu-go123-android-arm64-midrel1-isolate/v1",
  "source": os.environ["GITHUB_SHA"],
  "go_version": goversion,
  "original_cpu_sha256": sha(data),
  "test_only_cpu_sha256": sha(patched),
  "test_only_change": "only on Android skip MIDR_EL1 probe; ARM64 Go standard TLS/auth/product binary UNCHANGED",
  "original_arm64_product_go": "UNCHANGED",
  "arm64_ksu_nativebridge_runtime": "NOT_RUN"
}
out = root / "out/android-product-a1"
out.mkdir(parents=True, exist_ok=True)
(out / "ksu-go-midrel1-isolation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print("TEST_ONLY_GO_ARM64_MIDR_PROBE_TOOLCHAIN_ISOLATED", goversion)
