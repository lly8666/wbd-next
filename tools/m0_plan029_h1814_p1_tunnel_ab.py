#!/usr/bin/env python3
"""PLAN029 P1: the SAME VM, Windows signed NPF/Wintun and WSL2/TUN,
SAME SOURCE Go/Rust binaries, A original V4 Tunnel vs B V3 all Tunnel.
Overall implementation comparison, NOT isolated classifier overhead.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from m0_wl_perf_v2_config import read_scenario, first_delivery_ok_for_scenario

ROOT=pathlib.Path.cwd()
OUT=ROOT/"result"/"wl-public"
PAIR=OUT/"plan029-p1-ab"
SCENE="scenarios/plan029-p1-normal-50m-25ms0-60s.json"
SOURCE=os.environ.get("GITHUB_SHA","")
if (len(SOURCE)!=40 or os.environ.get("GITHUB_ACTIONS")!="true" or
    os.environ.get("WBD_PLAN029_P1_AB_SCENE")!="1" or
    os.environ.get("WBD_WL_PUBLIC_MODES")!="normal" or
    os.environ.get("WBD_WL_V2_SCENARIO")!=SCENE or
    os.environ.get("WBD_PLAN029_V3_DIRECT_SCENE")=="1" or
    os.environ.get("WBD_PLAN029_STARTUP_PADDING_SCENE")=="1"):
    raise SystemExit("H1814 exact Normal signed P1 scene precondition absent")
scene=read_scenario(ROOT/SCENE)
if (scene["duration_s"]!=60 or scene["tun_mtu"]!=1460 or
    any(scene[k]["offered_mbps"]!=50 or scene[k]["loss_pct"]!=0 or
        scene[k]["delay_ms"]!=25 for k in ("windows_to_linux","linux_to_windows"))):
    raise SystemExit("H1814 50Mbps/25ms/zero loss input drift")
if PAIR.exists():
    raise SystemExit("H1814 refuses previous generation pair directory")
PAIR.mkdir(parents=True)
result={"schema_version":1,"source_sha":SOURCE,"scenario":SCENE,
        "order":"A_OFF_B_ON_ALL","result":"NOT_RUN","legs":[],
        "oneway_p99":"NOT_MEASURED_UNCALIBRATED_CROSS_OS_CLOCKS",
        "scope":"SIGNED_SAME_VM_TOTAL_V4_V3_TUNNEL_COMPARATOR_NOT_SPLITTER_ONLY"}
def save():
    (PAIR/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")

def cpu_window(path,app):
    if not path.is_file():
        raise ValueError("original Windows Go+Rust 1Hz process sample missing")
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row=json.loads(line)
        except ValueError:
            continue
        if (row.get("scope")=="SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
            and isinstance(row.get("cpu_total_s"),(int,float))):
            rows.append(row)
    if len(rows)<3:
        raise ValueError("insufficient actual original Win32 CPU samples")
    start=float(app["measurement_start_monotonic_s"])
    end=float(app["measurement_end_monotonic_s"])
    first=min(rows,key=lambda x:abs(x["monotonic_s"]-start))
    last=min(rows,key=lambda x:abs(x["monotonic_s"]-end))
    if (abs(first["monotonic_s"]-start)>2.2 or
        abs(last["monotonic_s"]-end)>2.2 or
        last["monotonic_s"]-first["monotonic_s"]<55 or
        first["native_pid"]!=last["native_pid"]):
        raise ValueError("P1 actual measurement CPU window or native PID mismatch")
    return {"cpu_total_s":round(last["cpu_total_s"]-first["cpu_total_s"],4),
            "cpu_kernel_s":round(last["cpu_kernel_s"]-first["cpu_kernel_s"],4),
            "cpu_user_s":round(last["cpu_user_s"]-first["cpu_user_s"],4),
            "duration_s":round(last["monotonic_s"]-first["monotonic_s"],3),
            "peak_rss_bytes":max(x["peak_working_set_bytes"] for x in rows),
            "samples":len(rows),
            "scope":"ONE_WINDOWS_GO_PLUS_RUST_PROCESS_INCLUDES_SYSCALLS_NOT_DRIVER_CPU"}
save()
for name,v3 in (("A_off_old_tunnel","0"),("B_on_all_tunnel","1")):
    legdir=PAIR/name
    legdir.mkdir()
    env=os.environ.copy()
    env.update(WBD_WL_PUBLIC_MODES="normal",WBD_PLAN029_NATIVE_V3_TRIAL=v3,
        WBD_PLAN029_V3_DIRECT_SCENE="0",WBD_WL_OUTER_REPAIR="off",
        WBD_WL_V2_SCENARIO=SCENE,WBD_WL_RUN_N0="0",WBD_WL_RUN_P200="0",
        WBD_PLAN029_STARTUP_PADDING_SCENE="0")
    (OUT/"normal-report.json").unlink(missing_ok=True)
    print("PLAN029_H1814_P1_LEG_BEGIN name="+name+" source="+SOURCE,flush=True)
    process=subprocess.Popen([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],env=env)
    began=time.monotonic()
    try:
        rc=process.wait(timeout=440)
    except subprocess.TimeoutExpired:
        if os.name=="nt":
            subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],timeout=25,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        if process.poll() is None:
            process.kill()
        process.wait(timeout=15)
        rc=124
    rp=OUT/"normal-report.json"
    if rp.is_file():
        shutil.copy2(rp,legdir/"normal-report.json")
    for filename in ("windows-original-go-rust-process-1hz.jsonl",
                     "wl-n0-windows-app.json","wl-n0-linux-app.json"):
        path=OUT/filename
        if path.is_file():
            shutil.copy2(path,legdir/filename)
    report=json.loads(rp.read_text()) if rp.is_file() else {}
    entry={"name":name,"source_sha":SOURCE,"split_trial":v3=="1",
           "route_mode":"all" if v3=="1" else "legacy_tunnel",
           "child_exit":rc,"wall_s":round(time.monotonic()-began,2),
           "result":"NOT_QUALIFIED","owned_stop":report.get("stop","NOT_RUN"),
           "windows_cli_sha256":report.get("windows_cli_sha256"),
           "linux_server_sha256":report.get("linux_server_sha256")}
    result["legs"].append(entry)
    save()
    try:
        if (rc!=0 or report.get("source")!=SOURCE or
            report.get("mode_public")!="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal" or
            report.get("app_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
            report.get("tcp_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_TCP" or
            report.get("stop")!="PASS_BOTH_OWNED"):
            raise ValueError("one real original Windows/WSL2 UDP TCP owned Stop not qualified")
        left=[p.name for p in (OUT/"owned-wal.json.n4-owned-wal",
             OUT/"owned-wal.json.n4-owned-wal.routes") if p.exists()]
        if left:
            raise ValueError("owned Stop left generation WAL/route files "+repr(left))
        measured=report.get("WL_V2",{})
        if (measured.get("status")!="MEASURED_BOTH_OS_KERNEL" or
            measured.get("owned_stop")!="PASS_BOTH_OWNED" or
            measured.get("scenario_sha256")!=scene["scenario_sha256"] or
            not first_delivery_ok_for_scenario(scene,measured.get("first_delivery_fraction",{}))):
            raise ValueError("P1 real tc throughput first-delivery/Stop not qualified")
        apps=report.get("wl_n0_measured",{})
        if set(apps)!={"windows","linux"}:
            raise ValueError("both native user socket reports missing")
        delivered=0
        for side in ("windows","linux"):
            app=apps[side]
            if (app.get("source")!=SOURCE or
                app.get("scenario_sha256")!=scene["scenario_sha256"] or
                app.get("measurement_duration_s")!=60 or
                app.get("sent_payload_mbps",0)<47.5 or
                app.get("received_first_payload_bytes",0)<=0):
                raise ValueError("P1 traffic/identity/50Mbps generator gate "+side)
            latency=app.get("business_udp_rtt",{})
            if (not isinstance(latency.get("p99_ms"),(float,int)) or
                latency.get("real_replied",0)<200 or
                not isinstance(app.get("max_interdelivery_ms"),(float,int))):
                raise ValueError("P1 actual real kernel UDP RTT p99/gap missing "+side)
            delivered+=app["received_first_payload_bytes"]
        cpu=cpu_window(OUT/"windows-original-go-rust-process-1hz.jsonl",apps["windows"])
        if cpu["cpu_total_s"]<=0:
            raise ValueError("actual source-locked Go+Rust process CPU unavailable")
        gib=delivered/(1024**3)
        entry.update(result="PASS",actual_delivered_gib=round(gib,5),
            windows_cpu=cpu,windows_cpu_seconds_per_actual_delivered_gib=round(cpu["cpu_total_s"]/gib,4),
            applications={side:{
               "actual_delivered_mbps":apps[side]["received_payload_mbps"],
               "first_delivery_fraction":measured["first_delivery_fraction"][side],
               "udp_rtt_p99_ms":apps[side]["business_udp_rtt"]["p99_ms"],
               "rtt_probe_replies":apps[side]["business_udp_rtt"]["real_replied"],
               "max_interdelivery_gap_ms":apps[side]["max_interdelivery_ms"]}
               for side in ("windows","linux")})
        print("PLAN029_H1814_P1_REAL_LEG "+json.dumps(entry,sort_keys=True),flush=True)
        save()
    except (KeyError,TypeError,ValueError) as error:
        entry["result"]="FAIL"
        entry["first_failure"]=str(error)[:400]
        result["result"]="FAIL_FIRST_NATIVE_MEASUREMENT_OR_DELIVERY"
        save()
        print("PLAN029_H1814_P1_FIRST_ERROR "+str(error),flush=True)
        raise SystemExit(1)
a,b=result["legs"]
equal=(a["windows_cli_sha256"] and
       a["windows_cli_sha256"]==b["windows_cli_sha256"] and
       a["linux_server_sha256"] and
       a["linux_server_sha256"]==b["linux_server_sha256"])
result["binary_sha_equal"]=bool(equal)
if not equal:
    result["result"]="FAIL_BINARY_SHA_CHANGED";save()
    raise SystemExit("P1 A/B compiled binary hash changed")
result["comparison"]={
    "A_cpu_seconds_per_delivered_gib":a["windows_cpu_seconds_per_actual_delivered_gib"],
    "B_cpu_seconds_per_delivered_gib":b["windows_cpu_seconds_per_actual_delivered_gib"],
    "B_over_A_cpu_per_gib":round(b["windows_cpu_seconds_per_actual_delivered_gib"]/a["windows_cpu_seconds_per_actual_delivered_gib"],4),
    "A_windows_rtt_p99_ms":a["applications"]["windows"]["udp_rtt_p99_ms"],
    "B_windows_rtt_p99_ms":b["applications"]["windows"]["udp_rtt_p99_ms"],
    "scope":"SAME_WINDOWS_VM_TWO_REAL_60S_DATA_GENERATIONS_SAME_BINS_AND_BINARIES",
    "limitation":"V4 old Tunnel vs V3 split/all Tunnel; backend differs, not isolated splitter CPU",
    "driver_cpu":"NOT_ATTRIBUTED",
    "oldest_user_queue_age":"NOT_MEASURED"}
result["result"]="PASS_SCOPED_P1_BOTH_TRUE_NATIVE_TUNNEL_LEGS_MEASURED"
save()
print("PLAN029_H1814_P1_TRUE_SAME_VM_TUNNEL_COMPARATOR "+
      json.dumps(result["comparison"],sort_keys=True),flush=True)
