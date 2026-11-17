#!/usr/bin/env python3
"""Operator-controlled Android16 ARM64 Root acceptance, without device mutation.

The script reads only public device properties, owned private route rules and
fixed WBD_ROOT_DIAG event codes. The operator performs Start/Stop in the real
signed APK. Only explicit --install permits adb install -r; no su, ip rule
changes, kill, unlink, private secret reads, or raw logcat artifact.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
import zipfile
from pathlib import Path

PKG = "org.wbdnext.rootclient"
ACTIVITY = PKG + "/.RootClientActivity"
EVENTS = frozenset("""
START_REQUESTED NETWORK_SCOPE_VERIFIED APP_UID_GROUP_VERIFIED
ROOT_STAGE_REQUESTED NATIVE_SOURCE_VERIFIED ROOT_GRANT_REQUESTED
ROOT_PROCESS_LAUNCHED NATIVE_M4_RECEIPT UID_ROUTE_RECEIPT
NATIVE_M4_AND_UID_READY ROOT_PROCESS_EXIT_ZERO ROOT_PROCESS_EXIT_NONZERO
ROOT_LAUNCH_FAILED START_REFUSED STOP_REQUESTED STOP_SIGNAL_STARTED
STOP_SIGNAL_ACCEPTED STOP_SIGNAL_REFUSED STOP_SIGNAL_ERROR
OWNER_CLEANUP_FINISHED
""".split())
EVENT_RE = re.compile(r"\bWBD_ROOT_DIAG\s*:\s*([A-Z0-9_]+)\b")


def verify_elf(data):
    if len(data) < 64 or data[:5] != b"\x7fELF\x02":
        return False
    if struct.unpack_from("<H", data, 18)[0] != 183:
        return False
    pos = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    if size < 56 or count < 1 or pos + size * count > len(data):
        return False
    align = [struct.unpack_from("<Q", data, pos + size * i + 48)[0]
             for i in range(count)
             if struct.unpack_from("<I", data, pos + size * i)[0] == 1]
    return bool(align) and min(align) >= 16384


def inspect_apk(path):
    """Only ZIP/ELF/SOURCE integrity; signature verification belongs to CI."""
    with zipfile.ZipFile(path) as archive:
        prefix = "assets/native-arm64/"
        entries = archive.namelist()
        if any("x86" in x.lower() or "cshared-midr" in x
               for x in entries):
            raise ValueError("foreign architecture or test library in APK")
        source = archive.read(prefix + "SOURCE").decode("ascii").strip()
        meta = json.loads(archive.read(prefix + "manifest.json"))
        if not re.fullmatch(r"[a-f0-9]{40}", source):
            raise ValueError("invalid source SHA")
        if meta.get("source") != source:
            raise ValueError("APK native source mismatch")
        for name in ("wbd-v4-client-arm64", "libwbd_engine-arm64.so"):
            data = archive.read(prefix + name)
            if hashlib.sha256(data).hexdigest() != meta["artifacts"][name]["sha256"]:
                raise ValueError("signed-archive asset hash mismatch")
            if not verify_elf(data):
                raise ValueError("not an AArch64 16KiB aligned ELF")
        return {"source": source,
                "apk_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "same_source_arm64_16k_assets": "PASS",
                "apk_signature_verified_here": "NOT_RUN"}


def parse_devices(text):
    return [p[0] for line in text.splitlines()
            if (p := line.split()) and len(p) >= 2 and p[1] == "device"]


def parse_events(text):
    # No raw log lines or values enter the resulting ZIP.
    return [x for x in EVENT_RE.findall(text) if x in EVENTS]


def owned_rules(text):
    # Never export UID ranges, application addresses or complete route text.
    result = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+):\s+(.*)$", line)
        if not m:
            continue
        pref, rule = int(m.group(1)), m.group(2)
        if 9600 <= pref <= 9607 or re.search(r"(?:lookup|table)\s+19842(?:\s|$)", rule):
            result.append({"priority": pref,
                           "sha256": hashlib.sha256(line.strip().encode()).hexdigest()})
    return sorted(result, key=lambda r: (r["priority"], r["sha256"]))


def new_events(earlier, later):
    # Match suffix/prefix when logcat retains a known window. If the ring
    # rotated in a way we cannot authenticate, fail closed rather than forge.
    for n in range(min(len(earlier), len(later)), 0, -1):
        if earlier[-n:] == later[:n]:
            return later[n:]
    return later if not earlier else []


def command(argv, timeout=20):
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           errors="replace", timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, OSError) as e:
        return 124, "", type(e).__name__


class Device:
    def __init__(self, binary, serial):
        self.binary, self.serial = binary, serial

    def adb(self, *args, timeout=20):
        return command([self.binary, "-s", self.serial, *args], timeout=timeout)

    def shell(self, *args):
        return self.adb("shell", *args)

    def prop(self, key):
        rc, out, _ = self.shell("getprop", key)
        return out.strip() if rc == 0 else ""

    def events(self):
        rc, out, _ = self.adb("logcat", "-d", "-t", "1800",
                              "WBD_ROOT_DIAG:I", "*:S")
        return parse_events(out) if rc == 0 else []

    def route_rules(self):
        rc, out, _ = self.shell("ip", "-4", "rule", "show")
        return owned_rules(out) if rc == 0 else None


def preflight(device, apk):
    rc, arch, _ = device.shell("uname", "-m")
    kernel = arch.strip() if rc == 0 else ""
    sdk = device.prop("ro.build.version.sdk")
    abilist = device.prop("ro.product.cpu.abilist")
    rc, package_paths, _ = device.shell("pm", "path", PKG)
    return {
        "kernel_arch": kernel,
        "advertised_abis": abilist,
        "android_api": sdk,
        "arm64_kernel": "PASS" if kernel in ("aarch64", "arm64") else "FAIL",
        "android16": "PASS" if sdk == "36" else "FAIL",
        "original_apk_installed": "PASS" if rc == 0 and
            any(x.startswith("package:") for x in package_paths.splitlines())
            else "FAIL",
        "local_offline_apk": apk,
    }


def summarize(baseline, mid, final, route_before, route_after, interactive):
    observed = set(new_events(baseline, mid) + new_events(mid, final))
    if route_before is None or route_after is None:
        rollback = "NOT_RUN"
    elif route_before or route_after:
        rollback = "FAIL"
    elif "STOP_REQUESTED" in observed and "OWNER_CLEANUP_FINISHED" in observed:
        rollback = "PASS"  # private rule check plus Java cleanup, NOT Rust joined Stop
    else:
        rollback = "NOT_RUN"
    return {
        "physical_network_selection": "PASS" if "NETWORK_SCOPE_VERIFIED" in observed else "NOT_RUN",
        "installed_app_uid_check": "PASS" if "APP_UID_GROUP_VERIFIED" in observed else "NOT_RUN",
        "original_m4_and_uid_receipt": "PASS" if "NATIVE_M4_AND_UID_READY" in observed else "NOT_RUN",
        "native_root_process_exit": "PASS" if "ROOT_PROCESS_EXIT_ZERO" in observed
            else "FAIL" if "ROOT_PROCESS_EXIT_NONZERO" in observed else "NOT_RUN",
        "owned_kernel_routes_after_stop": rollback,
        "original_go_rust_joined_stop": "NOT_RUN",
        "real_android_linux_tls_and_data_e2e": "NOT_RUN",
        "system_dns_resolver_and_tcp53": "NOT_RUN",
        "ordinary_app_kernel_su_grant": "NOT_RUN",
        "interactive_run": interactive,
        "allowlisted_events": sorted(observed),
    }


def write_bundle(dest, report):
    dest.mkdir(mode=0o700, parents=True, exist_ok=False)
    doc = dest / "acceptance.json"
    doc.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    doc.chmod(0o600)
    archive = dest / "acceptance-bundle.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(doc, "acceptance.json")
    archive.chmod(0o600)
    return archive


def execute(args):
    os.umask(0o077)
    rc, lines, _ = command([args.adb, "devices", "-l"])
    if rc != 0:
        print("ADB_UNAVAILABLE", file=sys.stderr)
        return 2
    serials = parse_devices(lines)
    if args.serial and args.serial not in serials:
        print("SELECTED_ADB_DEVICE_NOT_AUTHORIZED", file=sys.stderr)
        return 2
    if not args.serial and len(serials) != 1:
        print("USE_EXPLICIT_SERIAL_FOR_MULTIPLE_OR_NO_DEVICES", file=sys.stderr)
        return 2
    serial = args.serial or serials[0]
    d = Device(args.adb, serial)

    apk = {"same_source_arm64_16k_assets": "NOT_RUN"}
    if args.apk:
        try:
            apk = inspect_apk(args.apk)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
            print("APK_SOURCE_LOCK_INVALID: " + type(e).__name__, file=sys.stderr)
            return 2
    if args.install:
        # Fail BEFORE an opt-in installation on a translated x86 guest.
        # A NativeBridge arm64 ABI advertisement is NOT an ARM64 kernel.
        rc_arch, host_arch, _ = d.shell("uname", "-m")
        if (rc_arch or host_arch.strip() not in ("aarch64", "arm64") or
            d.prop("ro.build.version.sdk") != "36"):
            print("INSTALL_REFUSED_NON_ARM64_OR_NON_ANDROID16_KERNEL",
                  file=sys.stderr)
            return 3
        if not args.apk:
            print("EXPLICIT_INSTALL_NEEDS_APK", file=sys.stderr)
            return 2
        code, _, _ = d.adb("install", "-r", str(args.apk), timeout=90)
        if code:
            print("ADB_INSTALL_FAILED_NO_UNINSTALL_FALLBACK", file=sys.stderr)
            return 2
    state = preflight(d, apk)
    baseline = d.events()
    rules_before = d.route_rules()
    interactive = not args.collect_only
    folder = args.output or Path("out/device-acceptance") / dt.datetime.now(
        dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "schema": "wbd-root-arm64-device-first-run-v1",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "device_id_sha256_12": hashlib.sha256(serial.encode()).hexdigest()[:12],
        "environment": state,
        "owned_rules_before": rules_before,
        "commands_allowed": ["read_only_adb"] + (["opt_in_adb_install_r"] if args.install else []),
    }

    middle = baseline
    if interactive and (state["arm64_kernel"] != "PASS" or
                        state["android16"] != "PASS" or
                        state["original_apk_installed"] != "PASS" or
                        rules_before is None or bool(rules_before)):
        print("PRECHECK_FAILED_NO_APP_STARTED_OR_ROOT_CHANGES", file=sys.stderr)
        interactive = False
    if interactive:
        code, out, _ = d.shell("am", "start", "-n", ACTIVITY)
        if code or "Error" in out or "Exception" in out:
            print("APP_UI_FAILED_TO_START", file=sys.stderr)
            interactive = False
        else:
            report["commands_allowed"].append("launch_app_activity_only")
            print("In the signed Root APK, select Network/App/server, then Start.")
            print("The script NEVER enters credentials, invokes su or edits routes.")
            try:
                input("Press Enter after Start has attempted connection: ")
                middle = d.events()
                print("Now press Stop in the APK; do not terminate it with adb kill.")
                input("Press Enter after requesting Stop: ")
            except (EOFError, KeyboardInterrupt):
                report["user_interrupted"] = True
                print("USER_INTERRUPTED: press Stop in the original App")
    final_events = d.events()
    rules_after = d.route_rules()
    result = summarize(baseline, middle, final_events,
                       rules_before, rules_after, interactive)
    if interactive and not report.get("user_interrupted"):
        deadline = time.monotonic() + args.stop_wait_seconds
        while result["owned_kernel_routes_after_stop"] != "PASS" and time.monotonic() < deadline:
            time.sleep(1)
            final_events, rules_after = d.events(), d.route_rules()
            result = summarize(baseline, middle, final_events,
                               rules_before, rules_after, interactive)
    report["owned_rules_after"] = rules_after
    report["result"] = result
    bundle = write_bundle(folder, report)
    print("SANITIZED_DEVICE_ACCEPTANCE_BUNDLE", bundle)
    for key, value in result.items():
        if key != "allowlisted_events":
            print(key, value)
    if state["arm64_kernel"] != "PASS" or state["android16"] != "PASS":
        return 3
    if result["owned_kernel_routes_after_stop"] == "FAIL":
        return 4
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", default="adb")
    p.add_argument("--serial")
    p.add_argument("--apk", type=Path, help="local same-SOURCE ARM64 debug APK")
    p.add_argument("--install", action="store_true",
                   help="EXPLICITLY install/reinstall APK; no uninstall")
    p.add_argument("--collect-only", action="store_true",
                   help="read-only snapshot, no Activity launch")
    p.add_argument("--stop-wait-seconds", type=int, default=30)
    p.add_argument("--output", type=Path, help="new private output directory")
    a = p.parse_args()
    if not 0 <= a.stop_wait_seconds <= 90:
        p.error("--stop-wait-seconds must be 0..90")
    try:
        return execute(a)
    except FileExistsError:
        print("OUTPUT_ALREADY_EXISTS_REFUSING_OVERWRITE", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
