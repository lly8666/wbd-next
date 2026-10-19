#!/usr/bin/env python3
"""R0 WBC4/WBG4 wire-only codec precompiled Rust test bundle.

Test compilation/execution occurs ONLY in GitHub Actions. Python records and
checks exact SOURCE/run/attempt/compiler/binary hashes; it does not simulate
wire parsing or stand in for Rust codec tests.
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

COMPILER = "rustc 1.85.1 (4eb161250 2025-03-15)"
INPUTS = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
    "crates/wbd-types/src/lib.rs", "crates/wbd-types/src/buffer_contract.rs",
    "crates/wbd-codec/Cargo.toml", "crates/wbd-codec/src/lib.rs",
    "crates/wbd-codec/src/record_frame.rs",
    "crates/wbd-codec/src/link_fec_wire.rs", "r0/fixtures/legacy-link-fec-wire-v1.txt", "r0/fixtures/legacy-record-wire-v1.txt",
    "r0/source-lock.json", "tools/r0_codec_bundle.py",
    ".github/workflows/r0-codec.yml",
)
TESTS = (
    "r0_wbc4_golden_receipt_exact_wire_and_roundtrip",
    "r0_wbc4_golden_legacy_tlv_bytes_not_v3_sniffing",
    "r0_wbc4_truncated_header_or_tlv_cannot_emit_output",
    "r0_wbc4_reject_schema_magic_declared_size_and_tlv_overflow",
    "r0_wbc4_reject_duplicate_receipt_and_tlv_count_over_eight",
    "r0_wbc4_receipt_page_count_flags_and_fixed_length",
    "r0_wbc4_receipt_bit_alignment_future_and_ack_delay_bounds",
    "r0_wbc4_receipt_duplicate_page_and_eight_page_boundary",
    "r0_wbc4_max_pn_and_max_u16_budget_do_not_wrap",
    "r0_wbc4_empty_and_eight_tlvs_are_bounded",
    "r0_wbg4_golden_exact_big_endian_and_roundtrip",
    "r0_wbg4_game_reject_all_truncations_and_malformed_frames",
    "r0_wbg4_zero_and_max_payload_id_preserve_bytes",
)

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pack(a):
    lock=json.loads(Path("r0/source-lock.json").read_text())
    if lock["rust"]["toolchain"] != "1.85.1" or a.rust != COMPILER:
        raise ValueError("toolchain does not match pinned SOURCE")
    if os.environ.get("RUNNER_OS") != "Linux" or os.environ.get("RUNNER_ARCH") != "X64":
        raise ValueError("not native Linux x64 Actions")
    binary=Path(a.binary)
    if not binary.is_file() or binary.stat().st_size < 4096:
        raise ValueError("no compiled Rust unit binary")
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=False)
    dest=out/"r0-codec.test"
    shutil.copy2(binary,dest)
    info={
        "schema_version":1,
        "source_sha":a.source,
        "run_id":a.run,
        "attempt":a.attempt,
        "target":"x86_64-unknown-linux-gnu",
        "rust_compiler":a.rust,
        "inputs_sha256":{name:digest(name) for name in INPUTS},
        "binary":{"name":dest.name,"bytes":dest.stat().st_size,"sha256":digest(dest)},
        "test_names":list(TESTS),
        "scope":"R0 Rust WBC4 receipt-control and WBG4 envelope wire codec ONLY, without authentication, recovery execution, Game pipeline or production V4",
    }
    (out/"manifest.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps(info,indent=2))

def validate_wire_anchors(log, returncode):
    """Exact 13 named R0 WBC4/WBG4 wire anchors, not 13 TOTAL Rust libtests.

    M3 FEC2 may register extra true tests in the same library test tree.
    A missing anchor, duplicate, suite failure or total/printed mismatch
    must not be promoted by a broader compiled/tested component.
    """
    anchors=re.findall(r"^test tests::(r0_[a-z0-9_]+) \.\.\. ok$",log,re.M)
    failed=re.findall(r"^test (\S+) \.\.\. FAILED$",log,re.M)
    all_passed=re.findall(r"^test \S+ \.\.\. ok$",log,re.M)
    result=re.findall(
        r"^test result: ok\. (\d+) passed; (\d+) failed; "
        r"(\d+) ignored; (\d+) measured; (\d+) filtered out; finished in ",
        log,re.M)
    passed_total=int(result[0][0]) if len(result)==1 else -1
    valid=(returncode==0 and len(result)==1 and int(result[0][1])==0 and
           len(anchors)==len(TESTS) and set(anchors)==set(TESTS) and
           not failed and passed_total==len(all_passed) and
           passed_total>=len(TESTS))
    return anchors,failed,valid,passed_total


def consume(a):
    manifest=Path(a.manifest)
    m=json.loads(manifest.read_text())
    if (m.get("schema_version")!=1 or m.get("source_sha")!=a.source or
        m.get("run_id")!=a.run or m.get("attempt")!=int(a.attempt) or
        m.get("target")!="x86_64-unknown-linux-gnu" or m.get("rust_compiler")!=COMPILER):
        raise ValueError("SOURCE/run/attempt/target/compiler mismatch")
    if set(m.get("inputs_sha256",{}))!=set(INPUTS):
        raise ValueError("SOURCE input inventory changed")
    for path in INPUTS:
        if digest(path)!=m["inputs_sha256"][path]:
            raise ValueError("SOURCE input hash mismatch: "+path)
    if tuple(m.get("test_names",()))!=TESTS:
        raise ValueError("test inventory drift")
    binary=manifest.parent/"r0-codec.test"
    expected=m["binary"]
    if (expected.get("name")!=binary.name or not binary.is_file() or
        binary.stat().st_size!=expected.get("bytes") or
        digest(binary)!=expected.get("sha256")):
        raise ValueError("compiled Rust codec binary drift")
    os.chmod(binary,binary.stat().st_mode|0o100)
    result=subprocess.run([str(binary.resolve()),"--nocapture","--skip","record_frame::","--skip","link_fec_wire::"],text=True,
                          capture_output=True,timeout=100)
    log=result.stdout+result.stderr
    output=Path("r0-codec-result")
    output.mkdir(exist_ok=True)
    (output/"tests.log").write_text(log)
    passed,failed,success,all_lib_tests=validate_wire_anchors(log,result.returncode)
    receipt={
        "schema_version":1,
        "source_sha":a.source,
        "run_id":a.run,
        "attempt":int(a.attempt),
        "result":"PASS" if success else "FAIL",
        "tests_passed":len(passed),
        "tests_failed":len(failed),
        "all_rust_libtest_cases_passed":all_lib_tests,
        "other_codecs_not_wire_anchors":max(0,all_lib_tests-len(TESTS)),
        "rust_test_binary_sha256":expected["sha256"],
        "test_log_sha256":digest(output/"tests.log"),
        "tests":list(passed),
        "scope":m["scope"],
        "product_qualification":"NOT_RUN",
        "real_rust_engine":"NOT_IMPLEMENTED",
        "go_v4_production":"DISABLED",
        "physical":"NOT_RUN",
        "performance":"NOT_RUN",
    }
    (output/"result.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(log)
    print(json.dumps(receipt,indent=2))
    if not success:
        sys.exit(1)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    pk=sub.add_parser("pack")
    for name in ("out","binary","source","run","rust"):
        pk.add_argument("--"+name,required=True)
    pk.add_argument("--attempt",required=True,type=int)
    pk.set_defaults(func=pack)
    cs=sub.add_parser("consume")
    for name in ("manifest","source","run","attempt"):
        cs.add_argument("--"+name,required=True)
    cs.set_defaults(func=consume)
    a=p.parse_args()
    a.func(a)
if __name__=="__main__":
    main()
