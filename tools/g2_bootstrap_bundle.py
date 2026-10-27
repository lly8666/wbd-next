#!/usr/bin/env python3
"""G2 proof of one checked-in five-crate workspace and one *unqualified*
precompiled recovery bootstrap test binary, consumed in a separate job.
No product execution, Rust real record crypto or worker branch test is implied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

FILES = (
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml",
    "crates/wbd-types/Cargo.toml", "crates/wbd-types/src/lib.rs",
    "crates/wbd-types/src/buffer_contract.rs",
    "crates/wbd-codec/Cargo.toml", "crates/wbd-codec/src/lib.rs",
    "crates/wbd-engine/Cargo.toml", "crates/wbd-engine/src/lib.rs",
    "crates/wbd-engine/src/runtime/mod.rs",
    "crates/wbd-engine/src/memory/mod.rs",
    "crates/wbd-platform/Cargo.toml", "crates/wbd-platform/src/lib.rs",
    "crates/wbd-recovery/Cargo.toml", "crates/wbd-recovery/src/lib.rs",
    "r0/source-lock.json", ".governance/registry.json",
    ".governance/workstreams/M0/cursor.json",
    ".governance/workstreams/M1/cursor.json",
    ".governance/workstreams/M2/cursor.json",
    ".governance/workstreams/M3/cursor.json",
    ".governance/workstreams/M4/cursor.json",
    "tools/g2_bootstrap_bundle.py", ".github/workflows/g2-bootstrap.yml",
)
BINARY = "wbd-recovery-bootstrap.test"
RUST = "rustc 1.85.1 (4eb161250 2025-03-15)"

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def identity():
    registry=json.loads(Path(".governance/registry.json").read_text())
    # PLAN020 rev3 transfer is authoritative: M4's rev2 cursor stays frozen,
    # but its registry lease is revoked (reserved, epoch2, zero write scope).
    if registry["reservation_revision"]!=3:
        raise ValueError("G2 registry revision changed")
    roles={r["id"]:r for r in registry["roles"]}
    if set(roles)!={"M0","M1","M2","M3","M4"}:
        raise ValueError("G2 role set changed")
    m0=roles["M0"]
    if (m0["state"]!="active" or m0["branch"]!="main" or
            m0["assignment_epoch"]!=1 or not m0["global_writer"]):
        raise ValueError("M0 integrator assignment changed")
    active=[roles[x] for x in ("M1","M2","M3")]
    if any(r["state"]!="active" or r["assignment_epoch"]!=1 or r["global_writer"]
           for r in active):
        raise ValueError("worker active metadata missing")
    m4=roles["M4"]
    if (m4["state"]!="reserved" or m4["assignment_epoch"]!=2 or
            m4["allowed_paths"] or m4["owned_semantics"]):
        raise ValueError("M4 revoked lease changed")
    for r in active:
        snap=json.loads(Path(f".governance/workstreams/{r['id']}/cursor.json").read_text())
        if (snap["role_id"]!=r["id"] or snap["assignment_epoch"]!=r["assignment_epoch"] or
                not 1<=snap["reservation_revision"]<=registry["reservation_revision"]):
            raise ValueError("bootstrap active cursor snapshot mismatch")
    frozen=json.loads(Path(".governance/workstreams/M4/cursor.json").read_text())
    if (frozen["role_id"]!="M4" or frozen["assignment_epoch"]!=1 or
            frozen["reservation_revision"]!=2):
        raise ValueError("M4 historic cursor was rewritten")
    lock=json.loads(Path("r0/source-lock.json").read_text())
    if set(lock["rust"]["crates"]) != {"wbd-types","wbd-codec","wbd-engine","wbd-platform","wbd-recovery"}:
        raise ValueError("five-crate pin missing")
    if os.environ.get("RUNNER_OS")!="Linux" or os.environ.get("RUNNER_ARCH")!="X64":
        raise ValueError("not native Ubuntu Linux X64")

def pack(a):
    identity()
    if subprocess.check_output(["rustc","--version"],text=True).strip()!=RUST:
        raise ValueError("unexpected Rust compiler")
    src=Path(a.binary)
    if not src.is_file() or src.stat().st_size<4096:
        raise ValueError("missing genuine compiled recovery unit test binary")
    out=Path("g2-bootstrap-build");out.mkdir(exist_ok=False)
    binary=out/BINARY
    shutil.copy2(src,binary)
    m={
        "schema_version":1,"source_sha":a.source,"run_id":a.run,
        "attempt":int(a.attempt),"toolchain":RUST,"target":"x86_64-unknown-linux-gnu",
        "input_sha256":{p:sha(p) for p in FILES},
        "binary":{"file":BINARY,"sha256":sha(binary),"bytes":binary.stat().st_size},
        "scope":"R1_R2_FIVE_CRATE_BOOTSTRAP_ONLY_NO_REAL_RECOVERY",
    }
    (out/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
    print(json.dumps(m,indent=2))

def consume(a):
    identity()
    m=json.loads(Path("g2-bootstrap-build/manifest.json").read_text())
    if (m.get("schema_version")!=1 or m.get("source_sha")!=a.source or
        m.get("run_id")!=a.run or m.get("attempt")!=int(a.attempt) or
        m.get("toolchain")!=RUST or m.get("target")!="x86_64-unknown-linux-gnu"):
        raise ValueError("SOURCE/run/compiler/target mismatch")
    if set(m["input_sha256"])!=set(FILES):
        raise ValueError("G2 input list inconsistent")
    for p in FILES:
        if sha(p)!=m["input_sha256"][p]:
            raise ValueError("changed input: "+p)
    x=m["binary"];path=Path("g2-bootstrap-build")/BINARY
    if x["file"]!=BINARY or not path.is_file() or path.stat().st_size!=x["bytes"] or sha(path)!=x["sha256"]:
        raise ValueError("binary SHA256 mismatch")
    os.chmod(path,path.stat().st_mode|0o100)
    proc=subprocess.run([str(path.resolve()),"--nocapture","--exact","tests::bootstrap_is_not_product_qualification"],capture_output=True,text=True,timeout=60)
    output=proc.stdout+proc.stderr
    print(output)
    ok=proc.returncode==0 and "bootstrap_is_not_product_qualification ... ok" in output and "test result: ok. 1 passed; 0 failed" in output
    out=Path("g2-bootstrap-result");out.mkdir(exist_ok=True)
    (out/"test.log").write_text(output)
    result={
      "schema_version":1,"source_sha":a.source,"run_id":a.run,"attempt":int(a.attempt),
      "result":"PASS_BOOTSTRAP_ONLY" if ok else "FAIL",
      "binary_sha256":x["sha256"],"test_log_sha256":sha(out/"test.log"),
      "test_count":1 if ok else 0,
      "scope":"RECOVERY_CRATE_SCAFFOLD_NO_PRODUCT_ENGINE",
      "registry_active_workers":3,
      "M4_status":"reserved_rev3_epoch2_historic_cursor_rev2",
      "real_recovery":"NOT_IMPLEMENTED","real_engine":"NOT_IMPLEMENTED",
      "rust_record_aead":"NOT_IMPLEMENTED","product":"NOT_RUN",
      "performance":"NOT_RUN","physical":"NOT_RUN","production_v4":"DISABLED",
    }
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not ok:
        sys.exit(1)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    for name,args in (("pack",("binary","source","run","attempt")),
                      ("consume",("source","run","attempt"))):
        sp=sub.add_parser(name)
        for arg in args:
            sp.add_argument("--"+arg,required=True)
        sp.set_defaults(fn=pack if name=="pack" else consume)
    a=p.parse_args();a.fn(a)
