#!/usr/bin/env python3
"""H2244 GE1% true original WBD bulk TCP + concurrent small UDP/TCP A/B/A.

Diagnostic ONLY, stacked on the H2243 *benchmark* branch. Never merge
rejected H2241 gate or experimental hard450 qdisc into production main.
True Go TLS/Rust M4/Stop; every client generation has a unique owned TUN.
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

PHASES=(("original_before",0),("tbf48kb_fq_codel",48),("original_after",0))
RESULT_STATUS="PASS_H2244_REAL_CONCURRENT_SMALL_UDP_TCP_ORIGINAL_TBF48_ORIGINAL_DIAGNOSTIC_ONLY"

def owned_echo_server_stop(node,role):
    """Only stop our separately spawned exact source python3 echo process."""
    pidfile=node.tmp/(role+".pid")
    if not pidfile.exists():
        raise RuntimeError("H2244_OWNED_ECHO_SERVER_PID_MISSING")
    pid=int(pidfile.read_text().strip())
    if pid<2:raise RuntimeError("H2244_INVALID_ECHO_PID")
    actual=L.root("ps","-o","comm=","-p",str(pid),allow_fail=True).stdout.strip()
    if actual!="python3":
        raise RuntimeError("H2244_NOT_OWNED_ECHO_PYTHON_PID")
    L.root("kill","-TERM",str(pid))
    node.procs[role].wait(timeout=7)
    if node.procs[role].returncode not in (0,143,-15):
        # sudo often propagates signal as +128; still require no live PID.
        if L.root("ps","-o","comm=","-p",str(pid),allow_fail=True).stdout.strip()=="python3":
            raise RuntimeError("H2244_ECHO_SERVER_STILL_ALIVE")
    return True

def echo_receipt(node,phase,case):
    """Receipt must overlap the same original iperf case on same VM/clock."""
    path=node.out/(phase+"-smallflow.json")
    role="h2244-small-"+phase.replace("_","-")
    script=str(REPO/"tools/m0_h2244_smallflow_echo.py")
    node.spawn(role,node.client,["env",
                                "GITHUB_SHA="+os.environ["GITHUB_SHA"],
                                "GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],
                                "python3","-u",script,"client",
                                "--server","10.66.0.1","--output",str(path)])
    # The app sleeps two seconds before sending. Run genuine bulk on the same
    # client namespace as this sidecar, not a synthetic fake transport.
    original_case=node.iperf_case(case,1,"wbd","upload",20,4)
    process=node.procs[role]
    process.wait(timeout=27)
    if process.returncode!=0 or not path.is_file():
        raise RuntimeError("H2244_SMALL_ECHO_PROCESS_FAILED_"+str(process.returncode))
    result=json.loads(path.read_text())
    if result.get("status")!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO":
        raise RuntimeError("H2244_SMALL_APP_ECHO_DID_NOT_PASS")
    if result.get("source_sha")!=os.environ["GITHUB_SHA"] or (
        result.get("run_id")!=os.environ["GITHUB_RUN_ID"]):
        raise RuntimeError("H2244_ECHO_SOURCE_RUN_MISMATCH")
    lo=original_case.get("iperf_start_monotonic_ns")
    hi=original_case.get("iperf_end_monotonic_ns")
    first=result.get("probe_start_monotonic_ns")
    last=result.get("probe_end_monotonic_ns")
    if not all(isinstance(x,int) for x in (lo,hi,first,last)) or not lo<first<last<=hi:
        raise RuntimeError("H2244_NOT_REALLY_CONCURRENT_WITH_ORIGINAL_BULK")
    for kind in ("udp","tcp"):
        data=result[kind]
        if data["requests_sent"]!=160 or data["unique_replies"]<50:
            raise RuntimeError("H2244_INSUFFICIENT_TRUE_SMALL_"+kind.upper())
        if data["missing"]+data["unique_replies"]!=160:
            raise RuntimeError("H2244_NOT_ACCOUNTING_MISSING_"+kind.upper())
        if data["latency_ms"]["p99"] is None:
            raise RuntimeError("H2244_P99_UNKNOWN_"+kind.upper())
    return original_case,result

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    source=os.environ["GITHUB_SHA"];runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",source):
        raise RuntimeError("H2244_UNQUALIFIED_SOURCE_SHA")
    build=workspace/"linux-plan029-public-bundle"
    if not all((build/n).is_file() for n in (
        "wbd-v4-client","wbd-v4-server","libwbd_engine.so")):
        raise RuntimeError("H2244_TRUE_ORIGINAL_NATIVE_BINARIES_NOT_FOUND")
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2244_REAL_LINUX_TUN_NOT_AVAILABLE")
    out=workspace/"h2244-small-bulk-abca"
    out.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2244-"+runid)
    tmp.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2234_TRACE"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    os.environ["WBD_H2240_NATIVE_TEST"]="1"
    os.environ["WBD_H2241_NATIVE_GATE"]="0"
    node=L.OwnedLocal(build,out,tmp)
    phases=[];references=[];server_stop=False;echo_stop=False
    status="NOT_RUN";error=None
    try:
        node.start_network()
        node.start_server()
        echo_role="h2244-inner-echo"
        node.spawn(echo_role,node.server,[
            "python3","-u",str(REPO/"tools/m0_h2244_smallflow_echo.py"),
            "server","--bind","10.66.0.1"])
        if not L.ready(out/(echo_role+".log"),"H2244_ECHO_SERVER_READY",12):
            raise RuntimeError("H2244_TRUE_INNER_ECHO_SERVER_NOT_READY")
        node.impairment(1)
        references.append(node.iperf_case(0,1,"direct","upload",20,4))
        if references[0]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or (
            references[0].get("receiver_goodput_mbps") or 0)<250:
            status="NOT_RUN_INDEPENDENT_DIRECT_CAPACITY_INSUFFICIENT"
        else:
            for i,(label,burst) in enumerate(PHASES,1):
                row={"name":label,"burst_kib":burst,"original_reader_gate":False,
                     "four_original_kernel_bbr_tcp_flows":True}
                phases.append(row)
                node.start_client(1)
                try:
                    if burst:
                        row["source_fair_setup"]=H.install_owned_tun_aggregate_burst_fair(
                            node,burst)
                    else:
                        q=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
                        if "qdisc fq " not in q or "maxrate 600Mbit" not in q:
                            raise RuntimeError("H2244_ORIGINAL_GO_FQ600_NOT_RESTORED")
                    before=H.tun_kernel_snapshot(node)
                    row["bulk_tcp"],row["smallflow"]=echo_receipt(node,label,i)
                    after=H.tun_kernel_snapshot(node)
                    row["actual_kernel_drops"]=H.source_kernel_qdisc_receipt(
                        before,after,"tbf" if burst else "original")
                    diagnostic,buckets=H.scoped_diagnostic(
                        node.clientlog.read_text(errors="replace"),row["bulk_tcp"],label)
                    row["original_tun_to_m4_timeline"]=diagnostic
                    L.save(out/(label+"-timeline.json"),buckets)
                finally:
                    if node.owned_pid("client") is not None:
                        row["original_client_owned_stop"]=node.stop_client(1)
                        node.procs["client"].wait(timeout=15)
                    row["no_reader_gate"]=H.gate_stop_receipt(
                        node.clientlog.read_text(errors="replace"),False)
                    log=out/"loss1-client.log"
                    if log.is_file():shutil.copyfile(log,out/(label+"-client.log"))
                if row["bulk_tcp"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP":
                    status="FAIL_REAL_ORIGINAL_BULK_TCP";break
            if len(phases)==3 and status=="NOT_RUN":
                references.append(H.rearm_direct_capacity_listener(node))
                references.append(node.iperf_case(4,1,"direct","upload",20,4))
                status=(RESULT_STATUS if references[-1]["status"]=="PASS_REAL_KERNEL_IPERF3_TCP"
                        else "FAIL_FINAL_TRUE_DIRECT_REFERENCE")
    except Exception as e:
        error=type(e).__name__+": "+str(e)[:450]
        status="FAIL_FIRST_REAL_H2244_EVENT"
    finally:
        if "h2244-inner-echo" in node.procs:
            try:echo_stop=owned_echo_server_stop(node,"h2244-inner-echo")
            except Exception as e:
                if error is None:error="H2244_ECHO_STOP_"+type(e).__name__+":"+str(e)[:150]
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try:server_stop=node.stop_server()
            except Exception as e:
                if error is None:error="H2244_SERVER_STOP_"+type(e).__name__+":"+str(e)[:150]
        node.cleanup()
        if status==RESULT_STATUS and not (server_stop and echo_stop):
            status="FAIL_AUTHENTIC_STOP_OR_ECHO_RESOURCE_CLEANUP"
        L.save(out/"summary.json",{
            "schema_version":1,
            "checkpoint":"H2244_REAL_ORIGINAL_GE1_BULK_CONCURRENT_SMALL_UDP_TCP_ABA",
            "source_sha":source,"run_id":runid,
            "arch":os.uname().machine,
            "status":status,"error":error,
            "network":"GE1% +200ms one-way unseeded, same VM three real netns",
            "physical_wan":False,"not_product_optimization":True,
            "no_product_default_changes":True,"source_only_test_450mbit":True,
            "real_original_tls_rust_one_owner":True,
            "no_cross_business_hol_or_reliable_outer_upgrade":True,
            "direct_real_before_after":references,
            "phases":phases,
            "echo_server_owned_stop":echo_stop,"native_server_owned_stop":server_stop,
            "all_results_are_causal_qualification_not_speedup_claim":True
        })
    if status!=RESULT_STATUS:
        raise RuntimeError("H2244_"+status+" "+str(error or ""))
    print("H2244_REAL_CONCURRENT_SMALL_UDP_TCP_BULK_GE1_ABA_OBSERVED")

if __name__=="__main__":main()
