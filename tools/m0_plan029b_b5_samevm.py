#!/usr/bin/env python3
"""PLAN029B P-B1: ONE original Windows/WSL2 VM, sequential 10Mbps V3 all/off A/B.

Genuine original Go+Rust, original Wintun/Npcap/TUN, real kernel traffic,
source-pinned binaries and owned Stop in BOTH arms. This measures a bounded
configuration pair, not an old V2 vs V3 CPU victory. TCP small-p99 is NOT_RUN.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from m0_wl_perf_v2_config import read_scenario, first_delivery_ok_for_scenario

ROOT = Path.cwd()
OUT = ROOT / "result" / "wl-public"
PAIR = OUT / "plan029b-b5-samevm"
SCENE = "scenarios/plan027a-h941-normal-1460-10m-25ms-loss0-60s.json"
SOURCE = os.environ.get("GITHUB_SHA", "")
if (len(SOURCE) != 40 or os.environ.get("GITHUB_ACTIONS") != "true" or
    os.environ.get("WBD_PLAN029B_B5_SAMEVM_SCENE") != "1" or
    os.environ.get("WBD_WL_PUBLIC_MODES") != "normal" or
    os.environ.get("WBD_WL_NATIVE_OUTER_MTU_REQUEST") != "default1460" or
    os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL") != "0" or
    os.environ.get("WBD_PLAN029_P1_AB_SCENE") == "1" or
    os.environ.get("WBD_PLAN029_V3_DIRECT_SCENE") == "1"):
    raise SystemExit("B5 requires one signed user-cold-V3 Normal/1460 same-VM A/B")
scene = read_scenario(ROOT / SCENE)
if (scene["duration_s"] != 60 or scene["tun_mtu"] != 1460 or
    any(scene[k]["offered_mbps"] != 10 or scene[k]["loss_pct"] != 0 or
        scene[k]["delay_ms"] != 25 for k in ("windows_to_linux","linux_to_windows"))):
    raise SystemExit("B5 bounded original 2x10Mbps, 60s, zero-loss scene changed")
if PAIR.exists():
    raise SystemExit("B5 refuses stale pair directory from an earlier generation")
PAIR.mkdir(parents=True)

result = {"schema_version":1,"source_sha":SOURCE,
          "scenario":SCENE,"scenario_sha256":scene["scenario_sha256"],
          "order":"A_SPLIT_OFF_ALL_THEN_B_SPLIT_REQUESTED_ALL",
          "scope":"ONE_WINDOWS_VM_TWO_SEQUENTIAL_ACTUAL_RUST_V3_PUBLIC_ALL_SESSIONS",
          "result":"NOT_RUN","legs":[],"comparison":None,
          "small_tcp_p99":"NOT_RUN",
          "linux_cpu_attribution":"NOT_RUN_SEPARATE_GUEST_CPU_WINDOW",
          "cpu_interpretation":"ONE_WINDOWS_GO_PLUS_RUST_PROCESS_NOT_DRIVER_OR_KERNEL_TOTAL"}

def save():
    (PAIR / "result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")

def cpu_window(path,app):
    if not path.is_file():
        raise ValueError("real original Go+Rust Windows process CPU samples absent")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try: row = json.loads(line)
        except ValueError: continue
        if (row.get("scope") == "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
            and isinstance(row.get("cpu_total_s"),(int,float))):
            rows.append(row)
    if len(rows) < 3:
        raise ValueError("B5 original Windows process CPU 1Hz samples insufficient")
    begin = float(app["measurement_start_monotonic_s"])
    end = float(app["measurement_end_monotonic_s"])
    first = min(rows,key=lambda r:abs(r["monotonic_s"]-begin))
    last = min(rows,key=lambda r:abs(r["monotonic_s"]-end))
    if (abs(first["monotonic_s"]-begin)>2.2 or
        abs(last["monotonic_s"]-end)>2.2 or
        last["monotonic_s"]-first["monotonic_s"]<55 or
        first["native_pid"]!=last["native_pid"]):
        raise ValueError("B5 actual Windows original PID/CPU measurement window drift")
    return {
      "cpu_total_s":round(last["cpu_total_s"]-first["cpu_total_s"],4),
      "cpu_kernel_s":round(last["cpu_kernel_s"]-first["cpu_kernel_s"],4),
      "cpu_user_s":round(last["cpu_user_s"]-first["cpu_user_s"],4),
      "peak_rss_bytes":max(x["peak_working_set_bytes"] for x in rows),
      "samples":len(rows),
      "duration_s":round(last["monotonic_s"]-first["monotonic_s"],3),
      "scope":"SAME_WIN32_PROCESS_GO_RUST_NO_DRIVER_CPU"}

save()
for name,arm in (("A_split_off_all","off"),
                 ("B_split_requested_all","requested_all")):
    folder = PAIR / name
    folder.mkdir()
    env = os.environ.copy()
    env.update(WBD_WL_PUBLIC_MODES="normal",
      WBD_WL_V2_SCENARIO=SCENE,WBD_WL_NATIVE_OUTER_MTU_REQUEST="default1460",
      WBD_WL_RUN_N0="0",WBD_WL_RUN_P200="0",
      WBD_WL_OUTER_REPAIR="off",WBD_PLAN029_NATIVE_V3_TRIAL="0",
      WBD_PLAN029_V3_DIRECT_SCENE="0",WBD_PLAN029_STARTUP_PADDING_SCENE="0",
      WBD_PLAN029_P1_AB_SCENE="0",WBD_PLAN029_P1_POLICY_ABBA_SCENE="0",
      WBD_PLAN029B_B5_SAMEVM_SCENE="1",WBD_PLAN029B_B5_ARM=arm)
    (OUT/"normal-report.json").unlink(missing_ok=True)
    print("PLAN029B_B5_TRUE_SAMEVM_ARM_BEGIN name="+name+" source="+SOURCE,flush=True)
    original = subprocess.Popen([sys.executable,"-u",
      "tools/m0_wl_public_modes_e2e.py"],env=env)
    began = time.monotonic()
    try:
        rc = original.wait(timeout=470)
    except subprocess.TimeoutExpired:
        if os.name=="nt":
            subprocess.run(["taskkill","/PID",str(original.pid),"/T","/F"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                timeout=20,check=False)
        if original.poll() is None: original.kill()
        original.wait(timeout=12)
        rc = 124
    report_path=OUT/"normal-report.json"
    if report_path.is_file():
        shutil.copy2(report_path,folder/"normal-report.json")
    for file in ("windows-original-go-rust-process-1hz.jsonl",
                 "wl-n0-windows-app.json","wl-n0-linux-app.json","client.log"):
        if (OUT/file).is_file():
            shutil.copy2(OUT/file,folder/file)
    report=json.loads(report_path.read_text()) if report_path.is_file() else {}
    entry={"name":name,"arm":arm,"source_sha":SOURCE,"child_exit":rc,
           "elapsed_s":round(time.monotonic()-began,2),
           "windows_cli_sha256":report.get("windows_cli_sha256"),
           "linux_server_sha256":report.get("linux_server_sha256"),
           "owned_stop":report.get("stop","NOT_RUN"),"result":"NOT_QUALIFIED"}
    result["legs"].append(entry)
    save()
    try:
        if (rc or report.get("source")!=SOURCE or
            report.get("product_binary_source")!=SOURCE or
            report.get("fixture_source")!=SOURCE or
            report.get("mode_public")!="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal" or
            report.get("app_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_UDP" or
            report.get("tcp_duplex")!="PASS_ACTUAL_TWO_OS_KERNEL_TCP" or
            report.get("stop")!="PASS_BOTH_OWNED" or
            report.get("requested_original_win_mtu")!=1460):
            raise ValueError("one genuine Normal original same-source two-OS TCP/UDP/Stop missing")
        if any(p.exists() for p in
               (OUT/"owned-wal.json.n4-owned-wal",
                OUT/"owned-wal.json.n4-owned-wal.routes")):
            raise ValueError("B5 original Windows owned WAL/routes left after Stop")
        cold=(folder/"client.log").read_text(errors="replace")
        marker=("WBD_PLAN029B_V3_COLD_EFFECTIVE route_mode=0 "
                "requested_route_mode=all business_split=false cn_domain_fakeip=false")
        if cold.count(marker)!=1:
            raise ValueError("B5 original Rust V3 public DNS with business Direct disabled not observed")
        measured=report.get("WL_V2",{})
        if (measured.get("status")!="MEASURED_BOTH_OS_KERNEL" or
            measured.get("owned_stop")!="PASS_BOTH_OWNED" or
            measured.get("scenario_sha256")!=scene["scenario_sha256"] or
            not first_delivery_ok_for_scenario(scene,measured.get("first_delivery_fraction",{}))):
            raise ValueError("B5 actual two-OS kernel 10Mbps TC/delivery/Stop absent")
        apps=report.get("wl_n0_measured",{})
        if set(apps)!={"windows","linux"}:
            raise ValueError("B5 actual Windows/Linux sender+receiver apps absent")
        delivered=0
        for side in ("windows","linux"):
            a=apps[side]
            if ((side=="windows" and a.get("source")!=SOURCE) or
                (side=="linux" and a.get("source") not in (None,SOURCE)) or
                a.get("scenario_sha256")!=scene["scenario_sha256"] or
                a.get("measurement_duration_s")!=60 or
                a.get("sent_payload_mbps",0)<9.5 or
                a.get("received_first_payload_bytes",0)<=0):
                raise ValueError("B5 true 10Mbps source/application delivery missing "+side)
            latency=a.get("business_udp_rtt",{})
            if (not isinstance(latency.get("p99_ms"),(float,int)) or
                latency.get("real_replied",0)<200 or
                not isinstance(a.get("max_interdelivery_ms"),(float,int))):
                raise ValueError("B5 original real kernel UDP RTT p99/longest gap missing "+side)
            delivered+=a["received_first_payload_bytes"]
        cpu=cpu_window(OUT/"windows-original-go-rust-process-1hz.jsonl",apps["windows"])
        if cpu["cpu_total_s"]<=0 or delivered<=0:
            raise ValueError("B5 actual original Windows CPU/received GiB invalid")
        gib=delivered/1024**3
        entry.update(result="PASS",windows_cpu=cpu,
            actual_delivered_gib=round(gib,6),
            windows_cpu_seconds_per_actual_delivered_gib=round(cpu["cpu_total_s"]/gib,4),
            application={side:{
             "received_payload_mbps":apps[side]["received_payload_mbps"],
             "unique_first_delivery_fraction":measured["first_delivery_fraction"][side],
             "real_udp_p99_ms":apps[side]["business_udp_rtt"]["p99_ms"],
             "real_rtt_replies":apps[side]["business_udp_rtt"]["real_replied"],
             "longest_interdelivery_gap_ms":apps[side]["max_interdelivery_ms"]}
             for side in ("windows","linux")})
        print("PLAN029B_B5_TRUE_SAMEVM_ARM "+json.dumps(entry,sort_keys=True),flush=True)
        save()
    except (ValueError,TypeError,KeyError) as err:
        entry["result"]="FAIL"
        entry["first_error"]=str(err)[:400]
        result["result"]="FAIL_FIRST_ORIGINAL_B5_MEASUREMENT"
        save()
        print("PLAN029B_B5_ORIGINAL_FIRST_FAILURE "+str(err),flush=True)
        raise SystemExit(1)
a,b=result["legs"]
same=(a.get("windows_cli_sha256") and
      a["windows_cli_sha256"]==b.get("windows_cli_sha256") and
      a.get("linux_server_sha256") and
      a["linux_server_sha256"]==b.get("linux_server_sha256"))
result["same_original_windows_and_linux_binary_sha256"]=bool(same)
if not same:
    result["result"]="FAIL_SAME_VM_BINARY_DRIFT"
    save()
    raise SystemExit("B5 did not use the same original EXE and Linux service binary")
cpu_ratio=(b["windows_cpu_seconds_per_actual_delivered_gib"]/
           a["windows_cpu_seconds_per_actual_delivered_gib"])
win_udp_ratio=(b["application"]["windows"]["real_udp_p99_ms"]/
               max(0.001,a["application"]["windows"]["real_udp_p99_ms"]))
linux_udp_ratio=(b["application"]["linux"]["real_udp_p99_ms"]/
                 max(0.001,a["application"]["linux"]["real_udp_p99_ms"]))
result["comparison"]={
    "windows_cpu_seconds_per_actual_delivered_gib_A":a["windows_cpu_seconds_per_actual_delivered_gib"],
    "windows_cpu_seconds_per_actual_delivered_gib_B":b["windows_cpu_seconds_per_actual_delivered_gib"],
    "B_over_A_cpu_per_gib":round(cpu_ratio,4),
    "windows_original_rss_peak_A_bytes":a["windows_cpu"]["peak_rss_bytes"],
    "windows_original_rss_peak_B_bytes":b["windows_cpu"]["peak_rss_bytes"],
    "windows_udp_p99_ms_A":a["application"]["windows"]["real_udp_p99_ms"],
    "windows_udp_p99_ms_B":b["application"]["windows"]["real_udp_p99_ms"],
    "linux_udp_p99_ms_A":a["application"]["linux"]["real_udp_p99_ms"],
    "linux_udp_p99_ms_B":b["application"]["linux"]["real_udp_p99_ms"],
    "investigate_if_reproduced":any(v>1.05 for v in (cpu_ratio,win_udp_ratio,linux_udp_ratio)),
    "scope":"ONE_SIGNED_SAME_VM_SEQUENTIAL_10MBPS_EACH_DIRECTION_NO_RATE_SWEEP",
    "tcp_p99":"NOT_RUN_GENUINE_TCP_FUNCTIONAL_ONLY",
    "no_percent_improvement_claim":True}
result["result"]="PASS_SCOPED_B5_TRUE_SAME_VM_10MBPS_TWO_NATIVE_ARMS_MEASURED"
save()
print("PLAN029B_B5_TRUE_SAME_VM_10MBPS_CPU_GIB_RSS_UDP_P99 "+
      json.dumps(result["comparison"],sort_keys=True),flush=True)
