#!/usr/bin/env python3
"""Read-only baseline: one exact historical Android16 ARM64 AVD; no exploit."""
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import traceback
import zipfile

ROOT = pathlib.Path(os.environ["GITHUB_WORKSPACE"])
OUT = ROOT / "out" / "dirtyfrag-api36"
OUT.mkdir(parents=True, exist_ok=True)
SDK = pathlib.Path(os.environ.get("ANDROID_HOME") or (pathlib.Path.home() / "Library/Android/sdk"))
RUNNER_TEMP = pathlib.Path(os.environ.get("RUNNER_TEMP") or "/tmp")
AVD_HOME = RUNNER_TEMP / "wbd-dirtyfrag-old-avd-home"
ARCHIVE = RUNNER_TEMP / "android16-arm64-r07.zip"
IMAGE = SDK / "system-images/android-36/google_apis_playstore/arm64-v8a"
EMULATOR = SDK / "emulator/emulator"
ADB = SDK / "platform-tools/adb"
SDKMANAGER = SDK / "cmdline-tools/latest/bin/sdkmanager"
AVDMANAGER = SDK / "cmdline-tools/latest/bin/avdmanager"
URL = "https://dl.google.com/android/repository/sys-img/google_apis_playstore/arm64-v8a-36_r07.zip"
EXPECTED_SHA1 = "5b91ef80a5eb60d7b7167528db259c2a12d20e9c"
EXPECTED_SIZE = 1886527965
SOURCE = os.getenv("GITHUB_SHA", "LOCAL")
D = {
    "schema": "android16-dirtyfrag-old-avd-unrooted-baseline/v1",
    "source": SOURCE,
    "execution_path": "adb-shell (read only)",
    "image_archive": URL,
    "image_catalog_sha1": EXPECTED_SHA1,
    "image_size_expected": EXPECTED_SIZE,
    "image_sdk_snapshot_source": "7c23968450618e94727e190d3a2ad3cf8f24adf7",
    "image_sdk_snapshot_date": "2025-12-02",
    "image_revision_expected": "7",
    "guest_booted": False,
    "dirtyfrag_executed": False,
    "dirtyfrag_app_to_su": "NOT_RUN",
    "post_root_wbd": "NOT_RUN",
    "status": "ENV_BLOCKED",
}
def save():
    D["measured_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT / "summary.json").write_text(json.dumps(D, ensure_ascii=False, indent=2, sort_keys=True)+"\n")
def cmd(argv, timeout=40, log=None, env=None):
    try:
        p = subprocess.run([str(v) for v in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, text=True, errors="replace", env=env)
        output = p.stdout or ""
        if log:
            (OUT / log).write_text(output[-12000:])
        return p.returncode, output.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        if log:
            (OUT / log).write_text(repr(e))
        return 124, repr(e)
def stop(reason, status="ENV_BLOCKED"):
    D.update(reason=reason, status=status)
    print(status, reason, flush=True)
    save()
    return
def getprop(k, env):
    return cmd([ADB, "shell", "getprop", k], 14, env=env)[1].strip()
def shell(command, env):
    return cmd([ADB, "shell", command], 15, env=env)[1].strip()
def hash_file(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()
def main():
    if not SDKMANAGER.is_file() or not AVDMANAGER.is_file():
        return stop("SDK_MANAGER_OR_AVD_MANAGER_MISSING")
    ret, _ = cmd([SDKMANAGER, "--install", "emulator", "platform-tools"], 220, "sdk-tools-install.log")
    if ret:
        return stop("SDK_TOOLS_INSTALL_FAILED")
    if not EMULATOR.is_file() or not ADB.is_file():
        return stop("EMULATOR_OR_ADB_MISSING")
    ret, check = cmd([EMULATOR, "-accel-check"], 30, "accel.txt")
    if ret:
        return stop("ARM64_HVF_UNAVAILABLE")
    D["host_arch"] = os.uname().machine
    D["emulator_accel_check"] = check[-1000:]
    ret, _ = cmd(["curl", "-fsSL", "--retry", "1", "--connect-timeout", "25",
                  "--max-time", "570", URL, "-o", ARCHIVE], 585, "image-download.log")
    if ret:
        return stop("HISTORICAL_ARCHIVE_UNAVAILABLE")
    actual_size = ARCHIVE.stat().st_size
    D["image_size_actual"] = actual_size
    if actual_size != EXPECTED_SIZE:
        return stop("HISTORICAL_ARCHIVE_SIZE_MISMATCH", "FAIL")
    D["image_sha1_actual"] = hash_file(ARCHIVE, "sha1")
    if D["image_sha1_actual"] != EXPECTED_SHA1:
        return stop("HISTORICAL_ARCHIVE_SHA1_MISMATCH", "FAIL")
    D["image_sha256"] = hash_file(ARCHIVE, "sha256")
    D["image_hash_verified"] = True
    (OUT / "archive.sha256").write_text(D["image_sha256"]+"  android16-arm64-r07.zip\n")
    # The SDK ZIP has its own top-level ABI directory. Inspect rather than
    # extracting the ABI folder inside another copy of itself.
    with zipfile.ZipFile(ARCHIVE) as z:
        entries = z.namelist()
        (OUT / "archive-entries.txt").write_text("\n".join(entries[:100])+"\n")
        found = [name for name in entries if name.endswith("source.properties")]
        if len(found) != 1:
            return stop("ARCHIVE_LAYOUT_NO_UNIQUE_SOURCE_PROPERTIES")
        prefix = found[0][:-len("source.properties")]
        if prefix not in ("arm64-v8a/", ""):
            return stop("ARCHIVE_LAYOUT_UNEXPECTED_PREFIX_"+repr(prefix))
        unpack_root = IMAGE.parent if prefix else IMAGE
    unpack_root.mkdir(parents=True, exist_ok=True)
    ret, _ = cmd(["unzip", "-q", ARCHIVE, "-d", unpack_root], 180, "unzip.log")
    if ret:
        return stop("IMAGE_UNZIP_FAILED")
    # Delete owned 1.9GB archive only after exact digest/size record.
    ARCHIVE.unlink()
    props = IMAGE / "source.properties"
    if not props.is_file():
        return stop("HISTORICAL_SOURCE_PROPERTIES_MISSING")
    sp = props.read_text(errors="replace")
    D["source_properties"] = sp[:1800]
    if not re.search(r"^Pkg\.Revision\s*=\s*7(?:\s|$)", sp, re.MULTILINE):
        return stop("HISTORICAL_IMAGE_REVISION_MISMATCH")
    AVD_HOME.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ANDROID_AVD_HOME=str(AVD_HOME))
    ret, _ = cmd([AVDMANAGER, "create", "avd", "-n", "wbd_dirtyfrag36",
                  "-k", "system-images;android-36;google_apis_playstore;arm64-v8a",
                  "-p", AVD_HOME / "wbd_dirtyfrag36.avd", "--force"],
                 75, "avd-create.log", env=env)
    if ret:
        return stop("HISTORICAL_IMAGE_NOT_REGISTERED_AS_AVD")
    ret, listing = cmd([EMULATOR, "-list-avds"], 20, "avd-list.log", env=env)
    if ret or "wbd_dirtyfrag36" not in listing.splitlines():
        return stop("AVD_NOT_REGISTERED")
    p = None
    try:
        with open(OUT / "emulator.log", "w") as outlog:
            p = subprocess.Popen([str(EMULATOR), "-avd", "wbd_dirtyfrag36",
                  "-no-window", "-no-audio", "-no-boot-anim", "-no-snapshot",
                  "-wipe-data", "-gpu", "swiftshader_indirect",
                  "-accel", "on", "-memory", "3072"],
                  stdout=outlog, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            D["emulator_pid"] = p.pid
            deadline = time.monotonic() + 300
            booted = False
            while time.monotonic() < deadline:
                if p.poll() is not None:
                    D["reason"] = "EMULATOR_EXITED_EARLY"
                    break
                code, _ = cmd([ADB, "get-state"], 10, env=env)
                if code == 0 and getprop("sys.boot_completed", env) == "1":
                    booted = True
                    break
                time.sleep(3)
            if not booted:
                return stop(D.get("reason", "GUEST_BOOT_TIMEOUT_300S"))
            D["guest_booted"] = True
            for key, prop in {
                "release":"ro.build.version.release", "api":"ro.build.version.sdk",
                "security_patch":"ro.build.version.security_patch",
                "fingerprint":"ro.build.fingerprint", "build_type":"ro.build.type",
                "debuggable":"ro.debuggable", "abi":"ro.product.cpu.abi"
            }.items():
                D[key] = getprop(prop, env)
            for key, command in {
                "kernel":"uname -r", "page_size":"getconf PAGESIZE",
                "selinux":"getenforce", "shell_id_before":"id",
                "shell_uid_before":"id -u", "su_path":"command -v su || true",
                "vendor_insmod":"ls -l /vendor/bin/insmod 2>&1",
                "vendor_module_target":"ls -l /vendor/lib64/libbinderdebug.so 2>&1",
                "crash_dump64":"ls -l /system/bin/crash_dump64 2>&1"
            }.items():
                D[key] = shell(command, env)
            rc, rootmsg = cmd([ADB, "root"], 32, "adb-root-attempt.txt", env=env)
            D["adb_root_rc"] = rc
            D["adb_root_response"] = rootmsg[-600:]
            D["shell_uid_after_adb_root"] = shell("id -u", env)
            k = re.match(r"^(\d+)\.(\d+)", D["kernel"])
            kernel_ge6 = bool(k and int(k.group(1)) >= 6)
            correct = (D["release"] == "16" and D["api"] == "36" and
                       D["abi"] == "arm64-v8a" and kernel_ge6 and
                       D["security_patch"] and D["security_patch"] < "2026-04-01")
            no_root = (D["build_type"] == "user" and D["debuggable"] == "0" and
                       D["shell_uid_before"] != "0" and
                       D["shell_uid_after_adb_root"] != "0")
            D["kernel_ge6"] = kernel_ge6
            D["unrooted_baseline"] = bool(no_root)
            D["status"] = "SUPPORTED_IN_SCOPE" if correct and no_root else "ENV_BLOCKED"
            D["reason"] = ("OLD_API36_ARM64_UNROOTED_BASELINE" if correct and no_root
                           else "GUEST_DOES_NOT_MATCH_REQUIRED_UNROOTED_API36")
            save()
    finally:
        if p is not None:
            cmd([ADB, "emu", "kill"], 15, env=env)
            try:
                p.terminate()
                p.wait(timeout=9)
            except subprocess.TimeoutExpired:
                p.kill()
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired: pass
            D["cleanup"] = ("EMULATOR_EXITED" if p.poll() is not None else "EMULATOR_UNREAPABLE")
        else:
            D["cleanup"] = "NO_GUEST"
        save()
        print(json.dumps({k:D.get(k) for k in (
            "source","status","reason","guest_booted","release","api","abi",
            "kernel","security_patch","build_type","shell_uid_before",
            "shell_uid_after_adb_root","dirtyfrag_app_to_su","cleanup")}, indent=2))
    if D.get("cleanup") == "EMULATOR_UNREAPABLE":
        raise SystemExit("emulator cleanup unreapable")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        D.update(status="FAIL",reason="FIXTURE_EXCEPTION",exception=traceback.format_exc()[-3000:])
        save()
        raise
