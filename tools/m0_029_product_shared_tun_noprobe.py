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
LEG=os.environ.get("WBD_M0_029_UDP_RESERVE_LEG","")
if LEG not in ("","A","B","Aprime"):
    raise RuntimeError("M029_UNKNOWN_ONE_FACTOR_LEG")

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
    G["OUT"]=ROOT/("m029-product-shared-noprobe"+("-"+LEG if LEG else ""))
    G["TMP"]=Path(os.environ["RUNNER_TEMP"])/(
        "m029-product-shared-"+RUN+"-"+ATTEMPT+("-"+LEG if LEG else ""))
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
                "WBD_SHARED_TUN_ROUTE_DIAG=1",
                *(["WBD_M0_029_UDP_RESERVE_TEST=1"] if LEG=="B" else []),
                str(BUNDLE/"wbd-v4-client"),"--raw-interface","wan0",
                "--local-ip",G["CLIENT_IP"],"--local-port","44100",
                "--peer-ip",G["SERVER_IP"],"--peer-port","443",
                "--tun-name",G["CLIENT_TUN"],
                "--server-name","wbd-m029.example.test",
                "--route-key-hex-file",str(route),"--tls-ca-pem",str(cert),
                "--username","bench0","--password","m029-scope-pass",
                "--auto-ip","--installation-id-file",str(self.secret_dir/"install"),
                "--mode","normal","--fec-profile","6",
                "--outer-repair","on","--outer-mtu","1160"])
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
            "trial_leg":LEG if LEG else "single",
            "test_only_udp_reservation":LEG=="B",
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
        # Explicit source-only diagnostic: UDP/TCP entering the authenticated
        # /32 shared reader versus NEW pending drops. Neither a M4 copied
        # prefix nor AEAD/PN verification nor a timed delivery receipt.
        result["shared_tun_protocol_ingress"]={}
        expected={"offered","tcp_offered","udp_offered","other_offered",
                  "tcp_new_dropped","udp_new_dropped","other_new_dropped",
                  "tcp_pending_displaced"}
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
                    row["other_new_dropped"]+row["tcp_pending_displaced"]
                    for row in rows)!=result["owned_stop"][role]["queue_full_drops"]):
                raise RuntimeError("M029_NEW_VS_DISPLACED_ACCOUNTING_MISMATCH_"+role)
            if LEG!="B" and any(row["tcp_pending_displaced"] for row in rows):
                raise RuntimeError("M029_OLD_LEG_MUST_NOT_DISPLACE")
            if role=="server" and any(row["tcp_pending_displaced"] for row in rows):
                raise RuntimeError("M029_SERVER_NEVER_OPTED_IN")
            result["shared_tun_protocol_ingress"][role]=rows
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
