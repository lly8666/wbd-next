#!/usr/bin/env python3
"""Same Windows runner A->B->B->A. Both variants are Rust NativeOwner, never legacy Go.
Independent real TLS/driver/WSL2/60s packet measurement and BOTH owned Stops per leg.
Report any red leg; do not replace failed data with other legs or simulated metrics.
"""
import hashlib,json,os,pathlib,shutil,subprocess,sys,time
from m0_wl_mode_evidence import capture_mode_evidence_baseline,archive_mode_evidence
from m0_wl_perf_v2_config import read_scenario
from m0_wl_native_abba_prepare import PAIRS,verify_pairs,sha

ROOT=pathlib.Path.cwd()
OUT=ROOT/"result"/"wl-public"
ABBA=OUT/"wl-native-abba"
WIN_NAMES=("wbd-client-embedded.exe","wbd_engine.dll")
LINUX_NAMES=("wbd-v4-server","wbd-v4-client","libwbd_engine.so")
CLEAR_NAMES=("report.json","windows-original-go-rust-process-1hz.jsonl",
  "wl-n0-windows-app.json","wl-n0-linux-app.json",
  "wl-n0-netem-after.json","wl-n0-netem-before.json",
  "windows-cpu-audit.json","wl-v2-scenario.json")
def gates(report,w,l):
    v=report.get("WL_V2") or {}
    frac=v.get("first_delivery_fraction") or {}
    offered=v.get("offered_mbps") or {}
    d=l.get("udp_socket_probe_deltas") or {}
    raw=d.get("linux_raw_socket_deltas") or {}
    owners=(l.get("udp_socket_probe_end") or {}).get("linux_raw_socket_owners") or {}
    raw_ok=bool(raw) and set(raw)==set(owners) and all(
        value.get("drops_delta")==0 for value in raw.values())
    udpok=d.get("linux_socket_udp_drops_delta")==0
    tc=report.get("wl_n0_tc_after") or {}
    q=tc.get("ifb") if isinstance(tc,dict) else None
    # Note: qdisc readback from e2e is raw "after" (not cumulative delta).
    # Linux freshly arms actual qdiscs within each leg, so drops0 is exact.
    qdisc={"status":"NOT_MEASURED"}
    if (OUT/"wl-n0-netem-after.json").exists():
        try:
            data=json.loads((OUT/"wl-n0-netem-after.json").read_text())
            fields={}
            for kind in ("ifb","eth0"):
                qds=[v for v in data.get(kind,[]) if v.get("kind")=="netem"]
                if len(qds)!=1:raise ValueError("ambiguous netem")
                fields[kind]={"drops":qds[0].get("drops",qds[0].get("stats",{}).get("drops")),
                              "packets":qds[0].get("packets",qds[0].get("stats",{}).get("packets"))}
            qdisc=fields
        except (OSError,ValueError,TypeError,KeyError):
            pass
    tc_ok=(all(isinstance(qdisc.get(d),dict) and
        qdisc[d].get("drops")==0 and (qdisc[d].get("packets") or 0)>0
        for d in ("ifb","eth0")))
    delivery_ok=(all(isinstance(frac.get(side),(int,float)) and
        frac[side]>=0.999 for side in ("windows","linux")))
    offer_ok=(all(isinstance(offered.get(side),(int,float)) and
        offered[side]>=142.5 for side in ("windows","linux")))
    status=(report.get("mode_public")=="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal" and
        report.get("stop")=="PASS_BOTH_OWNED" and
        v.get("status")=="MEASURED_BOTH_OS_KERNEL" and
        v.get("owned_stop")=="PASS_BOTH_OWNED")
    return {"native_stop_and_mode":status,"delivery_ge_99_9_both":delivery_ok,
            "offer_ge_95pct_150m_both":offer_ok,
            "linux_owned_raw_socket_kernel_drops_zero":raw_ok,
            "linux_fixture_udp_socket_drops_zero":udpok,
            "real_tc_drops_zero":tc_ok,
            "kernel_tc":qdisc}
def cpu_measure(report,w,l):
    c=report.get("windows_cpu_audit") or {}
    total=(c.get("process_cpu_s") or {}).get("total")
    kernels=(c.get("process_cpu_s") or {}).get("kernel")
    user=(c.get("process_cpu_s") or {}).get("user")
    window=c.get("elapsed_s")
    delivered=float(w.get("received_first_payload_bytes",0))+float(l.get("received_first_payload_bytes",0))
    gb=delivered/1e9
    top=c.get("top_threads_by_lower_bound_cpu") or []
    roles={}
    for t in top:
        role=t.get("rust_worker_role")
        if role in ("TX","RX"):
            roles[role]={"tid":t.get("tid"),
                         "sampled_top6_cpu_lower_bound_s":t.get("cpu_s_lower_bound"),
                         "sampled_top6_kernel_lower_bound_s":t.get("kernel_s_lower_bound"),
                         "sampled_top6_user_lower_bound_s":t.get("user_s_lower_bound")}
    return {"status":c.get("status","NOT_MEASURED"),
            "process_cpu_s":total,"kernel_cpu_s":kernels,"user_cpu_s":user,
            "cpu_sample_window_s":window,"first_delivered_payload_gb":round(gb,6),
            "cpu_seconds_per_first_delivered_gb":
                round(total/gb,6) if isinstance(total,(int,float)) and gb>0 else None,
            "worker_roles_from_os_ids":roles,
            "cpu_scope":"SAME_WINDOWS_EXE_GO_PLUS_RUST_AND_CHARGED_KERNEL_NOT_DRIVER_ISR_DPC"}
def decision(legs):
    if len(legs)!=4 or [x["variant"] for x in legs]!=list("ABBA"):
        return {"decision":"INCONCLUSIVE","reason":"incomplete ABBA sequence"}
    if any(not x["stop_verified"] for x in legs):
        return {"decision":"ROLL_BACK_B","reason":"any leg lacks both owned Stops"}
    fails=[x["leg"] for x in legs if not x["qualified"]]
    a=[x for x in legs if x["variant"]=="A"]
    b=[x for x in legs if x["variant"]=="B"]
    if any(not x["qualified"] for x in b):
        return {"decision":"ROLL_BACK_B","reason":"B failed real delivery, offer, kernel drop or Stop",
                "failed_legs":fails}
    if any(not x["qualified"] for x in a):
        return {"decision":"INCONCLUSIVE","reason":"baseline A failed on same runner",
                "failed_legs":fails}
    am=[x["cpu"]["cpu_seconds_per_first_delivered_gb"] for x in a]
    bm=[x["cpu"]["cpu_seconds_per_first_delivered_gb"] for x in b]
    if any(x is None or x<=0 for x in am+bm):
        return {"decision":"INCONCLUSIVE","reason":"per-leg original EXE CPU/receipt not measured"}
    av=sum(am)/2;bv=sum(bm)/2
    # A-B-B-A cancels a first-order linear same-host drift. This is a
    # paired run comparison, not a proof across machines/physical conditions.
    relative=bv/av-1
    return {"decision":"KEEP_B" if relative<=-0.05 else "ROLL_BACK_B",
            "reason":"B reliably qualifies and has >=5% ABBA-normalized CPU benefit"
                if relative<=-0.05 else "B has no >=5% ABBA-normalized CPU benefit",
            "a_cpu_s_per_delivered_gb":round(av,6),
            "b_cpu_s_per_delivered_gb":round(bv,6),
            "relative_b_vs_a":round(relative,6),
            "each_leg_measurement":list(zip(("A1","B1","B2","A2"),[round(x,5) for x in am[:1]+bm+am[1:]]))}
def run():
    if os.environ.get("WBD_WL_ABBA_NATIVE")!="1":
        raise RuntimeError("ABBA control flag is required")
    if os.environ.get("WBD_WL_PUBLIC_MODES")!="normal" or os.environ.get("WBD_WL_PERF_AB")!="0":
        raise RuntimeError("ABBA is Rust Normal only, not original Go steady A/B")
    sc=os.environ.get("WBD_WL_V2_SCENARIO")
    if sc!="scenarios/wl-normal-150m-300ms-0loss-60s.json":
        raise RuntimeError("wrong ABBA scenario")
    scenario=read_scenario(ROOT/sc)
    if scenario["duration_s"]!=60 or scenario["scenario_sha256"]!="e22a96fbd4d6de2b4dc581d7013b343e61f5775298480e185c7a5562906d516e":
        raise RuntimeError("wrong ABBA exact scenario")
    pool=OUT/"abba-bin"
    if any(not (pool/k/"windows"/"windows-binary-manifest.json").exists() for k in PAIRS):
        raise RuntimeError("missing prepared exact binary manifests")
    verified=verify_pairs(pool)
    ABBA.mkdir(exist_ok=True,parents=True)
    (ABBA/"source-identity.json").write_text(json.dumps(verified,indent=2)+"\n")
    legs=[]
    try:
        for index,variant in enumerate("ABBA",1):
            label=f"{index}-{variant}"
            print("WL_RUST_NATIVE_SAME_VM_ABBA_START "+label,flush=True)
            # This job's driver, WSL2, network adapter & observer are kept.
            # Binary swap only after fully joined prior Stop. Fail closed.
            for fn in WIN_NAMES:
                src=pool/variant/"windows"/fn
                dst=OUT/fn
                shutil.copy2(src,dst)
                if sha(dst)!=verified[variant]["sha256"][fn]:
                    raise RuntimeError(label+" Windows product mutation")
            for fn in LINUX_NAMES:
                src=pool/variant/"linux"/fn
                dst=ROOT/"linux-product"/fn
                dst.parent.mkdir(exist_ok=True)
                shutil.copy2(src,dst)
                if sha(dst)!=verified[variant]["sha256"][fn]:
                    raise RuntimeError(label+" Linux product mutation")
            for name in CLEAR_NAMES:
                (OUT/name).unlink(missing_ok=True)
            # A left-over WAL or Linux server PID after a successful Stop
            # would be a real ownership issue; never force-delete to mask it.
            baseline=capture_mode_evidence_baseline(OUT)
            env=os.environ.copy()
            env["WBD_WL_PUBLIC_MODE"]="normal"
            env["WBD_WL_V2_CPU_AUDIT"]="1"
            env["LINUX_BINARY_SRC"]=PAIRS[variant]["source"]
            env["WBD_WL_BINARY_SOURCE"]=PAIRS[variant]["source"]
            env["WBD_WL_PERF_AB_GO_STEADY"]="0"
            t=time.monotonic()
            rc=subprocess.run([sys.executable,"-u",
                "tools/m0_wl_public_normal_e2e.py"],env=env).returncode
            elapsed=time.monotonic()-t
            p=OUT/"report.json"
            report=json.loads(p.read_text()) if p.is_file() else {}
            wl=OUT/"wl-n0-windows-app.json"
            ll=OUT/"wl-n0-linux-app.json"
            w=json.loads(wl.read_text()) if wl.is_file() else {}
            l=json.loads(ll.read_text()) if ll.is_file() else {}
            leg_folder=ABBA/label
            leg_folder.mkdir(parents=True,exist_ok=True)
            artifact=archive_mode_evidence(OUT,"normal",env["GITHUB_SHA"],
                report,rc,baseline=baseline)
            shutil.copytree(artifact.parent,leg_folder/"redacted-mode-results",
                dirs_exist_ok=True)
            for name in ("wl-n0-netem-before.json","wl-v2-scenario.json","windows-cpu-audit.json"):
                file=OUT/name
                if file.exists():shutil.copy2(file,leg_folder/name)
            gate=gates(report,w,l) if w and l else {"status":"NOT_MEASURED"}
            cpu=cpu_measure(report,w,l) if w and l else {"status":"NOT_MEASURED"}
            qualified=(rc==0 and all(gate.get(k) is True for k in
                ("native_stop_and_mode","delivery_ge_99_9_both",
                 "offer_ge_95pct_150m_both",
                 "linux_owned_raw_socket_kernel_drops_zero",
                 "linux_fixture_udp_socket_drops_zero","real_tc_drops_zero")))
            leg={"leg":label,"variant":variant,"compiled_source_sha":PAIRS[variant]["source"],
                 "runner_name":os.environ.get("RUNNER_NAME"),
                 "runner_os":os.environ.get("RUNNER_OS"),
                 "runner_id":os.environ.get("RUNNER_TRACKING_ID"),
                 "scenario_sha256":scenario["scenario_sha256"],
                 "elapsed_s":round(elapsed,3),"process_exit_code":rc,
                 "stop_verified":report.get("stop")=="PASS_BOTH_OWNED",
                 "qualified":qualified,"gates":gate,"cpu":cpu,
                 "v2":report.get("WL_V2",{}),
                 "business_udp_rtt_p99_ms":{
                   "windows":(w.get("business_udp_rtt") or {}).get("p99_ms"),
                   "linux":(l.get("business_udp_rtt") or {}).get("p99_ms")},
                 "app_missing_packets":{
                   "windows":l.get("sent_packets",0)-w.get("received_first_packets",0),
                   "linux":w.get("sent_packets",0)-l.get("received_first_packets",0)},
                 "source_identity_sha256":verified[variant]["sha256"],
                 "evidence_dir":f"{label}/redacted-mode-results"}
            (leg_folder/"leg.json").write_text(json.dumps(leg,indent=2)+"\n")
            legs.append(leg)
            (ABBA/"progress.json").write_text(json.dumps(legs,indent=2)+"\n")
            print(f"WL_RUST_NATIVE_SAME_VM_ABBA_END {label} qualified={qualified} stop={leg['stop_verified']} process_cpu_s={cpu.get('process_cpu_s')}",flush=True)
            # Separate a load-performance FAIL from an owner safety FAIL.
            # Only owner Stop permits starting another product on same guest.
            if not leg["stop_verified"]:break
    finally:
        d=decision(legs)
        summary={"type":"SAME_RUNNER_RUST_NATIVE_ABBA","order":"ABBA",
            "scenario_sha256":scenario["scenario_sha256"],
            "compiled_product_source_a":PAIRS["A"]["source"],
            "compiled_product_source_b":PAIRS["B"]["source"],
            "runner_name":os.environ.get("RUNNER_NAME"),
            "runner_tracking_id":os.environ.get("RUNNER_TRACKING_ID"),
            "legs":legs,"decision":d,
            "scope":"ONE_WINDOWS_JOB_ONE_WSL2_AND_DRIVER_INSTANCE_FOUR_REAL_PRODUCT_START_STOP",
            "limitations":["Four runs do not measure system-wide driver ISR/DPC CPU",
                "CPU whole EXE includes original cold Go and Rust DLL",
                "A/B swap was fully stopped, Linux peer binary source matched each Windows DLL",
                "No Windows app socket drops sampled directly"]}
        (ABBA/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        (OUT/"report.json").write_text(json.dumps(
            {"mode":"normal","mode_public":"ABBA_NOT_SINGLE_COMPILED_SOURCE",
             "stop":"ABBA_AGGREGATE_USE_PER_LEG","WL_ABBA":d,
             "source":os.environ.get("GITHUB_SHA")},indent=2)+"\n")
        (OUT/"normal-report.json").write_text((OUT/"report.json").read_text())
    if len(legs)!=4 or d["decision"]=="INCONCLUSIVE":
        raise SystemExit("ABBA_INCOMPLETE_OR_INCONCLUSIVE")
    print("WL_RUST_NATIVE_SAME_VM_ABBA_DECISION "+json.dumps(d),flush=True)
    if d["decision"]!="KEEP_B":
        raise SystemExit("ABBA_ROLL_BACK_B_NO_VERIFIED_BENEFIT_OR_REGRESSION")
if __name__=="__main__":run()
