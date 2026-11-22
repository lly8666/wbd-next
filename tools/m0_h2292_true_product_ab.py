#!/usr/bin/env python3
"""H2292 only: same-VM old/Rust-TX16/old original Windows-to-ARM product trial.

Never replace the original Go TLS process, original signed drivers, true
Wintun->ARM Rust TUN TCP, M1/M4, original packet accounting, or owned Stop.
Each stage is a fresh original Go TLS/Rust client on the SAME Windows Runner
with the SAME independent ARM relay and original GoTLS/Rust server. Only the
verified original or source-frozen candidate Rust DLL is swapped after Stop.
The client-result summary is uploaded only AFTER all three stages complete.
"""
import contextlib
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time

import m0_h2276_three_runner_tcp as core

CANDIDATE_BUILD_SHA=os.environ.get("WBD_H2292_COMPILED_SOURCE_SHA",os.environ.get("GITHUB_SHA","NO_GITHUB_SHA"))
LEGS=("A_default","B_tx16","A_prime")
ROOT=pathlib.Path("h2292-out")
H2286=pathlib.Path("h2286-out")
BINARY=pathlib.Path("result/wl-public/wbd_engine.dll")
ORIGINAL=ROOT/"original-verified-wbd_engine.dll"
CANDIDATE=pathlib.Path("result/h2292-candidate/wbd_engine.dll")
MANIFEST=pathlib.Path("result/h2292-candidate/h2291-windows-dll-manifest.json")
# The shared original product validator reads the source-locked manifest from
# the same directory as the currently active actual Windows Rust DLL.
ACTIVE_MANIFEST=BINARY.parent/"h2291-windows-dll-manifest.json"


def require(ok,reason):
    core.require(ok,"H2292_"+reason)


def maybe_copy(src,dst):
    if src.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)


def stage_control(relay,op,tag):
    """Use only pre-existing group-authenticated UDP control (no new Runner)."""
    require(op in ("h2292_arm_stage_ready","h2292_query_stage") and
            tag in LEGS,"STAGE_CONTROL_INPUT")
    payload={"token":relay["control_token"],"op":op,"stage":tag}
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        for attempt in range(3):
            sock.sendto(json.dumps(payload).encode(),
                        (relay["relay_ip"],core.CONTROL_PORT))
            try:
                data,remote=sock.recvfrom(2000)
            except socket.timeout:
                continue
            require(remote==(relay["relay_ip"],core.CONTROL_PORT),
                    "H2292_AUTH_CONTROL_SOURCE")
            r=json.loads(data)
            require(r.get("status") in ("H2292_REAL_ARM_STAGE_READY",
                                       "H2292_REAL_ARM_STAGE_STATE"),
                    "H2292_RELAY_REAL_ARM_STAGE_REJECT")
            return r
    raise RuntimeError("H2292_REAL_RELAY_UDP_STAGE_CONTROL_UNREACHABLE")


def wait_arm_stage(relay,tag):
    end=time.monotonic()+90
    while time.monotonic()<end:
        r=stage_control(relay,"h2292_query_stage",tag)
        if r["stage"]==tag:
            return
        # A later/foreign stage cannot count as our expected original ARM
        # TCP listener. Fail rather than quietly skip a product generation.
        require(r["stage"] is None or
                LEGS.index(r["stage"])<=LEGS.index(tag),
                "H2292_ARM_STAGE_PASSED_BEFORE_CLIENT_READY")
        time.sleep(.5)
    raise RuntimeError("H2292_ARM_REAL_TUN_TCP_STAGE_NOT_READY")



def h2312_mode():
    return os.environ.get("WBD_H2312_FACTOR","legacy")


def h2312_profile(text):
    import re
    m=re.search(r"PLAN029_H2311_NPF_STOP_PROFILE ([^\r\n]+)",text)
    if m is None:return None
    fields=("queue_calls","queue_frames_submitted","queue_bytes_submitted",
            "queue_bytes_copied","queue_short_calls","direct_calls",
            "direct_bytes_submitted","direct_frames_accepted","direct_errors",
            "npf_queue_bytes","npf_queue_packets")
    pairs={k:int(v) for k,v in re.findall(r"([a-z_]+)=(\d+)",m.group(1)) if k in fields}
    return pairs if len(pairs)==len(fields) else None


def verify_binary_archive():
    require(os.name=="nt","ONLY_REAL_WINDOWS2025")
    require(os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1",
            "EXPLICIT_H2292_TRUE_ABA_ONLY")
    ROOT.mkdir(exist_ok=True)
    factor=h2312_mode()
    require(factor in ("legacy","npf_only","tx_only"),"H2312_TRIAL_SELECTOR")
    src=json.loads(MANIFEST.read_text())
    expected_trial="h2291_windows_tx_service" if factor=="legacy" else (
        "h2311_windows_npf64_only" if factor=="npf_only" else "h2311_windows_tx16_only")
    require(src["source_sha"]==CANDIDATE_BUILD_SHA and
            src["trial_feature"]==expected_trial and
            src["original_go_exe_source_sha"]==
             "c5066db61fc51bafd7c2ad2def3029e615efa777" and
            (factor=="legacy" or (CANDIDATE_BUILD_SHA==os.environ["GITHUB_SHA"] and
                                   src.get("h2312_factor")==factor)),
            "EXACT_CANDIDATE_COMPILE_SOURCE")
    require(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()==src["dll_sha256"],
            "EXACT_CANDIDATE_PE_BYTES")
    frozen=json.loads(pathlib.Path("result/wl-public/windows-binary-manifest.json").read_text())
    default=json.loads(pathlib.Path("result/wl-public/h2292-baseline-dll-manifest.json").read_text())
    exe=pathlib.Path("result/wl-public/wbd-client-embedded.exe")
    require(frozen["source_sha"]==src["original_go_exe_source_sha"] and
            hashlib.sha256(exe.read_bytes()).hexdigest()==frozen["sha256"]["exe"],
            "EXACT_ORIGINAL_WINDOWS_GO_TLS_EXE")
    expected_base="H2291_TX_SERVICE_DISABLED" if factor=="legacy" else (
        "H2312_NPF8_16_TRACE" if factor=="npf_only" else "H2312_NPF16_64_TRACE")
    require(default["source_sha"]==CANDIDATE_BUILD_SHA and
            default["feature"]==expected_base and
            default["base_features"]==
             "m0_v4_embedded_go,m0_v4_probe,m0_fec2_owner_probe,fec2_product_record" and
            (factor=="legacy" or default.get("h2312_factor")==factor) and
            hashlib.sha256(BINARY.read_bytes()).hexdigest()==default["dll_sha256"],
            "DEFAULT_AND_CANDIDATE_SAME_COMPILED_RUST_FEATURE_BASE")
    require(not ACTIVE_MANIFEST.exists(),
            "H2292_BASELINE_MUST_NOT_START_WITH_CANDIDATE_MANIFEST")
    shutil.copy2(BINARY,ORIGINAL)
    return default["dll_sha256"],src["dll_sha256"]


def win_trial(group,relay,arm,ready):
    from m0_h2286_full_windows_product import true_windows_product
    old_sha,new_sha=verify_binary_archive()
    relay_ready=core.load(relay)
    results=[]
    original_candidate=os.environ.get("WBD_H2291_WINDOWS_TX_CANDIDATE")
    original_sha=os.environ.get("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA")
    try:
        for tag in LEGS:
            tuned=tag=="B_tx16"
            chosen=CANDIDATE if tuned else ORIGINAL
            shutil.copy2(chosen,BINARY)
            if tuned:
                # H2286.assert_original_binaries reads this exact path for
                # every fresh original Go/Rust session. H2292 first A passed
                # but B never started because this companion manifest was
                # left only under result/h2292-candidate/.
                shutil.copy2(MANIFEST,ACTIVE_MANIFEST)
            else:
                ACTIVE_MANIFEST.unlink(missing_ok=True)
            require(hashlib.sha256(BINARY.read_bytes()).hexdigest()==
                    (new_sha if tuned else old_sha) and
                    ACTIVE_MANIFEST.exists()==tuned,
                    "ACTUAL_DLL_AND_CANDIDATE_MANIFEST_NOT_AT_ACTIVE_LOCATION")
            os.environ["WBD_H2291_WINDOWS_TX_CANDIDATE"]="1" if tuned else "0"
            if tuned:
                os.environ["WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA"]=CANDIDATE_BUILD_SHA
            else:
                os.environ.pop("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA",None)
            # The previous real Win32 Go/Rust client must have FINISHED its
            # original Rust/WAL Stop before a new one is launched. Do not
            # erase user WAL state: the original owner is responsible.
            for name in ("original-product-ready.flag",
                         "original-product-ready.flag.udp.json"):
                (H2286/name).unlink(missing_ok=True)
            require(not (H2286/"owned-wal.json.n4-owned-wal").exists(),
                    "ORIGINAL_GO_RUST_OWNED_STOP_BEFORE_NEXT_STAGE")
            wait_arm_stage(relay_ready,tag)
            started=time.monotonic()
            print("H2292_REAL_ORIGINAL_GO_RUST_LEG_START "+
                  json.dumps({"leg":tag,"group":group,
                              "exact_candidate":tuned}),flush=True)
            true_windows_product(group,relay,arm,ready)
            receipt=json.loads((H2286/"client-result.json").read_text())
            log=(H2286/"original-win-client.log").read_text(errors="replace")
            has_profile="H2291_ORIGINAL_WINDOWS_RUST_NPF_TX_SERVICE_PROFILE nqueue=1 queue_bytes=65536 max_frames=16 ready_only=1" in log
            require(receipt["status"]==
                    "PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP" and
                    receipt["client_owned_stop"]=="PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP" and
                    receipt["source_sha"]==os.environ["GITHUB_SHA"] and
                    receipt["group"]==group and
                    receipt["product_tcp"]["sparse_echo_received"]==160 and
                    receipt["product_tcp"]["bulk_remote_received_bytes"]>0 and
                    receipt["windows_original_go_rust_cpu_stage"]["process_cpu_s_per_actual_arm_gib"]>0,
                    "ORIGINAL_TRIPLET_LEG_TCP_OR_WAL_OR_CPU_INCOMPLETE")
            factor=h2312_mode()
            if factor=="legacy":
                require(has_profile==tuned and
                        receipt.get("h2291_original_windows_npf_queue_verified")==
                        (True if tuned else None),
                        "RUST_NPF16_ONLY_ON_B_LEG_NOT_REAL")
                trace=None
            else:
                trace=h2312_profile(log)
                expect_bytes=65536 if (factor=="tx_only" or tuned) else 16384
                expect_frames=16 if (factor=="tx_only" or tuned) else 8
                require(trace is not None and
                        trace["npf_queue_bytes"]==expect_bytes and
                        trace["npf_queue_packets"]==expect_frames and
                        trace["queue_calls"]>0 and
                        trace["queue_frames_submitted"]>0 and
                        trace["queue_bytes_copied"]>0 and
                        trace["queue_bytes_copied"]<=trace["queue_bytes_submitted"] and
                        not has_profile and
                        receipt.get("h2291_original_windows_npf_queue_verified") is None,
                        "H2312_ORIGINAL_DRIVER_REAL_ACTUAL_TRACE_NOT_MATCHED")
            for n in ("client-result.json","original-win-client.log",
                      "original-win-cpu.jsonl","win-inner-udp.log",
                      "original-product-ready.flag.udp.json"):
                maybe_copy(H2286/n,ROOT/tag/n)
            r={"stage":tag,"candidate_enabled":tuned,
               "compiled_rust_dll_sha256":new_sha if tuned else old_sha,
               "arm_rx_bytes":receipt["product_tcp"]["bulk_remote_received_bytes"],
               "tcp_mbps":receipt["product_tcp"]["bulk_receiver_goodput_mbps"],
               "p99_ms":receipt["product_tcp"]["sparse_tcp_rtt_p99_ms"],
               "late_over_1s":receipt["product_tcp"]["sparse_tcp_late_1000ms"],
               "windows_original_process_cpu_s_per_gib":
                   receipt["windows_original_go_rust_cpu_stage"]["process_cpu_s_per_actual_arm_gib"],
               "windows_original_rust_tx_cpu_lower_bound":
                   receipt["windows_original_go_rust_cpu_stage"]["rust_tx_rx_top6_lower_bound_cpu_s"]["TX"],
               "relay_tailscaled_cpu_of_one_core_pct":
                   receipt["relay_tailscaled_and_host_cpu_stage"]["tailscaled_pct_of_one_cpu"],
               "valid_160_echo":True,
               "real_windows_npcap_64k_16_profile":has_profile,
               "h2312_factor":factor,"h2312_npf_service":trace,
               "original_go_tls_rust_wal_stop":"PASS",
               "stage_elapsed_s_including_tls_setup":round(time.monotonic()-started,3)}
            results.append(r)
            core.save(ROOT/(tag+"-receipt.json"),r)
            print("H2292_REAL_ORIGINAL_GO_RUST_LEG_PASS "+json.dumps(r),flush=True)
        a,b,c=results
        baseline=(a["tcp_mbps"]+c["tcp_mbps"])/2
        require(baseline>0,"A_PRIME_ZERO_RX")
        middle_cpu=(a["windows_original_process_cpu_s_per_gib"]+
                    c["windows_original_process_cpu_s_per_gib"])/2
        result={"group":group,"source_sha":os.environ["GITHUB_SHA"],
                "candidate_binary_source_sha":CANDIDATE_BUILD_SHA,
                "original_go_exe_source_sha":"c5066db61fc51bafd7c2ad2def3029e615efa777",
                "status":"PASS_H2292_SAME_WINDOWS_VM_ORIGINAL_GO_TLS_RUST_A_B_A_PRIME_SCOPED",
                "stages":results,"comparison":{
                    "B_vs_same_vm_baseline_goodput_pct":round(
                        100*(b["tcp_mbps"]/baseline-1),3),
                    "B_vs_same_vm_baseline_cpu_s_per_gib_pct":round(
                        100*(b["windows_original_process_cpu_s_per_gib"]/middle_cpu-1),3),
                    "B_vs_worse_A_P99_ms":b["p99_ms"]-max(a["p99_ms"],c["p99_ms"]),
                    "default_go_rust_product_promoted":False,
                    "original_arm_server_same_vm":True,
                    "repeated_stop_per_leg":True,
                    "unqualified_weak_loss_modes":"NOT_RUN"}}
        core.save(ROOT/"three-leg-result.json",result)
        # Cross-runner ARM/relay consumers still receive their original
        # scoped true TCP/CPU/Stop receipt, plus all three actual stage facts.
        last=json.loads((H2286/"client-result.json").read_text())
        last["h2292_same_vm_original_product_abaprime"]=result
        core.save(core.ROOT/"client-result.json",last)
        core.save(H2286/"client-result.json",last)
        print("H2292_SAME_TRIPLET_WINDOWS_ORIGINAL_PRODUCT_THREE_REAL_LEGS_COMPLETE",flush=True)
    finally:
        # Never leave candidate DLL installed in this test job after Stop.
        if ORIGINAL.exists():
            shutil.copy2(ORIGINAL,BINARY)
        ACTIVE_MANIFEST.unlink(missing_ok=True)
        if original_candidate is None:
            os.environ.pop("WBD_H2291_WINDOWS_TX_CANDIDATE",None)
        else:
            os.environ["WBD_H2291_WINDOWS_TX_CANDIDATE"]=original_candidate
        if original_sha is None:
            os.environ.pop("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA",None)
        else:
            os.environ["WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA"]=original_sha


def arm_restart_original_tun_udp(tag,own):
    import m0_h2286_arm_product as arm
    for n in ("udp-stop.flag","udp-stop.flag.udp.json"):
        (arm.ROOT/n).unlink(missing_ok=True)
    log=(arm.ROOT/("arm-inner-udp-"+tag+".log")).open("w")
    cmd=["sudo","-n","ip","netns","exec",arm.NETNS,
         sys.executable,"-u","tools/m0_h2286_inner_udp.py",
         arm.APP_IP,arm.APP_PEER,own["source_sha"],
         str(arm.ROOT/"udp-stop.flag")]
    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
    (arm.ROOT/"arm-inner-udp.pid").write_text(str(proc.pid)+"\n")
    try:
        for i in range(100):
            if "H2286_TRUE_OS_TUN_UDP_BIND" in (arm.ROOT/("arm-inner-udp-"+tag+".log")).read_text(errors="replace"):
                break
            if proc.poll() is not None:
                raise RuntimeError("H2292_REAL_ARM_RUST_TUN_UDP_BIND_FAILED")
            time.sleep(.2)
        else:
            raise RuntimeError("H2292_REAL_ARM_RUST_TUN_UDP_TIMEOUT")
    finally:
        log.close()


def arm_trial(group):
    import m0_h2286_arm_product as arm
    require(os.name=="posix" and
            os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1",
            "ARM_TRUE_THREE_LEG_MODE")
    own=arm.own_meta(group)
    relay=core.load(pathlib.Path("h2276-peer/relay/relay-ready.json"))
    core.verify(own,relay,"relay")
    all_stages=[]
    for i,tag in enumerate(LEGS):
        if i:
            arm_restart_original_tun_udp(tag,own)
        stage=stage_control(relay,"h2292_arm_stage_ready",tag)
        require(stage["stage"]==tag,"H2292_ACTUAL_REMOTE_ARM_STAGE_ACK")
        arm.check_server_and_run_app(group)
        r=json.loads((arm.ROOT/"server-result.json").read_text())
        require(r["tcp_inner_arm_server_finished"] and
                r["real_original_arm_go_tls_rust_tun_native_tcp"] and
                r["native_true_arm_tun_udp"]["real_native_os_udp_received"]>=12,
                "REAL_ARM_RUST_TUN_TCP_UDP_RECEIPT_MISSING")
        r["stage"]=tag
        all_stages.append(r)
        core.save(arm.ROOT/("server-"+tag+".json"),r)
        for n in ("tcp-inner-server.log","tcp-tun-headers.log",
                  "tcp-passive-headers.json","tcpdump-stderr.log"):
            maybe_copy(arm.ROOT/n,arm.ROOT/tag/n)
        print("H2292_REAL_INDEPENDENT_ARM_ORIGINAL_TUN_TCP_STAGE_DONE "+
              json.dumps({"stage":tag,"group":group}),flush=True)
    summary=dict(all_stages[-1],
                 h2292_arm_server_three_original_tcp_stages=all_stages,
                 h2292_same_arm_original_go_tls_rust_server=True)
    core.save(arm.ROOT/"server-result.json",summary)
    print("H2292_REAL_ARM_TUN_THREE_ORIGINAL_TCP_STAGES_DONE",flush=True)


def main():
    if len(sys.argv)<3:
        raise SystemExit("H2292 role client <group> <relay> <armpeer> <armproductready> / arm <group>")
    role,group=sys.argv[1:3]
    require(group in ("a","b"),"GROUP")
    if role=="arm":
        require(len(sys.argv)==3,"ARM_ARGS")
        arm_trial(group)
    elif role=="client":
        require(len(sys.argv)==6,"CLIENT_ARGS")
        win_trial(group,*sys.argv[3:])
    else:
        raise RuntimeError("H2292_INVALID_ROLE")


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        ROOT.mkdir(exist_ok=True)
        core.save(ROOT/"first-error.json",{"source_sha":os.environ.get("GITHUB_SHA",""),
             "status":"FAIL_H2292_REAL_ORIGINAL_PRODUCT_THREE_LEG_NOT_PERF_PASS",
             "error_type":type(error).__name__,"error":str(error)[-800:]})
        raise
