#!/usr/bin/env python3
"""One original Windows VM runs five original Game split policies sequentially.

Four independent jobs: game2off, game2fixed, game4off, game4fixed.
Only genuine original Go TLS/Rust Npcap/Wintun/Linux TUN and owned Stop count.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path.cwd()
OUT=ROOT/"result"/"wl-public"
SOURCE=os.environ.get("GITHUB_SHA","")
SIDE=os.environ.get("WBD_PLAN029B_GAME_MATRIX_SIDE","")
SIDES=("game2off","game2fixed","game4off","game4fixed")
if (SIDE not in SIDES or len(SOURCE)!=40 or
    os.environ.get("GITHUB_ACTIONS")!="true" or
    os.environ.get("WBD_PLAN029B_GAME_MATRIX_SCENE")!="1" or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="0" or
    os.environ.get("WBD_WL_NATIVE_OUTER_MTU_REQUEST")!="default1460" or
    os.environ.get("WBD_PLAN029_GAME4_CN_SCENE")=="1" or
    os.environ.get("WBD_PLAN029B_GAME2_CN_SCENE")=="1"):
    raise SystemExit("refuse unsigned original Game native four-VM split matrix")
GAME=SIDE[:5]
FIXED=SIDE.endswith("fixed")
MODE=GAME+("-fec" if FIXED else "")
LANES=2 if GAME=="game2" else 4
if os.environ.get("WBD_WL_PUBLIC_MODES")!=MODE:
    raise SystemExit("original Game mode incompatible with matrix side")
BASE=OUT/"plan029b-game-matrix"/SIDE
if BASE.exists():
    raise SystemExit("refuse stale Game OS/lifecycle matrix results")
BASE.mkdir(parents=True)
CASES=("off","all","lan","ordinary","advanced")
result={"schema_version":1,"source_sha":SOURCE,"side":SIDE,
        "mode":MODE,"fec":("fixed" if FIXED else "off"),"lanes":LANES,
        "cases":[],"result":"NOT_RUN","expected_cases":list(CASES),
        "windows_cli_sha256":None,"linux_server_sha256":None}

def save():
    (BASE/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

def wait_bounded(proc):
    try:return proc.wait(timeout=225)
    except subprocess.TimeoutExpired:
        if os.name=="nt":
            subprocess.run(["taskkill.exe","/PID",str(proc.pid),"/T","/F"],
              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=False)
        if proc.poll() is None:proc.kill()
        try:proc.wait(timeout=12)
        except subprocess.TimeoutExpired:pass
        return 124

save()
for name in CASES:
    suffix="_fixed" if FIXED else ""
    tag=name+suffix
    folder=BASE/name
    folder.mkdir()
    env=os.environ.copy()
    env.update(WBD_WL_PUBLIC_MODES=MODE,
      WBD_PLAN029B_GAME_MATRIX_SCENE="1",
      WBD_PLAN029B_GAME_MATRIX_CASE=tag,
      WBD_PLAN029B_GAME2_CN_SCENE="0",WBD_PLAN029_GAME4_CN_SCENE="0",
      WBD_PLAN029_NATIVE_V3_TRIAL="0",WBD_PLAN029_V3_DIRECT_SCENE="0",
      WBD_PLAN029_STARTUP_PADDING_SCENE="0",WBD_WL_RUN_N0="0",
      WBD_WL_RUN_P200="0",WBD_WL_V2_SCENARIO="",
      WBD_WL_OUTER_REPAIR="on",
      WBD_WL_NATIVE_OUTER_MTU_REQUEST="default1460")
    (OUT/(MODE+"-report.json")).unlink(missing_ok=True)
    print("PLAN029B_GAME_REAL_CASE_START side="+SIDE+" case="+tag+
          " source="+SOURCE,flush=True)
    started=time.monotonic()
    p=subprocess.Popen([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],env=env)
    rc=wait_bounded(p)
    report_path=OUT/(MODE+"-report.json")
    if report_path.exists():shutil.copy2(report_path,folder/"report.json")
    for filename in ("client.log","server.log","windows-app.log","linux-app.log",
         "plan029b-game-lan-windows.log","plan029b-game-lan-guest.log"):
        f=OUT/filename
        if f.is_file():shutil.copy2(f,folder/filename)
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    item={"case":name,"config":tag,"source_sha":SOURCE,"child_exit":rc,
       "elapsed_s":round(time.monotonic()-started,3),"result":"NOT_QUALIFIED",
       "windows_cli_sha256":report.get("windows_cli_sha256"),
       "linux_server_sha256":report.get("linux_server_sha256")}
    result["cases"].append(item)
    save()
    try:
        if (rc or any(report.get(x)!=SOURCE for x in
                  ("source","fixture_source","product_binary_source","linux_binary_source")) or
            report.get("mode")!=MODE or
            report.get("mode_public")!="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_"+MODE or
            report.get("app_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
            report.get("tcp_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_TCP" or
            report.get("stop")!="PASS_BOTH_OWNED" or
            report.get("requested_original_win_mtu")!=1460):
            raise ValueError("actual original two-OS TLS/TUN UDP/TCP/Stop/source mismatch")
        cold=(folder/"client.log").read_text(errors="replace")
        candidates=__import__("re").findall(
            r"WBD_PLAN029B_GAME_V3_COLD_EFFECTIVE lanes=(\d+) "
            r"requested_route_mode=([a-z-]+) route_mode=(\d+) "
            r"requested_split=(true|false) business_split=(true|false) "
            r"cn_domain_fakeip=(true|false)",cold)
        wanted={"off":("bypass-lan-cn","0","false","false","false"),
                "all":("all","0","true","false","false"),
                "lan":("bypass-lan","1","true","true","false"),
                "ordinary":("bypass-lan-cn","2","true","true","false"),
                "advanced":("bypass-lan-cn","2","true","true","true")}[name]
        if len(candidates)!=1 or candidates[0]!=(str(LANES),)+wanted:
            raise ValueError("original authenticated Game policy/flags mismatch")
        if any(mark not in cold for mark in (
            "WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes="+str(LANES),
            "WBD_WINDOWS_OS_APPLIED",
            "WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1",
            "M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=PASS",
            "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes="+str(LANES))):
            raise ValueError("Game original 2/4 TLS/OS/MTU/owned WAL Stop missing")
        fec=__import__("re").findall(
          "WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes="+str(LANES)+r" fec=(\d+)",cold)
        if len(fec)!=1 or (int(fec[0])>0)!=FIXED:
            raise ValueError("actual original Game protected FEC mismatch")
        if any((OUT/p).exists() for p in ("owned-wal.json.n4-owned-wal",
            "owned-wal.json.n4-owned-wal.routes","owned-wal.json.plan029-defender-tcp")):
            raise ValueError("original Game owned WAL/Defender leaked after Stop")
        if name=="lan":
            p=report.get("plan029b_game_lan_real",{})
            if (p.get("source_sha")!=SOURCE or
                p.get("status")!="PASS_SCOPED_REAL_PHYSICAL_LAN_UDP_AND_BOTH_OWNED_STOP" or
                p.get("windows",{}).get("result")!="PASS_ORIGINAL_WINTUN_PHYSICAL_LAN_UDP" or
                p.get("linux",{}).get("result")!="PASS_ORIGINAL_LINUX_KERNEL_PHYSICAL_LAN_UDP"):
                raise ValueError("LAN true independent Windows Wintun physical source not proven")
        if name=="ordinary":
            p=report.get("plan029b_b2_ordinary_cn_real",{})
            if p.get("status")!="PASS_SCOPED_GENUINE_CN_REAL_A_AND_SHARED_OVERSEAS_TUNNEL":
                raise ValueError("ordinary CN physical DNS real A / overseas Tunnel not proven")
        if name=="advanced":
            p=report.get("plan029_game4_cn_real",{})
            if (p.get("source_sha")!=SOURCE or p.get("mode")!=MODE or
                p.get("lanes")!=LANES or p.get("fec")!=result["fec"] or
                p.get("stop")!="PASS_BOTH_OWNED" or
                p.get("tunnel_tcp")!="PASS_ACTUAL_TWO_OS_KERNEL_TCP" or
                p.get("cn_real_direct_tcp",{}).get("windows",{}).get("app_bytes_echoed")!=32768 or
                not p.get("cn_real_direct_tcp",{}).get("windows",{}).get("tcp_half_close") or
                not p.get("cn_real_direct_udp",{}).get("windows",{}).get("fake4","").startswith("198.18.")):
                raise ValueError("advanced FakeIP physical Direct TCP32K/UDP and Tunnel absent")
        if result["windows_cli_sha256"] is None:
            result["windows_cli_sha256"]=item["windows_cli_sha256"]
            result["linux_server_sha256"]=item["linux_server_sha256"]
        elif (item["windows_cli_sha256"]!=result["windows_cli_sha256"] or
              item["linux_server_sha256"]!=result["linux_server_sha256"]):
            raise ValueError("original source-locked Game VM binary changed between policies")
        if not result["windows_cli_sha256"] or not result["linux_server_sha256"]:
            raise ValueError("Game original binary SHA absent")
        item["result"]="PASS_ACTUAL_ORIGINAL_GAME_NATIVE_POLICY_AND_STOP"
        print("PLAN029B_GAME_REAL_CASE_PASS "+json.dumps(
              {"side":SIDE,"case":tag,"source":SOURCE},sort_keys=True),flush=True)
        save()
    except (ValueError,KeyError,TypeError,IndexError) as ex:
        item["result"]="FAIL"
        item["first_error"]=str(ex)[:450]
        result["result"]="FAIL_FIRST_REAL_ORIGINAL_GAME_POLICY"
        save()
        print("PLAN029B_GAME_REAL_FIRST_FAILURE side="+SIDE+
              " case="+tag+" reason="+str(ex),flush=True)
        raise SystemExit(1)
result["result"]="PASS_SCOPED_FIVE_ORIGINAL_GAME_SPLIT_CASES_BOTH_OS"
save()
print("PLAN029B_GAME_REAL_FIVE_POLICY_PASS side="+SIDE+" source="+SOURCE,flush=True)
