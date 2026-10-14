#!/usr/bin/env python3
"""R0 native Rust cdylib + C + pinned old Go cgo compiled-binary bundle.

The only verification execution occurs in GitHub Actions consumer job. No
Python approximation of a language ABI: three native executables invoke it.
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

OLD = "a7a82db31fe736ffedee330795a3234d358f1984"
FILES = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
    "crates/wbd-types/src/lib.rs",
    "crates/wbd-engine/Cargo.toml", "crates/wbd-engine/src/lib.rs",
    "r0/abi/include/wbd_abi.h", "r0/abi/tests/smoke.c",
    "r0/abi/old_go_probe/bridge.go", "r0/abi/old_go_probe/bridge_test.go",
    "r0/source-lock.json", "tools/r0_abi_bundle.py",
    ".github/workflows/r0-native-abi.yml",
)
BINARIES = ("libwbd_engine.so", "r0_abi_c", "r0_abi_go.test", "r0_abi_rust.test")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def pack(a):
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["legacy"]["source_sha"] != OLD or a.old != OLD:
        raise ValueError("old source mismatch")
    if a.rust != "rustc 1.85.1 (4eb161250 2025-03-15)":
        raise ValueError("Rust toolchain mismatch: " + a.rust)
    if not a.go.startswith("go version go1.23.12 "):
        raise ValueError("Go toolchain mismatch")
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("not native Linux X64 Actions")
    out = Path(a.out)
    out.mkdir(exist_ok=False, parents=True)
    bundle = {}
    for key, orig in [
        ("libwbd_engine.so", "target/release/libwbd_engine.so"),
        ("r0_abi_c", "r0_abi_c"),
        ("r0_abi_go.test", "r0_abi_go.test"),
        ("r0_abi_rust.test", a.rust_test),
    ]:
        path = Path(orig)
        if not path.is_file() or path.stat().st_size < 4096:
            raise ValueError("missing/too small native binary: " + orig)
        dest = out / key
        shutil.copy2(path, dest)
        bundle[key] = {"sha256": sha256(dest), "bytes": dest.stat().st_size}
    manifest = {
        "schema_version": 1,
        "source_sha": a.source,
        "legacy_sha": OLD,
        "run_id": a.run,
        "attempt": a.attempt,
        "target": "x86_64-unknown-linux-gnu",
        "rust_version": a.rust,
        "go_version": a.go,
        "inputs_sha256": {p: sha256(p) for p in FILES},
        "binaries": bundle,
        "scope": "R0 proto native cdylib C header + C executable + cgo in exact old Go module + precompiled Rust units; ABI features=0 no dataplane",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


RUST_ABI_CASES = frozenset({
    "r0_abi_token_domains_and_generation",
    "r0_abi_never_wraps_generations",
    "r0_abi_capacity_rejects_without_stealing_live_tokens",
})


def verify_three_rust_abi_cases(stdout):
    """Attest the exact native libtest ABI group, not a substring count."""
    names = re.findall(r"^test (?:[a-zA-Z0-9_]+::)*(r0_abi_[a-zA-Z0-9_]+) \\.\\.\\. ok$", stdout, re.M)
    result = re.search(r"^test result: ok\\. (\\d+) passed; (\\d+) failed; (\\d+) ignored; (\\d+) measured; (\\d+) filtered out;", stdout, re.M)
    if (result is None or tuple(map(int, result.groups()[:4])) != (3, 0, 0, 0)
            or len(names) != 3 or frozenset(names) != RUST_ABI_CASES):
        raise ValueError("R0 native Rust ABI exact test set/count mismatch")


def consume(a):
    path = Path(a.manifest)
    m = json.loads(path.read_text())
    if m.get("schema_version") != 1 or m.get("source_sha") != a.source or m.get("run_id") != a.run:
        raise ValueError("new SOURCE/run mismatch")
    if m.get("legacy_sha") != OLD or m.get("target") != "x86_64-unknown-linux-gnu":
        raise ValueError("legacy/architecture mismatch")
    if set(m.get("inputs_sha256", {})) != set(FILES):
        raise ValueError("SOURCE input inventory mismatch")
    for name in FILES:
        if sha256(name) != m["inputs_sha256"][name]:
            raise ValueError("SOURCE input bytes mismatch: " + name)
    if set(m.get("binaries", {})) != set(BINARIES):
        raise ValueError("native binary inventory mismatch")
    root = path.parent.resolve()
    for name, value in m["binaries"].items():
        f = root / name
        if not f.is_file() or f.stat().st_size != value["bytes"] or sha256(f) != value["sha256"]:
            raise ValueError("compiled native binary mismatch: " + name)
        if name != "libwbd_engine.so":
            os.chmod(f, f.stat().st_mode | 0o100)
    env = dict(os.environ, LD_LIBRARY_PATH=str(root) + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    records = []
    tests = [
        ("rust", [str(root / "r0_abi_rust.test"), "r0_abi_", "--nocapture"], None),
        ("C", [str(root / "r0_abi_c")], "R0_NATIVE_C_ABI_PASS"),
        ("Go", [str(root / "r0_abi_go.test"), "-test.v", "-test.run", "^TestR0Abi"], "--- PASS: TestR0AbiGoToRustCapacityNoClaimOfRealEngine"),
    ]
    for label, cmd, marker in tests:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=90, env=env)
        records.append("=== " + label + " ===\n" + result.stdout + result.stderr)
        if result.returncode != 0 or (marker is not None and marker not in result.stdout):
            raise RuntimeError(label + " ABI execution failed: rc " + str(result.returncode) + "\n" + (result.stdout + result.stderr)[-3000:])
        if label == "rust":
            # R0 selector is a real Rust libtest filter. Do not count M1's
            # growing r1_ suite or accept 13/23 as a substring of "3 passed".
            verify_three_rust_abi_cases(result.stdout)
    report = "\n".join(records)
    top = len(re.findall(r"^--- PASS: TestR0Abi", records[2], re.M))
    if top != 4:
        raise ValueError("Go native ABI group count mismatch: " + str(top))
    output = Path("r0-abi-out")
    output.mkdir(exist_ok=True)
    (output / "tests.log").write_text(report)
    result = {
        "schema_version": 1,
        "source_sha": a.source,
        "legacy_sha": OLD,
        "run_id": a.run,
        "attempt": m["attempt"],
        "result": "PASS",
        "rust_unit_tests": 3,
        "go_cgo_tests": top,
        "native_c_smoke": "PASS",
        "binary_sha256": {name: b["sha256"] for name,b in m["binaries"].items()},
        "test_log_sha256": sha256(output / "tests.log"),
        "capabilities": 0,
        "native_go_c_rust_abi": "PROBE_ONLY_PASS",
        "linux_amd64": "NATIVE",
        "windows_arm_abi": "NOT_RUN",
        "rust_product_engine": "NOT_IMPLEMENTED",
        "v4_production_readiness": "DISABLED",
        "physical": "NOT_RUN",
        "product_qualification": "NOT_RUN",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(report)
    print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser()
    subs = p.add_subparsers(dest="action", required=True)
    pack = subs.add_parser("pack")
    for n in ("out", "source", "old", "run", "go", "rust", "rust-test"):
        pack.add_argument("--" + n, required=True)
    pack.add_argument("--attempt", type=int, required=True)
    pack.set_defaults(fn=globals()["pack"])
    consume = subs.add_parser("consume")
    for n in ("manifest", "source", "run"):
        consume.add_argument("--" + n, required=True)
    consume.set_defaults(fn=globals()["consume"])
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
