#!/usr/bin/env python3
"""Actions-only R0 legacy Go control caller gate compiled-binary consumer.

Build once: original pinned Go + exact checked overlay -> four binaries.
Consumer checks SOURCE/input hashes/each binary hash, executes no Go build.
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
import tempfile

LEGACY = "a7a82db31fe736ffedee330795a3234d358f1984"
INPUTS = [
    "r0/source-lock.json",
    "r0/go_overlay/internal/realityfront/admission_v4.go",
    "r0/go_overlay/internal/runtimeentry/r0_admission_mode.go",
    "r0/go_overlay/internal/runtimeentry/r0_admission_mode_test.go",
    "tools/r0_go_control_patch.py",
    "tools/r0_go_control_gate.py",
]
EXECUTABLES = ("r0-runtime.test", "r0-realityfront.test", "r0-client", "r0-server")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack(args):
    lock = json.loads(Path(INPUTS[0]).read_text())
    if lock["legacy"]["source_sha"] != LEGACY or args.legacy != LEGACY:
        raise ValueError("pinned Go SOURCE mismatch")
    if not args.go.startswith("go version go1.23.12 "):
        raise ValueError("Go compiler version mismatch")
    out = Path(args.out)
    out.mkdir(exist_ok=False, parents=True)
    bins = {}
    for name in EXECUTABLES:
        file = Path(name)
        if not file.is_file():
            raise ValueError("missing built binary: " + name)
        dest = out / name
        shutil.copy2(file, dest)
        bins[name] = {"bytes": dest.stat().st_size, "sha256": sha(dest)}
    manifest = {
        "schema_version": 1,
        "new_source": args.source,
        "old_source": LEGACY,
        "run_id": args.run_id,
        "attempt": args.attempt,
        "go": args.go,
        "target": "linux-amd64",
        "inputs": {name: sha(name) for name in INPUTS},
        "binaries": bins,
        "scope": "pinned legacy Go runtimeentry and both Linux CLI entrypoints with fail-closed V4 capability gate; V3 still in old realityfront; no Rust V4 engine",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def run_binary(path, *args, timeout=35):
    result = subprocess.run([str(path.resolve()), *args], text=True, timeout=timeout,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result


def expect_gate(binary, version, text):
    result = run_binary(binary, "--admission-version=" + str(version))
    if result.returncode == 0 or text not in result.stderr or "required identity" in result.stderr:
        raise RuntimeError(f"{binary.name} did not fail early for {version}: exit={result.returncode}, stderr={result.stderr[:500]}")
    return f"{binary.name} version={version} fail-closed before identity/config/network"


def consumer(args):
    manifest_file = Path(args.manifest)
    manifest = json.loads(manifest_file.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("new_source") != args.source or manifest.get("run_id") != args.run_id:
        raise ValueError("run/source mismatch")
    if manifest.get("old_source") != LEGACY or manifest.get("target") != "linux-amd64":
        raise ValueError("legacy/toolchain target mismatch")
    if set(manifest.get("inputs", {})) != set(INPUTS):
        raise ValueError("input set mismatch")
    for name in INPUTS:
        if manifest["inputs"][name] != sha(name):
            raise ValueError("script/input drift: " + name)
    if set(manifest.get("binaries", {})) != set(EXECUTABLES):
        raise ValueError("binary set mismatch")
    root = manifest_file.parent
    for name in EXECUTABLES:
        file = root / name
        m = manifest["binaries"][name]
        if not file.is_file() or file.stat().st_size != m["bytes"] or sha(file) != m["sha256"]:
            raise ValueError("compiled binary bytes drift: " + name)
        os.chmod(file, file.stat().st_mode | 0o100)

    reports = []
    for name, test_re, expected in [
        ("r0-runtime.test", "^TestR0", 4),
        ("r0-realityfront.test", "^(TestV3ProtectedFixedAdmissionKeys|TestRequireV3RejectsLegacyV2WithoutAllocating)$", 2),
    ]:
        run = run_binary(root / name, "-test.v", "-test.run", test_re, timeout=115)
        reports.append(f"=== {name} ===\n{run.stdout}\n{run.stderr}")
        passed = len(re.findall(r"^--- PASS: Test", run.stdout, re.MULTILINE))
        failed = len(re.findall(r"^--- FAIL: Test", run.stdout, re.MULTILINE))
        if run.returncode != 0 or passed != expected or failed:
            raise RuntimeError(f"{name} failed or wrong test count: pass={passed} fail={failed} exit={run.returncode}")
    for name in ("r0-client", "r0-server"):
        binary = root / name
        reports.append(expect_gate(binary, 4, "V4 requested but Rust receipt/Game data plane and ABI are not implemented"))
        reports.append(expect_gate(binary, 5, "unsupported requested admission version"))
        reports.append(expect_gate(binary, 2, "unsupported requested admission version"))

    # Existing server --check-config validates without networking. Use ephemeral
    # TLS cert/key only inside runner temp dir and never publish their bytes.
    with tempfile.TemporaryDirectory(prefix="r0-go-server-check-") as temp:
        cert = str(Path(temp) / "cert.pem")
        key = str(Path(temp) / "key.pem")
        gen = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
                              "-nodes", "-days", "1", "-subj", "/CN=target.test",
                              "-keyout", key, "-out", cert],
                             text=True, capture_output=True, timeout=25)
        if gen.returncode:
            raise RuntimeError("ephemeral test certificate generation failed")
        opts = [
            "--check-config", "--admission-version=3", "--raw-interface=lo",
            "--listen-ip=127.0.0.1", "--server-name=target.test",
            "--route-key-hex=3031323334353637383961626364656630313233343536373839616263646566",
            "--tls-cert=" + cert, "--tls-key=" + key,
            "--username=test-user", "--password=test-password",
            "--decoy=example.org:443",
            "--lanes=1",
        ]
        run = run_binary(root / "r0-server", *opts)
        if run.returncode:
            raise RuntimeError("real server --check-config failed: " + run.stderr[:750])
        check = json.loads(run.stdout)
        if check.get("effective-admission-version") != "3" or check.get("v4-capabilities") != "not-implemented" or check.get("admission-version") != "3":
            raise RuntimeError("server did not report effective V3/no V4 capability")
        if check.get("password") != "configured" or check.get("route-key-hex") != "configured":
            raise RuntimeError("original check-config secret redaction regressed")
        reports.append("server real --check-config returns effective-admission-version=3, v4-capabilities=not-implemented and redacted credentials")

    out = Path("r0-control-out")
    out.mkdir(exist_ok=True)
    (out / "tests.log").write_text("\n".join(reports) + "\n")
    print("\n".join(reports))
    result = {
        "schema_version": 1,
        "new_source": args.source,
        "legacy_source": LEGACY,
        "run_id": args.run_id,
        "attempt": manifest["attempt"],
        "compiled_test_groups_passed": 6,
        "compiled_test_groups_failed": 0,
        "cli_negative_scenarios": 6,
        "server_check_config": "PASS",
        "result": "PASS",
        "test_log_sha256": sha(out / "tests.log"),
        "scope": manifest["scope"],
        "rust_v4_engine": "NOT_IMPLEMENTED",
        "production_v4_admission": "DISABLED",
        "epoch_release_in_runtime": "NOT_WIRED_DUE_TO_DISABLED_V4",
        "C_ABI": "NOT_RUN",
        "product": "NOT_RUN",
        "physical": "NOT_RUN",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("pack")
    for name in ("out", "source", "legacy", "run-id", "go"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.set_defaults(fn=pack)
    p = sub.add_parser("consume")
    for name in ("manifest", "source", "run-id"):
        p.add_argument("--" + name, required=True)
    p.set_defaults(fn=consumer)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
