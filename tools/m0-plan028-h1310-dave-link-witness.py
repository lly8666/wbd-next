#!/usr/bin/env python3
"""H1310 external read-only 500ms Dave physical link/neighbor/qdisc witness.

Original Product binaries, Go/Rust loop, TLS and Linux routing are UNTOUCHED.
No active probe (no ping/ARP/send/route), just netns readback. This observer
is independent of the 10-application real traffic clock.
"""
import argparse
import json
import os
import pathlib
import signal
import subprocess
import threading
import time

stop = threading.Event()

def query(*argv):
    try:
        p = subprocess.run(argv, text=True, capture_output=True, timeout=2)
        if p.returncode:
            return {"status": "NOT_MEASURED", "exit_code": p.returncode}
        return json.loads(p.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {"status": "NOT_MEASURED", "error": type(exc).__name__}

def link(blob):
    if not isinstance(blob,list) or len(blob)!=1:
        return {"status":"NOT_MEASURED"}
    x=blob[0]
    stats=x.get("stats64",x.get("stats",{}))
    result={"ifname":x.get("ifname")}
    for side in ("rx","tx"):
        result[side]={k:stats.get(side,{}).get(k)
            for k in ("packets","bytes","dropped","errors")}
    return result

def neighbour(blob,ip):
    if not isinstance(blob,list):
        return {"status":"NOT_MEASURED"}
    return [{k:item.get(k) for k in ("dst","state","used","confirmed","updated","probes")}
        for item in blob if item.get("dst")==ip]

def netem(blob):
    if not isinstance(blob,list):
        return {"kind":"NOT_MEASURED"}
    items=[x for x in blob if x.get("kind")=="netem"]
    if not items:return {"kind":"NOT_INSTALLED"}
    q=items[0]
    return {k:q.get(k) for k in
        ("kind","bytes","packets","drops","overlimits","requeues","backlog","qlen")}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    cfg=ap.parse_args()
    suffix=os.environ["GITHUB_RUN_ID"][-6:]
    server_ns="sv"+suffix
    server_nic="p9"+suffix
    client_ns="n3"+suffix
    client_nic="p3"+suffix
    host_nic="h3"+suffix
    ip="10.25.0.5" # Dave physical underlay, NOT his authenticated /32 lease
    signal.signal(signal.SIGTERM,lambda *_:stop.set())
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    rows=[]
    try:
        while not stop.is_set():
            stamp=time.monotonic_ns()
            neighbor=neighbour(query("sudo","-n","ip","-n",server_ns,"-j","-s",
                "neigh","show","to",ip,"dev",server_nic),ip)
            server=link(query("sudo","-n","ip","-n",server_ns,"-j","-s",
                "link","show","dev",server_nic))
            host=link(query("sudo","-n","ip","-j","-s","link",
                "show","dev",host_nic))
            client=link(query("sudo","-n","ip","-n",client_ns,"-j","-s",
                "link","show","dev",client_nic))
            host_qdisc=netem(query("sudo","-n","tc","-s","-j",
                "qdisc","show","dev",host_nic))
            client_qdisc=netem(query("sudo","-n","ip","netns","exec",client_ns,
                "tc","-s","-j","qdisc","show","dev",client_nic))
            if (server.get("ifname")==server_nic and host.get("ifname")==host_nic
                and client.get("ifname")==client_nic
                and host_qdisc.get("kind")=="netem"
                and client_qdisc.get("kind")=="netem"):
                rows.append({"mono_ns":stamp,"server_neighbor_dave":neighbor,
                    "server_shared_veth":server,
                    "host_dave_veth":host,"client_dave_veth":client,
                    "host_dave_downlink_netem":host_qdisc,
                    "client_dave_uplink_netem":client_qdisc})
            stop.wait(0.5)
    finally:
        out=pathlib.Path(cfg.out)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps({"scope":"Dave physical 10.25.0.5 15pct/100ms",
            "diagnostic":"read-only Linux native NUD+veth+netem, monotonic ~500ms",
            "source":"no product or network mutation, no ARP probe",
            "samples":rows},indent=2)+"\n")
        print("H1310_DAVE_READONLY_KERNEL_STAGE_SAMPLES",len(rows),flush=True)

if __name__=="__main__":
    main()
