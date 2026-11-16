#!/usr/bin/env bash
# Owned reduced-capability matrix, no routing/NAT mutations. Explicit emulator-only exercise.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/case
o=out/case
cp out/build/{SOURCE,manifest.json,SHA256SUMS} "$o/"
adb shell getprop ro.build.version.sdk >"$o/api.txt"
adb shell getprop ro.build.version.release >"$o/release.txt"
adb shell getprop ro.build.version.incremental >"$o/revision.txt"
adb shell getprop ro.product.cpu.abi >"$o/abi.txt"
adb shell getenforce >"$o/selinux-enforce.txt"
adb shell id >"$o/adb-shell-id.txt"
adb shell 'command -v su || true' >"$o/su-path.txt" || true
adb push out/build/bin/probe-x86_64-linux-android /data/local/tmp/android-root-probe >"$o/push.txt"
trap 'adb shell rm -f /data/local/tmp/android-root-probe >/dev/null 2>&1 || true' EXIT
adb shell chmod 0700 /data/local/tmp/android-root-probe
timeout --signal=TERM --kill-after=3s 20s adb shell /data/local/tmp/android-root-probe inspect >"$o/shell-inspect.json"
timeout --signal=TERM --kill-after=5s 30s adb root >"$o/adb-root.txt" 2>&1
adb wait-for-device
adb shell id >"$o/adb-root-id.txt"
adb shell getenforce >"$o/selinux-after-root.txt"
timeout 4s adb shell ip -4 rule show >"$o/ip-rule-readonly.txt" 2>"$o/ip-rule-readonly.err" || true
timeout 4s adb shell iptables -t nat -S >"$o/iptables-nat-readonly.txt" 2>"$o/iptables-nat-readonly.err" || true
timeout 4s adb shell cat /proc/sys/net/ipv4/ip_forward >"$o/ipv4-forward-readonly.txt" 2>"$o/ipv4-forward-readonly.err" || true
if [[ "$(adb shell id -u | tr -d '\r')" != "0" ]]; then
  printf '{"status":"ENV_BLOCKED","reason":"adb-root did not yield UID0"}\n' >"$o/summary.json"
  exit 3
fi
for profile in none netadmin netraw both; do
  for op in tun raw; do
    set +e
    timeout --signal=TERM --kill-after=3s 12s adb shell "/data/local/tmp/android-root-probe capgate $profile $op" >"$o/$profile-$op.json" 2>"$o/$profile-$op.err"
    rc=$?
    set -e
    printf '%s\n' "$rc" >"$o/$profile-$op.exit"
  done
done
python3 - <<'PY'
import json, os
from pathlib import Path
o=Path("out/case")
get=lambda n:(o/n).read_text().strip()
expected={"none":{"tun":"PERMISSION_DENIED","raw":"PERMISSION_DENIED"},
          "netadmin":{"tun":"SUPPORTED_IN_SCOPE","raw":"PERMISSION_DENIED"},
          "netraw":{"tun":"PERMISSION_DENIED","raw":"SUPPORTED_IN_SCOPE"},
          "both":{"tun":"SUPPORTED_IN_SCOPE","raw":"SUPPORTED_IN_SCOPE"}}
m=json.loads(Path("out/build/manifest.json").read_text())
summary={"schema":"android-root-capgate-case/v1","source":get("SOURCE"),
         "api_expected":os.environ["ANDROID_PROBE_API"],"api_observed":get("api.txt"),
         "release":get("release.txt"),"image_revision":get("revision.txt"),
         "abi":get("abi.txt"),"selinux":get("selinux-after-root.txt"),
         "execution_path":"adb-root","app_to_su":"NOT_RUN",
         "routing_fwmark_nat":"READ_ONLY_INVENTORY_ONLY","tether_wifi_usb":"NOT_RUN",
         "expectations":expected,"cases":{},"mismatches":[]}
errors=summary["mismatches"]
if summary["source"]!=os.environ["GITHUB_SHA"] or m["source"]!=summary["source"]: errors.append("SOURCE mismatch")
if m["min_sdk"]!=28: errors.append("minSdk manifest mismatch")
if summary["api_observed"]!=summary["api_expected"]: errors.append("API mismatch")
if summary["selinux"]!="Enforcing": errors.append("SELinux not Enforcing")
for profile,ops in expected.items():
    for op,expect in ops.items():
        key=f"{profile}-{op}"
        try: record=json.loads(get(key+".json"))
        except Exception as e:
            errors.append(f"{key}: unreadable JSON: {e}")
            continue
        check=record.get("check",{})
        seen=check.get("status")
        summary["cases"][key]={"observed":seen,"expected":expect,"exit":get(key+".exit"),
            "caps_effective":record.get("caps_after",{}).get("CapEff"),
            "capset_verified":record.get("status")=="CAPSET_VERIFIED",
            "no_new_privs":record.get("no_new_privs"),"cleanup":check.get("cleanup"),
            "raw_observed_syn":check.get("evidence",{}).get("observed_syn") if isinstance(check.get("evidence"),dict) else None,
            "raw_observed_rst":check.get("evidence",{}).get("observed_rst") if isinstance(check.get("evidence"),dict) else None}
        actual_cap={"none":"0000000000000000","netadmin":"0000000000001000",
                    "netraw":"0000000000002000","both":"0000000000003000"}[profile]
        if record.get("status")!="CAPSET_VERIFIED" or record.get("caps_after",{}).get("CapEff")!=actual_cap:
            errors.append(f"{key}: capability drop unverified")
        if seen!=expect: errors.append(f"{key}: {seen} != {expect}")
        if get(key+".exit")!="0": errors.append(f"{key}: command exit nonzero")
        if op=="tun" and seen=="SUPPORTED_IN_SCOPE" and check.get("cleanup")!="interface gone after close":
            errors.append(f"{key}: owned TUN cleanup mismatch")
        if op=="raw" and seen=="SUPPORTED_IN_SCOPE":
            ev=check.get("evidence",{})
            if not ev.get("observed_syn") or not ev.get("observed_rst"):
                errors.append(f"{key}: missing real loopback SYN/RST")
summary["status"]="FUNCTIONAL_PASS" if not errors else "FAIL"
(o/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary,indent=2,sort_keys=True))
if errors: raise SystemExit("reduced-capability matrix failed: see evidence")
PY
