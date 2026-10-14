#!/usr/bin/env python3
"""R0: pack one compiled unit binary, verify exact SOURCE and hashes, then run.

Only called by GitHub Actions. Consumer does not call cargo or rustc.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

FILES = ("libwbd_types.rlib", "wbd-types-test")
INPUTS = ("Cargo.lock", "rust-toolchain.toml", "r0/source-lock.json", "crates/wbd-types/src/lib.rs", "crates/wbd-types/src/buffer_contract.rs")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, original in (
        ("libwbd_types.rlib", Path("target/debug/libwbd_types.rlib")),
        ("wbd-types-test", Path(args.test_binary)),
    ):
        if not original.is_file():
            raise ValueError(f"not compiled: {original}")
        artifact = out / name
        shutil.copy2(original, artifact)
        records[name] = {"bytes": artifact.stat().st_size, "sha256": sha256(artifact)}
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["rust"]["target"] != args.target:
        raise ValueError("unexpected build target")
    manifest = {
        "schema_version": 1,
        "source_sha": args.source,
        "run_id": args.run_id,
        "run_attempt": args.attempt,
        "target": args.target,
        "runner_os": os.environ.get("RUNNER_OS", "unknown"),
        "runner_arch": os.environ.get("RUNNER_ARCH", "unknown"),
        "host": platform.platform(),
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "cargo": subprocess.check_output(["cargo", "--version"], text=True).strip(),
        "inputs": {name: sha256(name) for name in INPUTS},
        "files": records,
        "scope": "wbd-types unit tests on Linux x64 only; Go/ABI/product NOT_RUN",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def consume(args):
    path = Path(args.manifest)
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("unexpected manifest version")
    if manifest.get("source_sha") != args.source or manifest.get("run_id") != args.run_id:
        raise ValueError("SOURCE / run identity mismatch")
    if manifest.get("target") != args.target or set(manifest.get("files", {})) != set(FILES):
        raise ValueError("unexpected target/files")
    if set(manifest.get("inputs", {})) != set(INPUTS):
        raise ValueError("input manifest mismatch")
    for name in INPUTS:
        if sha256(name) != manifest["inputs"][name]:
            raise ValueError(f"source input mismatch: {name}")
    for name in FILES:
        file = path.parent / name
        expected = manifest["files"][name]
        if not file.is_file() or file.stat().st_size != expected["bytes"]:
            raise ValueError(f"missing/incorrect size: {name}")
        if sha256(file) != expected["sha256"]:
            raise ValueError(f"artifact hash mismatch: {name}")
    binary = path.parent / "wbd-types-test"
    os.chmod(binary, binary.stat().st_mode | 0o100)
    result = subprocess.run([str(binary.resolve()), "--nocapture"], check=False)
    evidence = {
        "schema_version": 1,
        "source_sha": args.source,
        "build_run_id": args.run_id,
        "build_attempt": manifest["run_attempt"],
        "consumer_job": os.environ.get("GITHUB_JOB", "unknown"),
        "test_exit_code": result.returncode,
        "result": "PASS" if result.returncode == 0 else "FAIL",
        "scope": manifest["scope"],
        "go_vector": "NOT_RUN",
        "c_abi": "NOT_RUN",
        "platform_abi": "NOT_RUN",
        "product_qualification": "NOT_RUN",
    }
    Path("r0-test-result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    if result.returncode:
        sys.exit(result.returncode)


def main():
    cli = argparse.ArgumentParser()
    subs = cli.add_subparsers(dest="action", required=True)
    p = subs.add_parser("pack")
    for name in ("out", "test-binary", "source", "run-id", "target"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.set_defaults(fn=pack)
    p = subs.add_parser("consume")
    for name in ("manifest", "source", "run-id", "target"):
        p.add_argument("--" + name, required=True)
    p.set_defaults(fn=consume)
    args = cli.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
