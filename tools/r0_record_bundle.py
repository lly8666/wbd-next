#!/usr/bin/env python3
"""Manifest for two genuinely compiled test binaries: Rust opaque framing +
pinned original-Go record Seal/Open. Python only verifies SHA/provenance and
launches them. No Python model of AEAD, wire record, or PN unprotection.
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
RUST = "rustc 1.85.1 (4eb161250 2025-03-15)"
INPUTS = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
    "crates/wbd-types/src/lib.rs",
    "crates/wbd-codec/Cargo.toml", "crates/wbd-codec/src/lib.rs",
    "crates/wbd-codec/src/record_frame.rs",
    "crates/wbd-codec/src/link_fec_wire.rs", "r0/fixtures/legacy-link-fec-wire-v1.txt",
    "r0/fixtures/legacy-record-wire-v1.txt",
    "r0/go_overlay/internal/tlsrecord/r0_record_wire_oracle_test.go",
    "r0/source-lock.json",
    "tools/r0_record_bundle.py", ".github/workflows/r0-record-framing.yml",
)
RUST_TESTS = (
    "r0_record_pinned_go_six_real_wire_oracles_have_exact_offsets",
    "r0_record_multi_frame_opaque_prefix_no_delivery_or_magic_scan",
    "r0_record_zero_to_minimum_and_all_truncated_prefixes_fail_closed",
    "r0_record_header_type_version_length_and_wire_budget_reject",
    "r0_record_hp_sample_can_overlap_tag_of_short_record",
    "r0_record_kind_is_encrypted_not_a_wire_field_and_pn_is_masked",
)
GO_TESTS = (
    "TestR0RecordRealPinnedGoSealAndOpenSixFixtures",
    "TestR0RecordRealGoLengthFailClosedWithoutMagicScan",
)
BINARIES = {
    "rust": "r0-record-rust.test",
    "go": "r0-record-go.test",
}

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_qual():
    lock = json.loads(Path("r0/source-lock.json").read_text())
    if lock["legacy"]["source_sha"] != OLD or lock["legacy"]["go_toolchain"] != "go1.23.12":
        raise ValueError("pinned old Go source/toolchain drift")
    if lock["rust"]["toolchain"] != "1.85.1" or lock["rust"]["target"] != "x86_64-unknown-linux-gnu":
        raise ValueError("Rust pin and native target drift")

def pack(a):
    verify_qual()
    if a.old != OLD or a.rust != RUST or not a.go.startswith("go version go1.23.12 "):
        raise ValueError("actual Go/Rust or old source does not match pin")
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("only Linux x64 native Actions allowed")
    source = {"rust": Path(a.rust_test), "go": Path(a.go_test)}
    out = Path(a.out)
    out.mkdir(exist_ok=False)
    binaries = {}
    for role in ("rust", "go"):
        src = source[role]
        if not src.is_file() or src.stat().st_size < 4096:
            raise ValueError(f"{role} native compiled binary missing")
        dest = out / BINARIES[role]
        shutil.copy2(src, dest)
        binaries[role] = {"file": dest.name, "bytes": dest.stat().st_size, "sha256": digest(dest)}
    manifest = {
        "schema_version": 1,
        "source_sha": a.source, "old_go_sha": a.old,
        "run_id": a.run, "attempt": int(a.attempt),
        "target": "x86_64-unknown-linux-gnu",
        "rust_toolchain": a.rust, "go_toolchain": a.go,
        "input_sha256": {x: digest(x) for x in INPUTS},
        "binaries": binaries,
        "rust_tests": list(RUST_TESTS),
        "go_tests": list(GO_TESTS),
        "oracle": "Original tlsrecord.sealRecord and Opener.OpenRecord at pinned old Go SHA, actual Go1.23.12 binary; same independent 6 vectors used by Rust opaque framing tests",
        "limits": "Rust framing never decrypts, unmasks PN, identifies kind or yields authenticated payload; Go fixture proofs are old-Go only, not Rust AEAD",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest, indent=2))

def consume(a):
    verify_qual()
    path = Path(a.manifest)
    m = json.loads(path.read_text())
    if (m.get("schema_version") != 1 or m.get("source_sha") != a.source or
        m.get("old_go_sha") != OLD or m.get("run_id") != a.run or
        m.get("attempt") != int(a.attempt) or
        m.get("rust_toolchain") != RUST or
        not m.get("go_toolchain", "").startswith("go version go1.23.12 ") or
        m.get("target") != "x86_64-unknown-linux-gnu"):
        raise ValueError("build/consume SOURCE/run/attempt/compiler target mismatch")
    if set(m.get("input_sha256", {})) != set(INPUTS):
        raise ValueError("source inventory changed")
    for name in INPUTS:
        if digest(name) != m["input_sha256"][name]:
            raise ValueError("original input SHA256 mismatch: " + name)
    if set(m.get("binaries", {})) != set(BINARIES):
        raise ValueError("compiled test artifact inventory changed")
    if m.get("rust_tests") != list(RUST_TESTS) or m.get("go_tests") != list(GO_TESTS):
        raise ValueError("test inventory drift")
    binaries = {}
    for role,name in BINARIES.items():
        info = m["binaries"][role]
        src = path.parent / name
        if info.get("file") != name or not src.is_file() or src.stat().st_size != info["bytes"] or digest(src) != info["sha256"]:
            raise ValueError(f"{role} binary SHA256/bytes mismatch")
        os.chmod(src, src.stat().st_mode | 0o100)
        binaries[role] = str(src.resolve())
    def execute(label, command):
        r = subprocess.run(command, capture_output=True, text=True, timeout=100)
        print(label, r.stdout, r.stderr)
        return r.returncode, r.stdout + r.stderr
    rust_rc, rust_log = execute("RUST_RECORD_OPAQUE_FRAMING", [binaries["rust"], "--nocapture", "record_frame::tests::r0_record"])
    go_rc, go_log = execute("PINNED_OLD_GO_ACTUAL_RECORD_ORACLE", [binaries["go"], "-test.v", "-test.run", "^TestR0Record"])
    rust_pass = re.findall(r"^test record_frame::tests::(r0_record[a-z0-9_]+) \.\.\. ok$", rust_log, re.M)
    rust_fail = re.findall(r"^test record_frame::tests::(r0_record[a-z0-9_]+) \.\.\. FAILED$", rust_log, re.M)
    go_pass = re.findall(r"^--- PASS: (TestR0Record[^/\s]+) \(",go_log,re.M)
    go_fail = re.findall(r"^--- FAIL: (TestR0Record[^/\s]+) \(",go_log,re.M)
    all_ok = (rust_rc == 0 and go_rc == 0 and
              len(rust_pass) == len(RUST_TESTS) and set(rust_pass) == set(RUST_TESTS) and
              "test result: ok. 6 passed; 0 failed" in rust_log and not rust_fail and
              len(go_pass) == len(GO_TESTS) and set(go_pass) == set(GO_TESTS) and not go_fail and
              "PASS" in go_log)
    out = Path("r0-record-framing-result")
    out.mkdir(exist_ok=True)
    (out / "rust.log").write_text(rust_log)
    (out / "go.log").write_text(go_log)
    result = {
        "schema_version":1,"source_sha":a.source,"old_go_sha":OLD,
        "run_id":a.run,"attempt":int(a.attempt),
        "result":"PASS" if all_ok else "FAIL",
        "rust_tests_passed":len(rust_pass),"go_top_level_tests_passed":len(go_pass),
        "rust_test_names":rust_pass,"go_test_names":go_pass,
        "rust_exit":rust_rc,"go_exit":go_rc,
        "rust_log_sha256":digest(out/"rust.log"),
        "go_log_sha256":digest(out/"go.log"),
        "binary_sha256":{role:m["binaries"][role]["sha256"] for role in BINARIES},
        "pinned_go_real_seal_open":"PASS" if all_ok else "UNVERIFIED",
        "rust_scope":"OPAQUE_RECORD_FRAMING_ONLY",
        "rust_authenticated_record_open":"NOT_IMPLEMENTED",
        "rust_header_protection":"NOT_IMPLEMENTED",
        "production_go_v4":"DISABLED",
        "product":"NOT_RUN","performance":"NOT_RUN","physical":"NOT_RUN",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    if not all_ok:
        sys.exit(1)

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    pk = sub.add_parser("pack")
    for arg in ("source","old","rust","go","rust-test","go-test","out","run","attempt"):
        pk.add_argument("--"+arg, required=True)
    pk.set_defaults(fn=pack)
    cs = sub.add_parser("consume")
    for arg in ("source","run","attempt","manifest"):
        cs.add_argument("--"+arg,required=True)
    cs.set_defaults(fn=consume)
    args = p.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
