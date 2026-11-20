#!/usr/bin/env python3
"""H2239: distinguish netem skb/GSO loss shape from a WBD product regression.

Run actual original Go TLS + Rust Linux native/TUN/AF_PACKET and actual BBR
iperf3 on ONE runner with THREE L3-routed network namespaces.
Controlled A/B/A: native offloads -> no TSO/GSO/GRO -> restore native.
Test-only interface flags, never host globals/product defaults. No fake wire,
new outer reliable transport, PN reseal, per-packet Go callback or HOL queue.
"""
import json
import os
import pathlib
import re
import sys

HERE=pathlib.Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from tools import m0_h2234_local_netns as L

# Project local GE5% and 200ms condition from H2228/H2234, not a new loss model.
LOSS=5
SEED=22390517
FEATURES={"tso":"tcp-segmentation-offload",
          "gso":"generic-segmentation-offload",
          "gro":"generic-receive-offload"}
PHASES=("original_offloads_before","no_segmentation_offloads","original_offloads_after")

def interfaces(node):
    return ((node.client,"wan0"),(node.server,"wan0"),
            (node.router,"rcli0"),(node.router,"rsrv0"))

def feature_readback(namespace,iface):
    raw=L.ns(namespace,"ethtool","-k",iface).stdout
    result={}
    for shorthand,long in FEATURES.items():
        match=re.search(r"(?m)^"+re.escape(long)+r": (on|off)(?: |\r?$)",raw)
        if not match:
            raise RuntimeError("H2239_KERNEL_OFFLOAD_FEATURE_UNKNOWN_"+shorthand)
        result[shorthand]=match.group(1)
    return {"source":"TRUE_LINUX_ETHTOOL_KERNEL_READBACK",
            "ns":namespace,"interface":iface,"features":result}

def offload_baseline(node):
    return [feature_readback(n,iface) for n,iface in interfaces(node)]

def set_offloads(node,baseline,disable):
    if len(baseline)!=4 or [(x["ns"],x["interface"]) for x in baseline]!=list(interfaces(node)):
        raise RuntimeError("H2239_NOT_ORIGINAL_OWNED_NETNS")
    output=[]
    for entry in baseline:
        n,iface=entry["ns"],entry["interface"]
        wanted={key:"off" if disable else entry["features"][key]
                for key in FEATURES}
        # Older kernels can reject setting a fixed-off feature to off.
        # Check actual readback, not whether ethtool reported an echo.
        for key in ("tso","gso","gro"):
            current=feature_readback(n,iface)["features"][key]
            if current!=wanted[key]:
                L.ns(n,"ethtool","-K",iface,key,wanted[key])
        now=feature_readback(n,iface)
        if now["features"]!=wanted:
            raise RuntimeError("H2239_OFFLOAD_READBACK_MISMATCH_"+iface)
        output.append(now)
    return output

def seeded_router_loss(node,loss=LOSS,seed=SEED):
    if loss!=5 or seed!=SEED: raise RuntimeError("H2239_NOT_FROZEN_LOSS_SCENE")
    ge=L.H.ge_params(float(loss))
    records=[]
    for dev in ("rcli0","rsrv0"):
        L.ns(node.router,"tc","qdisc","replace","dev",dev,"root",
             "netem","limit","65536","delay","200ms",
             "loss","gemodel",
             str(ge["transition_good_bad_pct"])+"%",
             "25%","90%","0.1%","seed",str(seed))
        q=L.ns(node.router,"tc","-d","qdisc","show","dev",dev).stdout
        if not ("netem" in q and "200" in q and
                "gemodel" in q and "seed "+str(seed) in q):
            raise RuntimeError("H2239_NETEM_FIXED_SEED_READBACK_UNKNOWN")
        records.append({"device":dev,"seed":seed,
                        "verified_kernel_readback":q})
    return records

def qdisc_actual(receipt):
    """Report qdisc packet drops and link packets separately, never TCP loss."""
    output={}
    for side,item in receipt.items():
        q=item["qdisc"]
        netem=[x for x in q if x.get("kind")=="netem" and x.get("root",False)]
        if len(netem)!=1:
            # Some iproute2 builds express root as the string "root".
            netem=[x for x in q if x.get("kind")=="netem"]
        if len(netem)!=1:
            raise RuntimeError("H2239_QDISC_NOT_SINGLE_REAL_NETEM")
        q=netem[0]
        stats=q.get("stats",{})
        basic=stats.get("basic",{})
        queue=stats.get("queue",{})
        link=item["link"]
        if len(link)!=1:raise RuntimeError("H2239_LINK_READBACK_NOT_EXACT")
        output[side]={
            "netem_qdisc_packets":basic.get("packets"),
            "netem_qdisc_bytes":basic.get("bytes"),
            "netem_qdisc_drops":queue.get("drops"),
            "physical_link_tx_packets":link[0].get("stats64",link[0].get("stats",{})).get("tx",{}).get("packets"),
            "qdisc_drops_are_skb_not_tcp_segment_or_business_bytes":True,
        }
    return output

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    source=os.environ["GITHUB_SHA"]
    runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",source):
        raise RuntimeError("H2239_SOURCE_SHA_MISSING")
    build=workspace/"linux-plan029-public-bundle"
    for filename in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
        if not (build/filename).is_file():
            raise RuntimeError("H2239_MISSING_GENUINE_GO_RUST_NATIVE_"+filename)
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2239_NO_TRUE_KERNEL_TUN")
    out=workspace/"h2239-loss-granularity"
    out.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2239-"+runid)
    tmp.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    os.environ["WBD_H2234_TRACE"]="1"
    node=L.OwnedLocal(build,out,tmp)
    first=[]
    phases=[]
    baseline=None
    status="NOT_RUN"
    error=None
    server_stop=False
    try:
        node.start_network()
        node.start_server()
        baseline=offload_baseline(node)
        node.impairment(0)
        reference=node.iperf_case(0,0,"direct","upload",12,8)
        first.append(reference)
        if (reference.get("status")!="PASS_REAL_KERNEL_IPERF3_TCP" or
            (reference.get("receiver_goodput_mbps") or 0)<500):
            status="NOT_RUN_CAPACITY_BELOW_500"
        elif not any(item["features"]["tso"]=="on" or
                     item["features"]["gso"]=="on" for item in baseline):
            status="NOT_RUN_NATIVE_OFFLOAD_ALREADY_DISABLED_NO_CONTRAST"
        else:
            for idx,name in enumerate(PHASES):
                observed=set_offloads(node,baseline,disable=(idx==1))
                phase={"name":name,"kernel_offloads":observed,
                       "direct":None,"wbd":None}
                phases.append(phase)
                phase["direct_loss_setup"]=seeded_router_loss(node)
                phase["direct"]=node.iperf_case(idx*2+1,LOSS,"direct","upload",20,4)
                phase["direct_qdisc"]=qdisc_actual(node.router_snapshot())
                phase["wbd_loss_setup"]=seeded_router_loss(node)
                node.start_client(LOSS)
                try:
                    phase["wbd"]=node.iperf_case(idx*2+2,LOSS,"wbd","upload",20,4)
                    phase["wbd_qdisc"]=qdisc_actual(node.router_snapshot())
                finally:
                    if node.owned_pid("client") is not None:
                        phase["client_owned_stop"]=node.stop_client(LOSS)
                        node.procs["client"].wait(timeout=15)
                if (phase["direct"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or
                    phase["wbd"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or
                    phase.get("client_owned_stop",{}).get("status")!="REAL_RUST_OWNED_STOP"):
                    status="FAIL_REAL_CASE_OR_OWNED_STOP"
                    break
            if len(phases)==3 and status=="NOT_RUN":
                status="PASS_NATIVE_GSO_CAUSAL_CASES_NOT_PRODUCT_GAIN"
    except Exception as e:
        error=type(e).__name__+": "+str(e)[:450]
        status="FAIL_REAL_SOURCE_FIRST_EXCEPTION"
    finally:
        if baseline is not None and node.namespaces:
            try:
                restored=set_offloads(node,baseline,disable=False)
                L.save(out/"offloads_restored.json",restored)
            except Exception as e:
                if not error:error="RESTORE_"+type(e).__name__+": "+str(e)[:200]
                if status.startswith("PASS"):status="FAIL_OFFLOAD_RESTORE"
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try:server_stop=node.stop_server()
            except Exception as e:
                if not error:error="SERVER_STOP_"+type(e).__name__+": "+str(e)[:200]
        node.cleanup()
        if status.startswith("PASS") and not server_stop:
            status="FAIL_SERVER_OWNED_STOP"
        summary={
            "schema_version":1,"checkpoint":"H2239_GSO_NETEM_SEGMENTATION_REAL",
            "source_sha":source,"run_id":runid,"status":status,"error":error,
            "topology":"ONE_VM_THREE_KERNEL_LINUX_NETNS_ORIGINAL_GO_TLS_RUST",
            "physical_wan":False,"physical_windows":False,
            "target_loss_pct":LOSS,"seed_per_router_direction_per_case":SEED,
            "seed_controls_prng_not_identical_packet_stream":True,
            "oneway_added_delay_ms":200,"jitter_added_ms":0,
            "native_arch":os.uname().machine,"reference":first,
            "offload_baseline":baseline,"phases":phases,
            "server_owned_stop_verified":server_stop,
            "normal_off_fec_only":True,"production_config_unchanged":True,
            "packet_counts_are_skb_not_tcp_segment_loss":True,
            "product_improvement":"NOT_IMPLEMENTED_NOT_VERIFIED"
        }
        L.save(out/"summary.json",summary)
    if status!="PASS_NATIVE_GSO_CAUSAL_CASES_NOT_PRODUCT_GAIN":
        raise RuntimeError("H2239_SOURCE_LOCKED_"+status+" "+str(error or ""))
    print("H2239_TRUE_NATIVE_5PCT_SKB_CAUSAL_DATA_ONLY_PASS_NOT_PRODUCT_OPTIMIZATION")

if __name__=="__main__":
    main()
