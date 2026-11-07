#!/usr/bin/env python3
"""PLAN028 offline 10ms app versus 500ms original M4 per-generation stage audit.

Same Linux host CLOCK_MONOTONIC only. M4 kernel-copied != wire/peer/app receipt.
"""
import argparse
import json
import pathlib
import re

STAGES = ("source_queued","m4_copied","tx_err","tx_backpressure",
          "kernel_raw_observed","tuple_candidates","fec_source","fec_parity",
          "fec_recovered","tun_delivered","rx_err","rx_worker_cpu_ns",
          "tx_worker_cpu_ns","physical_rx_packets","physical_tx_packets",
          "physical_rx_dropped")

def samples(log,role):
    out={}
    for line in log.splitlines():
        if f"V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG role={role} " not in line:
            continue
        d={k:int(v) for k,v in re.findall(r"\b([a-z][a-z0-9_]*)=([0-9]+)\b",line)}
        if {"client_port","mono_ns","generation"}<=d.keys():
            out.setdefault(d["client_port"],[]).append(d)
    for rows in out.values():
        rows.sort(key=lambda v:v["mono_ns"])
    return out

def stage(rows,start,end):
    inside=[r for r in rows if start<=r["mono_ns"]<end]
    delta={}
    if len(inside)>=2:
        a,b=inside[0],inside[-1]
        delta={k:b[k]-a[k] for k in STAGES if k in a and k in b}
    return {"samples_in_gap":len(inside),
        "first_ns":inside[0]["mono_ns"] if inside else None,
        "last_ns":inside[-1]["mono_ns"] if inside else None,
        "generation":inside[0]["generation"] if inside else None,
        "inside_deltas":delta,
        "raw_socket_readable_samples":[r.get("raw_socket_readable") for r in inside]}

def analyze(root,who="erin",direction="downlink"):
    root=pathlib.Path(root)
    client=json.loads((root/f"h1250-c-{who}.json").read_text())
    server=json.loads((root/f"h1250-s-{who}.json").read_text())
    assert client["start_ns"]==server["start_ns"],"different monotonic origins"
    sender,receiver=(server,client) if direction=="downlink" else (client,server)
    tx=sender["tx_bytes_bins_10ms"]["udp"]
    rx=receiver["rx_bytes_bins_10ms"]["udp"]
    assert len(tx)==len(rx)
    runs=[];first=None
    for i,(a,b) in enumerate(zip(tx,rx)):
        if a>0 and b==0:
            if first is None:first=i
        elif first is not None:
            runs.append((i-first,first,i));first=None
    if first is not None:runs.append((len(tx)-first,first,len(tx)))
    duration,begin,finish=max(runs,default=(0,0,0))
    start=sender["start_ns"]+begin*10_000_000
    end=sender["start_ns"]+finish*10_000_000
    client_log=(root/f"h1250-product-{who}.log").read_text(errors="replace")
    server_log=(root/"h1250-product-server.log").read_text(errors="replace")
    c=samples(client_log,"client");s=samples(server_log,"server")
    mid=(start+end)//2
    # The old grace still prints samples; choose newest generation started
    # before the gap, and join server by actual port (not server gen ID).
    choices=[(rows[0]["mono_ns"],port) for port,rows in c.items()
             if port in s and rows[0]["mono_ns"]<=mid and rows[-1]["mono_ns"]>=start]
    if not choices:raise ValueError("no exact client/server generation")
    _,port=max(choices)
    adaptations=[]
    for line in server_log.splitlines():
        if "V4_PUBLIC_RAW_TX_PRESSURE_BOUNDED_ADAPT role=server " not in line:
            continue
        d={k:int(v) for k,v in re.findall(r"\b([a-z][a-z0-9_]*)=([0-9]+)\b",line)}
        if d.get("client_port") in c:adaptations.append(d)
    return {"who":who,"direction":direction,"duration_ms":duration*10,
        "app_start_seconds":round(begin/100,3),"mono_start_ns":start,
        "mono_end_ns":end,"offered_bytes_during_gap":sum(tx[begin:finish]),
        "delivered_bytes_during_gap":sum(rx[begin:finish]),
        "active_client_port":port,"observed_client_ports":sorted(c),
        "server_stage":stage(s[port],start,end),
        "client_stage":stage(c[port],start,end),
        "server_adaptations_in_all_client_generations":adaptations,
        "limitations":["kernel copied is not physical NIC/remote receipt",
            "raw observed is native socket-consumed, not interface ingress",
            "same-host CLOCK_MONOTONIC and 500ms sampling only"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True)
    p.add_argument("--who",default="erin")
    p.add_argument("--direction",choices=("uplink","downlink"),default="downlink")
    p.add_argument("--output")
    a=p.parse_args()
    data=json.dumps(analyze(a.art,a.who,a.direction),sort_keys=True,indent=2)+"\n"
    if a.output:pathlib.Path(a.output).write_text(data)
    print(data,end="")
if __name__=="__main__":main()
