#!/usr/bin/env python3
"""Compile-once proof bundle for actual pinned Go LINK/FEC wire and Rust bytes.

No FEC math is implemented in Python. Build job only compiles Rust and pinned
old Go LINK/FEC packages; separate consumer hashes then runs the binaries.
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
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "r0/source-lock.json",
    "crates/wbd-types/src/lib.rs", "crates/wbd-codec/Cargo.toml",
    "crates/wbd-codec/src/lib.rs", "crates/wbd-codec/src/record_frame.rs",
    "crates/wbd-codec/src/link_fec_wire.rs",
    "r0/fixtures/legacy-link-fec-wire-v1.txt",
    "r0/go_overlay/internal/linkdata/r0_link_wire_oracle_test.go",
    "r0/go_overlay/internal/fec/r0_fec_wire_oracle_test.go",
    "tools/r0_link_fec_bundle.py", ".github/workflows/r0-link-fec-wire.yml",
)
ROLES = {
    "rust": "r0-link-fec-rust.test",
    "link_go": "r0-link-fec-link-go.test",
    "fec_go": "r0-link-fec-fec-go.test",
}
RUST_TESTS = (
    "r0_l01_pinned_go_mtu_minus_equal_plus_one_exact_link_bytes",
    "r0_l01_magic_and_wf_escape_exact_old_go_wire_modes",
    "r0_l01_invalid_index_count_total_id_flags_and_truncation_reject",
    "r0_l01_fragment_max_length_65535_and_zero_or_invalid_budget",
    "r0_fec_go_streaming_header_56b_exact_and_small_mtu_boundary",
    "r0_fec_go_final_parity_header_only_profile_and_length",
    "r0_fec_reject_incompatible_headers_profile_flags_lengths",
)
GO_LINK_TESTS = (
    "TestR0LinkPinnedRealGoMtu63_64_65Wire",
    "TestR0LinkPinnedRealGoMagicWFandInvalidLength",
)
GO_FEC_TESTS = (
    "TestR0FecPinnedActualStreamingSourceAndFinalParityHeaders",
    "TestR0FecPinnedRealGoProfilesWireBounds",
)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1048576),b""):
            h.update(part)
    return h.hexdigest()

def lock():
    d=json.loads(Path("r0/source-lock.json").read_text())
    if d["legacy"]["source_sha"]!=OLD or d["legacy"]["go_toolchain"]!="go1.23.12" or d["rust"]["toolchain"]!="1.85.1":
        raise ValueError("source-lock mismatch")

def pack(a):
    lock()
    if (a.old!=OLD or a.rust!=RUST or
        not a.go.startswith("go version go1.23.12 ") or
        os.environ.get("RUNNER_OS")!="Linux" or os.environ.get("RUNNER_ARCH")!="X64"):
        raise ValueError("wrong native toolchain/source/host")
    out=Path(a.out)
    out.mkdir(exist_ok=False)
    outputs={}
    for role,src in (("rust",a.rust_bin),("link_go",a.link_bin),("fec_go",a.fec_bin)):
        p=Path(src)
        if not p.is_file() or p.stat().st_size<4096:
            raise ValueError("missing real compiled test binary: "+role)
        dest=out/ROLES[role]
        shutil.copy2(p,dest)
        outputs[role]={"filename":dest.name,"bytes":dest.stat().st_size,"sha256":sha(dest)}
    m={
        "schema_version":1,"source_sha":a.source,"old_go_source_sha":OLD,
        "run_id":a.run,"attempt":int(a.attempt),
        "target":"x86_64-unknown-linux-gnu","rust_compiler":a.rust,
        "go_compiler":a.go,
        "source_sha256":{path:sha(path) for path in INPUTS},
        "binaries":outputs,
        "rust_tests":list(RUST_TESTS),"go_link_tests":list(GO_LINK_TESTS),
        "go_fec_tests":list(GO_FEC_TESTS),
        "scope":"Actual Go LINK fragment/reassemble + streaming source/final parity header; Rust LINK/FEC explicit bytes and MTU only. Not Rust FEC encoder, decoder, parity equivalence or real product path"
    }
    (out/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
    print(json.dumps(m,indent=2))

def consume(a):
    lock()
    m=json.loads(Path(a.manifest).read_text())
    if (m.get("schema_version")!=1 or m.get("source_sha")!=a.source or
        m.get("old_go_source_sha")!=OLD or m.get("run_id")!=a.run or
        m.get("attempt")!=int(a.attempt) or
        m.get("target")!="x86_64-unknown-linux-gnu" or
        m.get("rust_compiler")!=RUST or
        not m.get("go_compiler","").startswith("go version go1.23.12 ")):
        raise ValueError("source/run/attempt/platform provenance mismatch")
    if set(m.get("source_sha256",{}))!=set(INPUTS):
        raise ValueError("source inventory changed")
    for path in INPUTS:
        if sha(path)!=m["source_sha256"][path]:
            raise ValueError("source bytes changed: "+path)
    if (m.get("rust_tests")!=list(RUST_TESTS) or m.get("go_link_tests")!=list(GO_LINK_TESTS)
        or m.get("go_fec_tests")!=list(GO_FEC_TESTS)):
        raise ValueError("test inventory mismatch")
    if set(m.get("binaries",{}))!=set(ROLES):
        raise ValueError("binary inventory mismatch")
    compiled={}
    for role,name in ROLES.items():
        info=m["binaries"][role]
        p=Path(a.manifest).parent/name
        if (info.get("filename")!=name or not p.is_file() or
            p.stat().st_size!=info["bytes"] or sha(p)!=info["sha256"]):
            raise ValueError("binary hash/size mismatch: "+role)
        os.chmod(p,p.stat().st_mode|0o100)
        compiled[role]=str(p.resolve())
    cmds={
        "rust":[compiled["rust"],"--nocapture","link_fec_wire::tests::r0_"],
        "link_go":[compiled["link_go"],"-test.v","-test.run","^TestR0Link"],
        "fec_go":[compiled["fec_go"],"-test.v","-test.run","^TestR0Fec"],
    }
    logs={}
    statuses={}
    for name,cmd in cmds.items():
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=120)
        logs[name]=p.stdout+p.stderr
        statuses[name]=p.returncode
        print("=== "+name+" ===")
        print(logs[name])
    rust_pass=re.findall(r"^test link_fec_wire::tests::(r0_[a-z0-9_]+) \.\.\. ok$",logs["rust"],re.M)
    go_link_pass=re.findall(r"^--- PASS: (TestR0Link[^/\s]+) \(",logs["link_go"],re.M)
    go_fec_pass=re.findall(r"^--- PASS: (TestR0Fec[^/\s]+) \(",logs["fec_go"],re.M)
    ok=(all(rc==0 for rc in statuses.values()) and
        len(rust_pass)==len(RUST_TESTS) and set(rust_pass)==set(RUST_TESTS) and
        len(go_link_pass)==len(GO_LINK_TESTS) and set(go_link_pass)==set(GO_LINK_TESTS) and
        len(go_fec_pass)==len(GO_FEC_TESTS) and set(go_fec_pass)==set(GO_FEC_TESTS) and
        "test result: ok. 7 passed; 0 failed" in logs["rust"] and
        "PASS" in logs["link_go"] and "PASS" in logs["fec_go"])
    out=Path("r0-link-fec-result")
    out.mkdir(exist_ok=True)
    for name,log in logs.items():
        (out/(name+".log")).write_text(log)
    result={
        "schema_version":1,"source_sha":a.source,"old_go_source_sha":OLD,
        "run_id":a.run,"attempt":int(a.attempt),
        "result":"PASS" if ok else "FAIL",
        "rust_tests_passed":len(rust_pass),
        "go_link_tests_passed":len(go_link_pass),
        "go_fec_tests_passed":len(go_fec_pass),
        "rust_test_names":rust_pass,
        "go_link_test_names":go_link_pass,
        "go_fec_test_names":go_fec_pass,
        "binaries_sha256":{key:m["binaries"][key]["sha256"] for key in ROLES},
        "test_logs_sha256":{key:sha(out/(key+".log")) for key in cmds},
        "exit_codes":statuses,
        "rust_scope":"LINK_AND_FEC_WIRE_LAYOUT_ONLY",
        "old_go_real_link_fec":"ACTUAL_GO_SOURCE_USED" if ok else "UNVERIFIED",
        "rust_fec_math":"NOT_IMPLEMENTED",
        "rust_reassembly":"NOT_IMPLEMENTED",
        "full_L01":"PARTIAL_ONLY",
        "go_v4_production":"DISABLED","product":"NOT_RUN","performance":"NOT_RUN","physical":"NOT_RUN",
    }
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not ok:sys.exit(1)

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="command",required=True)
    b=s.add_parser("pack")
    for name in ("source","old","rust","go","rust-bin","link-bin","fec-bin","out","run","attempt"):
        b.add_argument("--"+name,required=True)
    b.set_defaults(fn=pack)
    c=s.add_parser("consume")
    for name in ("source","manifest","run","attempt"):
        c.add_argument("--"+name,required=True)
    c.set_defaults(fn=consume)
    a=p.parse_args()
    a.fn(a)
if __name__=="__main__":
    main()
