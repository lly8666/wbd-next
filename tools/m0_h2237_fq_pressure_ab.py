#!/usr/bin/env python3
"""H2237: original Go TLS/Rust low-loss ingress pressure A/B/A, native only.

Runs genuine original product and TCP in one VM with three Linux netns.
Tests whether owned Linux-TUN per-flow fq pacing prevents local SharedTun
loss and improves actual TCP receiver goodput. It does NOT change product
default configuration, create a new transport, or prove WAN/Windows speed.
"""
import json
import os
import pathlib
import re
import shutil
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools import m0_h2234_local_netns as L

PHASES=(("normal600_before",600),("kernel_fq250_probe",250),
        ("normal600_after",600))

def observed_qdisc(node,expected_mbps):
    # The original client has already created and owns wbdc0. Bench-only:
    # changing its qdisc cannot mutate global/sysctl or another user iface.
    if not node.owned_pid("client"):
        raise RuntimeError("H2237_UNOWNED_CLIENT_QDISC_REFUSED")
    expected=("maxrate %dMbit"%expected_mbps)
    q=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
    if not ("qdisc fq " in q and " root " in q and
            expected in q and "flow_limit 256" in q):
        raise RuntimeError("H2237_OWNED_TUN_QDISC_READBACK_MISMATCH")
    return q

def change_only_owned_tun(node,rate_mbps):
    if rate_mbps not in (250,600):
        raise RuntimeError("H2237_QDISC_TEST_RATE_OUT_OF_SCOPE")
    if not node.owned_pid("client"):
        raise RuntimeError("H2237_CLIENT_IDENTITY_MISSING_BEFORE_QDISC")
    L.ns(node.client,"tc","qdisc","replace","dev","wbdc0","root","fq",
         "maxrate",str(rate_mbps)+"mbit","flow_limit","256")
    return observed_qdisc(node,rate_mbps)

def tun_receipt(node):
    return {
        "source":"EXACT_ORIGINAL_CLIENT_LINUX_NETNS_TUN_ONLY",
        "qdisc":json.loads(L.ns(node.client,"tc","-s","-j","qdisc",
                               "show","dev","wbdc0").stdout),
        "link":json.loads(L.ns(node.client,"ip","-s","-j","link",
                              "show","dev","wbdc0").stdout)
    }

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    source=os.environ["GITHUB_SHA"]
    runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",source):
        raise RuntimeError("H2237_SOURCE_SHA_INVALID")
    build=workspace/"linux-plan029-public-bundle"
    if not all((build/name).is_file() for name in
               ("wbd-v4-client","wbd-v4-server","libwbd_engine.so")):
        raise RuntimeError("H2237_ORIGINAL_GO_TLS_RUST_BUILD_MISSING")
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2237_GENUINE_KERNEL_TUN_NOT_AVAILABLE")
    output=workspace/"h2237-fq-pressure"
    output.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2237-"+runid)
    tmp.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2234_TRACE"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    node=L.OwnedLocal(build,output,tmp)
    phases=[]
    direct_cases=[]
    status="NOT_RUN"
    stop_server_verified=False
    error=None
    try:
        node.start_network()
        node.start_server()
        node.impairment(1)
        # Same-VM direct capacity / actual MSS / netem skb reference, no
        # cross-runner speed averaging and no chosen target loss as a fact.
        direct_cases.append(node.iperf_case(0,1,"direct","upload",20,4))
        if direct_cases[0]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or (
                direct_cases[0].get("receiver_goodput_mbps") or 0)<250:
            status="NOT_RUN_UNQUALIFIED_DIRECT_REFERENCE"
        else:
            for index,(label,rate) in enumerate(PHASES,1):
                phase={"name":label,"test_only_tun_qdisc_rate_mbps":rate,
                       "genuine_original_product_default_rate_mbps":600}
                phases.append(phase)
                # Each A/B/A case gets an independent cold TLS + Rust lease
                # generation, same install-ID/lease semantics and owned Stop.
                node.start_client(1)
                try:
                    if rate==250:
                        phase["qdisc_before"]=change_only_owned_tun(node,rate)
                    else:
                        phase["qdisc_before"]=observed_qdisc(node,600)
                    phase["tun_before"]=tun_receipt(node)
                    phase["case"]=node.iperf_case(index,1,"wbd","upload",20,4)
                    phase["tun_after"]=tun_receipt(node)
                finally:
                    if node.owned_pid("client") is not None:
                        phase["owned_stop"]=node.stop_client(1)
                        # Original Rust + Go threads must cease before next
                        # client generation takes control of same route.
                        node.procs["client"].wait(timeout=15)
                        if node.procs["client"].returncode not in (0,-15,-2):
                            raise RuntimeError("H2237_CLIENT_EXIT_UNEXPECTED")
                    prior=output/"loss1-client.log"
                    if prior.is_file():
                        shutil.copyfile(prior,output/(label+"-client.log"))
                if phase["case"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP":
                    status="FAIL_REAL_WBD_IPERF"
                    break
            if len(phases)==3 and all(
                x.get("owned_stop",{}).get("status")=="REAL_RUST_OWNED_STOP"
                for x in phases
            ) and status!="FAIL_REAL_WBD_IPERF":
                direct_cases.append(node.iperf_case(4,1,"direct","upload",20,4))
                status=("PASS_GENUINE_ABA_DATA_ONLY_NO_PRODUCT_CHANGE"
                    if direct_cases[-1]["status"]=="PASS_REAL_KERNEL_IPERF3_TCP"
                    else "FAIL_FINAL_DIRECT_REFERENCE")
    except Exception as ex:
        error=type(ex).__name__+": "+str(ex)[:350]
        status="FAIL_FIRST_EXCEPTION"
    finally:
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try: stop_server_verified=node.stop_server()
            except Exception as ex:
                if not error:error="STOP_"+type(ex).__name__+": "+str(ex)[:350]
        node.cleanup()
        if status=="PASS_GENUINE_ABA_DATA_ONLY_NO_PRODUCT_CHANGE" and not stop_server_verified:
            status="FAIL_ORIGINAL_SERVER_STOP"
        summary={
            "schema_version":1,"checkpoint":"H2237_LOW_LOSS_TUN_FQ_CAUSAL_PROBE",
            "source_sha":source,"run_id":runid,"status":status,
            "error":error,"arch":os.uname().machine,
            "topology":"ONE_VM_THREE_LINUX_NETNS_ORIGINAL_GO_TLS_RUST_TRUE_TUN",
            "real_wan":False,"real_windows":False,
            "original_product_fq_default_mbps":600,
            "qdisc_250_is_BENCH_ONLY_NOT_PRODUCT_CONFIG":True,
            "no_protocol_or_source_queue_change":True,
            "target_loss_pct":1,"added_oneway_delay_ms":200,
            "jitter_ms":0,"direct_before_after":direct_cases,
            "phases":phases,"server_owned_stop_verified":stop_server_verified,
            "interpretation":"A-B-A is a source/VM matched diagnostic only; "
                "reduction of local drops alone does not prove receiver goodput "
                "or small-flow p99 improvement",
            "product_improvement":"NOT_IMPLEMENTED_NOT_TESTED"
        }
        L.save(output/"summary.json",summary)
    if status!="PASS_GENUINE_ABA_DATA_ONLY_NO_PRODUCT_CHANGE":
        raise RuntimeError("H2237_FQ_ABA_"+status+" "+str(error or ""))
    print("H2237_NATIVE_FQ_ABA_REAL_DATA_COMPLETED_NOT_PRODUCT_GAIN")

if __name__=="__main__":
    main()
