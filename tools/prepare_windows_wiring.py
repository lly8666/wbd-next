"""Shared exact-source Windows assembly for cheap compile and native full CI.

No driver installation or product execution. --check-only needs no legacy clone.
The full path uses the same assembler, pinned original Go and bridge file list
that m0-wl-public-normal-full.yml used before preflight/full separation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "a7a82db31fe736ffedee330795a3234d358f1984"
MANIFEST = "r0/go_overlay/assembly/manifest-plan020-m0.json"
EXTRA_BRIDGES = {
    "realityfront": (
        "admission_v4.go", "bridge_v4_windows_private_owner.go",
        "bridge_v4_windows_game_group.go", "bridge_v4_windows_game_server_group.go",
        "bridge_v4_windows_game_fec_batch.go", "bridge_v4_windows_game_group_test.go",
        "bridge_v4_windows_fec2_abi_status_test.go", "bridge_v4_windows_auto_cohort_test.go",
        "bridge_v4_windows_fec2_owner.go", "bridge_v4_windows_fixed_stream.go", "bridge_v4_windows_fixed_stream_test.go",
        "bridge_v4_windows_wintun_lease.go", "bridge_v4_windows_wintun_lease_test.go",
        "bridge_v4_windows_scoped_client.go",
        "bridge_v4_windows_m2_effective.go", "bridge_v4_windows_m2_effective_test.go",
    ),
    "windowsownerlease": (
        "created_wintun_windows.go", "scoped_original_tls_native_wintun_windows.go",
    ),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check_spec(spec, read_source):
    need(spec["legacy_source"] == ORIGINAL, "original Go SOURCE changed")
    for op in spec["operations"]:
        if op.get("overlay_path"):
            need(blob(read_source(op["overlay_path"])) == op["result_blob"],
                 "assembly blob mismatch: " + op["overlay_path"])


def prepare(root, legacy, output, source, spec):
    need(git(legacy, "rev-parse", "HEAD").decode().strip() == ORIGINAL, "legacy checkout SOURCE changed")
    # Normalize bytes from Git just as the original workflow did; Windows
    # checkout newline conversion must not change frozen assembly hashes.
    for op in spec["operations"]:
        if op["kind"] == "replace":
            data = git(legacy, "show", ORIGINAL + ":" + op["path"])
            need(blob(data) == op["original_blob"], "original blob mismatch: " + op["path"])
            target = legacy / op["path"]
            need(target.is_file(), "missing replacement target")
            target.write_bytes(data)
        if op.get("overlay_path"):
            (root / op["overlay_path"]).write_bytes(git(root, "show", source + ":" + op["overlay_path"]))
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([os.sys.executable, str(root / "r0/go_overlay/assembly/assemble.py"),
                    "--legacy-root", str(legacy), "--overlay-root", str(root),
                    "--manifest", str(root / MANIFEST), "--receipt", str(output / "assembly.json")], check=True)
    for part, names in EXTRA_BRIDGES.items():
        dest = legacy / "internal" / part
        dest.mkdir(parents=True, exist_ok=True)
        for name in names:
            relative = "r0/go_overlay/internal/" + part + "/" + name
            target = dest / name
            need(not target.exists(), "competing original/overlay owner: " + relative)
            data = git(root, "show", source + ":" + relative)
            need(len(data) > 60, "empty bridge: " + relative)
            need(b"package realityfront" in data if name == "admission_v4.go"
                 else data.startswith(b"//go:build windows"), "wrong bridge target: " + relative)
            target.write_bytes(data)
    for path in ("internal/windowsownerlease/original_tls_native_product_windows.go",
                 "internal/windowsclient/native_real_product_service_windows.go",
                 "internal/windowsclient/native_udp_kernel_driver_windows.go"):
        need((legacy / path).is_file(), "product assembly missing: " + path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--legacy-root", type=Path, default=ROOT / "legacy")
    parser.add_argument("--output", type=Path, default=ROOT / "result")
    args = parser.parse_args()
    source = git(ROOT, "rev-parse", "HEAD").decode().strip()
    need(source == os.environ.get("GITHUB_SHA", source), "checkout differs from event SOURCE")
    spec = json.loads(git(ROOT, "show", source + ":" + MANIFEST))
    check_spec(spec, lambda path: git(ROOT, "show", source + ":" + path))
    if not args.check_only:
        prepare(ROOT, args.legacy_root.resolve(), args.output.resolve(), source, spec)
    print(json.dumps({"source": source, "original_go": ORIGINAL,
                      "scope": "manifest_only" if args.check_only else "assembly_only",
                      "result": "PASS", "product_tests": "NOT_RUN"}))


if __name__ == "__main__":
    main()
