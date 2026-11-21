#!/usr/bin/env python3
"""M0 PLAN029 real *non-probe* Normal shared-TUN product acceptance, one leg.

One genuine same-native-ISA runner, one exact-SOURCE original-Go TLS+Rust
build, 3 native namespaces, real authenticated auto-IP /32 and kernel
AF_PACKET/TUN. No developer M1 flag, no new data plane, no mock success.
The separate five-mode product suite uses dedicated-TUN and cannot prove
the authenticated *shared* TUN 128/64 inbox configuration. This does.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import runpy
import subprocess
import time

ROOT=Path(os.environ["GITHUB_WORKSPACE"])
SOURCE="tools/m0_029_native_inbox_abca.py"
FROZEN_BLOB="b1094391ec9729931979c5158357ef2cbf72b84e"
SHA=os.environ["GITHUB_SHA"]
ARCH=os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
RUN=os.environ["GITHUB_RUN_ID"]
ATTEMPT=os.environ["GITHUB_RUN_ATTEMPT"]
BUNDLE=ROOT/"linux-plan029-public-bundle"
STAGE=os.environ.get("WBD_M0_029_STAGE_TIMELINE","0")
if STAGE not in ("0","1"):
    raise RuntimeError("M029_STAGE_TIMELINE_SWITCH_INVALID")
STAGE=(STAGE=="1")
SERVICE=os.environ.get("WBD_M0_029_SERVICE_CPU","0")
if SERVICE not in ("0","1") or (SERVICE=="1" and not STAGE):
    raise RuntimeError("M029_SERVICE_CPU_REQUIRES_REAL_STAGE")
SERVICE=(SERVICE=="1")
RAWCOST=os.environ.get("WBD_M0_029_RAW_CALL_COST","0")
RECOVERY=os.environ.get("WBD_M0_029_RECOVERY","0")
if RAWCOST not in ("0","1") or RECOVERY not in ("0","1"):
    raise RuntimeError("M029_RAW_COST_OR_RECOVERY_MODE_INVALID")
RAWCOST=(RAWCOST=="1")
RECOVERY=(RECOVERY=="1")
if (RAWCOST and not (STAGE and SERVICE)) or (RECOVERY and (STAGE or SERVICE or RAWCOST)):
    raise RuntimeError("M029_RAW_COST_REQUIRES_NATIVE_STAGE_AND_SERVICE")
TCP_TIMELINE=os.environ.get("WBD_M0_029_ECHO_TIMELINE","0")
if TCP_TIMELINE not in ("0","1"):
    raise RuntimeError("M029_TCP_DIRECTIONAL_TIMELINE_INVALID")
TCP_TIMELINE=(TCP_TIMELINE=="1")
TCP_INFO=os.environ.get("WBD_M0_029_TCP_INFO","0")
if TCP_INFO not in ("0","1"):
    raise RuntimeError("M029_H2260_TCP_INFO_INVALID")
TCP_INFO=TCP_INFO=="1"
if TCP_INFO and not TCP_TIMELINE:
    raise RuntimeError("M029_H2260_TCP_INFO_NEEDS_APP_TRACE")
FIRSTDROP=os.environ.get("WBD_M0_029_FIRST_DROP_WINDOW","0")
if FIRSTDROP not in ("0","1"):
    raise RuntimeError("M029_H2261_FIRST_DROP_WINDOW_INVALID")
FIRSTDROP=(FIRSTDROP=="1")
SPARSEFLOW=os.environ.get("WBD_M0_029_SPARSE_TCP_DIAG","0")
if SPARSEFLOW not in ("0","1"):
    raise RuntimeError("M029_H2262_SPARSE_FLOW_SWITCH_INVALID")
SPARSEFLOW=SPARSEFLOW=="1"
if SPARSEFLOW and not (STAGE and TCP_TIMELINE and TCP_INFO):
    raise RuntimeError("M029_H2262_SPARSE_FLOW_REQUIRES_REAL_APP_AND_TCP_INFO")
if FIRSTDROP and not (STAGE and TCP_TIMELINE and TCP_INFO):
    raise RuntimeError("M029_H2261_REQUIRES_STAGE_REAL_TCP_INFO")

def authenticate_source_and_bundle():
    if os.environ.get("GITHUB_ACTIONS")!="true" or platform.machine()!=ARCH or (
        ARCH not in ("x86_64","aarch64")) or len(SHA)!=40:
        raise RuntimeError("M029_PRODUCT_SHARED_NATIVE_ACTION_ISA_AND_SOURCE_REQUIRED")
    blob=subprocess.check_output(["git","hash-object",SOURCE],cwd=ROOT,text=True).strip()
    if blob!=FROZEN_BLOB:
        raise RuntimeError("M029_PRODUCT_SHARED_ORIGINAL_FIXTURE_BLOB_CHANGED")
    manifest=json.loads((BUNDLE/"manifest.json").read_text())
    if manifest["source_sha"]!=SHA or manifest["architecture"]!=ARCH or (
        manifest["m0_probe_compiled"] is not False):
        raise RuntimeError("M029_PRODUCT_SHARED_REAL_NONPROBE_BUILD_NOT_VERIFIED")
    if (manifest["normal_linux_client_shared_tun_inbox_default"],
        manifest["normal_linux_server_shared_tun_inbox_default"],
        manifest["game_group_shared_tun_inbox_default"])!=(128,64,64):
        raise RuntimeError("M029_PRODUCT_SHARED_EXPECTED_CAPACITY_MANIFEST_MISSING")
    for name,expected in manifest["sha256"].items():
        actual=hashlib.sha256((BUNDLE/name).read_bytes()).hexdigest()
        if actual!=expected:
            raise RuntimeError("M029_PRODUCT_SHARED_BIN_HASH_MISMATCH_"+name)
    exported=subprocess.check_output(["nm","-D",str(BUNDLE/"libwbd_engine.so")],text=True)
    if "wbd_m0_embedded_go_loop_debug_pause_jumbo" in exported:
        raise RuntimeError("M029_PRODUCT_SHARED_DEVELOPER_DEBUG_ABI_EXPORTED")
    return manifest

def main():
    manifest=authenticate_source_and_bundle()
    # Use original accepted topology, owned pid identities, app accounting
    # and Stop implementation. No substitution of an easier packet carrier.
    original=runpy.run_path(str(ROOT/SOURCE),run_name="m029_real_fixture_reuse")
    G=original["main"].__globals__
    suffix="recovery" if RECOVERY else "stage" if STAGE else "noprobe"
    G["OUT"]=ROOT/("m029-product-shared-"+suffix)
    G["TMP"]=Path(os.environ["RUNNER_TEMP"])/(
        "m029-product-shared-"+RUN+"-"+ATTEMPT+"-"+suffix)
    G["TMP"].mkdir(parents=True,mode=0o700,exist_ok=False)
    G["OUT"].mkdir(exist_ok=False)
    Owned=G["Owned"]
    root=G["root"]
    ns=G["ns"]
    ready=G["ready"]

    class ProductShared(Owned):
        def spawn(self,role,place,argv):
            # Frozen original fixture's small TCP/UDP real app is untouched
            # except test-only numeric timestamps in the same namespace.
            if TCP_TIMELINE and role.startswith("small-"):
                if not argv or argv[0]!="env":
                    raise RuntimeError("M029_ECHO_TCP_TIMELINE_NOT_ORIGINAL_APP")
                env=["WBD_M0_029_ECHO_TIMELINE=1"]
                if TCP_INFO:env.append("WBD_M0_029_TCP_INFO=1")
                argv=["env",*env,*argv[1:]]
            return super().spawn(role,place,argv)

        def start_product(self):
            # Original TLS, owned cert/secret and route key, never test keys
            # supplied straight to Rust instead of the original Go owner.
            route=self.secret_dir/"route.hex"
            route.write_text(hashlib.sha256(
                (RUN+"/"+SHA+"/"+str(self.index)).encode()).hexdigest()+"\n")
            route.chmod(0o600)
            cert=self.secret_dir/"cert.pem"
            key=self.secret_dir/"key.pem"
            with (self.secret_dir/"cert-generation.log").open("w") as o:
                subprocess.run(["openssl","req","-x509","-newkey","rsa:2048",
                    "-sha256","-days","1","-nodes","-keyout",str(key),
                    "-out",str(cert),"-subj","/CN=wbd-m029.example.test",
                    "-addext","subjectAltName=DNS:wbd-m029.example.test"],
                    stdout=o,stderr=subprocess.STDOUT,check=True)
            key.chmod(0o600)
            users=self.secret_dir/"users.json"
            users.write_text(json.dumps({"bench0":"m029-scope-pass"})+"\n")
            users.chmod(0o600)
            self.spawn("server",self.server,["env","LD_LIBRARY_PATH="+str(BUNDLE),
                "WBD_SHARED_TUN_ROUTE_DIAG=1",
                *(["WBD_PLAN028_EXTERNAL_STAGE_DIAG=1"] if STAGE else []),
                *(["WBD_M0_029_TX_SYSCPU_DIAG=1"] if SERVICE else []),
                *(["WBD_M0_029_RAW_CALL_COST=1"] if RAWCOST else []),
                *(["WBD_M0_029_FIRST_DROP_WINDOW=1"] if FIRSTDROP else []),
                *(["WBD_M0_029_SPARSE_TCP_DIAG=1"] if SPARSEFLOW else []),
                str(BUNDLE/"wbd-v4-server"),"--raw-interface","wan0",
                "--local-ip",G["SERVER_IP"],"--local-port","443",
                "--tun-name",G["SERVER_TUN"],
                "--tun-ipv4",G["SERVER_INNER"]+"/24",
                "--server-name","wbd-m029.example.test",
                "--route-key-hex-file",str(route),"--users-file",str(users),
                "--lease-pool","10.66.0.128/25","--tls-cert",str(cert),
                "--tls-key",str(key),"--outer-repair","off",
                "--outer-mtu","1160","--mode","shared"])
            if not ready(self.logs["server"],
                "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",70):
                raise RuntimeError("M029_PRODUCT_ORIGINAL_SHARED_SERVER_NOT_READY")
            self.spawn("bulk-server",self.server,
                ["iperf3","-s","-B",G["SERVER_INNER"],"-p","5201"])
            self.spawn("direct-server",self.server,
                ["iperf3","-s","-B",G["SERVER_IP"],"-p","5202"])
            self.spawn("echo-server",self.server,[
                "env",*(["WBD_M0_029_ECHO_TIMELINE=1"] if TCP_TIMELINE else []),
                "GITHUB_SHA="+SHA,"GITHUB_RUN_ID="+RUN,
                "python3","-u",str(ROOT/"tools/m0_h2244_smallflow_echo.py"),
                "server","--bind",G["SERVER_INNER"]])
            if not ready(self.logs["echo-server"],"H2244_ECHO_SERVER_READY",15):
                raise RuntimeError("M029_PRODUCT_ORIGINAL_ECHO_SERVER_NOT_READY")
            self.spawn("client",self.client,["env","LD_LIBRARY_PATH="+str(BUNDLE),
                "WBD_SHARED_TUN_ROUTE_DIAG=1",
                *(["WBD_PLAN028_EXTERNAL_STAGE_DIAG=1"] if STAGE else []),
                *(["WBD_M0_029_TX_SYSCPU_DIAG=1"] if SERVICE else []),
                *(["WBD_M0_029_RAW_CALL_COST=1"] if RAWCOST else []),
                *(["WBD_M0_029_FIRST_DROP_WINDOW=1"] if FIRSTDROP else []),
                *(["WBD_M0_029_SPARSE_TCP_DIAG=1"] if SPARSEFLOW else []),
                str(BUNDLE/"wbd-v4-client"),"--raw-interface","wan0",
                "--local-ip",G["CLIENT_IP"],"--local-port","44100",
                "--peer-ip",G["SERVER_IP"],"--peer-port","443",
                "--tun-name",G["CLIENT_TUN"],
                "--server-name","wbd-m029.example.test",
                "--route-key-hex-file",str(route),"--tls-ca-pem",str(cert),
                "--username","bench0","--password","m029-scope-pass",
                "--auto-ip","--installation-id-file",str(self.secret_dir/"install"),
                "--mode","normal","--fec-profile","6",
                "--outer-repair","off","--outer-mtu","1160"])
            if not ready(self.logs["client"],
                "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",85):
                raise RuntimeError("M029_PRODUCT_ORIGINAL_CLIENT_NOT_READY")
            text=self.logs["client"].read_text(errors="replace")
            leases=re.findall(
                r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",
                text)
            if len(leases)!=1:
                raise RuntimeError("M029_PRODUCT_AUTHENTICATED_LEASE_MISSING")
            self.lease=leases[0]
            readbacks={}
            for role,capacity in (("client",128),("server",64)):
                if not ready(self.logs[role],
                    "M0_PLAN029_NATIVE_INBOX_BOUND role="+role,25):
                    raise RuntimeError("M029_PRODUCT_TRUE_"+role.upper()+
                                       "_SHARED_INBOX_RECEIPT_MISSING")
                log=self.logs[role].read_text(errors="replace")
                matches=re.findall(
                    r"M0_PLAN029_NATIVE_INBOX_BOUND role="+role+
                    r" generation=(\d+) slots=(\d+) probe_only=(\d+)",log)
                if len(matches)!=1:
                    raise RuntimeError("M029_PRODUCT_MUST_READ_EXACTLY_ONE_"+role)
                generation,slots,probe=map(int,matches[0])
                if generation<=0 or slots!=capacity or probe!=0:
                    raise RuntimeError("M029_PRODUCT_AUTHENTICATED_"+role+
                                       "_INBOX_WRONG_REAL_COLD_CAPACITY")
                readbacks[role]={"generation":generation,"slots":slots,
                                 "probe_only":probe}
            root("ip","-n",self.client,"route","replace",
                 G["SERVER_INNER"]+"/32","dev",G["CLIENT_TUN"])
            return readbacks

        def impair(self):
            # Real unfaked zero-artificial-loss high-supply scenario; retain
            # router qdisc and all original skb/drop receipts.
            for dev in ("rcli0","rsrv0"):
                ns(self.router,"tc","qdisc","replace","dev",dev,"root",
                   "netem","delay","0ms","loss","0%","limit","65536")
            return {dev:json.loads(ns(self.router,"tc","-s","-j","qdisc",
                    "show","dev",dev).stdout) for dev in ("rcli0","rsrv0")}

    result={"source_sha":SHA,"run_id":RUN,"attempt":ATTEMPT,
            "outer_repair_cli":"off_both_endpoints",
            "independent_m1_m4_stage_observer":STAGE,
            "native_user_system_cpu_service_observer":SERVICE,
            "original_m4_raw_sendmmsg_sampled_timing":RAWCOST,
            "same_source_recovery_leg":RECOVERY,
            "tcp_directional_application_timeline":TCP_TIMELINE,
            "native_inner_tcp_info_readonly":TCP_INFO,
            "original_shared_tun_first_drop_window":FIRSTDROP,
            "outer_ip_mtu_explicit_bytes":1160,
            "arch":ARCH,"original_go_sha":manifest["original_go_sha"],
            "same_release_binary_sha256":manifest["sha256"],
            "probe_compiled":False,"status":"NOT_RUN",
            "product_mode":"original Go TLS Rust authenticated Normal shared TUN",
            "scope":"one true shared TUN /32 client generation, no load-shim",
            "exclusions":["Windows","physical WAN","multi-lease fairness",
                          "full FEC Game/Auto capacity","real-time UDP p99 SLA"]}
    G["save"]("summary.json",result)
    node=ProductShared(0,128)
    try:
        node.network()
        result["cold_readbacks"]=node.start_product()
        result["actual_router_netem"]=node.impair()
        time.sleep(3)
        result["measurement"]=node.measure("product_no_probe128")
        result["owned_stop"]={
            "client":node.stop("client","V4_PUBLIC_SHARED_TUN_STOP generation="),
            "server":node.stop("server","V4_PUBLIC_SHARED_TUN_STOP generation=")}
        # This is the actual protected original-Go -> Rust owner status,
        # not merely the CLI flag or an assumed default.
        # Before Stop, original multi-session server has exactly one READY
        # authenticated Rust generation. Prove effective repair state there;
        # absence or read error must NOT be inferred from CLI --repair off.
        server_log=node.logs["server"].read_text(errors="replace")
        server_ready=re.findall(
            r"V4_PUBLIC_MIXED_NORMAL_OUTER_READY role=server client_port=(\d+) repair_enabled=(\d+) proof=authenticated_original_rust_owner",
            server_log)
        if len(server_ready)!=1 or server_ready[0][1]!="0" or int(server_ready[0][0])<=0:
            raise RuntimeError("M029_SERVER_AUTHENTICATED_RUST_OUTER_OFF_READY_MISSING")
        result["server_native_outer_ready_readback"]={
            "client_port":int(server_ready[0][0]),
            "repair_enabled":int(server_ready[0][1]),
            "proof":"authenticated_original_rust_owner"}
        result["outer_repair_native_stop_readback"]={}
        result["outer_repair_native_stop_scope"]={}
        for role in ("client","server"):
            raw=node.logs[role].read_text(errors="replace")
            values=re.findall(r"V4_PUBLIC_M2_OUTER role="+role+
                              r"[^\n]*? repair_enabled=(\d+)",raw)
            if any(value!="0" for value in values):
                raise RuntimeError("M029_TRUE_NORMAL_OFF_NATIVE_OUTER_ON_"+role)
            if role=="client" and not values:
                raise RuntimeError("M029_CLIENT_NORMAL_OFF_NATIVE_READBACK_MISSING")
            # Original shared multi-server may retire its session before
            # emitting Go V4_PUBLIC_M2_OUTER on Stop. Keep this UNKNOWN,
            # never invent a server Rust readback from the CLI string.
            result["outer_repair_native_stop_readback"][role]=[int(x) for x in values]
            result["outer_repair_native_stop_scope"][role]=(
                "NATIVE_OFF_CONFIRMED" if values else "NOT_EMITTED_UNVERIFIED")
        # Explicit source-only diagnostic: UDP/TCP entering the authenticated
        # /32 shared reader versus NEW pending drops. Neither a M4 copied
        # prefix nor AEAD/PN verification nor a timed delivery receipt.
        result["shared_tun_protocol_ingress"]={}
        expected={"offered","tcp_offered","udp_offered","other_offered",
                  "tcp_new_dropped","udp_new_dropped","other_new_dropped"}
        for role in ("client","server"):
            rows=[]
            for line in node.logs[role].read_text(errors="replace").splitlines():
                if not line.startswith("M0_SHARED_TUN_LEASE_QUEUE_DIAG "):
                    continue
                fields={k:int(v) for k,v in re.findall(r"([a-z_]+)=(\d+)",line)}
                if not expected.issubset(fields):
                    raise RuntimeError("M029_INGRESS_PROTOCOL_COUNTERS_MISSING_"+role)
                if fields["offered"]!=sum(fields[k] for k in
                       ("tcp_offered","udp_offered","other_offered")):
                    raise RuntimeError("M029_INGRESS_PROTOCOL_DENOMINATOR_MISMATCH_"+role)
                if any(fields[k+"_new_dropped"]>fields[k+"_offered"]
                       for k in ("tcp","udp","other")):
                    raise RuntimeError("M029_INGRESS_PROTOCOL_DROP_EXCEEDS_OFFERED_"+role)
                rows.append({k:fields[k] for k in sorted(expected)})
            if not rows or sum(x["offered"] for x in rows)==0:
                raise RuntimeError("M029_TRUE_SHARED_TUN_INGRESS_DIAG_NOT_OBSERVED_"+role)
            if (sum(row["tcp_new_dropped"]+row["udp_new_dropped"]+
                    row["other_new_dropped"] for row in rows)
                    !=result["owned_stop"][role]["queue_full_drops"]):
                raise RuntimeError("M029_NEW_SOURCE_DROP_ACCOUNTING_MISMATCH_"+role)
            result["shared_tun_protocol_ingress"][role]=rows
        if SPARSEFLOW:
            # B-only original TCP/53222 segments; zero refusals is a valid
            # negative. No application sequence, ciphertext or PN identity.
            result["h2262_sparse_tcp_ingress"]={}
            required={"forward_offered","forward_dropped",
                      "reverse_offered","reverse_dropped"}
            for role in ("client","server"):
                rows=[]
                for line in node.logs[role].read_text(errors="replace").splitlines():
                    if not line.startswith("M0_SHARED_TUN_SPARSE_TCP_DIAG "):
                        continue
                    fields={k:int(v) for k,v in re.findall(r"([a-z_]+)=(\\d+)",line)}
                    if not required.issubset(fields):
                        raise RuntimeError("M029_H2262_SPARSE_ORIGINAL_RUST_FIELDS_MISSING_"+role)
                    if fields["forward_dropped"]>fields["forward_offered"] or (
                        fields["reverse_dropped"]>fields["reverse_offered"]):
                        raise RuntimeError("M029_H2262_SPARSE_DENOMINATOR_INVALID_"+role)
                    rows.append({k:fields[k] for k in sorted(required)})
                if len(rows)!=1:
                    raise RuntimeError("M029_H2262_EXACT_ONE_AUTHENTIC_SHARED_ROUTE_"+role)
                item=rows[0]
                if (role=="client" and item["forward_offered"]<=0) or (
                    role=="server" and item["reverse_offered"]<=0):
                    raise RuntimeError("M029_H2262_TRUE_53222_TCP_SEGMENTS_MISSING_"+role)
                result["h2262_sparse_tcp_ingress"][role]=item
            result["h2262_scope"]="original_test_TCP_53222_first_fragment_source_segments_no_app_seq_PN_causality"
        if STAGE:
            # Existing independent Rust observer: 500ms samples of original
            # atomic counters. Do not add locks/FFI/timers on packet paths.
            bounds=result["measurement"]["smallflow"]
            begin=bounds["probe_start_monotonic_ns"]
            end=bounds["probe_end_monotonic_ns"]
            # m4_copied contains a digit: permit numeric field identifiers.
            assert dict(re.findall(r"([a-z0-9_]+)=(\d+)","m4_copied=7"))["m4_copied"]=="7"
            required=("mono_ns","generation","source_queued","m4_copied",
                      "tx_backpressure","tx_worker_cpu_ns","rx_worker_cpu_ns",
                      "tun_delivered","kernel_raw_observed")
            result["m1_m4_stage_timeline"]={}
            for role in ("client","server"):
                rows=[]
                raw=node.logs[role].read_text(errors="replace")
                for line in raw.splitlines():
                    if "V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG role="+role+" " not in line:
                        continue
                    fields={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",line)}
                    if any(k not in fields for k in required):
                        raise RuntimeError("M029_M1_M4_STAGE_FIELD_MISSING_"+role)
                    rows.append({k:fields[k] for k in required})
                if len(rows)<8 or len({x["generation"] for x in rows})!=1:
                    raise RuntimeError("M029_STAGE_NATIVE_SAMPLES_TOO_FEW_OR_WRONG_GENERATION_"+role)
                for old,new in zip(rows,rows[1:]):
                    if new["mono_ns"]<=old["mono_ns"] or any(
                        new[key]<old[key] for key in
                        ("m4_copied","tx_backpressure","tx_worker_cpu_ns",
                         "rx_worker_cpu_ns","tun_delivered","kernel_raw_observed")
                    ):
                        raise RuntimeError("M029_STAGE_COUNTER_OR_CLOCK_NOT_MONOTONE_"+role)
                overlap=sum(begin<=x["mono_ns"]<=end for x in rows)
                if overlap<4 or max(x["m4_copied"] for x in rows)==0:
                    raise RuntimeError("M029_TRUE_PACKET_SERVICE_STAGE_NOT_OBSERVED_"+role)
                result["m1_m4_stage_timeline"][role]={
                    "samples":rows,"echo_window_samples":overlap,
                    "source":"independent_Rust_500ms_observer",
                    "observed_without_new_DATA_path":True}
        if SERVICE:
            required=("mono_ns","generation","rx_tid","tx_tid",
                      "rx_user_ticks","rx_system_ticks",
                      "tx_user_ticks","tx_system_ticks",
                      "m4_success_turns","m4_bin_1","m4_bin_2_4",
                      "m4_bin_5_8","m4_bin_9_16","m4_bin_17_32")
            bins=("m4_bin_1","m4_bin_2_4","m4_bin_5_8",
                  "m4_bin_9_16","m4_bin_17_32")
            result["native_user_system_cpu_service_timeline"]={}
            for role in ("client","server"):
                rows=[]
                for line in node.logs[role].read_text(errors="replace").splitlines():
                    if "V4_PUBLIC_M4_NATIVE_SERVICE_DIAG role="+role+" " not in line:
                        continue
                    fields={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=([0-9]+)",line)}
                    if any(k not in fields for k in required):
                        raise RuntimeError("M029_NATIVE_USER_SYS_TASK_STAT_UNAVAILABLE_"+role)
                    rows.append({k:fields[k] for k in required})
                if len(rows)<8 or len({x["generation"] for x in rows})!=1:
                    raise RuntimeError("M029_NATIVE_SERVICE_GENERATION_OR_SAMPLE_MISSING_"+role)
                for row in rows:
                    if row["tx_tid"]<=0 or row["rx_tid"]<=0 or row["tx_tid"]==row["rx_tid"] or (
                        sum(row[k] for k in bins)!=row["m4_success_turns"]):
                        raise RuntimeError("M029_NATIVE_M4_BATCH_HISTOGRAM_INVALID_"+role)
                for a,b in zip(rows,rows[1:]):
                    if b["mono_ns"]<=a["mono_ns"] or any(
                        b[k]<a[k] for k in
                        ("rx_user_ticks","rx_system_ticks","tx_user_ticks",
                         "tx_system_ticks","m4_success_turns",*bins)):
                        raise RuntimeError("M029_NATIVE_USER_SYS_OR_SEND_TURNS_NONMONOTONE_"+role)
                if rows[-1]["m4_success_turns"]<=rows[0]["m4_success_turns"]:
                    raise RuntimeError("M029_NATIVE_M4_COPY_TURNS_NOT_OBSERVED_"+role)
                result["native_user_system_cpu_service_timeline"][role]={
                    "samples":rows,
                    "source":"authentic_linux_task_stat_and_original_definite_M4_copy_turns",
                    "clock_ticks_per_second":os.sysconf("SC_CLK_TCK"),
                    "scope":"positive_copied_turns_not_all_sendmmsg_syscalls"}
        if RAWCOST:
            needed=("mono_ns","generation","enabled","sample_every",
                    "sendmmsg_samples","sendmmsg_wall_ns",
                    "whole_driver_wall_ns","copied_positive_samples",
                    "copied_positive_records")
            result["m4_exact_sendmmsg_timeline"]={}
            for role in ("client","server"):
                samples=[]
                for line in node.logs[role].read_text(errors="replace").splitlines():
                    if "V4_PUBLIC_M4_RAW_SENDMMSG_COST role="+role+" " not in line:
                        continue
                    fields={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=([0-9]+)",line)}
                    if any(k not in fields for k in needed):
                        raise RuntimeError("M029_REAL_SENDMMSG_COST_FIELD_MISSING_"+role)
                    samples.append({k:fields[k] for k in needed})
                if len(samples)<8 or len({x["generation"] for x in samples})!=1:
                    raise RuntimeError("M029_REAL_SENDMMSG_COST_NOT_SAMPLED_"+role)
                for row in samples:
                    if row["enabled"]!=1 or row["sample_every"]!=128 or (
                        row["sendmmsg_wall_ns"]>row["whole_driver_wall_ns"]) or (
                        row["copied_positive_samples"]>row["sendmmsg_samples"]):
                        raise RuntimeError("M029_RAW_COST_INVALID_DENOMINATOR_"+role)
                for a,b in zip(samples,samples[1:]):
                    if b["mono_ns"]<=a["mono_ns"] or any(b[k]<a[k] for k in (
                        "sendmmsg_samples","sendmmsg_wall_ns","whole_driver_wall_ns",
                        "copied_positive_samples","copied_positive_records")):
                        raise RuntimeError("M029_RAW_COST_NON_MONOTONE_"+role)
                if (samples[-1]["sendmmsg_samples"]-samples[0]["sendmmsg_samples"])<10:
                    raise RuntimeError("M029_RAW_COST_LIVE_ORIGINAL_SENDMMSG_TOO_FEW_"+role)
                result["m4_exact_sendmmsg_timeline"][role]={
                    "samples":samples,"metric":"sampled_true_sendmmsg_wall_ns_vs_full_raw_driver_wall_ns",
                    "not_cpu_time_not_all_calls_not_peer_receipt":True}
        if FIRSTDROP:
            # Original protected router and Rust M1/M4/RX counters. They
            # have their own denominators, never identify a TCP test seq.
            needed=("mono_ns","generation","shared_delivered",
                    "shared_full","shared_byte","shared_age",
                    "shared_retired","shared_unrouted","shared_backpressure",
                    "tx_tcp_seen","tx_tcp_staged","tx_udp_seen",
                    "tx_arena_failed","tx_deferred","m4_copied",
                    "rx_kernel","rx_tuple","rx_unique","rx_tun","rx_invalid")
            begin=result["measurement"]["smallflow"]["probe_start_monotonic_ns"]
            end=result["measurement"]["smallflow"]["probe_end_monotonic_ns"]
            result["h2261_original_tun_m4_rx_windows"]={}
            for role in ("client","server"):
                rows=[]
                for line in node.logs[role].read_text(errors="replace").splitlines():
                    if "V4_PUBLIC_M4_FIRST_DROP_WINDOW role="+role+" " not in line:
                        continue
                    values={k:int(v) for k,v in re.findall(
                        r"([a-z0-9_]+)=([0-9]+)",line)}
                    if any(k not in values for k in needed):
                        raise RuntimeError("M029_H2261_MISSING_NATIVE_ROUTER_OR_FIELDS_"+role)
                    rows.append({k:values[k] for k in needed})
                if len(rows)<8 or len({row["generation"] for row in rows})!=1:
                    raise RuntimeError("M029_H2261_NATIVE_OWNER_WINDOW_MISSING_"+role)
                for old,new in zip(rows,rows[1:]):
                    if new["mono_ns"]<=old["mono_ns"] or any(
                        new[k]<old[k] for k in needed if k!="generation"):
                        raise RuntimeError("M029_H2261_COUNTER_OR_CLOCK_NOT_MONOTONE_"+role)
                overlap=sum(begin<=row["mono_ns"]<=end for row in rows)
                if overlap<4 or not any(row["m4_copied"]>0 for row in rows):
                    raise RuntimeError("M029_H2261_NO_REAL_BUSINESS_WINDOW_"+role)
                result["h2261_original_tun_m4_rx_windows"][role]={
                    "samples":rows,"echo_window_samples":overlap,
                    "clock":"Linux_MONOTONIC_shared_between_netns",
                    "source":"existing_original_Rust_shared_TUN_M1_M4_RX_counters",
                    "scope":"cumulative_aggregates_not_per_TCP_sequence"}
        if TCP_TIMELINE:
            # One real client TCP stream/one server worker in this leg.
            # Both namespaces share Linux CLOCK_MONOTONIC, and sequence
            # numbers match existing test-only 16-byte echo frames.
            small_path=G["OUT"]/"product_no_probe128-echo.json"
            small_raw=json.loads(small_path.read_text())
            client_trace=small_raw.get("tcp_client_trace",[])
            if not ready(node.logs["echo-server"],"H2259_SERVER_TCP_TRACE ",5):
                raise RuntimeError("M029_TCP_SERVER_DIRECTIONAL_TRACE_MISSING")
            raw=node.logs["echo-server"].read_text(errors="replace")
            assert re.findall(r"^H2259_SERVER_TCP_TRACE (\[.*\])$","H2259_SERVER_TCP_TRACE [[0,1,2]]",re.M)==["[[0,1,2]]"]
            matches=re.findall(r"^H2259_SERVER_TCP_TRACE (\[.*\])$",raw,re.M)
            if len(matches)!=1:
                raise RuntimeError("M029_EXACTLY_ONE_TCP_SERVER_STREAM_REQUIRED")
            server_trace=json.loads(matches[0])
            if len(client_trace)!=160 or len(server_trace)!=160:
                raise RuntimeError("M029_TCP_TRACE_MUST_COVER_ALL_160_REAL_REPLIES")
            if len({x[0] for x in client_trace})!=160 or (
                len({x[0] for x in server_trace})!=160):
                raise RuntimeError("M029_TCP_DIRECTIONAL_DUPLICATE_SEQUENCE")
            server_by_seq={x[0]:x for x in server_trace}
            samples=[]
            for row in client_trace:
                seq,c_start,c_done,c_reply=row
                matching=server_by_seq.get(seq)
                if (matching is None or c_done is None or c_reply is None):
                    raise RuntimeError("M029_TCP_DIRECTIONAL_MISSING_AUTHENTIC_TEST_REPLY")
                _,s_recv,s_done=matching
                if not (c_start<=c_done and c_start<=s_recv<=s_done and
                        c_start<=c_reply):
                    raise RuntimeError("M029_TCP_DIRECTIONAL_MONOTONIC_ORDER_INVALID")
                samples.append({
                    "seq":seq,"client_before_send_ns":c_start,
                    "client_send_done_ns":c_done,"server_recv_ns":s_recv,
                    "server_send_done_ns":s_done,"client_reply_ns":c_reply,
                    "forward_app_observed_ms":round((s_recv-c_start)/1e6,4),
                    "server_processing_ms":round((s_done-s_recv)/1e6,4),
                    "reverse_app_observed_ms":round((c_reply-s_done)/1e6,4),
                    "client_sendall_ms":round((c_done-c_start)/1e6,4),
                    "end_to_end_ms":round((c_reply-c_start)/1e6,4)
                })
            def pct(values,n):
                values=sorted(values)
                return round(values[max(0,(len(values)*n+99)//100-1)],4)
            summaries={}
            for field in ("forward_app_observed_ms","server_processing_ms",
                          "reverse_app_observed_ms","client_sendall_ms","end_to_end_ms"):
                values=[x[field] for x in samples]
                summaries[field]={"p50":pct(values,50),"p95":pct(values,95),
                                  "p99":pct(values,99),"max":max(values)}
            result["tcp_directional_timeline"]={
                "scope":"test_only_one_real_inner_TCP_socket_same_host_monotonic",
                "same_original_payload_and_real_160_sequences":True,
                "samples":samples,"summaries_ms":summaries,
                "caution":"server_recv is app-recv not inner M3, TCP sendall return is not peer ACK"}
        if TCP_INFO:
            # This sole original TCP application socket is already matched
            # to 160 real nonce+seq app request/response timestamps.
            native=small_raw.get("tcp_info_native",{})
            fields=["mono_ns","rto_us","unacked","retrans","rtt_us",
                    "snd_cwnd","total_retrans"]
            samples=native.get("rows",[])
            if (native.get("abi_bytes")!=104 or native.get("fields")!=fields or
                native.get("errors") or not (30<=len(samples)<=160)):
                raise RuntimeError("M029_H2260_NATIVE_TCP_INFO_NOT_AVAILABLE")
            for row in samples:
                if (len(row)!=7 or any(not isinstance(v,int) or v<0 for v in row)
                    or row[1]<=0 or row[5]<=0):
                    raise RuntimeError("M029_H2260_TCP_INFO_WRONG_NATIVE_FIELDS")
            for old,new in zip(samples,samples[1:]):
                if new[0]<=old[0] or new[6]<old[6]:
                    raise RuntimeError("M029_H2260_TCP_INFO_NONMONOTONE_CLOCK_OR_RETRANS")
            begin=result["measurement"]["smallflow"]["probe_start_monotonic_ns"]
            end=result["measurement"]["smallflow"]["probe_end_monotonic_ns"]
            during=[x for x in samples if begin<=x[0]<=end]
            if len(during)<30:
                raise RuntimeError("M029_H2260_TCP_INFO_NO_TRUE_ECHO_OVERLAP")
            rtos=sorted(x[1] for x in during)
            result["native_tcp_info_timeline"]={
                "fields":fields,"samples":samples,
                "echo_overlap_samples":len(during),
                "retransmitted_tcp_segments_delta":during[-1][6]-during[0][6],
                "rto_us_p95":rtos[max(0,(len(rtos)*95+99)//100-1)],
                "max_unacked":max(x[2] for x in during),
                "min_snd_cwnd":min(x[5] for x in during),
                "source":"exact_original_test_inner_TCP_socket_linux_getsockopt_104B",
                "caution":"retransmits are not proof of which Rust/underlay layer delayed the forward app receipt"}
        if FIRSTDROP:
            # Same absolute Linux monotonic basis across client/server netns,
            # independent Rust observers and exact original app TCP_INFO.
            # This does NOT prove a unique first lost packet.
            c=result["h2261_original_tun_m4_rx_windows"]["client"]["samples"]
            srv=result["h2261_original_tun_m4_rx_windows"]["server"]["samples"]
            tcp=result["tcp_directional_timeline"]["samples"]
            info=result["native_tcp_info_timeline"]["samples"]
            start=result["measurement"]["smallflow"]["probe_start_monotonic_ns"]
            end=result["measurement"]["smallflow"]["probe_end_monotonic_ns"]
            if len(tcp)!=160 or not any(start<=r[0]<=end for r in info):
                raise RuntimeError("M029_H2261_ORIGINAL_SEQ_AND_TCP_INFO_NOT_ALIGNED")
            if not all(any(start<=r["mono_ns"]<=end for r in xs)
                       for xs in (c,srv)):
                raise RuntimeError("M029_H2261_ORIGINAL_BOTH_RUST_OBSERVERS_NOT_ALIGNED")
            # Preserve the exact 160 real forward intervals and all 500ms
            # native counters for post-run differential attribution.
            result["h2261_alignment"]={
                "true_echo_start_ns":start,"true_echo_end_ns":end,
                "app_original_tcp_sequences":len(tcp),
                "native_client_samples":len(c),"native_server_samples":len(srv),
                "true_inner_tcp_info_samples":len(info),
                "first_per_sequence_lost_location":"UNPROVEN_AGGREGATE_ONLY",
                "no_added_packet_read_or_native_data_path":True}
        traffic=result["measurement"]["original_product_tcp"]
        small=result["measurement"]["smallflow"]
        if traffic["receiver_bytes"]<=0 or traffic["tcp_streams"]!=4 or (
            small["status"]!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO"):
            raise RuntimeError("M029_PRODUCT_REAL_TCP_AND_UDP_DELIVERY_NOT_VERIFIED")
        for role in ("client","server"):
            if result["owned_stop"][role]["generation"]<=0:
                raise RuntimeError("M029_PRODUCT_SHARED_STOP_NOT_DRAINED")
        result["status"]="PASS_SCOPED_REAL_NO_PROBE_SHARED_TUN_NORMAL_128_64"
        G["save"]("summary.json",result)
        print("M0_PLAN029_REAL_NONPROBE_SHARED_NORMAL_CLIENT128_SERVER64 "
              "native_isa="+ARCH+" run="+RUN+" status=PASS_SCOPED",flush=True)
    except BaseException as exc:
        result["status"]="FAIL_OR_INCONCLUSIVE_TRUE_NONPROBE_SHARED_TUN"
        result["first_error"]=str(exc)[-300:]
        result["error_class"]=type(exc).__name__
        G["save"]("summary.json",result)
        raise
    finally:
        node.cleanup()

if __name__=="__main__":
    main()
