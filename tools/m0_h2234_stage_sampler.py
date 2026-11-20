#!/usr/bin/env python3
"""H2234: opt-in, outside-data-plane Linux scheduler and NIC forensic sampler.

No packet contents, no network reads, no Go per-packet callback, no new
Rust scheduler, no control of the owned worker. Runs as an independent
short-lived diagnostic process; never makes product readiness claims.
"""
import argparse
import json
import os
import pathlib
import re
import time

THREADS={"wbd-m4-tx","wbd-m4-rx","wbd-tun-reader","wbd-tun-ingress",
         "wbd-m4-observe"}
MAX_SAMPLES=400
MAX_SECONDS=100
MIN_INTERVAL_MS=100
MAX_INTERVAL_MS=1000

def read_text(path):
    try:return pathlib.Path(path).read_text().strip()
    except (OSError,UnicodeError):return None

def read_scheduler(task):
    raw=read_text(task/"schedstat")
    if raw is None:return {"status":"UNAVAILABLE_SCHEDSTAT"}
    parts=raw.split()
    if len(parts)<3:return {"status":"UNAVAILABLE_SCHEDSTAT"}
    try: run,wait,slices=map(int,parts[:3])
    except ValueError:return {"status":"UNAVAILABLE_SCHEDSTAT"}
    if min(run,wait,slices)<0:return {"status":"UNAVAILABLE_SCHEDSTAT"}
    status=read_text(task/"status") or ""
    context={}
    for label,name in (("voluntary_ctxt_switches","voluntary"),
                       ("nonvoluntary_ctxt_switches","involuntary")):
        match=re.search(r"(?m)^"+label+r":\s*(\d+)$",status)
        context[name]=int(match.group(1)) if match else None
    return {"status":"LINUX_TASK_SCHEDSTAT",
            "cpu_run_ns":run,"runnable_wait_ns":wait,"scheduler_slices":slices,
            "wchan":read_text(task/"wchan"),**context}

def read_netdev(proc_pid_dir):
    raw=read_text(proc_pid_dir/"net"/"dev")
    if raw is None:return {"status":"UNAVAILABLE_NETDEV"}
    data={}
    for line in raw.splitlines():
        if ":" not in line:continue
        name,fields=line.split(":",1)
        name=name.strip()
        if name not in ("wan0","wbdc0"):continue
        try:
            n=[int(x) for x in fields.split()]
            if len(n)<16:continue
            data[name]={"rx_bytes":n[0],"rx_packets":n[1],"rx_dropped":n[3],
                        "tx_bytes":n[8],"tx_packets":n[9],"tx_dropped":n[11]}
        except ValueError:continue
    return {"status":"LINUX_KERNEL_NETDEV" if data else "UNKNOWN_NETDEV_NAMES",
            "interfaces":data}

def snapshot(proc_root,pid):
    root=pathlib.Path(proc_root)/str(pid)
    comm=read_text(root/"comm")
    if comm not in ("wbd-v4-client","wbd-v4-server"):
        return {"status":"UNKNOWN_NOT_VERIFIED_ORIGINAL_WORKER",
                "actual_comm":comm,"threads":{}}
    tasks=root/"task"
    threads={}
    try:tids=sorted(int(d.name) for d in tasks.iterdir() if d.name.isdecimal())
    except OSError:return {"status":"UNKNOWN_TASK_DIRECTORY","threads":{}}
    for tid in tids:
        entry=tasks/str(tid)
        name=read_text(entry/"comm")
        if name not in THREADS:continue
        threads[str(tid)]={"name":name,**read_scheduler(entry)}
    return {"status":"GENUINE_ORIGINAL_PROCESS",
            "worker_comm":comm,"threads":threads,"netdev":read_netdev(root)}

def deltas(old,new):
    """Never turn absent/retired task counters into a zero-wait PASS."""
    prev=old.get("threads",{}) if isinstance(old,dict) else {}
    curr=new.get("threads",{}) if isinstance(new,dict) else {}
    output=[]
    for tid,entry in curr.items():
        a=prev.get(tid)
        if not a or a.get("name")!=entry.get("name") or (
            a.get("status")!="LINUX_TASK_SCHEDSTAT" or
            entry.get("status")!="LINUX_TASK_SCHEDSTAT"):
            continue
        fields=("cpu_run_ns","runnable_wait_ns","scheduler_slices",
                "voluntary","involuntary")
        delta={}
        for name in fields:
            x=a.get(name);y=entry.get(name)
            delta[name]=(y-x if isinstance(x,int) and isinstance(y,int) and y>=x
                         else None)
        output.append({"tid":int(tid),"name":entry["name"],**delta})
    return output

def diagnose(samples):
    observations=[x for x in samples if x.get("kind")=="SAMPLE"]
    pairs=[]
    for a,b in zip(observations,observations[1:]):
        if b["monotonic_ns"]<=a["monotonic_ns"]:continue
        for row in deltas(a.get("value",{}),b.get("value",{})):
            row["interval_ns"]=b["monotonic_ns"]-a["monotonic_ns"]
            pairs.append(row)
    grouped={}
    for row in pairs:
        item=grouped.setdefault(row["name"],{
            "intervals":0,"run_ns":0,"wait_ns":0,"max_wait_ns_in_sample":0,
            "max_run_ns_in_sample":0,"sched_slices":0,
            "involuntary_context_switches":0})
        item["intervals"]+=1
        for key,field in (("run_ns","cpu_run_ns"),("wait_ns","runnable_wait_ns"),
                          ("sched_slices","scheduler_slices"),
                          ("involuntary_context_switches","involuntary")):
            if isinstance(row[field],int):item[key]+=row[field]
        if isinstance(row["runnable_wait_ns"],int):
            item["max_wait_ns_in_sample"]=max(item["max_wait_ns_in_sample"],
                                              row["runnable_wait_ns"])
        if isinstance(row["cpu_run_ns"],int):
            item["max_run_ns_in_sample"]=max(item["max_run_ns_in_sample"],
                                             row["cpu_run_ns"])
    return {"status":"SAMPLED_NOT_FULL_PACKET_CAUSAL_PROOF" if pairs else
              "UNKNOWN_NO_COMPARABLE_SCHEDSTAT",
            "sampled_intervals":len(pairs),"threads":grouped,
            "no_packet_or_secret_data_collected":True}

def capture(args,proc_root="/proc"):
    output=pathlib.Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    stop=pathlib.Path(args.stop_file)
    start=time.monotonic()
    count=0
    samples=[]
    status="MAX_DURATION_REACHED"
    pidstr=read_text(args.pidfile)
    try:pid=int(pidstr or "")
    except ValueError:pid=0
    if pid<=1 or pid>=4194304:pid=0
    with output.open("w") as f:
        def emit(obj):
            f.write(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n")
            f.flush()
        emit({"kind":"HEADER","schema_version":1,"pid":pid,
              "source_sha":args.source_sha,"run_id":args.run_id,
              "interval_ms":args.interval_ms,
              "classification":"EXTERNAL_LINUX_PROC_OBSERVER_NOT_WIRE_OR_DELIVERY",
              "monotonic_ns":time.monotonic_ns()})
        while count<MAX_SAMPLES and time.monotonic()-start<min(args.max_seconds,MAX_SECONDS):
            if stop.exists():
                status="STOPFILE_SIGNALLED";break
            sample={"kind":"SAMPLE","monotonic_ns":time.monotonic_ns(),
                    "value":snapshot(proc_root,pid) if pid else
                            {"status":"UNKNOWN_PID_FILE","threads":{}}}
            emit(sample);samples.append(sample);count+=1
            time.sleep(args.interval_ms/1000)
        if count>=MAX_SAMPLES:status="SAMPLE_CAP_REACHED"
        result=diagnose(samples)
        emit({"kind":"FOOTER","stop_reason":status,"samples":count,**result})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pidfile",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--stop-file",required=True)
    p.add_argument("--source-sha",default="")
    p.add_argument("--run-id",default="")
    p.add_argument("--interval-ms",type=int,default=200)
    p.add_argument("--max-seconds",type=int,default=45)
    a=p.parse_args()
    if not MIN_INTERVAL_MS<=a.interval_ms<=MAX_INTERVAL_MS or not 1<=a.max_seconds<=MAX_SECONDS:
        p.error("invalid bounded sampler interval/duration")
    if a.source_sha and not re.fullmatch("[a-f0-9]{40}",a.source_sha):
        p.error("source-sha must be a commit SHA")
    capture(a)

if __name__=="__main__":main()
