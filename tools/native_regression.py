#!/usr/bin/env python3
"""One Release build per SOURCE, shared by affected functional groups (not perf)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.native_results import rust_results

CONTRACT = Path(".governance/native-suites.json")
BUILD = Path("native-build")
RUST = "rustc 1.85.1 (4eb161250 2025-03-15)"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suites():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["suites"]


def affected(paths, specs):
    # Lower layer changes affect engine composition; docs/cursors affect none.
    chosen = set()
    for path in paths:
        if path in {"Cargo.toml", "Cargo.lock", "rust-toolchain.toml"} or path.startswith(
                ("crates/wbd-types/", "tools/native_", ".governance/native-suites.json",
                 ".github/workflows/native-regression.yml")):
            return sorted(specs)
        for name, spec in specs.items():
            if any(path.startswith(prefix) for prefix in spec["affected_by"]):
                chosen.add(name)
    return sorted(chosen)


def plan():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    before = event.get("before", "0" * 40)
    specs = suites()
    if os.environ["GITHUB_REF_NAME"].startswith("governance/") or before == "0" * 40:
        groups = sorted(specs)
    else:
        paths = subprocess.check_output(["git", "diff", "--name-only", before, os.environ["GITHUB_SHA"]], text=True).splitlines()
        groups = affected(paths, specs)
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("groups=" + json.dumps(groups) + "\n")
    print(json.dumps({"groups": groups, "performance": "NOT_RUN"}))


def inputs():
    files = subprocess.check_output(["git", "ls-files", "crates", "Cargo.toml", "Cargo.lock",
                                    "rust-toolchain.toml", str(CONTRACT), "tools/native_regression.py",
                                    "tools/native_results.py", ".github/workflows/native-regression.yml"], text=True).splitlines()
    return {p: digest(p) for p in files}


def pack(groups):
    specs = suites()
    if not groups or len(groups) != len(set(groups)) or not set(groups) <= specs.keys():
        raise ValueError("empty/unknown/repeated groups")
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("unapproved native build target")
    if subprocess.check_output(["rustc", "--version"], text=True).strip() != RUST:
        raise ValueError("unapproved compiler")
    packages = sorted({specs[g]["package"] for g in groups})
    command = ["cargo", "test", "--release", "--locked", "--lib", "--tests", "--no-run", "--message-format=json"]
    for package in packages:
        command += ["-p", package]
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
    artifacts = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    BUILD.mkdir(exist_ok=False)
    binaries = {}
    for group in groups:
        spec = specs[group]
        matches = [a for a in artifacts if a.get("reason") == "compiler-artifact" and
                   a.get("profile", {}).get("test") and a.get("executable") and
                   a["target"]["name"] == spec["target"]]
        if len(matches) != 1:
            raise ValueError("ambiguous/missing compiled binary: " + group)
        destination = BUILD / (group + ".test")
        shutil.copy2(matches[0]["executable"], destination)
        binaries[group] = {"name": destination.name, "bytes": destination.stat().st_size,
                           "sha256": digest(destination)}
    manifest = {"schema_version": 1, "source_sha": os.environ["GITHUB_SHA"],
                "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "target": "x86_64-unknown-linux-gnu", "rust": RUST, "profile": "release",
                "rustflags": os.environ.get("RUSTFLAGS", ""), "features": "default",
                "command": command, "groups": groups, "inputs": inputs(), "binaries": binaries}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verify(manifest, group):
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("native consumer target mismatch")
    for key, value in {"source_sha": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
                       "attempt": os.environ["GITHUB_RUN_ATTEMPT"], "target": "x86_64-unknown-linux-gnu",
                       "rust": RUST, "profile": "release", "features": "default",
                       "rustflags": os.environ.get("RUSTFLAGS", "")}.items():
        if manifest.get(key) != value:
            raise ValueError("build identity mismatch: " + key)
    if manifest["inputs"] != inputs():
        raise ValueError("build inputs changed")
    info = manifest["binaries"][group]
    if info["name"] != group + ".test":
        raise ValueError("unexpected binary path")
    binary = BUILD / info["name"]
    if binary.stat().st_size != info["bytes"] or digest(binary) != info["sha256"]:
        raise ValueError("binary size/hash changed")
    return binary


def consume(group):
    spec = suites()[group]
    manifest = json.loads((BUILD / "manifest.json").read_text())
    binary = verify(manifest, group)
    binary.chmod(binary.stat().st_mode | 0o100)
    out = Path("native-results") / group
    out.mkdir(parents=True, exist_ok=True)
    command = [str(binary.resolve()), "--nocapture", "--test-threads=1"]
    if spec["filter"]:
        command.append(spec["filter"])
    try:
        run = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=240)
        log, code = run.stdout, run.returncode
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or b""
        log, code = raw.decode(errors="replace") if isinstance(raw, bytes) else raw, 124
    (out / "tests.log").write_text(log)
    result = rust_results(log, code, spec["required"], spec["allowed_ignored"])
    result.update(schema_version=1, source_sha=manifest["source_sha"], group=group,
                  run_id=manifest["run_id"], attempt=manifest["attempt"],
                  manifest_sha256=digest(BUILD / "manifest.json"),
                  binary_sha256=manifest["binaries"][group]["sha256"],
                  log_sha256=digest(out / "tests.log"), scope=spec["scope"],
                  supersedes_workflows=spec["supersedes_workflows"],
                  product="NOT_RUN", performance="NOT_RUN", physical="NOT_RUN",
                  not_qualified="LIVE_GO_V4_ADMISSION;PRODUCTION_RAW;NATIVE_WINDOWS_ARM;500MBPS;PACKET_P99")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(log)
    print(json.dumps(result, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "pack", "consume"])
    parser.add_argument("--groups")
    parser.add_argument("--group")
    args = parser.parse_args()
    if args.action == "plan":
        plan()
    elif args.action == "pack":
        pack(json.loads(args.groups))
    else:
        consume(args.group)
