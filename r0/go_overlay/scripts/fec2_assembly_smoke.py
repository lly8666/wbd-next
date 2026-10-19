#!/usr/bin/env python3
"""M0-owned Actions entrypoint can run this against two checked-out exact SHAs.

It never downloads floating sources, never configures a real NIC, and never
treats cross-compilation as native. M0 supplies Go1.23.12/Linux+Windows runner.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def invoke(argv: list[str], cwd: Path, env: dict[str, str], log: Path):
    proc = subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=240, check=False)
    log.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"command {argv[0]} failed {proc.returncode}; inspect {log}")
    return proc.stdout


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--legacy-root",type=Path,required=True)
    p.add_argument("--overlay-root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--target",choices=["linux-amd64","linux-arm64","windows-amd64"],required=True)
    args=p.parse_args()
    legacy=args.legacy_root.resolve(strict=True)
    overlay=args.overlay_root.resolve(strict=True)
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    script=overlay/"r0/go_overlay/assembly/assemble.py"
    manifest=overlay/"r0/go_overlay/assembly/manifest.json"
    receipt=out/"assembled.json"
    invoke([sys.executable,str(script),"--legacy-root",str(legacy),
            "--overlay-root",str(overlay),"--manifest",str(manifest),
            "--receipt",str(receipt)],overlay,dict(os.environ),out/"assembly.log")
    values=json.loads(receipt.read_text(encoding="utf-8"))
    assert values["result"]=="APPLIED_TO_PINNED_TEMP_CLONE"
    assert values["effective_catalog"]=="docs/PARAMETERS.json"
    env=dict(os.environ)
    env.update(GOTOOLCHAIN="local",CGO_ENABLED="0")
    triple={"linux-amd64":("linux","amd64"),"linux-arm64":("linux","arm64"),
            "windows-amd64":("windows","amd64")}[args.target]
    env["GOOS"],env["GOARCH"]=triple
    suffix=".exe" if triple[0]=="windows" else ""
    binaries={}
    for name in ("wbd-client","wbd-server") if triple[0]=="linux" else ("wbd-client",):
        binary=out/(name+suffix)
        invoke(["go","build","-trimpath","-o",str(binary),"./cmd/"+name],legacy,env,out/(name+".compile.log"))
        binaries[name]={"sha256":sha(binary),"bytes":binary.stat().st_size}
    # Run ONLY native host binaries. An ARM64 cross ELF or a Windows PE built
    # on Linux is not evidence of executable or GUI/native driver success.
    native=(sys.platform.startswith("linux") and triple[0]=="linux" and
            ((os.uname().machine=="x86_64" and triple[1]=="amd64") or
             (os.uname().machine=="aarch64" and triple[1]=="arm64"))) or (
            sys.platform=="win32" and triple==("windows","amd64"))
    if native:
        name="wbd-client"
        invoke([str(out/(name+suffix)),"--version"],legacy,env,out/"client-version.log")
        if triple[0]=="linux":
            invoke([str(out/("wbd-server"+suffix)),"--version"],legacy,env,out/"server-version.log")
    # Test the REAL original Go package with the M4 injected adapter and
    # original configfile parser. Do not accept a mock Go package.
    tests="NOT_RUN_CROSS_TARGET"
    if native:
        exe=out/("fec2-config.test"+suffix)
        invoke(["go","test","-c","-o",str(exe),"./internal/configfile"],legacy,env,out/"config-build.log")
        text=invoke([str(exe),"-test.run","^TestPLAN008FEC2","-test.v"],legacy,env,out/"config-test.log")
        if "PASS" not in text: raise RuntimeError("Go config test PASS marker absent")
        tests="PASS_SCOPED_FEC2_PARSER_READBACK_ONLY"
    report={
        "schema_version":1,"result":"PASS_SCOPED_BUILD_AND_NATIVE_IF_AVAILABLE",
        "target":args.target,"host_native":native,"toolchain":invoke(["go","version"],legacy,env,out/"go-version.log").strip(),
        "legacy_source":values["legacy_source"],"overlay_source":values["overlay_source"],
        "rust_source_reference":values["rust_source"],"assembly_sha256":sha(receipt),
        "files":values["files"],"binaries":binaries,"go_tests":tests,
        "windows_gui_native":"NOT_RUN_BY_THIS_SCRIPT",
        "native_rust_loader":"NOT_RUN","real_driver":"NOT_RUN",
        "protected_Go_Rust_applied":"NOT_RUN",
        "product_fec2":"OFF"
    }
    (out/"result.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print("FEC2_PRODUCT_SMOKE_FAIL: "+str(exc),file=sys.stderr)
        sys.exit(1)
