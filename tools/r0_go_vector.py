#!/usr/bin/env python3
"""Pack and verify the compiled pinned-legacy Go admission vector probe.

Actions-only: build job checks out exact old source, compiles the Go test binary
once; consume job checks hashes/SOURCE then executes binary without go build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

OLD_SOURCE = "a7a82db31fe736ffedee330795a3234d358f1984"
INPUTS = ("r0/source-lock.json", "r0/legacy_v3_v4_probe_test.go")
BINARY = "r0-legacy-probe.test"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pack(args):
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["legacy"]["source_sha"] != OLD_SOURCE:
        raise ValueError("new repository source lock differs from pinned old source")
    if args.old_sha != OLD_SOURCE:
        raise ValueError("old Go checkout is not the locked SHA")
    if not args.go_version.startswith("go version go1.23.12 "):
        raise ValueError("not the required pinned Go toolchain")
    source = Path(args.binary)
    if not source.is_file():
        raise ValueError("no compiled Go test")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    artifact = out / BINARY
    shutil.copy2(source, artifact)
    manifest = {
        "schema_version": 1,
        "new_source_sha": args.new_sha,
        "legacy_source_sha": args.old_sha,
        "build_run_id": args.run_id,
        "build_attempt": args.attempt,
        "go_version": args.go_version,
        "platform": platform.platform(),
        "runner_os": os.environ.get("RUNNER_OS", ""),
        "runner_arch": os.environ.get("RUNNER_ARCH", ""),
        "probe_inputs_sha256": {p: sha256(p) for p in INPUTS},
        "binary": {
            "file": BINARY,
            "sha256": sha256(artifact),
            "bytes": artifact.stat().st_size,
        },
        "scope": "Go 1.23.12 original realityfront V3 writer/parser at locked commit; R0 test-only V4 admission 24B envelope and exporter/HKDF; Linux x64; no installed product or TLS roundtrip",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def consume(args):
    path = Path(args.manifest)
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("manifest version mismatch")
    if manifest.get("new_source_sha") != args.new_sha or manifest.get("build_run_id") != args.run_id:
        raise ValueError("source/run mismatch")
    if manifest.get("legacy_source_sha") != OLD_SOURCE:
        raise ValueError("old Go source mismatch")
    if manifest.get("runner_os") != "Linux" or manifest.get("runner_arch") != "X64":
        raise ValueError("not Linux x64 artifact")
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["legacy"]["source_sha"] != manifest["legacy_source_sha"]:
        raise ValueError("source-lock mismatch")
    if set(manifest.get("probe_inputs_sha256", {})) != set(INPUTS):
        raise ValueError("input list mismatch")
    for p in INPUTS:
        if sha256(p) != manifest["probe_inputs_sha256"][p]:
            raise ValueError("harness/lock changed: " + p)
    expected = manifest["binary"]
    if expected["file"] != BINARY:
        raise ValueError("unrecognized executable")
    binary = path.parent / BINARY
    if not binary.is_file() or binary.stat().st_size != expected["bytes"] or sha256(binary) != expected["sha256"]:
        raise ValueError("compiled Go binary hash/length mismatch")
    os.chmod(binary, binary.stat().st_mode | 0o100)
    run = subprocess.run(
        [str(binary.resolve()), "-test.v", "-test.run", "^TestR0"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        timeout=90,
    )
    print(run.stdout, end="")
    result_dir = Path("r0-go-out")
    result_dir.mkdir(exist_ok=True)
    (result_dir / "tests.log").write_text(run.stdout)
    passed = len(re.findall(r"^--- PASS: TestR0", run.stdout, flags=re.MULTILINE))
    failed = len(re.findall(r"^--- FAIL: TestR0", run.stdout, flags=re.MULTILINE))
    result = {
        "schema_version": 1,
        "new_source_sha": args.new_sha,
        "legacy_source_sha": OLD_SOURCE,
        "build_run_id": args.run_id,
        "build_attempt": manifest["build_attempt"],
        "build_binary_sha256": expected["sha256"],
        "test_log_sha256": sha256(result_dir / "tests.log"),
        "compiled_tests_passed": passed,
        "compiled_tests_failed": failed,
        "exit_code": run.returncode,
        "result": "PASS" if run.returncode == 0 and passed == 5 and failed == 0 else "FAIL",
        "scope": manifest["scope"],
        "actual_go_v4_production_adapter": "NOT_IMPLEMENTED",
        "tls_protected_v4_handshake": "NOT_RUN",
        "go_to_rust_abi": "NOT_RUN",
        "platform_abi": "NOT_RUN",
        "product_qualification": "NOT_RUN",
    }
    (result_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["result"] != "PASS":
        sys.exit(1)


def main():
    cli = argparse.ArgumentParser()
    s = cli.add_subparsers(dest="command", required=True)
    p = s.add_parser("pack")
    for name in ("out", "binary", "old-sha", "new-sha", "run-id", "go-version"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.set_defaults(fn=pack)
    p = s.add_parser("consume")
    for name in ("manifest", "new-sha", "run-id"):
        p.add_argument("--" + name, required=True)
    p.set_defaults(fn=consume)
    args = cli.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
