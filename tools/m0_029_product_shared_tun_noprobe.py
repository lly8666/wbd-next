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
    G["OUT"]=ROOT/("m029-product-shared-stage" if STAGE else "m029-product-shared-noprobe")
    G["TMP"]=Path(os.environ["RUNNER_TEMP"])/(
        "m029-product-shared-"+RUN+"-"+ATTEMPT+("-stage" if STAGE else ""))
    G["TMP"].mkdir(parents=True,mode=0o700,exist_ok=False)
    G["OUT"].mkdir(exist_ok=False)
    Owned=G["Owned"]
    root=G["root"]
    ns=G["ns"]
    ready=G["ready"]

    class ProductShared(Owned):
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
                "env","GITHUB_SHA="+SHA,"GITHUB_RUN_ID="+RUN,
                "python3","-u",str(ROOT/"tools/m0_h2244_smallflow_echo.py"),
                "server","--bind",G["SERVER_INNER"]])
            if not ready(self.logs["echo-server"],"H2244_ECHO_SERVER_READY",15):
                raise RuntimeError("M029_PRODUCT_ORIGINAL_ECHO_SERVER_NOT_READY")
            self.spawn("client",self.client,["env","LD_LIBRARY_PATH="+str(BUNDLE),
                "WBD_SHARED_TUN_ROUTE_DIAG=1",
                *(["WBD_PLAN028_EXTERNAL_STAGE_DIAG=1"] if STAGE else []),
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
        if STAGE:
            # Existing independent Rust observer: 500ms samples of original
            # atomic counters. Do not add locks/FFI/timers on packet paths.
            bounds=result["measurement"]["smallflow"]
            begin=bounds["probe_start_monotonic_ns"]
            end=bounds["probe_end_monotonic_ns"]
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
                    fields={k:int(v) for k,v in re.findall(r"([a-z_]+)=(\d+)",line)}
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
