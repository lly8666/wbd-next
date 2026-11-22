#!/usr/bin/env python3
"""H2293: same original Windows TX16 Rust DLL throughout FEC OFF/Fixed/OFF.
The only causal candidate is Normal FEC2 profile light (1% loss) or mild
(5% loss) under real symmetric kernel 200ms plus packet loss.

Never replace the original Go TLS process, original signed drivers, true
Wintun->ARM Rust TUN TCP, M1/M4, original packet accounting, or owned Stop.
Each stage is a fresh original Go TLS/Rust client on the SAME Windows Runner
with the SAME independent ARM relay and original GoTLS/Rust server. The
source-locked Windows Rust TX16/NPF candidate DLL stays identical in all legs.
The client-result summary is uploaded only AFTER all three stages complete.
"""
import contextlib
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time

import m0_h2276_three_runner_tcp as core

CANDIDATE_BUILD_SHA=os.environ.get("WBD_H2292_COMPILED_SOURCE_SHA",os.environ.get("GITHUB_SHA","NO_GITHUB_SHA"))
FEC_LOSS=int(os.environ.get("WBD_H2293_WEAK_LOSS_PCT","0"))
FEC_PROFILE="light" if FEC_LOSS==1 else "mild"
H2294_OFF_REPAIR=os.environ.get("WBD_H2294_OFF_REPAIR_ABA")=="1"
H2302_WINDOW_ABA=os.environ.get("WBD_H2302_WINDOW_ABA")=="1"
H2307_FIXED_FIRST=os.environ.get("WBD_H2307_FEC_FIXED_FIRST")=="1"
H2302_BASE_BYTES=int(os.environ.get("WBD_H2302_BASE_BYTES","2097152"))
H2302_TUNED_BYTES=int(os.environ.get("WBD_H2302_TUNED_BYTES","8388608"))
if H2302_WINDOW_ABA and (H2302_BASE_BYTES,H2302_TUNED_BYTES) not in (
    (2*1024*1024,8*1024*1024),
    (8*1024*1024,16*1024*1024),
    (8*1024*1024,2*1024*1024),
    (16*1024*1024,8*1024*1024)):
    # Historical H2303_WINDOW_ABA_ONLY_2_TO_8_OR_8_TO_16_MIB unit
    # retained; H2304 also tests two reverse signed kernel TCP contrasts.
    raise RuntimeError("H2304_UNSUPPORTED_2_8_16_MIB_WINDOW_CONTRAST")
def h2302_window_bytes(tag):
    if tag not in ("A_base","B_window","A_prime_base"):
        raise RuntimeError("H2303_UNKNOWN_WINDOW_STAGE")
    return H2302_TUNED_BYTES if tag=="B_window" else H2302_BASE_BYTES
if H2302_WINDOW_ABA and H2294_OFF_REPAIR:
    raise RuntimeError("H2302_WINDOW_AND_REPAIR_MUST_NOT_COEXIST")
if H2307_FIXED_FIRST and (H2302_WINDOW_ABA or H2294_OFF_REPAIR):
    raise RuntimeError("H2307_FEC_FIRST_MUST_ISOLATE_WINDOW_AND_REPAIR")
LEGS=(("A_fixed","B_off","A_prime_fixed") if H2307_FIXED_FIRST else
      ("A_base","B_window","A_prime_base") if H2302_WINDOW_ABA else
      ("A_off","B_repair","A_prime_off") if H2294_OFF_REPAIR else
      ("A_off","B_fixed","A_prime_off"))
ROOT=pathlib.Path("h2307-out" if H2307_FIXED_FIRST else
                  "h2302-out" if H2302_WINDOW_ABA else
                  "h2294-out" if H2294_OFF_REPAIR else "h2293-out")
H2286=pathlib.Path("h2286-out")
BINARY=pathlib.Path("result/wl-public/wbd_engine.dll")
ORIGINAL=ROOT/"original-verified-wbd_engine.dll"
CANDIDATE=pathlib.Path("result/h2292-candidate/wbd_engine.dll")
MANIFEST=pathlib.Path("result/h2292-candidate/h2291-windows-dll-manifest.json")
# The shared original product validator reads the source-locked manifest from
# the same directory as the currently active actual Windows Rust DLL.
ACTIVE_MANIFEST=BINARY.parent/"h2291-windows-dll-manifest.json"


def require(ok,reason):
    core.require(ok,"H2293_"+reason)


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




def owned_wsl_liveness_marker(group):
    """One Windows-owned Ubuntu guest sleep, scoped to this exact CI run/group."""
    require(group in ("a","b"),"GUEST_KEEPER_GROUP")
    run=os.environ.get("GITHUB_RUN_ID","")
    require(run.isdecimal() and 1<=len(run)<=20,"GUEST_KEEPER_RUN_ID")
    return "/tmp/h2293-"+run+"-"+group+"-wsl-keeper.pid"


def wsl_probe_keeper(marker):
    from m0_h2285_windows_wsl_route import wsl
    # A missing file/PID is evidence the guest may have been reset.
    # Kernel boot ID is independent corroboration.
    result=wsl("sh","-c",
           "test -s "+marker+" && kill -0 $(cat "+marker+") && "
           "cat /proc/sys/kernel/random/boot_id",timeout=18,tolerate=True)
    if result.returncode:
        return None
    value=result.stdout.strip()
    return value if len(value)==36 else None


def start_owned_wsl_liveness(group):
    require(os.name=="nt","ONLY_WINDOWS_ORIGINAL_GUEST_KEEPER")
    marker=owned_wsl_liveness_marker(group)
    # Original Windows Npcap emits L2 to Ubuntu eth0; the guest must
    # survive even when all short WSL iptables command processes exit.
    # Run-owned pipe: Linux cat remains resident until the exact Windows
    # caller closes stdin. Shell '$$' is the real Linux PID; a literal
    # '$' breaks the owned guest liveness admission. Preserve both dollars.
    child=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
        "sh","-c","umask 077; echo $$ > "+marker+"; exec cat"],
        stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    boot=None
    try:
        for _ in range(30):
            if child.poll() is not None:
                raise RuntimeError("H2293_WSL_GUEST_KEEPER_EXITED_DURING_START")
            boot=wsl_probe_keeper(marker)
            if boot:
                break
            time.sleep(.4)
        require(bool(boot),"WINDOWS_REAL_WSL_GUEST_RESIDENT_PID_NOT_APPLIED")
        print("H2293_REAL_WSL_KERNEL_KEEPALIVE_STARTED "+
              json.dumps({"group":group,"boot_id":boot,
                          "pid_file":marker,"original_wbd_data":False}),
              flush=True)
        return child,marker,boot
    except Exception:
        if child.poll() is None:
            child.terminate()
        raise


def require_owned_wsl_liveness(child,marker,boot,tag):
    current=wsl_probe_keeper(marker)
    require(child.poll() is None and current==boot,
            "GUEST_WSL_KERNEL_LIVENESS_LOST_BEFORE_OR_DURING_"+tag)
    return {"stage":tag,"guest_boot_id_unchanged":True,
            "test_owned_resident_linux_pid_alive":True}


def stop_owned_wsl_liveness(child,marker):
    from m0_h2285_windows_wsl_route import wsl
    # Close only our own WSL cat stdin: a kernel EOF, not an assumed kill.
    # Verify the original marker PID really disappeared before claiming Stop.
    try:
        require(child.poll() is None and child.stdin is not None,
                "ORIGINAL_TEST_GUEST_KEEPER_PID_NOT_STOPPED")
        child.stdin.close()
        child.wait(timeout=18)
        v=wsl("sh","-c",
              "test -s "+marker+" && pid=$(cat "+marker+") && "
              "! kill -0 $pid 2>/dev/null && rm -f "+marker,
              timeout=18,tolerate=True)
        require(v.returncode==0,"ORIGINAL_TEST_GUEST_KEEPER_PID_NOT_STOPPED")
        v=wsl("sh","-c","test ! -e "+marker,timeout=18,tolerate=True)
        require(v.returncode==0,"GUEST_KEEPER_PID_FILE_NOT_REMOVED")
        print("H2293_REAL_WINDOWS_OWNED_GUEST_KEEPALIVE_STOP_VERIFIED",
              flush=True)
        return True
    finally:
        if child.poll() is None:
            child.terminate()


def native_underlay_preflight(group):
    """Fail DERP before downloading Ubuntu WSL2 or installing signed drivers.

    Exact Windows peer artifact is uploaded FIRST (H2292 existing fix), so
    Linux relay and ARM server may publish their real tailnet identities.
    Neither real Npcap nor GoTLS is started until the direct path qualifies.
    """
    own=core.load(core.ROOT/"client-peer.json")
    relay=core.load(pathlib.Path("h2276-peer/relay/relay-ready.json"))
    arm=core.load(pathlib.Path("h2276-peer/server/server-peer.json"))
    require(own["role"]=="client" and own["group"]==group,
            "EARLY_CLIENT_OWN_IDENTITY")
    relay_ip=core.verify(own,relay,"relay")
    arm_ip=core.verify(own,arm,"server")
    observed={"status":"INFRA_DIRECT_UNQUALIFIED",
              "source_sha":own["source_sha"],"run_id":own["run_id"],
              "group":group,
              "original_Windows_signed_Npcap_installed":False,
              "wsl_booted":False,
              "original_go_tls_rust_product_test":"NOT_RUN",
              "direct_candidate_probes":[]}
    good=False
    for attempt in range(6):
        relay_state=core.ping_class(relay_ip)
        arm_state=core.ping_class(arm_ip)
        observed["relay_path"]=relay_state
        observed["arm_path"]=arm_state
        observed["direct_candidate_probes"].append({
            "attempt":attempt+1,
            "relay":relay_state["status"],"arm":arm_state["status"]})
        good=(relay_state["status"]=="DIRECT_CANDIDATE" and
              arm_state["status"]=="DIRECT_CANDIDATE")
        if good:
            break
        time.sleep(3)
    observed["status"]=("H2293_DIRECT_TWO_PEERS_BEFORE_EXPENSIVE_DRIVERS"
                         if good else
                         "INFRA_DERP_BEFORE_EXPENSIVE_PRODUCT_START")
    core.save(ROOT/"network-preflight.json",observed)
    if not good:
        core.save(core.ROOT/"client-result.json",observed)
        raise RuntimeError("H2293_EARLY_DERP_NETWORK_NOT_PRODUCT_FAILURE")
    print("H2293_DIRECT_TWO_PEERS_QUALIFIED_BEFORE_WSL_AND_NPCAP "+
          json.dumps({"group":group,"source_sha":own["source_sha"]}),
          flush=True)



def verify_binary_archive():
    require(os.name=="nt","ONLY_REAL_WINDOWS2025")
    require(os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1" and
            os.environ.get("WBD_H2293_FEC_ABA")=="1" and
            (FEC_LOSS in (0,1,5) if H2302_WINDOW_ABA else FEC_LOSS in (1,5)) and
            os.environ.get("WBD_H2291_WINDOWS_TX_CANDIDATE")=="0",
            "H2293_EXPLICIT_PRODUCT_FEC2_ONLY_AND_ALL_TX16_FROZEN")
    ROOT.mkdir(exist_ok=True)
    src=json.loads(MANIFEST.read_text())
    require(src["source_sha"]==CANDIDATE_BUILD_SHA and
            src["trial_feature"]=="h2291_windows_tx_service" and
            src["original_go_exe_source_sha"]==
             "c5066db61fc51bafd7c2ad2def3029e615efa777",
            "EXACT_CANDIDATE_COMPILE_SOURCE")
    require(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()==src["dll_sha256"],
            "EXACT_CANDIDATE_PE_BYTES")
    frozen=json.loads(pathlib.Path("result/wl-public/windows-binary-manifest.json").read_text())
    default=json.loads(pathlib.Path("result/wl-public/h2292-baseline-dll-manifest.json").read_text())
    exe=pathlib.Path("result/wl-public/wbd-client-embedded.exe")
    require(frozen["source_sha"]==src["original_go_exe_source_sha"] and
            hashlib.sha256(exe.read_bytes()).hexdigest()==frozen["sha256"]["exe"],
            "EXACT_ORIGINAL_WINDOWS_GO_TLS_EXE")
    require(default["source_sha"]==CANDIDATE_BUILD_SHA and
            default["feature"]=="H2291_TX_SERVICE_DISABLED" and
            default["base_features"]==
             "m0_v4_embedded_go,m0_v4_probe,m0_fec2_owner_probe,fec2_product_record" and
            hashlib.sha256(BINARY.read_bytes()).hexdigest()==default["dll_sha256"],
            "DEFAULT_AND_CANDIDATE_SAME_COMPILED_RUST_FEATURE_BASE")
    require(not ACTIVE_MANIFEST.exists(),
            "H2292_BASELINE_MUST_NOT_START_WITH_CANDIDATE_MANIFEST")
    shutil.copy2(BINARY,ORIGINAL)
    return default["dll_sha256"],src["dll_sha256"]


def win_trial(group,relay,arm,ready):
    from m0_h2286_full_windows_product import true_windows_product
    preflight=json.loads((ROOT/"network-preflight.json").read_text())
    require(preflight["status"]=="H2293_DIRECT_TWO_PEERS_BEFORE_EXPENSIVE_DRIVERS" and
            preflight["group"]==group and
            preflight["source_sha"]==os.environ["GITHUB_SHA"],
            "REAL_DIRECT_UNDERLAY_EARLY_GATE_MISSING")
    old_sha,new_sha=verify_binary_archive()
    relay_ready=core.load(relay)
    # Keep the actual Ubuntu kernel resident throughout 3 original sessions.
    keeper,keeper_marker,keeper_boot=start_owned_wsl_liveness(group)
    results=[]
    original_candidate=os.environ.get("WBD_H2291_WINDOWS_TX_CANDIDATE")
    original_sha=os.environ.get("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA")
    original_fec_stage=os.environ.get("WBD_H2293_FEC_STAGE")
    original_repair_stage=os.environ.get("WBD_H2294_REPAIR_STAGE")
    original_window_bytes=os.environ.get("WBD_H2302_INNER_TCP_TEST_BYTES")
    kernel_liveness=[]
    try:
        for tag in LEGS:
            if H2302_WINDOW_ABA:
                os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"]=str(
                    h2302_window_bytes(tag))
            # H2292's genuine source-frozen TX16/NPF64KiB candidate
            # is used for ALL legs. Only original FEC2 cold admission varies.
            tuned=True
            fec_fixed=(tag=="B_fixed")
            if H2307_FIXED_FIRST:
                fec_fixed=tag in ("A_fixed","A_prime_fixed")
            if H2294_OFF_REPAIR:
                # Real Normal/FEC OFF in ALL three cold GoTLS/Rust sessions.
                fec_fixed=False
                os.environ["WBD_H2294_REPAIR_STAGE"]=(
                    "on" if tag=="B_repair" else "off")
            os.environ["WBD_H2293_FEC_STAGE"]="fixed" if fec_fixed else "off"
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
            kernel_liveness.append(require_owned_wsl_liveness(
                keeper,keeper_marker,keeper_boot,tag+"_pre_tls"))
            # Apply impairment BEFORE the genuine Windows cold Go
            # FakeTCP/TLS handshake; H2286 will also take fresh native
            # packet counters immediately before the original inner TCP.
            config=core.remote_shape(relay_ready,FEC_LOSS)
            require(config["loss"]==FEC_LOSS and config["netem"]["real_bidir_kernel_netem"],
                    "REAL_BIDIR_KERNEL_LOSS_BEFORE_ORIGINAL_TLS_NOT_APPLIED")
            started=time.monotonic()
            print("H2293_REAL_WINDOWS_FEC2_LEG_START "+
                  json.dumps({"leg":tag,"group":group,
                              "exact_candidate":tuned}),flush=True)
            true_windows_product(group,relay,arm,ready)
            kernel_liveness.append(require_owned_wsl_liveness(
                keeper,keeper_marker,keeper_boot,tag+"_post_tcp"))
            receipt=json.loads((H2286/"client-result.json").read_text())
            log=(H2286/"original-win-client.log").read_text(errors="replace")
            has_profile="H2291_ORIGINAL_WINDOWS_RUST_NPF_TX_SERVICE_PROFILE nqueue=1 queue_bytes=65536 max_frames=16 ready_only=1" in log
            # A Windows FEC2 fixed readback must be from the genuine
            # authenticated Rust owner, not CLI flags or the test's intent.
            readback=re.findall(
                r"WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=(\d+) revision=(\d+) applied=1",
                log)
            matched=[(int(p),int(rev)) for p,rev in readback
                     if int(p)==(0 if FEC_LOSS==1 else 1) and int(rev)>0]
            require(bool(matched)==fec_fixed,
                    "ORIGINAL_WINDOWS_FEC2_COLD_APPLIED_MUST_MATCH_REAL_LEG")
            if H2294_OFF_REPAIR:
                require(not readback,"H2294_FEC2_MUST_NEVER_BE_INSTALLED")
            telemetry=[]
            marker="WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "
            for line in log.splitlines():
                if marker in line:
                    telemetry.append(json.loads(line.split(marker,1)[1]))
            if H2294_OFF_REPAIR:
                require(bool(telemetry),"H2294_REAL_NATIVE_PACKET_TELEMETRY_MISSING")
                enabled=(tag=="B_repair")
                require(all(bool(t.get("actual_rust_m2_effective",{}).get(
                    "opportunistic_v3_enabled"))==enabled for t in telemetry),
                    "H2294_ORIGINAL_NATIVE_REPAIR_POLICY_NOT_APPLIED")
            if H2302_WINDOW_ABA:
                require(bool(telemetry) and all(
                    not v.get("actual_rust_m2_effective",{}).get("opportunistic_v3_enabled",True)
                    for v in telemetry),"H2302_OUTER_REPAIR_MUST_REMAIN_OFF_ALL_STAGES")
            native_repair_copies=max((int(t.get("frozen_ciphertext_retransmits",0))
                                      for t in telemetry),default=0)
            if H2294_OFF_REPAIR:
                # H2316 actual original Windows Rust M2 shadow and appearance
                # ACK readback. This is a Stop receipt, NOT proof of remote ACK.
                from m0_h2316_native_m2_stop import parse_native_m2_stop
                m2_stop=parse_native_m2_stop(log)
                require(m2_stop is not None and
                        (enabled or m2_stop["repair_polls"]==0) and
                        (enabled or m2_stop["queued"]==0),
                        "H2316_ORIGINAL_NATIVE_M2_CANDIDATE_ACCOUNTING_MISSING")
            else:
                m2_stop=None
            require(receipt["status"]==
                    "PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP" and
                    receipt["client_owned_stop"]=="PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP" and
                    receipt["source_sha"]==os.environ["GITHUB_SHA"] and
                    receipt["group"]==group and
                    receipt["product_tcp"]["sparse_echo_received"]==160 and
                    receipt["product_tcp"]["bulk_remote_received_bytes"]>0 and
                    receipt["windows_original_go_rust_cpu_stage"]["process_cpu_s_per_actual_arm_gib"]>0,
                    "ORIGINAL_TRIPLET_LEG_TCP_OR_WAL_OR_CPU_INCOMPLETE")
            require(has_profile and
                    receipt.get("h2291_original_windows_npf_queue_verified")==
                    (True if tuned else None),
                    "RUST_NPF16_ONLY_ON_B_LEG_NOT_REAL")
            for n in ("client-result.json","original-win-client.log",
                      "original-win-cpu.jsonl","win-inner-udp.log",
                      "original-product-ready.flag.udp.json"):
                maybe_copy(H2286/n,ROOT/tag/n)
            win_buffers=receipt["product_tcp"]["client_bulk_buffers_os"]
            if H2302_WINDOW_ABA:
                expected=int(os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"])
                require(len(win_buffers)==4 and all(
                    v["requested_bytes"]==expected and
                    v["sndbuf_os"]>=expected and v["rcvbuf_os"]>=expected
                    for v in win_buffers),"H2302_WINDOWS_REAL_TCP_SOCKET_READBACK")
                require(native_repair_copies==0,"H2302_REPAIR_OFF_MUST_HAVE_ZERO_COPIES")
            r={"stage":tag,"candidate_enabled":tuned,
               "h2302_window_test":H2302_WINDOW_ABA,
               "window_bytes_requested":(int(os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"])
                                         if H2302_WINDOW_ABA else None),
               "windows_actual_socket_buffers":win_buffers if H2302_WINDOW_ABA else None,
               "h2294_fec_off_only":H2294_OFF_REPAIR or H2302_WINDOW_ABA,
               "original_outer_repair_expected_on":(H2294_OFF_REPAIR and tag=="B_repair"),
               "actual_original_native_frozen_repair_packets":native_repair_copies,
               "h2316_original_m2_shadow_stop":m2_stop,
               "fec2_fixed_expected":fec_fixed,
               "fec2_profile_expected":(FEC_PROFILE if fec_fixed else "off"),
               "fec2_genuine_rust_owner_applied_readback":matched,
               "actual_impairment_pct_each_kernel_direction":FEC_LOSS,
               "real_kernel_drop_counts": {
                   direction: receipt["kernel_relay_qdisc"]["per_direction"][direction]["intentional_netem_drops"]
                   for direction in ("win_to_arm","arm_to_win")},
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
               "original_go_tls_rust_wal_stop":"PASS",
               "stage_elapsed_s_including_tls_setup":round(time.monotonic()-started,3)}
            results.append(r)
            core.save(ROOT/(tag+"-receipt.json"),r)
            print("H2293_REAL_WINDOWS_FEC2_LEG_PASS "+json.dumps(r),flush=True)
        a,b,c=results
        baseline=(a["tcp_mbps"]+c["tcp_mbps"])/2
        require(baseline>0,"A_PRIME_ZERO_RX")
        middle_cpu=(a["windows_original_process_cpu_s_per_gib"]+
                    c["windows_original_process_cpu_s_per_gib"])/2
        require(all(x["compiled_rust_dll_sha256"]==new_sha and
                    x["real_windows_npcap_64k_16_profile"] for x in results),
                "FEC_AB_THREE_SAME_WINDOWS_RUST_DLL_MUST_NEVER_SWITCH")
        if H2302_WINDOW_ABA:
            require([x["window_bytes_requested"] for x in results]==
                    [H2302_BASE_BYTES,H2302_TUNED_BYTES,H2302_BASE_BYTES] and
                    all(not x["fec2_fixed_expected"] and
                        not x["fec2_genuine_rust_owner_applied_readback"] and
                        not x["original_outer_repair_expected_on"] and
                        x["actual_original_native_frozen_repair_packets"]==0
                        for x in results),"H2302_WINDOW_ALONE_WITH_FEC_REPAIR_OFF")
        elif H2294_OFF_REPAIR:
            require(all(not x["fec2_fixed_expected"] and
                        not x["fec2_genuine_rust_owner_applied_readback"]
                        for x in results),
                    "H2294_FEC_OFF_MUST_NEVER_TURN_ON")
            require([x["original_outer_repair_expected_on"] for x in results]==
                    [False,True,False],
                    "H2294_ORIGINAL_SINGLE_COPY_REPAIR_ABA_FAILED")
        elif H2307_FIXED_FIRST:
            require([x["fec2_fixed_expected"] for x in results]==[True,False,True] and
                    [bool(x["fec2_genuine_rust_owner_applied_readback"]) for x in results]==
                    [True,False,True] and
                    all(not x["original_outer_repair_expected_on"] and
                        x["actual_original_native_frozen_repair_packets"]==0
                        for x in results),
                    "H2307_FIXED_OFF_FIXED_GENUINE_RUST_APPLICATION_MISSING")
        else:
            require([x["fec2_fixed_expected"] for x in results]==[False,True,False] and
                    [bool(x["fec2_genuine_rust_owner_applied_readback"]) for x in results]==
                    [False,True,False],"REAL_FEC2_FROZEN_ABA_MECHANISM_FAILED")
        result={"group":group,"source_sha":os.environ["GITHUB_SHA"],
                "candidate_binary_source_sha":CANDIDATE_BUILD_SHA,
                "original_go_exe_source_sha":"c5066db61fc51bafd7c2ad2def3029e615efa777",
                "status":("PASS_H2307_MEASURED_ORIGINAL_FEC2_FIXED_OFF_FIXED_SCOPED"
                          if H2307_FIXED_FIRST else
                          "PASS_H2302_MEASURED_ORIGINAL_TCP_WINDOW_ABA_FEC_OFF_SCOPED"
                          if H2302_WINDOW_ABA else
                          "PASS_H2294_MEASURED_FEC_OFF_OUTER_REPAIR_ABA_SCOPED"
                          if H2294_OFF_REPAIR else
                          "PASS_H2293_MEASURED_ORIGINAL_WINDOWS_FEC2_FIXED_ABA_SAME_RUST_SCOPED"),
                "real_bidir_kernel_loss_pct":FEC_LOSS,
                "fec2_fixed_profile":("off" if H2294_OFF_REPAIR else FEC_PROFILE),
                "fec_off_outer_repair_only":H2294_OFF_REPAIR or H2302_WINDOW_ABA,
                "outer_repair_true_native_copies_by_stage":{
                    x["stage"]:x["actual_original_native_frozen_repair_packets"]
                    for x in results},
                "original_rust_binary_identical_all_legs":True,
                "original_wsl_kernel_boot_id":keeper_boot,
                "owned_wsl_residency_observed":kernel_liveness,
                "stages":results,"comparison":{
                    "B_vs_same_vm_baseline_goodput_pct":round(
                        100*(b["tcp_mbps"]/baseline-1),3),
                    "B_vs_same_vm_baseline_cpu_s_per_gib_pct":round(
                        100*(b["windows_original_process_cpu_s_per_gib"]/middle_cpu-1),3),
                    "B_vs_worse_A_P99_ms":b["p99_ms"]-max(a["p99_ms"],c["p99_ms"]),
                    "default_go_rust_product_promoted":False,
                    "original_arm_server_same_vm":True,
                    "repeated_stop_per_leg":True,
                    "FEC2_causal_gain_hypothesis_not_automatic_pass":True,
                    "other_modes_or_physical_hosts":"NOT_RUN"}}
        core.save(ROOT/"three-leg-result.json",result)
        # Cross-runner ARM/relay consumers still receive their original
        # scoped true TCP/CPU/Stop receipt, plus all three actual stage facts.
        last=json.loads((H2286/"client-result.json").read_text())
        result_key=("h2307_same_vm_original_fec2_fixed_off_fixed" if H2307_FIXED_FIRST else
                    "h2302_same_vm_tcp_window_abaprime" if H2302_WINDOW_ABA else
                    "h2294_same_vm_original_product_fecoff_repair_abaprime"
                    if H2294_OFF_REPAIR else
                    "h2293_same_vm_original_product_fec2_abaprime")
        last[result_key]=result
        core.save(core.ROOT/"client-result.json",last)
        core.save(H2286/"client-result.json",last)
        print(("H2302_TCP_WINDOW_THREE_REAL_LEGS_COMPLETE" if H2302_WINDOW_ABA else
               "H2294_FEC_OFF_REPAIR_THREE_REAL_LEGS_COMPLETE" if H2294_OFF_REPAIR
               else "H2293_TWO_INDEPENDENT_TRIPLET_WINDOWS_FEC2_THREE_REAL_LEGS_COMPLETE"),flush=True)
    finally:
        primary_exc=sys.exc_info()[0]
        keeper_stop_error=None
        try:
            core.save(ROOT/"guest-liveness-at-stop.json",{
                "source_sha":os.environ.get("GITHUB_SHA",""),
                "guest_boot_id_initial":keeper_boot,
                "guest_boot_id_current":wsl_probe_keeper(keeper_marker),
                "resident_while_testing":kernel_liveness,
                "original_product_status":"MEASURED" if len(results)==3 else
                    "NOT_VERIFIED_COMPLETE"})
        except Exception:
            pass
        try:
            stop_owned_wsl_liveness(keeper,keeper_marker)
        except Exception as stop_error:
            keeper_stop_error=stop_error
            with contextlib.suppress(Exception):
                core.save(ROOT/"guest-keeper-stop-error.json",{
                    "status":"FAIL_TEST_OWNED_WSL_KEEPER_STOP",
                    "error_type":type(stop_error).__name__,
                    "error":str(stop_error)[-400:]})
        # Never leave candidate DLL installed in this test job after Stop.
        if ORIGINAL.exists():
            shutil.copy2(ORIGINAL,BINARY)
        ACTIVE_MANIFEST.unlink(missing_ok=True)
        if original_candidate is None:
            os.environ.pop("WBD_H2291_WINDOWS_TX_CANDIDATE",None)
        else:
            os.environ["WBD_H2291_WINDOWS_TX_CANDIDATE"]=original_candidate
        if original_fec_stage is None:
            os.environ.pop("WBD_H2293_FEC_STAGE",None)
        else:
            os.environ["WBD_H2293_FEC_STAGE"]=original_fec_stage
        if original_window_bytes is None:
            os.environ.pop("WBD_H2302_INNER_TCP_TEST_BYTES",None)
        else:
            os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"]=original_window_bytes
        if original_repair_stage is None:
            os.environ.pop("WBD_H2294_REPAIR_STAGE",None)
        else:
            os.environ["WBD_H2294_REPAIR_STAGE"]=original_repair_stage
        if original_sha is None:
            os.environ.pop("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA",None)
        else:
            os.environ["WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA"]=original_sha
        if primary_exc is None and keeper_stop_error is not None:
            raise keeper_stop_error


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
            os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1" and
            os.environ.get("WBD_H2293_FEC_ABA")=="1" and
            (FEC_LOSS in (0,1,5) if H2302_WINDOW_ABA else FEC_LOSS in (1,5)),
            "ARM_TRUE_THREE_LEG_MODE")
    own=arm.own_meta(group)
    relay=core.load(pathlib.Path("h2276-peer/relay/relay-ready.json"))
    core.verify(own,relay,"relay")
    all_stages=[]
    for i,tag in enumerate(LEGS):
        if H2302_WINDOW_ABA:
            os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"]=str(
                h2302_window_bytes(tag))
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
        if H2302_WINDOW_ABA:
            expected=int(os.environ["WBD_H2302_INNER_TCP_TEST_BYTES"])
            marker="M029_H2271_NATIVE_TCP_SERVER_DONE "
            server_rows=[json.loads(s.split(marker,1)[1])
                for s in (arm.ROOT/"tcp-inner-server.log").read_text(errors="replace").splitlines()
                if marker in s]
            require(len(server_rows)==1,"H2302_ARM_TCP_READBACK_MISSING")
            bufs=server_rows[0]
            require(bufs["listener_buffers_os"]["requested_bytes"]==expected and
                    bufs["listener_buffers_os"]["rcvbuf_os"]>=expected and
                    len(bufs["accepted_bulk_buffers_os"])==4 and
                    all(v["requested_bytes"]==expected and v["rcvbuf_os"]>=expected
                        for v in bufs["accepted_bulk_buffers_os"]),
                    "H2302_REAL_ARM_ACCEPTED_TCP_RCVBUF_NOT_APPLIED")
            r["h2302_window_bytes_requested"]=expected
            r["h2302_real_arm_tcp_socket_readback"]=bufs
        all_stages.append(r)
        core.save(arm.ROOT/("server-"+tag+".json"),r)
        for n in ("tcp-inner-server.log","tcp-tun-headers.log",
                  "tcp-passive-headers.json","tcpdump-stderr.log"):
            maybe_copy(arm.ROOT/n,arm.ROOT/tag/n)
        print("H2293_REAL_ARM_FEC2_TCP_STAGE_DONE "+
              json.dumps({"stage":tag,"group":group}),flush=True)
    summary=dict(all_stages[-1],
                 h2293_arm_server_three_original_tcp_stages=all_stages,
                 h2293_same_arm_original_go_tls_rust_server=True,
                 h2293_actual_bidir_loss_pct=FEC_LOSS)
    if H2302_WINDOW_ABA:
        summary.update(h2302_arm_server_three_original_tcp_stages=all_stages,
                       h2302_same_arm_original_go_tls_rust_server=True)
    if H2294_OFF_REPAIR:
        summary.update(h2294_arm_server_three_original_tcp_stages=all_stages,
                       h2294_same_arm_original_go_tls_rust_server=True,
                       h2294_actual_bidir_loss_pct=FEC_LOSS)
    core.save(arm.ROOT/"server-result.json",summary)
    print(("H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE" if H2302_WINDOW_ABA else
           "H2294_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE" if H2294_OFF_REPAIR
           else "H2293_REAL_ARM_TUN_THREE_FEC2_LOSS_TCP_STAGES_DONE"),flush=True)


def main():
    if len(sys.argv)<3:
        raise SystemExit("H2292 role client <group> <relay> <armpeer> <armproductready> / arm <group>")
    role,group=sys.argv[1:3]
    require(group in ("a","b"),"GROUP")
    if role=="arm":
        require(len(sys.argv)==3,"ARM_ARGS")
        arm_trial(group)
    elif role=="preflight":
        require(len(sys.argv)==3,"EARLY_CLIENT_UNDERLAY_ARGS")
        native_underlay_preflight(group)
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
             "status":"FAIL_H2293_REAL_ORIGINAL_WINDOWS_FEC2_LOSS_NOT_PERF_PASS",
             "error_type":type(error).__name__,"error":str(error)[-800:]})
        raise
