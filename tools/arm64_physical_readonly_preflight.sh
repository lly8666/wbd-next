#!/usr/bin/env bash
# Read-only Linux ARM64 physical-host preflight. Does not bring up TUN,
# install anything, read credential bytes, alter kernel routes or execute VPN.
set -euo pipefail
bundle="${1:-${WBD_ARM64_BUNDLE:-$PWD/arm64-public-bundle}}"
if [ ! -d "$bundle" ]; then echo 'BLOCKED: ARM64 bundle directory not found' >&2; exit 2; fi
bundle="$(cd "$bundle" && pwd -P)"
test "$(uname -s)" = Linux || { echo 'BLOCKED: not Linux' >&2; exit 2; }
test "$(uname -m)" = aarch64 || { echo 'BLOCKED: not native AArch64' >&2; exit 2; }
for cmd in sha256sum ip python3 readelf; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: missing read-only tool $cmd" >&2; exit 2; }
done
for name in wbd-v4-client wbd-v4-server libwbd_engine.so manifest.json SHA256SUMS; do
  test -s "$bundle/$name" || { echo "BLOCKED: missing $name" >&2; exit 2; }
done
(cd "$bundle" && sha256sum -c SHA256SUMS)
for name in wbd-v4-client wbd-v4-server libwbd_engine.so; do
  readelf -h "$bundle/$name" | grep -Eq 'Machine:.*AArch64' || {
    echo "BLOCKED: $name not AArch64 ELF" >&2; exit 2;
  }
done
test -c /dev/net/tun || { echo 'BLOCKED: /dev/net/tun missing' >&2; exit 2; }
BUNDLE="$bundle" python3 - <<'PY'
import json,os,pathlib,hashlib,platform
p=pathlib.Path(os.environ["BUNDLE"])
m=json.loads((p/"manifest.json").read_text())
assert m.get("architecture")=="aarch64"
assert m.get("source") and m.get("go_source") and m.get("backend_requested")
for n in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
    assert (p/n).is_file()
print("ARM64_PHYSICAL_READ_ONLY_PREFLIGHT_PASS")
print("frozen_binary_source="+m["source"])
print("original_go_source="+m["go_source"])
print("acceleration_variant="+m["backend_requested"])
print("host_arch="+platform.machine())
print("manifest_sha256="+hashlib.sha256((p/"manifest.json").read_bytes()).hexdigest())
print("critical_instructions: copy SAME bundle to BOTH hosts, no secrets or root network mutation in preflight")
PY
# Actual carrier/raw privileges, reachability and trust remain for separate
# explicitly authorized physical trial. Never infer these from preflight.
