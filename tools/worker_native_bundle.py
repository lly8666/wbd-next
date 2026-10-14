#!/usr/bin/env python3
"""Precompile once, verify exact source and execute real scoped worker Rust tests.
No test count from an old R0 suite is borrowed as a new worker PASS.
"""
import argparse,hashlib,json,os
from pathlib import Path
import re,shutil,subprocess,sys

SPECS={
 "work/m1-r1-runtime":("M1","wbd-engine","r1_"),
 "work/m2-r2-recovery":("M2","wbd-recovery","r2_"),
 "work/m3-r1-codec":("M3","wbd-codec","r1_"),
 "work/m4-r1-platform":("M4","wbd-platform","r1_"),
}
SRC={
 "M1":"crates/wbd-engine","M2":"crates/wbd-recovery",
 "M3":"crates/wbd-codec","M4":"crates/wbd-platform",
}
RUST="rustc 1.85.1 (4eb161250 2025-03-15)"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()
def scope():
    branch=os.environ["GITHUB_REF_NAME"]
    if branch not in SPECS:raise ValueError("not a worker's assigned branch")
    return SPECS[branch]
def inputs(role):
    paths=[
        Path("Cargo.toml"),Path("Cargo.lock"),Path("rust-toolchain.toml"),
        Path("crates/wbd-types/Cargo.toml"),
        *Path("crates/wbd-types/src").rglob("*.rs"),
        Path(".governance/registry.json"),Path(f".governance/workstreams/{role}/cursor.json"),
        Path("tools/worker_native_bundle.py"),Path(".github/workflows/worker-native-tests.yml"),
    ]
    paths+=list(Path(SRC[role]).rglob("*.rs"))
    paths+=list(Path(SRC[role]).rglob("Cargo.toml"))
    if len(set(paths))!=len(paths) or not all(p.is_file() for p in paths):
        raise ValueError("missing/duplicate Rust input")
    return [str(p) for p in sorted(paths)]
def pack(a):
    role,package,filter_name=scope()
    if (os.environ.get("RUNNER_OS")!="Linux" or os.environ.get("RUNNER_ARCH")!="X64"
        or subprocess.check_output(["rustc","--version"],text=True).strip()!=RUST):
        raise ValueError("host/compiler not approved")
    b=Path(a.binary)
    if not b.is_file() or b.stat().st_size<4096:raise ValueError("compiled test binary missing")
    out=Path("worker-native-build");out.mkdir(exist_ok=False)
    name="worker-"+role.lower()+".test"
    shutil.copy2(b,out/name)
    m={
      "schema_version":1,"role_id":role,"package":package,
      "filter":filter_name,"branch":os.environ["GITHUB_REF_NAME"],
      "source_sha":a.source,"run_id":a.run,"attempt":int(a.attempt),
      "rust_toolchain":RUST,"target":"x86_64-unknown-linux-gnu",
      "inputs":{p:sha(p) for p in inputs(role)},
      "binary":{"name":name,"bytes":(out/name).stat().st_size,"sha256":sha(out/name)},
      "scope":"NEW_WORKER_NATIVE_TESTS_ONLY; never historic R0 exact-count suites",
    }
    (out/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
    print(json.dumps(m,indent=2))
def consume(a):
    role,package,filter_name=scope()
    m=json.loads(Path("worker-native-build/manifest.json").read_text())
    if (m.get("schema_version")!=1 or m["source_sha"]!=a.source or m["run_id"]!=a.run
        or m["attempt"]!=int(a.attempt) or m["role_id"]!=role or m["branch"]!=os.environ["GITHUB_REF_NAME"]
        or m["package"]!=package or m["filter"]!=filter_name
        or m["rust_toolchain"]!=RUST or m["target"]!="x86_64-unknown-linux-gnu"):
        raise ValueError("wrong identity/SOURCE/toolchain")
    if set(m["inputs"])!=set(inputs(role)):raise ValueError("worker exact input manifest drift")
    for p,d in m["inputs"].items():
        if sha(p)!=d:raise ValueError("worker source bytes changed: "+p)
    info=m["binary"]; b=Path("worker-native-build")/info["name"]
    if not b.is_file() or b.stat().st_size!=info["bytes"] or sha(b)!=info["sha256"]:
        raise ValueError("worker test binary hash/size mismatch")
    os.chmod(b,b.stat().st_mode|0o100)
    cmd=[str(b.resolve()),"--nocapture",filter_name]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=100)
    log=result.stdout+result.stderr;print(log)
    names=re.findall(r"^test ([^\n]+r[12]_[A-Za-z0-9_]+) \.\.\. ok$",log,re.M)
    total_match=re.search(r"test result: ok\. (\d+) passed; 0 failed",log)
    count=int(total_match.group(1)) if total_match else -1
    ok=(result.returncode==0 and count>0 and len(names)==count
        and len(set(names))==len(names) and
        all(filter_name in n for n in names))
    out=Path("worker-native-result");out.mkdir(exist_ok=True)
    (out/"test.log").write_text(log)
    report={
        "schema_version":1,"role_id":role,"source_sha":a.source,
        "run_id":a.run,"attempt":int(a.attempt),
        "result":"PASS_SCOPED_WORKER_TESTS" if ok else "FAIL_OR_NOT_YET_IMPLEMENTED",
        "test_names":names,"tests_passed":len(names),"binary_sha256":info["sha256"],
        "log_sha256":sha(out/"test.log"),"compiled_once":True,
        "worker_entry":"NATIVE_TESTS_ONLY","product":"NOT_RUN","performance":"NOT_RUN","physical":"NOT_RUN"
    }
    (out/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not ok:sys.exit(1)
def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    for name,fn,options in (("pack",pack,("binary","source","run","attempt")),
                            ("consume",consume,("source","run","attempt"))):
        p=sub.add_parser(name)
        for field in options:p.add_argument("--"+field,required=True)
        p.set_defaults(fn=fn)
    args=parser.parse_args();args.fn(args)
if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,OSError) as e:
        print("WORKER_NATIVE_ERROR: "+str(e),file=sys.stderr);sys.exit(1)
