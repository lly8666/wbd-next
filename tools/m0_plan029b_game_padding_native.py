#!/usr/bin/env python3
"""Signed original Windows2025/WSL2 Game startup-padding representative.

Exactly two independent jobs: Game2 FEC off, Game4 FEC fixed. Each reuses the
original Go TLS/Npcap/Wintun and Linux original TUN app three times (off/tls/
flows), with real SYN/UDP/TCP/Stop. Do not trigger the old 20-case matrix.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

OUT=Path("result/wl-public")
SRC=os.environ.get("GITHUB_SHA","")
SIDE=os.environ.get("WBD_PLAN029B_GAME_PADDING_SIDE","")
MAP={"game2off":("game2","all",2,False),
     "game4fixed":("game4-fec","all_fixed",4,True)}
if (SIDE not in MAP or len(SRC)!=40 or
    os.environ.get("GITHUB_ACTIONS")!="true" or
    os.environ.get("WBD_PLAN029B_GAME_PADDING_SCENE")!="1" or
    os.environ.get("WBD_PLAN029B_GAME_MATRIX_SCENE")!="0" or
    os.environ.get("WBD_WL_NATIVE_OUTER_MTU_REQUEST")!="default1460" or
    os.environ.get("WBD_WL_TUN_MTU")!="1460"):
    raise SystemExit("refuse unsourced Game cold-padding network claim")
MODE,CASE,LANES,FIXED=MAP[SIDE]
if os.environ.get("WBD_WL_PUBLIC_MODES")!=MODE:
    raise SystemExit("original signed Game source mode mismatch")
base=OUT/"plan029b-game-padding"/SIDE
if base.exists():
    raise SystemExit("refuse stale Game padding results")
base.mkdir(parents=True)
result={"schema_version":1,"source_sha":SRC,"side":SIDE,"mode":MODE,
        "fec":"fixed" if FIXED else "off","lanes":LANES,
        "cases":[],"expected_cases":["off","tls","flows"],"result":"NOT_RUN",
        "original_windows_cli_sha256":None,"original_linux_server_sha256":None}
def save():
    (base/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
def wait(proc):
    try:
        return proc.wait(timeout=235)
    except subprocess.TimeoutExpired:
        if os.name=="nt":
            subprocess.run(["taskkill.exe","/PID",str(proc.pid),"/T","/F"],
              timeout=25,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        if proc.poll() is None:proc.kill()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:pass
        return 124

save()
for mode in ("off","tls","flows"):
    folder=base/mode
    folder.mkdir()
    env=os.environ.copy()
    env.update(WBD_PLAN029B_GAME_MATRIX_SCENE="1",
      WBD_PLAN029B_GAME_MATRIX_CASE=CASE,
      WBD_PLAN029B_GAME_PADDING_MODE=mode,
      WBD_WL_PUBLIC_MODES=MODE,
      WBD_PLAN029_NATIVE_V3_TRIAL="0",WBD_PLAN029_V3_DIRECT_SCENE="0",
      WBD_PLAN029_STARTUP_PADDING_SCENE="0",
      WBD_PLAN029_GAME4_CN_SCENE="0",WBD_PLAN029B_GAME2_CN_SCENE="0",
      WBD_WL_RUN_N0="0",WBD_WL_RUN_P200="0",WBD_WL_V2_SCENARIO="",
      WBD_WL_OUTER_REPAIR="on",WBD_WL_NATIVE_OUTER_MTU_REQUEST="default1460")
    (OUT/(MODE+"-report.json")).unlink(missing_ok=True)
    started=time.monotonic()
    print("PLAN029_GAME_PADDING_ORIGINAL_START side="+SIDE+" mode="+mode+
          " source="+SRC,flush=True)
    child=subprocess.Popen([sys.executable,"-u",
                            "tools/m0_wl_public_modes_e2e.py"],env=env)
    rc=wait(child)
    report_file=OUT/(MODE+"-report.json")
    report=json.loads(report_file.read_text()) if report_file.exists() else {}
    for name in ("client.log","server.log","windows-app.log",
                 "linux-app.log","windows-tcp-app.log","linux-tcp-app.log"):
        a=OUT/name
        if a.is_file():shutil.copy2(a,folder/name)
    if report_file.exists():shutil.copy2(report_file,folder/"report.json")
    row={"padding":mode,"source_sha":SRC,"child_exit":rc,
         "elapsed_s":round(time.monotonic()-started,2),"status":"NOT_QUALIFIED",
         "original_windows_cli_sha256":report.get("windows_cli_sha256"),
         "original_linux_server_sha256":report.get("linux_server_sha256"),
         "npf_copied_records":None,"npf_copied_bytes":None}
    result["cases"].append(row);save()
    try:
        if (rc!=0 or
            any(report.get(k)!=SRC for k in
                ("source","fixture_source","product_binary_source",
                 "linux_binary_source")) or
            report.get("mode")!=MODE or
            report.get("mode_public")!="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_"+MODE or
            report.get("app_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
            report.get("tcp_duplex")!="PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP" or
            report.get("stop")!="PASS_BOTH_OWNED" or
            report.get("requested_original_win_mtu")!=1460 or
            report.get("actual_kernel_tcp",{}).get("windows",{}).get("client_echo") is not True or
            report.get("actual_kernel_tcp",{}).get("linux",{}).get("received_bytes",0)<=0 or
            report.get("actual_kernel_tcp",{}).get("linux",{}).get("client_ip")!="10.66.0.2" or
            report.get("actual_kernel_tcp",{}).get("windows",{}).get("tls_record_prefix") is not (mode=="tls") or
            report.get("actual_kernel_tcp",{}).get("linux",{}).get("tls_record_prefix") is not (mode=="tls")):
            raise ValueError("original live TLS/Game Wintun→Linux TCP/UDP/Stop/source missing")
        cold=(folder/"client.log").read_text(errors="replace")
        expected_cold=("WBD_PLAN029_GAME_PADDING_COLD_EFFECTIVE mode="+mode+
                       " lanes="+str(LANES)+" fec="+str(int(FIXED))+
                       " original_authenticated_game_owner=1")
        if cold.count(expected_cold)!=1:
            raise ValueError("Game V5 authenticated cold-padding effective receipt absent")
        copied=re.findall(
            r"WBD_PLAN029_GAME_PADDING_NPF_RECEIPT mode=(off|tls|flows) "
            r"lanes=(\d+) copied_records=(\d+) copied_bytes=(\d+) "
            r"source=original_Game_M4_authenticated_NPF_accepted",cold)
        if len(copied)!=1 or copied[0][0]!=mode or int(copied[0][1])!=LANES:
            raise ValueError("real Rust Game original M4 owned NPF receipt absent")
        n,b=(int(copied[0][2]),int(copied[0][3]))
        if (mode=="off" and (n or b)) or (
            mode!="off" and (n<1 or b<1 or b>500*n)):
            raise ValueError("off/eligible TLS-prefix/flows original NPF accepted padding mismatch")
        if any(k not in cold for k in (
            "WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes="+str(LANES),
            "WBD_WINDOWS_OS_APPLIED",
            "WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1",
            "M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=PASS",
            "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes="+str(LANES))):
            raise ValueError("original Game OS applied/inner MTU/native Stop missing")
        if any((OUT/name).exists() for name in (
                "owned-wal.json.n4-owned-wal",
                "owned-wal.json.n4-owned-wal.routes",
                "owned-wal.json.plan029-defender-tcp")):
            raise ValueError("native owner leaked OS/WAL state")
        if not row["original_windows_cli_sha256"] or not row["original_linux_server_sha256"]:
            raise ValueError("signed actual Go/Linux binary SHA missing")
        if result["original_windows_cli_sha256"] is None:
            result["original_windows_cli_sha256"]=row["original_windows_cli_sha256"]
            result["original_linux_server_sha256"]=row["original_linux_server_sha256"]
        if (result["original_windows_cli_sha256"]!=row["original_windows_cli_sha256"] or
            result["original_linux_server_sha256"]!=row["original_linux_server_sha256"]):
            raise ValueError("same native Game VM binary identity changed across padding arms")
        row["npf_copied_records"]=n;row["npf_copied_bytes"]=b
        row["status"]="PASS_SCOPED_ACTUAL_ORIGINAL_GAME_PADDING_NPF_TCP_UDP_STOP"
        row["linux_initiated_windows_tcp"]="NOT_RUN_SCOPE_SEPARATE"
        row["tls_scope"]=("REAL_KERNEL_TCP_TLS_RECORD_PREFIX_NOT_TLS_HANDSHAKE"
                          if mode=="tls" else "NOT_APPLICABLE")
        print("PLAN029_GAME_PADDING_ORIGINAL_PASS "+json.dumps(
            {"side":SIDE,"mode":mode,"npf_records":n,"npf_bytes":b,
             "source":SRC},sort_keys=True),flush=True)
        save()
    except (ValueError,KeyError,TypeError,IndexError,FileNotFoundError) as ex:
        row["status"]="FAIL";row["first_error"]=str(ex)[:550]
        result["result"]="FAIL_FIRST_SCOPED_ORIGINAL_GAME_PADDING"
        save()
        print("PLAN029_GAME_PADDING_ORIGINAL_FAIL "+str(ex),flush=True)
        raise SystemExit(1)
result["result"]="PASS_SCOPED_GAME_PADDING_OFF_TLS_FLOWS_REAL_NPF_TWO_OS"
save()
print("PLAN029_GAME_PADDING_ORIGINAL_THREE_MODES_PASS side="+SIDE+
      " source="+SRC,flush=True)
