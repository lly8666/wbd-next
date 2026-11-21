#!/usr/bin/env bash
# The SAME one API36 KSU App AV D after original appflow/mainstream/SIGKILL.
# Tether NAT only in CLONE_NEWNET; restore uses explicit actual App UI click.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
o=out/tether-recovery
mkdir -p "$o"
test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
(cd out/native && sha256sum -c SHA256SUMS) >"$o/native-hashes.txt"
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36
test "$(adb shell getprop ro.kernel.qemu | tr -d '\r')" = 1
test "$(adb shell getenforce | tr -d '\r')" = Enforcing
uid="$(python3 - <<'PY'
import json
v=json.load(open("out/appflow/summary.json"))
assert v["status"]=="APP_UID_TUN_ROUNDTRIP_PASS"
assert 10000<=v["app_uid"]<=199999
print(v["app_uid"])
PY
)"
echo "$uid" >"$o/app-uid.txt"
native=/data/local/tmp/wbd-app-native
adb push out/native/bin/probe-x86_64-linux-android "$native" >"$o/native-stage.txt"
adb shell chmod 0755 "$native"
trap 'adb shell rm -f /data/local/tmp/wbd-app-native >/dev/null 2>&1 || true' EXIT
adb shell su -c 'ip -4 rule show' >"$o/global-rule-before.txt"
adb shell su -c 'ip -4 route show table all' >"$o/global-route-before.txt"
adb shell su -c 'ip -4 route show table 235' >"$o/table235-before.txt"
test ! -s "$o/table235-before.txt" || { echo "table235 collision";exit 1;}
# Actual root in a real KSU emulator, yet all synthetic tethering changes
# happen strictly inside a distinct empty network namespace.
set +e
timeout --signal=TERM --kill-after=4s 28s adb shell su -c "$native tethergate" >"$o/tether.stdout" 2>"$o/tether.stderr"
tether_rc=$?
set -e
echo "$tether_rc" >"$o/tether-exit.txt"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("out/tether-recovery")
x=(p/"tether.stdout").read_text()
k="WBD_TETHER_RESULT "
assert k in x,"no native tethergate evidence"
v=json.loads(x[x.index(k)+len(k):].splitlines()[0])
(p/"tether.json").write_text(json.dumps(v,indent=2)+"\n")
assert v["global_changes"] is False,"must prove no global changes"
assert v["status"] in ("SUPPORTED_IN_SCOPE","UNAVAILABLE","ENV_BLOCKED")
if v["status"]=="SUPPORTED_IN_SCOPE":
    e=v["evidence"]
    assert e["client_count"]==3 and e["owned_tun_gone"]
    assert all(v["snat_pass"] and v["conntrack_reverse_pass"] for v in e["synthetic_clients"])
print("tether mode",v["status"])
PY
adb shell su -c 'ip -4 rule show' >"$o/global-rule-after-tether.txt"
adb shell su -c 'ip -4 route show table all' >"$o/global-route-after-tether.txt"
cmp "$o/global-rule-before.txt" "$o/global-rule-after-tether.txt"
cmp "$o/global-route-before.txt" "$o/global-route-after-tether.txt"
# Seed exactly the old legacy WBD /32 rule as if a crashed worker left it.
# No broad routing / DNS / Android tether setup is modified.
adb shell su -c "$native recover-seed $uid" >"$o/seed.stdout" 2>"$o/seed.stderr"
grep -q 'FIXTURE_SEEDED' "$o/seed.stdout"
python3 experiments/android-root-probe/ci/tether-recovery-ui.py FIRST RESTORED
python3 experiments/android-root-probe/ci/tether-recovery-ui.py SECOND ALREADY_CLEAN
adb shell su -c 'ip -4 rule show' >"$o/global-rule-final.txt"
adb shell su -c 'ip -4 route show table all' >"$o/global-route-final.txt"
adb shell su -c 'ip -4 route show table 235' >"$o/table235-final.txt"
cmp "$o/global-rule-before.txt" "$o/global-rule-final.txt"
cmp "$o/global-route-before.txt" "$o/global-route-final.txt"
test ! -s "$o/table235-final.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/tether-recovery")
t=json.loads((p/"tether.json").read_text())
first=json.loads((p/"button-FIRST.json").read_text())
second=json.loads((p/"button-SECOND.json").read_text())
errors=[]
if first["status"]!="RESTORED":errors.append("first App button did not remove orphan")
if second["status"]!="ALREADY_CLEAN":errors.append("second App button not idempotent")
if first["app_uid"]!=second["app_uid"]:errors.append("changed app UID")
if (p/"global-rule-before.txt").read_text()!=(p/"global-rule-final.txt").read_text():
    errors.append("global Android rule snapshot differs")
if (p/"global-route-before.txt").read_text()!=(p/"global-route-final.txt").read_text():
    errors.append("global Android route snapshot differs")
status="FAIL" if errors else "SYNTHETIC_TETHER_NAT_AND_RECOVERY_PASS" if t["status"]=="SUPPORTED_IN_SCOPE" else "RECOVERY_PASS_TETHER_UNAVAILABLE"
data={"schema":"android-temp-root-tether-recovery-case/v1",
 "source":os.environ["GITHUB_SHA"],"api":36,
 "status":status,"root":"real KernelSU3.3.1 App->su authorized",
 "app_uid":first["app_uid"],
 "tether_private_netns":t["status"],"synthetic_nat_clients":(t.get("evidence") or {}).get("synthetic_clients"),
 "manual_app_restore_first":first["status"],"manual_app_restore_second":second["status"],
 "global_rule_route_unchanged":not errors,
 "real_wifi_hotspot":"NOT_RUN","real_usb_tether":"NOT_RUN",
 "ebpf_hardware_offload":"NOT_RUN","physical_clat":"NOT_RUN",
 "errors":errors}
(p/"summary.json").write_text(json.dumps(data,indent=2)+"\n")
print(json.dumps(data,indent=2))
if errors:raise SystemExit("recovery or global routing modified unexpectedly")
PY
