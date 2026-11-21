#!/usr/bin/env python3
"""H2286 full original Windows signed Npcap/Wintun+GoTLS/Rust to remote ARM.

Not Winsock outer socket. The only Winsock sockets are ORIGINAL Wintun 10.66/24
business traffic. Physical FakeTCP443 originates from ORIGINAL client Npcap
on a true Windows 2025 WSL2 vEthernet adapter. WSL2 + ARM relay use kernel
DNAT/conntrack only. A distinct ARM server runs original AF_PACKET GoTLS/Rust.
"""
import contextlib
import hashlib
import io
import ipaddress
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time

from m0_wl_native_resource_sampler import sample_windows_original_process
from m0_h2290_windows_hotpath_cpu import original_window_cpu

import m0_h2276_three_runner_tcp as core
import m0_h2285_windows_wsl_route as guestroute
import m0_wl_loss_tcp_probe as tcp

ROOT=pathlib.Path("h2286-out")
APP_IP="10.66.0.2"
APP_PEER="10.66.0.1"
GUEST_PORT=443
RELAY_PORT=18727
# Product inside REAL Wintun/TUN must NEVER inherit the outer/relay TCP port.
# Importing legacy m0_h2276_three_runner_tcp sets tcp.PORT=18727 globally!
INNER_TUN_TCP_PORT=45902


def require(cond,label):
    core.require(cond,"H2286_"+label)


def scope_nat_rules(win,guest,relay):
    require(ipaddress.ip_address(win).is_private and
            ipaddress.ip_address(guest).is_private and
            ipaddress.ip_address(relay) in core.TAIL,"WIN_GUEST_ARM_IDENTITY")
    return [
      ("-t","nat","-I","PREROUTING","1","-i","eth0",
       "-s",win+"/32","-d",guest+"/32","-p","tcp","--dport","443",
       "-j","DNAT","--to-destination",relay+":"+str(RELAY_PORT)),
      ("-t","nat","-I","POSTROUTING","1","-o","eth0",
       "-d",relay+"/32","-p","tcp","--dport",str(RELAY_PORT),
       "-j","MASQUERADE"),
      ("-I","FORWARD","1","-i","eth0","-o","eth0",
       "-s",win+"/32","-d",relay+"/32","-p","tcp",
       "--dport",str(RELAY_PORT),"-j","ACCEPT"),
      ("-I","FORWARD","1","-i","eth0","-o","eth0",
       "-s",relay+"/32","-d",win+"/32","-p","tcp",
       "--sport",str(RELAY_PORT),"-j","ACCEPT"),
    ]


def assert_original_binaries():
    p=pathlib.Path("result/wl-public")
    m=json.loads((p/"windows-binary-manifest.json").read_text())
    require(m["source_sha"]=="c5066db61fc51bafd7c2ad2def3029e615efa777",
            "FROZEN_WIN_BINARY_SOURCE_MANIFEST")
    h2291=os.environ.get("WBD_H2291_WINDOWS_TX_CANDIDATE")=="1"
    c=None
    if h2291:
        c=json.loads((p/"h2291-windows-dll-manifest.json").read_text())
        # H2292 reuses H2291's EXACT original compiled Rust DLL. The
        # workflow first checks that no crate/Go/ABI source changed between
        # that build SHA and this fixture-only test SHA. Do not falsify a
        # binary manifest's true compile source to match a new test commit.
        approved_source=(os.environ.get("WBD_H2291_CANDIDATE_BINARY_SOURCE_SHA",
                                        os.environ["GITHUB_SHA"])
                         if os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1"
                         else os.environ["GITHUB_SHA"])
        require(c["source_sha"]==approved_source and
                c["trial_feature"]=="h2291_windows_tx_service" and
                c["original_go_exe_source_sha"]==m["source_sha"],
                "H2291_EXACT_RUST_SOURCE_AND_ORIGINAL_GO_ABI_MANIFEST")
    original_ab=os.environ.get("WBD_H2292_TRUE_PRODUCT_ABA")=="1"
    baseline=None
    if original_ab and not h2291:
        baseline=json.loads((p/"h2292-baseline-dll-manifest.json").read_text())
        compiled_source=os.environ.get("WBD_H2292_COMPILED_SOURCE_SHA",os.environ["GITHUB_SHA"])
        require(baseline["source_sha"]==compiled_source and
                baseline["feature"]=="H2291_TX_SERVICE_DISABLED" and
                baseline["base_features"]==
                 "m0_v4_embedded_go,m0_v4_probe,m0_fec2_owner_probe,fec2_product_record",
                "H2292_REAL_RUST_DEFAULT_FEATURE_MATCHED_SOURCE")
    for filename,key in (("wbd-client-embedded.exe","exe"),
                         ("wbd_engine.dll","dll")):
        f=p/filename
        expected=(c["dll_sha256"] if h2291 and key=="dll" else
                  baseline["dll_sha256"] if baseline and key=="dll" else
                  m["sha256"][key])
        require(f.is_file() and f.stat().st_size>100000 and
                hashlib.sha256(f.read_bytes()).hexdigest()==expected,
                "WIN_NATIVE_EXE_DLL_ACTUAL_SHA256_"+key)
    require((p/"wintun.dll").is_file() and
            (p/"wpcap.dll").is_file(),"SIGNED_NATIVE_DRIVER_LIBRARY_ABSENT")
    service=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
        "-Command","(Get-Service npcap -ErrorAction Stop).Status.ToString()"],
        capture_output=True,text=True,timeout=14)
    require(service.returncode==0 and "Running" in service.stdout,
            "TRUE_SIGNED_NPCAP_DRIVER_SERVICE_NOT_RUNNING")
    return str((p/"wbd-client-embedded.exe").resolve())


def nat_packet_counters(win,guest,relay):
    facts={}
    for table,chain in (("nat","PREROUTING"),("nat","POSTROUTING"),
                        ("filter","FORWARD")):
        output=guestroute.wsl("iptables","-t",table,"-L",chain,
                               "-n","-v","-x",timeout=20).stdout
        rows=[]
        for line in output.splitlines():
            fields=line.split()
            if (len(fields)>=8 and fields[0].isdigit() and
                (win in line or guest in line or relay in line) and
                ("443" in line or str(RELAY_PORT) in line)):
                rows.append({"packets":int(fields[0]),"bytes":int(fields[1]),
                             "description":line[-300:]})
        facts[table+"_"+chain]=rows
    return facts


def original_win_client_args(exe,peer,server):
    root=pathlib.Path("result/wl-public")
    return [
      exe,"--native-v4-product","--control-stdin",
      "--server-ip",peer,"--server-port",str(GUEST_PORT),
      "--source-port","41031","--server-name","wbd-v4.example.test",
      "--route-key-hex-file",str(server/"route-key-private.hex"),
      "--tls-ca-pem",str(server/"cert.pem"),
      "--username","wbd-ci-native","--password","native-tls-ci-only",
      "--tunnel-id","102030405060708090a0b0c0d0e0f001",
      "--installation-id","445566778899aabbccddeeff00112233",
      "--lease4",APP_IP+"/32","--adapter","WBDWLMAIN",
      "--state-path",str(ROOT/"owned-wal.json"),
      "--mtu","1280","--lanes","1","--fec-mode","off","--fec-parity","0",
      "--fec.mode","off","--fec.profile","strong",
      "--route-mode","all","--outer-repair","off"
    ]


def process_ready(proc,path,marker,timeout_s):
    until=time.monotonic()+timeout_s
    while time.monotonic()<until:
        s=path.read_text(errors="replace") if path.exists() else ""
        if marker in s:
            require(proc.poll() is None,"ORIGINAL_WIN_WORKER_EXIT_AT_READY")
            return s
        if proc.poll() is not None:
            raise RuntimeError("H2286_ORIGINAL_GO_TLS_RUST_CLIENT_EXIT "+s[-1500:])
        time.sleep(.2)
    raise RuntimeError("H2286_ORIGINAL_WIN_CLIENT_NOT_AUTHENTICATED_READY "+
                       (path.read_text(errors="replace") if path.exists() else "")[-1600:])


def true_windows_product(group,relay_path,server_peer_path,server_ready_path):
    ROOT.mkdir(exist_ok=True)
    own=core.load(core.ROOT/"client-peer.json")
    require(os.name=="nt" and own["group"]==group and own["role"]=="client",
            "WINDOWS_TRUE_NATIVE_SOURCE")
    relay=core.load(relay_path)
    server=core.load(server_peer_path)
    relay_ip=core.verify(own,relay,"relay")
    arm_ip=core.verify(own,server,"server")
    ready=json.loads(pathlib.Path(server_ready_path).read_text())
    require(ready["group"]==group and ready["source_sha"]==own["source_sha"] and
            ready["run_id"]==own["run_id"] and
            ready["real_original_arm_go_tls_rust_running"] is True and
            ready["real_original_arm_tun_created"] is True,
            "ORIGINAL_ARM_REMOTE_SERVER_SOURCE_OR_TUN_NOT_READY")
    server_dir=pathlib.Path(server_ready_path).parent
    require(hashlib.sha256((server_dir/"cert.pem").read_bytes()).hexdigest()==
            ready["server_cert_sha256"] and
            len((server_dir/"route-key-private.hex").read_text().strip())==64,
            "ARM_SSL_PRIVATE_ROUTE_TEST_ARTIFACT_MISMATCH")
    exe=assert_original_binaries()
    env=os.environ.copy()
    owner=json.loads((ROOT/"windows-vethernet-owner.json").read_text())
    require(owner["source_sha"]==own["source_sha"] and
            owner["run_id"]==own["run_id"] and owner["group"]==group and
            owner["neighbor_installed"] and owner["hyperv_rule_installed"],
            "SIGNED_ORIGINAL_WINDOWS_WSL_NPF_NEIGHBOR_NOT_APPLIED")
    guest=guestroute.guest_eth0()
    win=guestroute.windows_guest_source(guest)
    require(guest==owner["guest_ip"] and win==owner["host_ip"],
            "REAL_WINDOWS_SOURCE_VS_SIGNED_NPF_OWNER_MISMATCH")
    env.update(WBD_PLAN024_NATIVE_VERIFIED_GUEST_MAC=owner["guest_mac"],
        WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4=guest,
        WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4=win,
        WBD_PLAN024_NATIVE_VERIFIED_IFINDEX=str(owner["interface_index"]))
    output={"source_sha":own["source_sha"],"run_id":own["run_id"],
            "group":group,"scope":"ORIGINAL_SIGNED_WIN2025_NPCAP_WINTUN_GO_TLS_RUST_TO_SEPARATE_ARM64_ORIGINAL_GO_RUST_TUN",
            "status":"NOT_RUN","real_windows_signed_npcap":True,
            "real_original_windows_exe_dll":True,"real_arm_server_source_match":True,
            "windows_real_vethernet_ip":win,"wsl_real_eth0_ip":guest,
            "arm_native_server_tail_ip":arm_ip,
            "client_relay_path":core.ping_class(relay_ip),
            "client_arm_path":core.ping_class(arm_ip),
            "no_windows_winsock_outer_substitution":True,
            "original_arm_server_product_receipt":"PENDING",
            "client_owned_stop":"PENDING"}
    core.save(ROOT/"client-result.json",output)
    require(output["client_relay_path"]["status"]=="DIRECT_CANDIDATE" and
            output["client_arm_path"]["status"]=="DIRECT_CANDIDATE",
            "NETWORK_DERP_UNQUALIFIED_NOT_PRODUCT")
    orig_forward=guestroute.wsl("sysctl","-n","net.ipv4.ip_forward").stdout.strip()
    installed=[]
    proc=None
    udp=None
    clientlog=ROOT/"original-win-client.log"
    prev_window=tcp.WINDOW_TEST_BYTES
    prev_bytes=tcp.BULK_MAX_BYTES
    prev_seconds=tcp.BULK_SEND_S
    prev_timeout=tcp.TIMEOUT_S
    prev_inner_tcp_port=tcp.PORT
    win32_cpu_stop=threading.Event()
    win32_cpu_sampler=None
    source_win_cpu_file=ROOT/"original-win-cpu.jsonl"
    try:
        guestroute.wsl("sysctl","-w","net.ipv4.ip_forward=1")
        for rule in scope_nat_rules(win,guest,relay_ip):
            guestroute.wsl("iptables","-w",*rule)
            installed.append(rule)
        cmd=original_win_client_args(exe,guest,server_dir)
        # No generated ACKs/READY; Go TLS & Rust own all original connections.
        with clientlog.open("w") as f:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=f,
                  stderr=subprocess.STDOUT,text=True,env=env)
        output["original_windows_pid"]=proc.pid
        # Read-only actual Win32 GetProcessTimes + Toolhelp GetThreadTimes;
        # no product callback or packet-path instrumentation.
        win32_cpu_sampler=threading.Thread(
            target=sample_windows_original_process,
            args=(proc,source_win_cpu_file,win32_cpu_stop),
            name="H2290-real-Windows-Go-Rust-CPU-observer",daemon=True)
        win32_cpu_sampler.start()
        # Genuine Windows Wintun UDP must overlap original protected admission.
        udplog=(ROOT/"win-inner-udp.log").open("w")
        udp=subprocess.Popen([sys.executable,"-u",
                   "tools/m0_h2286_inner_udp.py",APP_IP,APP_PEER,
                   own["source_sha"],str(ROOT/"original-product-ready.flag")],
                   stdout=udplog,stderr=subprocess.STDOUT,env=env)
        text=process_ready(proc,clientlog,"WBD_WINDOWS_CLIENT_READY",145)
        require("WBD_WINDOWS_OS_APPLIED" in text,
                "REAL_WINDOWS_WINTUN_OS_APPLIED_RECEIPT_ABSENT")
        output["client_original_authenticated_ready"]=True
        (ROOT/"original-product-ready.flag").write_text(own["source_sha"]+"\n")
        # Wait true Windows native Wintun inner UDP receipt, not a script READY.
        if udp.wait(timeout=50):
            raise RuntimeError("H2286_WIN_WINTUN_INNER_UDP_FAIL "+
                               (ROOT/"win-inner-udp.log").read_text(errors="replace")[-1000:])
        udp_proof=json.loads((ROOT/"original-product-ready.flag.udp.json").read_text())
        require(udp_proof["real_native_os_udp_received"]>=12 and
                udp_proof["remote_lease_ips"]==[APP_PEER],
                "ORIGINAL_SIGNED_WINTUN_TO_ARM_TUN_ACTUAL_UDP_NOT_RX")
        output["native_original_win_to_arm_udp"]=udp_proof
        # Start real ARM relay two-direction clean qdisc owned by THIS triplet.
        shape=core.remote_shape(relay,-1)
        before=core.os_host_cpu()
        tcp.WINDOW_TEST_BYTES=2*1024*1024
        tcp.BULK_MAX_BYTES=512*1024*1024
        tcp.BULK_SEND_S=25
        tcp.TIMEOUT_S=180
        require(core.PORT==RELAY_PORT and
                INNER_TUN_TCP_PORT!=RELAY_PORT and
                tcp.PORT==RELAY_PORT,
                "LEGACY_CORE_PORT_MUTATION_NOT_IDENTIFIED_FAIL_CLOSED")
        tcp.PORT=INNER_TUN_TCP_PORT
        require(tcp.PORT==45902,"INNER_TUN_TCP_PORT_NOT_ISOLATED")
        output["original_product_inner_tcp_port"]=tcp.PORT
        output["outer_kernel_arm_relay_port"]=core.PORT
        print("H2289_ORIGINAL_WINDOWS_WINTUN_INNER_TCP_PORT45902_NOT_OUTER18727",flush=True)
        print("H2286_WINDOWS_ORIGINAL_NPCAP_TLS_WINTUN_TCP_START",flush=True)
        capture=io.StringIO()
        original_tcp_wall_start=time.monotonic()
        with contextlib.redirect_stdout(capture):
            tcp.client(APP_IP,APP_PEER,own["source_sha"])
        original_tcp_wall_end=time.monotonic()
        parsed=[json.loads(s.split(tcp.MARK+"CLIENT_DONE ",1)[1])
                for s in capture.getvalue().splitlines()
                if tcp.MARK+"CLIENT_DONE " in s]
        require(len(parsed)==1 and parsed[0]["bulk_remote_received_bytes"]>0 and
                parsed[0]["sparse_echo_received"]==160 and
                parsed[0]["bind"]==APP_IP and parsed[0]["peer"]==APP_PEER,
                "ORIGINAL_WINTUN_ARM_TUN_REAL_TCP_BAD_RECEIPT")
        q=core.remote_diag(relay)
        qdisc=core.netem_phase_receipt(shape["netem"]["qdisc"],q["kernel_tc"],-1)
        relay_resource=core.relay_resource_delta(
            shape["netem"]["relay_resource_before"],q["relay_resource_now"])
        require(relay_resource["tailscaled_pid_count_common"]>0 and
                relay_resource["relay_core_count"]>0,
                "ORIGINAL_PRODUCT_RELAY_NATIVE_CPU_SAMPLES_INCOMPLETE")
        win32_product_cpu=original_window_cpu(
            source_win_cpu_file,original_tcp_wall_start,
            original_tcp_wall_end,parsed[0]["bulk_remote_received_bytes"],clientlog)
        require(qdisc["status"]=="REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED" and
                all(qdisc["per_direction"][d]["egress_packets"]>0
                    for d in ("win_to_arm","arm_to_win")),
                "ORIGINAL_PRODUCT_TWO_WAY_RELAY_KERNEL_DATA_MISSING")
        counters=nat_packet_counters(win,guest,relay_ip)
        require(sum(x["packets"] for x in counters["nat_PREROUTING"])>0 and
                sum(x["packets"] for x in counters["nat_POSTROUTING"])>0 and
                any(x["packets"]>0 for x in counters["filter_FORWARD"]),
                "ORIGINAL_NPCAP_TO_WSL_KERNEL_NAT_NO_REAL_PACKETS")
        output.update(status="MEASURED_ORIGINAL_SIGNED_WIN_GO_RUST_TO_ARM_GO_RUST_NEEDS_STOP",
            product_tcp=parsed[0],
            windows_original_product_bulk_stage_cpu_percent=
                core.cpu_busy_percent(before,core.os_host_cpu()),
            kernel_relay_qdisc=qdisc,
            relay_tailscaled_and_host_cpu_stage=relay_resource,
            windows_original_go_rust_cpu_stage=win32_product_cpu,
            real_wsl_conntrack_counters=counters,
            true_go_tls_rust_windows_arm=True)
        core.save(ROOT/"client-result.json",output)
        print("H2286_ORIGINAL_SIGNED_WINDOWS_WINTUN_TO_REAL_ARM_TUN_TCP_RECEIVED "+
              json.dumps({"mbps":parsed[0]["bulk_receiver_goodput_mbps"],
                          "p99_ms":parsed[0]["sparse_tcp_rtt_p99_ms"]}),flush=True)
    except Exception as err:
        output["status"]="FAIL_H2286_ORIGINAL_PRODUCT_OR_HARNESS_EXACT_FIRST_STAGE"
        output["first_error_type"]=type(err).__name__
        output["first_error_message"]=str(err)[-1400:]
        with contextlib.suppress(Exception):
            output["wsl_nat_on_error"]=nat_packet_counters(win,guest,relay_ip)
        with contextlib.suppress(Exception):
            output["relay_diag_on_error"]=core.remote_diag(relay)
        core.save(ROOT/"client-result.json",output)
        raise
    finally:
        tcp.PORT=prev_inner_tcp_port
        tcp.WINDOW_TEST_BYTES=prev_window
        tcp.BULK_MAX_BYTES=prev_bytes
        tcp.BULK_SEND_S=prev_seconds
        tcp.TIMEOUT_S=prev_timeout
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.stdin.write("stop\n")
                    proc.stdin.flush()
                proc.wait(timeout=50)
            except (OSError,subprocess.TimeoutExpired):
                with contextlib.suppress(OSError):proc.kill()
                with contextlib.suppress(Exception):proc.wait(timeout=8)
            fin=clientlog.read_text(errors="replace")
            stop=("WBD_WINDOWS_NATIVE_DISCONNECTED_V1" in fin and
                  "M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS" in fin and
                  not (ROOT/"owned-wal.json.n4-owned-wal").exists())
            output["client_owned_stop"]="PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP" if stop else "FAIL_UNPROVEN_ORIGINAL_STOP"
            if output["status"].startswith("MEASURED") and stop:
                output["status"]="PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP"
            elif output["status"].startswith("MEASURED"):
                output["status"]="FAIL_H2286_REAL_ORIGINAL_WINDOWS_OWNED_STOP"
        win32_cpu_stop.set()
        if win32_cpu_sampler is not None:
            win32_cpu_sampler.join(timeout=8)
        if udp is not None and udp.poll() is None:
            with contextlib.suppress(OSError):udp.kill()
        for rule in reversed(installed):
            guestroute.wsl("iptables","-w",*guestroute.reversible_rule(rule))
        guestroute.wsl("sysctl","-w","net.ipv4.ip_forward="+orig_forward)
        output["guest_iptables_and_ip_forward_restored"]=True
        core.save(ROOT/"client-result.json",output)
        # H2276 cross-runner awaits exactly one top-level client-result.json
        # inside the h2276-out-only artifact. The prior multi-root ZIP broke
        # ARM and relay post-test cleanup despite both Win products PASS.
        core.save(core.ROOT/"client-result.json",output)
        print("H2290_SOURCE_LOCKED_MINIMAL_CROSS_RUNNER_RESULT_READY",flush=True)
        if os.environ.get("WBD_H2291_WINDOWS_TX_CANDIDATE")=="1":
            actual=clientlog.read_text(errors="replace") if clientlog.exists() else ""
            output["h2291_original_windows_npf_queue_verified"]=(
                "H2291_ORIGINAL_WINDOWS_RUST_NPF_TX_SERVICE_PROFILE nqueue=1 queue_bytes=65536 max_frames=16"
                in actual)
            if not output["h2291_original_windows_npf_queue_verified"]:
                output["status"]="FAIL_H2291_RUST_CANDIDATE_QUEUE_NOT_ACTUALLY_USED"
            core.save(ROOT/"client-result.json",output)
        print("H2286_CLIENT_ACTUAL_WINDOWS_ORIGINAL_RESULT "+output["status"],flush=True)
    require(output["status"]=="PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",
            "ORIGINAL_PRODUCT_OR_STOP_NOT_VERIFIED")


if __name__=="__main__":
    if len(sys.argv)!=5:raise SystemExit("usage: full_product.py <group> <relay> <server-peer> <server-product-ready>")
    true_windows_product(*sys.argv[1:])
