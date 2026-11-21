#!/usr/bin/env python3
"""M0 PLAN029 original Go/Rust *nonprobe* single-TCP kernel fq600/fq1500 screen.

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
    G["OUT"]=ROOT/"m029-fq-singleflow-ab"
    G["TMP"]=Path(os.environ["RUNNER_TEMP"])/(
        "m029-fq-singleflow-"+RUN+"-"+ATTEMPT)
    G["TMP"].mkdir(parents=True,mode=0o700,exist_ok=False)
    G["OUT"].mkdir(exist_ok=False)
    # The genuine product fixture uses 4 streams for broad local capacity.
    # This distinct fq experiment changes *only* that actual kernel TCP
    # iperf3 invocation to one stream; the 160 UDP+160 TCP echoes remain.
    base_iperf=G["iperf_json"]
    def true_single_kernel_tcp(namespace,dest,source,port,seconds,streams):
        if streams!=4:raise RuntimeError("M029_FQ_UNEXPECTED_PRODUCT_TCP_STREAM_COUNT")
        return base_iperf(namespace,dest,source,port,seconds,1)
    G["iperf_json"]=true_single_kernel_tcp
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
                str(BUNDLE/"wbd-v4-server"),"--raw-interface","wan0",
                "--local-ip",G["SERVER_IP"],"--local-port","443",
                "--tun-name",G["SERVER_TUN"],
                "--tun-ipv4",G["SERVER_INNER"]+"/24",
                "--server-name","wbd-m029.example.test",
                "--route-key-hex-file",str(route),"--users-file",str(users),
                "--lease-pool","10.66.0.128/25","--tls-cert",str(cert),
                "--tls-key",str(key),"--outer-mtu","1160","--mode","shared"])
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
                str(BUNDLE/"wbd-v4-client"),"--raw-interface","wan0",
                "--local-ip",G["CLIENT_IP"],"--local-port","44100",
                "--peer-ip",G["SERVER_IP"],"--peer-port","443",
                "--tun-name",G["CLIENT_TUN"],
                "--server-name","wbd-m029.example.test",
                "--route-key-hex-file",str(route),"--tls-ca-pem",str(cert),
                "--username","bench0","--password","m029-scope-pass",
                "--auto-ip","--installation-id-file",str(self.secret_dir/"install"),
                "--mode","normal","--tun-fq-maxrate-mbps",str(self.fq_maxrate),
                "--fec-profile","6",
                "--outer-repair","on","--outer-mtu","1160"])
            if not ready(self.logs["client"],
                "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",85):
                raise RuntimeError("M029_PRODUCT_ORIGINAL_CLIENT_NOT_READY")
            text=self.logs["client"].read_text(errors="replace")
            fq_receipts=re.findall(
                r"V4_PUBLIC_TUN_FQ role=client interface=\S+ maxrate_mbps=(\d+) "
                r"flow_limit_packets=(\d+) readback=kernel_fq_(\d+)Mbit",
                text)
            if len(fq_receipts)!=1 or fq_receipts[0]!=(
                str(self.fq_maxrate),"256",str(self.fq_maxrate)):
                raise RuntimeError("M029_FQ_REAL_KERNEL_COLD_PERFLOW_READBACK_INVALID")
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

    result={"source_sha":SHA,"run_id":RUN,"attempt":ATTEMPT,"arch":ARCH,
            "original_go_sha":manifest["original_go_sha"],
            "same_release_binary_sha256":manifest["sha256"],
            "probe_compiled":False,"status":"NOT_RUN",
            "scenario":"NATIVE_LINUX_ARM64_NONPROBE_ORIGINAL_GO_RUST_SINGLE_STREAM_FQ600_VS_FQ1500",
            "independent_variable":"original-owned client TUN kernel fq per-flow maxrate 600 vs 1500 Mbit/s",
            "controlled":["same fully source-locked binaries on same native ARM64 VM",
               "same tc root fq flow_limit256, not qdisc disabled, server600",
               "same client128/server64 authenticated Rust M1 inbox, shared TUN",
               "same 0% artificial loss in two router qdiscs",
               "one real kernel TCP stream 20s + each 160 sparse UDP/TCP echo requests",
               "Go TLS, Rust AF_PACKET/TUN, exact owned Stop"],
            "phases":[],
            "exclusions":["physical WAN","Windows","cross-ISA causal CPU",
                          "different impairment or active FEC modes"]}
    G["save"]("summary.json",result)
    try:
        for idx,(label,fq) in enumerate((("fq600_baseline",600),("fq1500_candidate",1500))):
            node=ProductShared(idx,128)
            node.fq_maxrate=fq
            try:
                node.network()
                receipt=node.start_product()
                netem=node.impair()
                time.sleep(3)
                perf=node.measure(label)
                stop_client=node.stop("client","V4_PUBLIC_SHARED_TUN_STOP generation=")
                stop_server=node.stop("server","V4_PUBLIC_SHARED_TUN_STOP generation=")
                traffic=perf["original_product_tcp"]
                small=perf["smallflow"]
                if traffic["receiver_bytes"]<=0 or traffic["tcp_streams"]!=1 or (
                    small["status"]!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO"):
                    raise RuntimeError("M029_FQ_TRUE_SINGLE_TCP_AND_SMALLFLOW_MISSING")
                row={"name":label,"fq_client_mbps":fq,
                     "fq_server_mbps":600,"cold_readbacks":receipt,
                     "kernel_netem":netem,"measure":perf,
                     "owned_stop":{"client":stop_client,"server":stop_server},
                     "status":"PASS_SCOPED_TRUE_SINGLE_TCP_APP_FQ_COLD_MEASURED"}
                result["phases"].append(row)
                G["save"]("summary.json",result)
            finally:
                node.cleanup()
        if [x["fq_client_mbps"] for x in result["phases"]]!=[600,1500]:
            raise RuntimeError("M029_FQ_AB_ORDER_OR_KERNEL_IDENTITY_MISMATCH")
        result["status"]="PASS_SCOPED_FQ_AB_MEASURED_NOT_PRODUCT_GAIN"
        G["save"]("summary.json",result)
        print("M029_TRUE_NONPROBE_FQ600_1500_ONE_TCP_NATIVE_SOURCE_MEASURED "
              "isa="+ARCH+" source="+SHA,flush=True)
    except BaseException as exc:
        result["status"]="FAIL_OR_INCONCLUSIVE_FQ_TRUE_NATIVE_AB"
        result["error_class"]=type(exc).__name__
        result["first_error"]=str(exc)[-350:]
        G["save"]("summary.json",result)
        raise

if __name__=="__main__":
    main()
