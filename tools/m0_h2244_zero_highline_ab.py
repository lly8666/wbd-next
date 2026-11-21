#!/usr/bin/env python3
"""H2244: zero-loss high-capacity A/B/A with true original native source.

Compare ORIGINAL per-flow fq600 to TEST-ONLY TBF1200Mbit/48KiB/fq_codel
on a *verified* owned ephemeral TUN. 1200 is a diagnostic stress rate,
not an acceptable shipping cap or auto-service algorithm. Every phase
includes actual small UDP/TCP echoes concurrently with four bulk TCP.
"""
import json
import os
import pathlib
import re
import shutil
import sys

REPO=pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools import m0_h2234_local_netns as L
from tools import m0_h2243_burst_fair_abca as H
from tools import m0_h2244_native_tail_abca as N

PHASES=(("original_before",0),("tbf1200_48kiB_fq_codel",1200),("original_after",0))
FINAL="PASS_H2244_TRUE_ZERO_LOSS_HIGHLINE_NATIVE_BULK_AND_SMALL_ABA_DIAGNOSTIC_ONLY"

def install_highline_owned_tun(node):
    if node.owned_pid("client") is None:
        raise RuntimeError("H2244_HIGHLINE_NO_OWNED_ORIGINAL_CLIENT_PID")
    before=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
    if "qdisc fq " not in before or " root " not in before or "maxrate 600Mbit" not in before:
        raise RuntimeError("H2244_HIGHLINE_NOT_ORIGINAL_GO_FQ600")
    link=json.loads(L.ns(node.client,"ip","-j","link","show","dev","wbdc0").stdout)
    if len(link)!=1 or link[0].get("ifname")!="wbdc0" or link[0].get("txqlen")!=2048:
        raise RuntimeError("H2244_HIGHLINE_UNOWNED_TUN_OR_TX_RING_CHANGED")
    L.ns(node.client,"tc","qdisc","replace","dev","wbdc0",
         "root","handle","1:","tbf","rate","1200mbit",
         "burst","48kb","latency","15ms")
    L.ns(node.client,"tc","qdisc","replace","dev","wbdc0",
         "parent","1:1","handle","10:","fq_codel",
         "limit","256","target","5ms","interval","100ms","ecn")
    after=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
    if not ("qdisc tbf 1:" in after and " root " in after
            and "qdisc fq_codel 10:" in after and "parent 1:1" in after):
        raise RuntimeError("H2244_HIGHLINE_QDISC_READBACK_FAILED")
    if not re.search(r"\brate\s+(?:1200Mbit|1\.2Gbit|1200000Kbit)\b",after):
        raise RuntimeError("H2244_HIGHLINE_ACTUAL_RATE_NOT_1200MBIT")
    return {"test_only_fixed_rate_mbit":1200,"burst_kib":48,
            "owned_ephemeral_tun":"wbdc0",
            "original_per_flow_fq600_before":before,
            "original_source_highline_tbf_fair_child":after,
            "no_global_or_unowned_qdisc_change":True,
            "not_new_product_configuration":True}

def concurrent_probe(node,label,idx):
    probe_out=node.out/(label+"-smallflow.json")
    role="h2244-zero-small-"+label.replace("_","-")
    node.spawn(role,node.client,[
        "env","GITHUB_SHA="+os.environ["GITHUB_SHA"],
        "GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],
        "python3","-u",str(REPO/"tools/m0_h2244_smallflow_echo.py"),
        "client","--server","10.66.0.1","--output",str(probe_out)])
    case=node.iperf_case(idx,0,"wbd","upload",20,4)
    p=node.procs[role]
    p.wait(timeout=27)
    if p.returncode!=0 or not probe_out.is_file():
        raise RuntimeError("H2244_HIGHLINE_REAL_ECHO_FAILED")
    probe=json.loads(probe_out.read_text())
    if probe.get("status")!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO":
        raise RuntimeError("H2244_HIGHLINE_INVALID_APP_PROBE")
    if probe.get("source_sha")!=os.environ["GITHUB_SHA"] or (
        probe.get("run_id")!=os.environ["GITHUB_RUN_ID"]):
        raise RuntimeError("H2244_HIGHLINE_ECHO_DIFFERENT_SOURCE")
    a=case.get("iperf_start_monotonic_ns")
    b=case.get("iperf_end_monotonic_ns")
    c=probe.get("probe_start_monotonic_ns")
    d=probe.get("probe_end_monotonic_ns")
    if not all(isinstance(x,int) for x in (a,b,c,d)) or not (a<c<d<=b):
        raise RuntimeError("H2244_HIGHLINE_UDP_TCP_NOT_CONCURRENT_WITH_BULK")
    for kind in ("tcp","udp"):
        v=probe[kind]
        if v["requests_sent"]!=160 or v["unique_replies"]<50 or (
            v["missing"]+v["unique_replies"]!=160 or
            v["latency_ms"]["p99"] is None):
            raise RuntimeError("H2244_HIGHLINE_SMALL_FLOW_MISSING_REAL_SAMPLES_"+kind)
    return case,probe

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    source=os.environ["GITHUB_SHA"];runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",source):
        raise RuntimeError("H2244_HIGHLINE_UNQUALIFIED_SHA")
    build=workspace/"linux-plan029-public-bundle"
    if not all((build/n).is_file() for n in (
        "wbd-v4-client","wbd-v4-server","libwbd_engine.so")):
        raise RuntimeError("H2244_HIGHLINE_ORIGINAL_GO_RUST_BINARY_MISSING")
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2244_HIGHLINE_NO_REAL_TUN")
    out=workspace/"h2244-zero-highline"
    out.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2244-zero-"+runid)
    tmp.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2234_TRACE"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    os.environ["WBD_H2240_NATIVE_TEST"]="1"
    os.environ["WBD_H2241_NATIVE_GATE"]="0"
    node=L.OwnedLocal(build,out,tmp)
    phases=[];direct=[];server_stop=False;echo_stop=False
    status="NOT_RUN";error=None
    try:
        node.start_network();node.start_server()
        role="h2244-zero-echo"
        node.spawn(role,node.server,[
            "python3","-u",str(REPO/"tools/m0_h2244_smallflow_echo.py"),
            "server","--bind","10.66.0.1"])
        if not L.ready(out/(role+".log"),"H2244_ECHO_SERVER_READY",12):
            raise RuntimeError("H2244_HIGHLINE_INNER_ECHO_SERVER_NOT_READY")
        node.impairment(0)
        direct.append(node.iperf_case(0,0,"direct","upload",12,8))
        if direct[0]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or (
            direct[0].get("receiver_goodput_mbps") or 0)<800:
            status="NOT_RUN_ORIGINAL_DIRECT_HIGHLINE_CAPACITY_UNQUALIFIED"
        else:
            for i,(name,rate) in enumerate(PHASES,1):
                row={"name":name,"test_only_rate_mbit":rate,
                     "no_original_reader_pause":True}
                phases.append(row)
                node.start_client(0)
                try:
                    if rate:
                        row["owned_highline_qdisc"]=install_highline_owned_tun(node)
                    else:
                        q=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
                        if "qdisc fq " not in q or "maxrate 600Mbit" not in q:
                            raise RuntimeError("H2244_HIGHLINE_BASELINE_FQ600_NOT_RESTORED")
                    before=H.tun_kernel_snapshot(node)
                    row["bulk_tcp"],row["smallflow"]=concurrent_probe(node,name,i)
                    after=H.tun_kernel_snapshot(node)
                    row["layered_kernel_drops"]=H.source_kernel_qdisc_receipt(
                        before,after,"tbf" if rate else "original")
                    diag,buckets=H.scoped_diagnostic(
                        node.clientlog.read_text(errors="replace"),row["bulk_tcp"],name)
                    row["original_sharedtun_m4_time_bins"]=diag
                    L.save(out/(name+"-timeline.json"),buckets)
                finally:
                    if node.owned_pid("client") is not None:
                        row["client_owned_stop"]=node.stop_client(0)
                        node.procs["client"].wait(timeout=15)
                    row["gate_disabled"]=H.gate_stop_receipt(
                        node.clientlog.read_text(errors="replace"),False)
                    log=out/"loss0-client.log"
                    if log.exists():shutil.copyfile(log,out/(name+"-client.log"))
                if row["bulk_tcp"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP":
                    status="FAIL_ORIGINAL_BULK_APP";break
            if len(phases)==3 and status=="NOT_RUN":
                direct.append(H.rearm_direct_capacity_listener(node))
                direct.append(node.iperf_case(4,0,"direct","upload",12,8))
                status=(FINAL if direct[-1]["status"]=="PASS_REAL_KERNEL_IPERF3_TCP"
                        else "FAIL_FINAL_DIRECT_REFERENCE")
    except Exception as e:
        error=type(e).__name__+": "+str(e)[:450]
        status="FAIL_FIRST_TRUE_HIGHLINE_EVENT"
    finally:
        if "h2244-zero-echo" in node.procs:
            try:echo_stop=N.owned_echo_server_stop(node,"h2244-zero-echo")
            except Exception as e:
                if error is None:error="ECHO_STOP_"+type(e).__name__+str(e)[:180]
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try:server_stop=node.stop_server()
            except Exception as e:
                if error is None:error="SERVER_STOP_"+type(e).__name__+str(e)[:180]
        node.cleanup()
        if status==FINAL and not(echo_stop and server_stop):
            status="FAIL_EXACT_NATIVE_OR_ECHO_STOP"
        L.save(out/"summary.json",{
            "schema_version":1,
            "checkpoint":"H2244_TRUE_ZERO_LOSS_HIGHLINE_NO_RATE_CAP_PRODUCT",
            "source_sha":source,"run_id":runid,"arch":os.uname().machine,
            "status":status,"error":error,
            "same_runner_three_real_linux_netns":True,
            "true_original_go_tls_rust_owner":True,
            "network":"zero added loss/delay, kernel native path, no DERP",
            "not_physical_wan":True,"not_product_optimization":True,
            "test_only_fixed_1200mbit_not_default":True,
            "true_original_no_gate_and_0_hol":True,
            "direct_before_after":direct,
            "phases":phases,
            "echo_server_owned_stop":echo_stop,"server_owned_stop":server_stop
        })
    if status!=FINAL:
        raise RuntimeError("H2244_HIGHLINE_"+status+" "+str(error or ""))
    print("H2244_TRUE_ZERO_LOSS_HIGHLINE_BULK_AND_SMALL_UDP_TCP_SCOPED")

if __name__=="__main__":main()
