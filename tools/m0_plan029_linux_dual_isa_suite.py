#!/usr/bin/env python3
"""Source-locked bounded PLAN029 NON-WINDOWS real Linux client+server trials.

Run on *native* x86_64 or aarch64 GitHub hosted Linux, never QEMU. One built
Go/Rust bundle per ISA, sequential independent netns sessions; stop on first
true product failure. 5 representative modes, not a 20-case rerun/stress test.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

SOURCE=os.environ["GITHUB_SHA"]
ARCH=os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
ROOT=Path(os.environ["GITHUB_WORKSPACE"])
BUNDLE=ROOT/"linux-plan029-public-bundle"
OUT=ROOT/"linux-plan029-result"
if (platform.machine()!=ARCH or ARCH not in ("aarch64","x86_64")
    or os.environ.get("GITHUB_ACTIONS")!="true"
    or len(SOURCE)!=40 or os.environ.get("WBD_PLAN029_LINUX_DUAL_ISA")!="1"):
    raise SystemExit("PLAN029 refuses simulated/foreign ISA or non-Action source")
assert (BUNDLE/"SHA256SUMS").is_file(), "original Go/Rust bundle missing"
m=json.loads((BUNDLE/"manifest.json").read_text())
if (m["source_sha"]!=SOURCE or m["architecture"]!=ARCH
    or m["original_go_sha"]!="a7a82db31fe736ffedee330795a3234d358f1984"
    or m["scope"]!="NATIVE_LINUX_DUAL_ISA_BINARY_BUILD_ONLY"):
    raise SystemExit("Linux original source/ISA manifest not exact")
h=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for binary,checksum in m["sha256"].items():
    if h(BUNDLE/binary)!=checksum:
        raise SystemExit("original native binary SHA mismatch: "+binary)
cases=[
    ("normal","normal",None,True),
    ("fixed","fec-fixed",None,False),
    ("auto","fec-auto",None,False),
    ("game2","game2",None,False),
    ("game4-fixed6","game4","6",False),
]
OUT.mkdir(exist_ok=False)
result={
    "schema_version":1,"source_sha":SOURCE,"native_isa":ARCH,
    "real_linux_client_isa":ARCH,"real_linux_server_isa":ARCH,
    "product_build_source_sha":SOURCE,"original_go_source":m["original_go_sha"],
    "binary_sha256":m["sha256"],"same_binaries_all_modes":True,
    "runner_kernel":platform.release(),"native_runner":True,
    "not_emulated":True,"requested_outer_mtu":1460,
    "cases":[],"status":"NOT_RUN",
    "scope_exclusions":["Windows WinGUI/Direct/FakeIP/WFP/Npcap",
        "Linux host-global IPv6/AAAA resolver; only newly owned TUN IPv6 off",
        "game4-off, game2-fixed and extra FEC profiles",
        "Linux throughput or p99/CPU causality; physical ARM board",
        "inter-ISA cross-link and Windows inbound TCP"]
}
def save():
    (OUT/"summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
save()
for label,mode,fec,mtu_boundary in cases:
    case_dir=OUT/label
    env=os.environ.copy()
    env.update({
        "WBD_V4_MODE":mode,
        "WBD_ARM64_OUTER_MTU":"1460",
        "WBD_ARM64_SERVER_OUTER_MTU":"1460",
        "WBD_ARM64_MTU_BOUNDARY":"1" if mtu_boundary else "0",
        "WBD_ARM64_FROZEN_SOURCE":SOURCE,
        "WBD_PLAN029_LINUX_BUNDLE":str(BUNDLE),
        "WBD_PLAN029_LINUX_OUTPUT":str(case_dir),
        "WBD_ARM64_GAME_FEC_PROFILE":fec or ""
    })
    row={"label":label,"mode":mode,"fec":fec or "off",
         "source_sha":SOURCE,"status":"NOT_RUN","timeout_s":220}
    result["cases"].append(row);save()
    stamp=time.monotonic()
    print(f"PLAN029_LINUX_NATIVE_BEGIN isa={ARCH} case={label} source={SOURCE}",flush=True)
    try:
        # Existing original TLS/AF_PACKET/TUN fixture creates & then removes
        # all netns, RST guards, and per-session Go/Rust owners with real Stop.
        with (OUT/(label+"-runner.log")).open("w") as log:
            p=subprocess.run(
                ["bash","tools/arm64_linux_netns_smoke.sh"],
                cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                timeout=220,check=False)
        row["exit_code"]=p.returncode
        row["elapsed_s"]=round(time.monotonic()-stamp,2)
        if p.returncode:
            raise RuntimeError(f"original native Linux netns product returned {p.returncode}")
        proof=json.loads((case_dir/"receipt.json").read_text())
        if (proof.get("source")!=SOURCE or
            proof.get("test_harness_source")!=SOURCE or
            proof.get("actual_native_isa")!=ARCH or
            proof.get("actual_client_server_isa")!=ARCH or
            proof.get("mode")!=mode or
            proof.get("game_fec_profile")!=(fec or "") or
            proof.get("owned_stop")!="TWO_DRAINED" or
            proof.get("netns_cleanup")!="PASS" or
            proof.get("real_linux_kernel_udp_tcp_both_directions")!="PASS" or
            proof.get("linux_owned_tun_ipv6_disable")!="PASS_BOTH_OWNED_TUN_ONLY" or
            proof.get("requested_outer_mtu")!=1460 or
            proof.get("source_binary_sha256_verified") is not True or
            proof.get("qualification")!="PASS_SCOPED_TWO_LINUX_SAME_ISA_NETNS_ORIGINAL_GO_TLS_RUST_RAW_TUN"):
            raise RuntimeError("native Linux same-SOURCE original product/OS/Stop scope invalid")
        for d in ("c2s","s2c"):
            for role in ("listener","sender"):
                lines=(case_dir/("app-"+d+"-"+role+".log")).read_text().splitlines()
                receipts=[json.loads(x.split(" ",1)[1]) for x in lines
                    if x.startswith("PLAN029_LINUX_APP_TRUE_KERNEL_PASS ")]
                if (len(receipts)!=1 or
                    receipts[0]["udp"]!="PASS_NATIVE_KERNEL_APP" or
                    receipts[0]["tcp"]!="PASS_NATIVE_KERNEL_APP"):
                    raise RuntimeError("actual native kernel TCP/UDP app proof missing")
        for role in ("client","server"):
            raw=(case_dir/(role+".log")).read_text(errors="replace")
            if not (("V4_PUBLIC_NATIVE_STOP_DRAINED" in raw or
                     "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" in raw)
                    and ("V4_ORIGINAL_GO_" in raw)):
                raise RuntimeError("original Go TLS/Rust owned Stop missing: "+role)
        row.update(status="PASS_SCOPED_NATIVE_LINUX_TWO_ENDPOINTS",
                   real_both_way_tcp="PASS",real_both_way_udp="PASS",
                   ipv6_tun_owned="PASS",outer_mtu=1460,
                   tls_auth=True,owned_stop="PASS_BOTH",netns_cleanup="PASS")
        print(f"PLAN029_LINUX_NATIVE_CASE_PASS isa={ARCH} case={label}",flush=True)
        save()
    except (OSError,RuntimeError,KeyError,ValueError,AssertionError,
            subprocess.TimeoutExpired) as exc:
        row["status"]="FAIL_FIRST_SCOPED_NATIVE"
        row["first_error"]=str(exc)[:400]
        result["status"]="FAIL_FIRST_SCOPED_NATIVE"
        save()
        logfile=OUT/(label+"-runner.log")
        if logfile.exists():
            tail=logfile.read_text(errors="replace").splitlines()[-65:]
            print("\n".join(re.sub(
                r"(?i)(password|route.key|secret|credential|token)[=:]\\S+",
                r"\\1=[REDACTED]",x) for x in tail),file=sys.stderr)
        print(f"PLAN029_LINUX_NATIVE_CASE_FAIL isa={ARCH} case={label} "+str(exc),flush=True)
        raise SystemExit(1)
result["status"]="PASS_SCOPED_FIVE_REAL_LINUX_CLIENT_SERVER_MODES"
save()
print(f"PLAN029_LINUX_NATIVE_FIVE_MODES_PASS isa={ARCH} source={SOURCE}",flush=True)
