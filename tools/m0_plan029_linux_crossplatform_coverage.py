#!/usr/bin/env python3
"""H2181 PLAN029 Linux-only functionality omitted by H2177's 10 sessions.

Two real native ISAs each use ONE original Go TLS/Rust/ISA-L binary bundle;
minimal complementary 8 cold cases, not a duplicate 5x2 mode matrix.
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

ROOT=Path(os.environ["GITHUB_WORKSPACE"])
SOURCE=os.environ["GITHUB_SHA"]
ARCH=os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
OUT=ROOT/"linux-plan029-crossplatform-result"
BUNDLE=ROOT/"linux-plan029-public-bundle"
if (os.getenv("GITHUB_ACTIONS")!="true" or
    os.getenv("WBD_PLAN029_LINUX_DUAL_ISA")!="1" or
    platform.machine()!=ARCH or ARCH not in ("x86_64","aarch64") or
    len(SOURCE)!=40):
    raise SystemExit("native Linux two-endpoint source/ISA guard failure")
manifest=json.loads((BUNDLE/"manifest.json").read_text())
assert manifest["source_sha"]==SOURCE and manifest["architecture"]==ARCH
assert manifest["scope"]=="NATIVE_LINUX_DUAL_ISA_BINARY_BUILD_ONLY"
for binary,sha in manifest["sha256"].items():
    assert hashlib.sha256((BUNDLE/binary).read_bytes()).hexdigest()==sha

# Each row is a completely new authenticated original TLS+Rust M4 client
# AND server in separately owned kernel namespaces, with double real app echo.
CASES=[
 ("game2-off","game2","off","",1460,"chacha20-poly1305","on","",False,False),
 ("game2-tls","game2","tls","",1460,"chacha20-poly1305","on","",True,False),
 ("game2-flows-outer-off","game2","flows","",1460,"chacha20-poly1305","off","",False,False),
 ("game2-fec6-flows","game2","flows","6",1460,"chacha20-poly1305","on","",False,False),
 ("game4-fec6-flows","game4","flows","6",1460,"chacha20-poly1305","on","",False,False),
 ("game4-off-immediate-flows","game4","flows","",1460,"chacha20-poly1305","off","immediate",False,False),
 ("normal-aes128-live-mtu","normal","off","",1460,"aes-128-gcm","on","",False,True),
 ("normal-aes256-x25519-mtu1280","normal","off","",1280,"aes-256-gcm","on","",False,False),
]
OUT.mkdir(exist_ok=False)
results={"schema_version":1,"source_sha":SOURCE,"native_isa":ARCH,
         "original_go_source_sha":manifest["original_go_sha"],
         "binary_sha256":manifest["sha256"],"same_original_bundle_all_cases":True,
         "scenarios":[],"qualification":"IN_PROGRESS",
         "excluded":["Linux Normal/Fixed/Auto startup-padding tls/flows NOT_WIRED",
             "Windows Direct/CN/FakeIP/WFP/WinGUI/OS-WAL",
             "ARM physical board, cross-ISA link, long stress and CPU/p99",
             "Linux host-global IPv6/AAAA and encrypted app TLS handshake"]}
def persist():
    (OUT/"summary.json").write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
persist()

# A Linux public CLI must FAIL CLOSED rather than silently accept a Normal
# flows selector that is only implemented for authenticated Game M4.
for mode in ("normal","fec-fixed","fec-auto"):
    command=[str(BUNDLE/"wbd-v4-client"),"--mode",mode,
             "--startup-padding","flows"]
    env=os.environ.copy()
    env["LD_LIBRARY_PATH"]=str(BUNDLE)
    p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=7)
    if p.returncode==0 or "not supported" not in (p.stdout+p.stderr):
        raise SystemExit("unsafe Linux Normal/FEC startup padding silently enabled: "+mode)
print("PLAN029_LINUX_NORMAL_FEC_PADDING_UNWIRED_FAIL_CLOSED_PASS",flush=True)

for name,mode,padding,game_fec,outer,cipher,repair,copy,tls_shape,live_mtu in CASES:
    env=os.environ.copy()
    env.update(
        WBD_PLAN029_LINUX_COVERAGE="1",
        WBD_V4_MODE=mode,
        WBD_PLAN029_LINUX_STARTUP_PADDING=padding,
        WBD_PLAN029_LINUX_CLIENT_CIPHER=cipher,
        WBD_PLAN029_LINUX_OUTER_REPAIR=repair,
        WBD_PLAN029_LINUX_GAME4_COPY=copy,
        WBD_PLAN029_LINUX_TCP_TLS_SHAPE="1" if tls_shape else "0",
        WBD_ARM64_GAME_FEC_PROFILE=game_fec,
        WBD_ARM64_OUTER_MTU=str(outer),
        WBD_ARM64_SERVER_OUTER_MTU=str(outer),
        WBD_ARM64_MTU_BOUNDARY="1" if mode=="normal" else "0",
        WBD_ARM64_LIVE_MTU_CYCLE="1" if live_mtu else "0",
        WBD_ARM64_USE_AUTO_ROUTE="1" if name=="normal-aes256-x25519-mtu1280" else "0",
        WBD_ARM64_FROZEN_SOURCE=SOURCE,
        WBD_PLAN029_LINUX_BUNDLE=str(BUNDLE),
        WBD_PLAN029_LINUX_OUTPUT=str(OUT/name),
    )
    row={"name":name,"mode":mode,"padding":padding,"fec":game_fec or "off",
         "outer_mtu":outer,"cipher":cipher,"repair":repair,
         "game4_copy":copy,"tls_shaped_application_probe":tls_shape,
         "physical_mtu_live_cycle":live_mtu,"status":"NOT_RUN"}
    results["scenarios"].append(row);persist()
    log=OUT/(name+"-runner.log");start=time.monotonic()
    print("PLAN029_LINUX_CROSSPLATFORM_BEGIN arch="+ARCH+" case="+name+" source="+SOURCE,flush=True)
    try:
        with log.open("w") as f:
            p=subprocess.run(["bash","tools/arm64_linux_netns_smoke.sh"],
                cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,
                timeout=240,check=False)
        row["duration_s"]=round(time.monotonic()-start,3)
        row["exit_code"]=p.returncode
        if p.returncode:
            raise RuntimeError("real Linux original Go/Rust two endpoints exit "+str(p.returncode))
        case=OUT/name
        receipt=json.loads((case/"receipt.json").read_text())
        for k,v in {
            "source":SOURCE,"test_harness_source":SOURCE,
            "mode":mode,"actual_native_isa":ARCH,"requested_outer_mtu":outer,
            "real_linux_kernel_udp_tcp_both_directions":"PASS",
            "linux_owned_tun_ipv6_disable":"PASS_BOTH_OWNED_TUN_ONLY",
            "owned_stop":"TWO_DRAINED","netns_cleanup":"PASS"
        }.items():
            if receipt.get(k)!=v:raise RuntimeError("missing true native result: "+k)
        for side in ("client","server"):
            raw=(case/(side+".log")).read_text(errors="replace")
            if mode.startswith("game"):
                match=re.findall(
                    r"V4_PUBLIC_GAME_PADDING_RAW_RECEIPT role="+side+
                    r" lanes=(2|4) mode=(off|tls|flows) padded_records=(\d+) padded_bytes=(\d+) original_TLS_Rust_M4=1 real_AF_PACKET_send=1",raw)
                if len(match)!=1:
                    raise RuntimeError(side+" original Rust Game padding kernel counter not found")
                lanes,actual,count,padded=match[0]
                count=int(count);padded=int(padded)
                if actual!=padding or padded>count*500 or (
                    padding=="off" and (count!=0 or padded!=0)) or (
                    padding!="off" and (count==0 or padded==0)):
                    raise RuntimeError(side+" original AF_PACKET padding mismatch")
                row[side+"_padding_records"]=count
                row[side+"_padding_bytes"]=padded
            if cipher!="chacha20-poly1305" and side=="client":
                row["client_requested_record_cipher"]=cipher
        for direction in ("c2s","s2c"):
            for side in ("sender","listener"):
                raw=(case/("app-"+direction+"-"+side+".log")).read_text()
                if "PLAN029_LINUX_APP_TRUE_KERNEL_PASS" not in raw:
                    raise RuntimeError("real Linux "+direction+"/"+side+" kernel app missing")
        if live_mtu:
            raw=(case/"dynamic-mtu.txt").read_text()
            if "ARM64_LIVE_MTU_1460_1280_RECOVER_REAL_OS_PASS" not in raw:
                raise RuntimeError("real Linux physical NIC MTU reauth/restore not proved")
        if name=="normal-aes256-x25519-mtu1280":
            cl=(case/"client.log").read_text()
            sv=(case/"server.log").read_text()
            if ("mode=ephemeral_x25519" not in cl or
                "mode=ephemeral_x25519" not in sv):
                raise RuntimeError("original Go route X25519 not established both ends")
        row["status"]="PASS_SCOPED_REAL_LINUX_NATIVE_CROSSPLATFORM"
        persist()
        print("PLAN029_LINUX_CROSSPLATFORM_CASE_PASS arch="+ARCH+" case="+name,flush=True)
    except (OSError,KeyError,RuntimeError,ValueError,subprocess.TimeoutExpired) as exc:
        row["status"]="FAIL_FIRST_SCOPED_NATIVE"
        row["first_error"]=str(exc)[:500]
        results["qualification"]="FAIL_FIRST_NATIVE";persist()
        if log.exists():
            # Only log test runner output, never private route key files.
            for line in log.read_text(errors="replace").splitlines()[-65:]:
                print(line,file=sys.stderr)
        print("PLAN029_LINUX_CROSSPLATFORM_CASE_FAIL arch="+ARCH+" case="+name+
              " error="+str(exc),flush=True)
        raise SystemExit(1)
results["qualification"]="PASS_SCOPED_EIGHT_COMPLEMENTARY_NATIVE_LINUX_SCENES"
persist()
print("PLAN029_LINUX_CROSSPLATFORM_EIGHT_NATIVE_PASS arch="+ARCH+" source="+SOURCE,flush=True)
