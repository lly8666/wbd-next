#!/usr/bin/env python3
"""R0 V4 TLS test: compile the fixed original Go control plus opted-in non-test
V4 extension once, then reuse the hashed test binary in an Actions consumer job.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

OLD = "a7a82db31fe736ffedee330795a3234d358f1984"
INPUTS = (
    "r0/source-lock.json",
    "r0/go_overlay/internal/realityfront/admission_v4.go",
    "r0/go_overlay/internal/realityfront/admission_v4_test.go",
)
BIN = "r0-v4-tls.test"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pack(args):
    lock = json.loads(Path(INPUTS[0]).read_text())
    if lock["legacy"]["source_sha"] != OLD or args.old != OLD:
        raise ValueError("wrong old Go SOURCE")
    if not args.go_version.startswith("go version go1.23.12 "):
        raise ValueError("wrong Go compiler")
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=False)
    src = Path(args.binary)
    if not src.is_file():
        raise ValueError("compiled Go binary missing")
    target = output / BIN
    shutil.copy2(src, target)
    manifest = {
        "schema_version": 1,
        "source_sha": args.source,
        "legacy_sha": OLD,
        "run_id": args.run,
        "run_attempt": args.attempt,
        "target": "linux-amd64",
        "go_version": args.go_version,
        "inputs": {p: digest(p) for p in INPUTS},
        "file": BIN,
        "bytes": target.stat().st_size,
        "sha256": digest(target),
        "test_filter": "^TestR0V4",
        "scope": "original TLS1.3/uTLS+FakeTCP with non-test opt-in V4 Go admission; test-only ready flag; no Rust dataplane/ABI/real device",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def consume(args):
    manifest = json.loads(Path(args.manifest).read_text())
    if manifest.get("schema_version") != 1 or manifest.get("source_sha") != args.source or manifest.get("run_id") != args.run:
        raise ValueError("manifest identity mismatch")
    if manifest.get("legacy_sha") != OLD or manifest.get("target") != "linux-amd64":
        raise ValueError("original SOURCE/target mismatch")
    if set(manifest.get("inputs", {})) != set(INPUTS):
        raise ValueError("input list mismatch")
    for path in INPUTS:
        if digest(path) != manifest["inputs"][path]:
            raise ValueError("modified SOURCE input: " + path)
    if manifest.get("file") != BIN or manifest.get("test_filter") != "^TestR0V4":
        raise ValueError("binary/filter mismatch")
    binary = Path(args.manifest).parent / BIN
    if not binary.is_file() or binary.stat().st_size != manifest["bytes"] or digest(binary) != manifest["sha256"]:
        raise ValueError("binary bytes/hash mismatch")
    os.chmod(binary, binary.stat().st_mode | 0o100)
    run = subprocess.run([str(binary.resolve()), "-test.v", "-test.run", "^TestR0V4"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=115)
    print(run.stdout)
    out = Path("r0-v4-out")
    out.mkdir(exist_ok=True)
    (out / "tests.log").write_text(run.stdout)
    passed = len(re.findall(r"^--- PASS: TestR0V4", run.stdout, re.M))
    failed = len(re.findall(r"^--- FAIL: TestR0V4", run.stdout, re.M))
    result = {
        "schema_version": 1,
        "source_sha": args.source,
        "legacy_sha": OLD,
        "build_run_id": args.run,
        "build_attempt": manifest["run_attempt"],
        "test_log_sha256": digest(out / "tests.log"),
        "binary_sha256": manifest["sha256"],
        "tests_passed": passed,
        "tests_failed": failed,
        "exit_code": run.returncode,
        "result": "PASS" if run.returncode == 0 and passed == 5 and failed == 0 else "FAIL",
        "scope": manifest["scope"],
        "v4_production_dispatch_wired": False,
        "v4_rust_capabilities_advertised": False,
        "c_abi": "NOT_RUN",
        "physical": "NOT_RUN",
        "product_qualification": "NOT_RUN",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["result"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("pack")
    for name in ("out", "binary", "source", "old", "run", "go-version"):
        b.add_argument("--" + name, required=True)
    b.add_argument("--attempt", type=int, required=True)
    b.set_defaults(func=pack)
    c = sub.add_parser("consume")
    for name in ("manifest", "source", "run"):
        c.add_argument("--" + name, required=True)
    c.set_defaults(func=consume)
    args = p.parse_args()
    args.func(args)
