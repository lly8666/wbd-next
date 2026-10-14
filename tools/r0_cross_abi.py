#!/usr/bin/env python3
"""R0 target-architecture and ABI/layout verifier, for Actions cross builds.

Real Rust target compilation and target-C static_assert + linking happen in
build jobs. Separate consumer jobs verify the exact SOURCE hashes and compiled
artifact bytes, then parse ELF/PE headers and inspect dynamic exported symbols
via target binutils. NEVER execute cross-target binaries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

RUST = "rustc 1.85.1 (4eb161250 2025-03-15)"
TARGETS = {
    "aarch64-unknown-linux-gnu": {
        "lib": "libwbd_engine.so",
        "exe": "r0-cross-link",
        "nm": "aarch64-linux-gnu-nm",
        "objdump": "aarch64-linux-gnu-objdump",
        "format": "ELF64_AARCH64",
    },
    "x86_64-pc-windows-gnu": {
        "lib": "wbd_engine.dll",
        "exe": "r0-cross-link.exe",
        "nm": "x86_64-w64-mingw32-nm",
        "objdump": "x86_64-w64-mingw32-objdump",
        "format": "PE32+_AMD64",
    },
}
INPUTS = [
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain.toml",
    "crates/wbd-types/src/lib.rs",
    "crates/wbd-platform/Cargo.toml",
    "crates/wbd-platform/src/lib.rs",
    "crates/wbd-engine/Cargo.toml",
    "crates/wbd-engine/src/lib.rs",
    "r0/abi/include/wbd_abi.h",
    "r0/abi/tests/cross_layout.c",
    "r0/source-lock.json",
    "tools/r0_cross_abi.py",
    ".github/workflows/r0-cross-abi.yml",
]
EXPORTS = (
    "wbd_r0_abi_query",
    "wbd_r0_engine_open",
    "wbd_r0_engine_close",
    "wbd_r0_lane_open",
    "wbd_r0_lane_close",
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def file_identity(path, target):
    binary = Path(path).read_bytes()
    if target == "aarch64-unknown-linux-gnu":
        # ELF64 / little endian / e_machine=183 (AArch64) / ET_EXEC or ET_DYN
        if len(binary) < 64 or binary[:4] != b"\x7fELF" or binary[4] != 2 or binary[5] != 1:
            raise ValueError(f"{path}: not little-endian ELF64")
        machine = int.from_bytes(binary[18:20], "little")
        e_type = int.from_bytes(binary[16:18], "little")
        if machine != 183 or e_type not in (2, 3):
            raise ValueError(f"{path}: not ARM64 executable/shared object: {machine}/{e_type}")
        return {"format": "ELF64", "machine": 183, "type": e_type}
    if len(binary) < 0x40 or binary[:2] != b"MZ":
        raise ValueError(f"{path}: not PE MZ")
    pos = int.from_bytes(binary[0x3c:0x40], "little")
    if pos < 0x40 or pos + 26 > len(binary) or binary[pos:pos + 4] != b"PE\x00\x00":
        raise ValueError(f"{path}: missing PE header")
    machine = int.from_bytes(binary[pos+4:pos+6], "little")
    magic = int.from_bytes(binary[pos+24:pos+26], "little")
    if machine != 0x8664 or magic != 0x20b:
        raise ValueError(f"{path}: expected PE32+ x86_64, got {machine:#x}, {magic:#x}")
    return {"format": "PE32+", "machine": "0x8664", "optional_header_magic": "0x20b"}


def subprocess_text(args):
    r = subprocess.run(args, text=True, capture_output=True, timeout=30, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"command {args} returned {r.returncode}: {r.stderr[-1200:]}")
    return r.stdout


def verify_export_names(libpath, target):
    if target == "aarch64-unknown-linux-gnu":
        output = subprocess_text([TARGETS[target]["nm"], "-D", "--defined-only", str(libpath)])
    else:
        output = subprocess_text([TARGETS[target]["objdump"], "-p", str(libpath)])
    missing = [name for name in EXPORTS if not re.search(r"\b" + re.escape(name) + r"\b", output)]
    if missing:
        raise ValueError(f"{target}: missing actual DLL/SO exports: {missing}")
    return list(EXPORTS)


def pack(a):
    if a.target not in TARGETS:
        raise ValueError("unexpected cross target")
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["rust"]["toolchain"] != "1.85.1" or a.rust != RUST:
        raise ValueError("Rust SOURCE/compiler drift")
    cfg = TARGETS[a.target]
    src = Path("target") / a.target / "release"
    dynamic = src / cfg["lib"]
    link_exe = Path(a.linked)
    platform = Path(a.platform)
    for path in (dynamic, link_exe, platform):
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"real cross-built file is missing: {path}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    paths = {
        "dynamic_library": dynamic,
        "c_link_executable": link_exe,
        "platform_rlib": platform,
    }
    binaries = {}
    for name, source in paths.items():
        destination = out / source.name
        shutil.copy2(source, destination)
        binaries[name] = {
            "filename": source.name,
            "size_bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }
    identity = {name: file_identity(out / entries["filename"], a.target)
                for name, entries in binaries.items() if name != "platform_rlib"}
    symbols = verify_export_names(out / cfg["lib"], a.target)
    manifest = {
        "schema_version": 1,
        "source_sha": a.source,
        "run_id": a.run,
        "attempt": a.attempt,
        "runner_architecture": "ubuntu-24.04-x86_64",
        "target": a.target,
        "qualification": "CROSS_BUILD_ONLY",
        "target_native_execution": "NOT_RUN",
        "rust_compiler": a.rust,
        "target_c_compiler": a.cc,
        "input_sha256": {name: sha256(name) for name in INPUTS},
        "binaries": binaries,
        "native_file_identification": identity,
        "observed_exports": symbols,
        "layout_static_assert": "COMPILED_IN_TARGET_C",
        "real_C_to_Rust_link": "LINKED_FOR_TARGET",
        "capabilities": 0,
        "scope": "R0 cross-target Rust engine ABI sentinel + platform rlib and target-C linked ABI layout, no target execution or product data-plane",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def consume(a):
    if a.target not in TARGETS:
        raise ValueError("unexpected target")
    manifest_path = Path(a.manifest)
    m = json.loads(manifest_path.read_text())
    if (m.get("schema_version") != 1 or m.get("source_sha") != a.source or
            m.get("run_id") != a.run or m.get("target") != a.target or
            m.get("runner_architecture") != "ubuntu-24.04-x86_64" or
            m.get("rust_compiler") != RUST or m.get("qualification") != "CROSS_BUILD_ONLY" or
            m.get("target_native_execution") != "NOT_RUN" or m.get("capabilities") != 0):
        raise ValueError("cross-build provenance and status mismatch")
    if set(m.get("input_sha256", {})) != set(INPUTS):
        raise ValueError("SOURCE file set changed")
    for name in INPUTS:
        if sha256(name) != m["input_sha256"][name]:
            raise ValueError("exact SOURCE input bytes drift: " + name)
    if set(m.get("binaries", {})) != {"dynamic_library", "c_link_executable", "platform_rlib"}:
        raise ValueError("binary manifest roles mismatch")
    base = manifest_path.parent
    for name, info in m["binaries"].items():
        path = base / info["filename"]
        if (not path.is_file() or path.stat().st_size != info["size_bytes"] or
                sha256(path) != info["sha256"]):
            raise ValueError(f"{name}: target cross binary hash/length changed")
    target = a.target
    dll = base / m["binaries"]["dynamic_library"]["filename"]
    exe = base / m["binaries"]["c_link_executable"]["filename"]
    for role, path in (("dynamic_library", dll), ("c_link_executable", exe)):
        observed = file_identity(path, target)
        if observed != m["native_file_identification"][role]:
            raise ValueError(f"{role}: target header changed")
    names = verify_export_names(dll, target)
    if names != m.get("observed_exports"):
        raise ValueError("cross target ABI symbol inventory changed")
    if m.get("layout_static_assert") != "COMPILED_IN_TARGET_C" or m.get("real_C_to_Rust_link") != "LINKED_FOR_TARGET":
        raise ValueError("target C proof was not built/linked")
    # This consumer never executes .dll/.so, target program, or Rust rlib.
    out = Path("r0-cross-abi-result")
    out.mkdir(exist_ok=True)
    result = {
        "schema_version": 1,
        "source_sha": a.source,
        "run_id": a.run,
        "attempt": m["attempt"],
        "target": target,
        "result": "CROSS_BUILD_PASS",
        "target_native_execution": "NOT_RUN",
        "rust_target_build": "PASS",
        "target_c_struct_layout_static_assert": "PASS_COMPILE_ONLY",
        "target_c_to_rust_link": "PASS_LINK_ONLY",
        "target_architecture_header": "PASS",
        "dynamic_symbols": names,
        "binary_sha256": {n: v["sha256"] for n, v in m["binaries"].items()},
        "v4_features": 0,
        "real_rust_engine": "NOT_IMPLEMENTED",
        "product_qualification": "NOT_RUN",
        "physical": "NOT_RUN",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pk = sub.add_parser("pack")
    for name in ("target", "out", "linked", "platform", "source", "run", "rust", "cc"):
        pk.add_argument("--" + name, required=True)
    pk.add_argument("--attempt", type=int, required=True)
    pk.set_defaults(fn=pack)
    c = sub.add_parser("consume")
    for name in ("target", "manifest", "source", "run"):
        c.add_argument("--" + name, required=True)
    c.set_defaults(fn=consume)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
