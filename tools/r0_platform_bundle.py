#!/usr/bin/env python3
"""R0 native Rust platform fake-driver precompiled test provenance bundle.

Build and test execution are Actions-only; Python checks provenance, it does
not implement a second platform simulator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

FILES = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
    "crates/wbd-types/src/lib.rs", "crates/wbd-platform/Cargo.toml",
    "crates/wbd-platform/src/lib.rs", "r0/source-lock.json",
    "tools/r0_platform_bundle.py", ".github/workflows/r0-platform-fake.yml",
)
TESTS = (
    "r0_i01_prefix_partial_uncertain_does_not_count_as_ack",
    "r0_i01_zero_prefix_failure_does_not_block_fresh",
    "r0_c01_failed_seal_burns_pn_and_u64_never_wraps",
    "r0_i01_invalid_driver_accounting_is_fail_closed",
    "r0_b01_stop_waits_for_driver_borrow_and_rejects_new_loans",
    "r0_b01_fake_driver_returns_while_holding_a_live_loan",
    "r0_r01_injected_fake_clock_saturates_and_never_uses_wall_time",
)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pack(a):
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["rust"]["toolchain"] != "1.85.1":
        raise ValueError("rust toolchain source lock mismatch")
    if a.rust != "rustc 1.85.1 (4eb161250 2025-03-15)":
        raise ValueError("actual rust compiler mismatch")
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("not native Linux x64 Actions")
    binary = Path(a.binary)
    if not binary.is_file():
        raise ValueError("missing precompiled Rust test binary")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    target = out / "r0-platform-fake.test"
    shutil.copy2(binary, target)
    manifest = {
        "schema_version": 1,
        "source_sha": a.source,
        "run_id": a.run,
        "attempt": a.attempt,
        "target": "x86_64-unknown-linux-gnu",
        "rust_version": a.rust,
        "source_inputs": {file: digest(file) for file in FILES},
        "test_binary": {
            "name": target.name,
            "bytes": target.stat().st_size,
            "sha256": digest(target),
        },
        "test_names": TESTS,
        "scope": "R0 Rust platform trait + fake TxDriver and MonoClock unit probes; no OS socket, real kernel copy, Rust real engine, native cross-target, or physical test",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def consume(a):
    manifest_path = Path(a.manifest)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("source_sha") != a.source or manifest.get("run_id") != a.run:
        raise ValueError("source/run/manifest mismatch")
    if manifest.get("target") != "x86_64-unknown-linux-gnu" or manifest.get("rust_version") != "rustc 1.85.1 (4eb161250 2025-03-15)":
        raise ValueError("native target and toolchain mismatch")
    if set(manifest.get("source_inputs", {})) != set(FILES):
        raise ValueError("exact source input set mismatch")
    for name in FILES:
        if digest(name) != manifest["source_inputs"][name]:
            raise ValueError("source input changed: " + name)
    if tuple(manifest.get("test_names", ())) != TESTS:
        raise ValueError("test inventory mismatch")
    binary = manifest_path.parent / "r0-platform-fake.test"
    declared = manifest.get("test_binary", {})
    if (not binary.is_file() or declared.get("name") != binary.name or
            binary.stat().st_size != declared.get("bytes") or digest(binary) != declared.get("sha256")):
        raise ValueError("precompiled binary bytes/hash mismatch")
    os.chmod(binary, binary.stat().st_mode | 0o100)
    result = subprocess.run([str(binary.resolve()), "--nocapture"], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=100)
    print(result.stdout)
    out = Path("r0-platform-fake-result")
    out.mkdir(exist_ok=True)
    (out / "tests.log").write_text(result.stdout)
    passed = re.findall(r"^test tests::(r0_[^ ]+) \.\.\. ok$", result.stdout, re.M)
    failed = re.findall(r"^test tests::(r0_[^ ]+) \.\.\. FAILED$", result.stdout, re.M)
    all_ok = (result.returncode == 0 and
              set(passed) == set(TESTS) and len(passed) == len(TESTS) and not failed and
              "test result: ok. 7 passed; 0 failed" in result.stdout)
    report = {
        "schema_version": 1,
        "source_sha": a.source,
        "run_id": a.run,
        "attempt": manifest["attempt"],
        "result": "PASS" if all_ok else "FAIL",
        "tests_passed": len(passed),
        "tests_failed": len(failed),
        "exit_code": result.returncode,
        "test_names": passed,
        "test_log_sha256": digest(out / "tests.log"),
        "binary_sha256": declared["sha256"],
        "scope": manifest["scope"],
        "platform_driver": "FAKE_ONLY",
        "clock": "FAKE_MONOTONIC_ONLY",
        "native_os_io": "NOT_RUN",
        "real_engine": "NOT_IMPLEMENTED",
        "v4_production": "DISABLED",
        "product_qualification": "NOT_RUN",
        "physical": "NOT_RUN",
    }
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not all_ok:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser()
    subs = p.add_subparsers(dest="action", required=True)
    build = subs.add_parser("pack")
    for arg in ("out", "binary", "source", "run", "rust"):
        build.add_argument("--" + arg, required=True)
    build.add_argument("--attempt", type=int, required=True)
    build.set_defaults(fn=pack)
    consumer = subs.add_parser("consume")
    for arg in ("manifest", "source", "run"):
        consumer.add_argument("--" + arg, required=True)
    consumer.set_defaults(fn=consume)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
