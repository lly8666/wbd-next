#!/usr/bin/env python3
"""One real Normal TCP measurement, invoked only inside the existing netns fixture."""
import json, os, pathlib, subprocess, sys, time
client,server,out=sys.argv[1:]
out=pathlib.Path(out)
def pid(ns,comm):
    ids=subprocess.check_output(["sudo","-n","ip","netns","pids",ns],text=True).split()
    found=[int(p) for p in ids if pathlib.Path("/proc",p,"comm").read_text().strip()==comm]
    assert len(found)==1,(ns,comm,found)
    return found[0]
def ticks(p):
    a=pathlib.Path("/proc",str(p),"stat").read_text().rsplit(")",1)[1].split()
    return int(a[11])+int(a[12])
pids=[pid(client,"wbd-v4-client"),pid(server,"wbd-v4-server")]
with (out/"tcp-iperf-server.log").open("w") as f:
    s=subprocess.Popen(["sudo","-n","ip","netns","exec",server,"iperf3","-s","-1","-B","10.188.18.2","-p","5201"],stdout=f,stderr=subprocess.STDOUT)
    try:
        time.sleep(1)
        before=[ticks(p) for p in pids]
        raw=subprocess.check_output(["sudo","-n","ip","netns","exec",client,"iperf3","-c","10.188.18.2","-B","10.188.18.1","-p","5201","-P","4","-t","10","-J"],text=True,timeout=45)
        after=[ticks(p) for p in pids]
        s.wait(timeout=10)
    finally:
        if s.poll() is None: s.terminate()
(out/"tcp-iperf.json").write_text(raw)
d=json.loads(raw)
assert "error" not in d,d.get("error")
rx=d["end"]["sum_received"]
n=rx["bytes"]; assert n>0
cpu=[(b-a)/os.sysconf("SC_CLK_TCK") for a,b in zip(before,after)]
row={"received_bytes":n,"goodput_mbps":rx["bits_per_second"]/1e6,"client_cpu_s":cpu[0],"server_cpu_s":cpu[1],"cpu_s_per_gib":sum(cpu)/(n/2**30),"seconds":rx["seconds"],"flows":4}
(out/"tcp-perf.json").write_text(json.dumps(row,indent=2)+"\n")
print(json.dumps(row,sort_keys=True),flush=True)
