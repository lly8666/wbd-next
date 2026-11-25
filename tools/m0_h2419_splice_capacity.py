#!/usr/bin/env python3
"""H2419 isolate the exact production transparent TCP splice owner.
Three local kernel namespaces, NOT three physical runners or WBD performance.
A/B/B/A: NAT vs actual TPROXY + splice, single reverse TCP, zero impairment.
"""
import json, os, pathlib, re, signal, subprocess, time, sys, hashlib
O=pathlib.Path("h2419-out").resolve()
O.mkdir(exist_ok=True)
BIN=pathlib.Path("h2419-build/relay").resolve()
NS=("h19client","h19relay","h19origin")
C,R,S=NS
def run(*a):
    return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT)
def ns(n,*a):
    return run("ip","netns","exec",n,*a)
def proc_cpu(pid):
    s=pathlib.Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()
    return [int(s[11]),int(s[12])]
def host_cpu():
    return [int(x) for x in pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
def delta(a,b):
    return [y-x for x,y in zip(a,b)]
def save(name,v):
    (O/name).write_text(json.dumps(v,indent=2)+"\n")
def make():
    for n in NS:
        run("ip","netns","add",n);ns(n,"ip","link","set","lo","up")
    for a,b,n,m in [("h19c","h19in",C,R),("h19out","h19s",R,S)]:
        run("ip","link","add",a,"type","veth","peer","name",b)
        run("ip","link","set",a,"netns",n)
        run("ip","link","set",b,"netns",m)
    for n,dev,addr in [(C,"h19c","10.219.1.2/24"),(R,"h19in","10.219.1.1/24"),(R,"h19out","10.219.2.1/24"),(S,"h19s","10.219.2.2/24")]:
        ns(n,"ip","addr","add",addr,"dev",dev)
        ns(n,"ip","link","set",dev,"mtu","1500","up")
        ns(n,"sysctl","-qw","net.ipv4.conf."+dev+".rp_filter=0")
    ns(C,"ip","route","add","default","via","10.219.1.1")
    ns(S,"ip","route","add","default","via","10.219.2.1")
    for n in NS:
        ns(n,"sysctl","-qw","net.ipv4.conf.all.rp_filter=0")
        ns(n,"sysctl","-qw","net.ipv4.tcp_congestion_control=cubic")
        ns(n,"sysctl","-qw","net.ipv4.tcp_rmem=4096 87380 67108864")
        ns(n,"sysctl","-qw","net.ipv4.tcp_wmem=4096 65536 67108864")
        ns(n,"sysctl","-qw","net.core.rmem_max=67108864")
        ns(n,"sysctl","-qw","net.core.wmem_max=67108864")
    ns(R,"sysctl","-qw","net.ipv4.ip_forward=1")
    ns(R,"iptables","-t","nat","-A","POSTROUTING","-o","h19out","-s","10.219.1.0/24","-j","MASQUERADE")
    save("topology.json",{n:{"routes":ns(n,"ip","route"),"cc":ns(n,"sysctl","-n","net.ipv4.tcp_congestion_control"),"interfaces":json.loads(ns(n,"ip","-j","link","show"))} for n in NS})
def until(check,p):
    for _ in range(100):
        if p.poll() is not None:raise RuntimeError("process exited early: "+str(p.returncode))
        if check():return
        time.sleep(.1)
    raise RuntimeError("readiness timed out")
def stop(p):
    if p and p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:p.wait(8)
        except subprocess.TimeoutExpired:
            p.kill();p.wait()
def measure(idx,kind):
    label=f"{idx}-{kind}";port=5210+idx;proxy=None;server=None
    pl=O/(label+"-proxy.log"); sl=O/(label+"-origin.log")
    with pl.open("w") as pf,sl.open("w") as sf:
      try:
        if kind=="B":
            proxy=subprocess.Popen(["ip","netns","exec",R,str(BIN)],stdout=pf,stderr=subprocess.STDOUT)
            until(lambda:"WBD_TCP_SPLICE_READY" in pl.read_text(),proxy)
        server=subprocess.Popen(["ip","netns","exec",S,"iperf3","-s","-1","-B","10.219.2.2","-p",str(port)],stdout=sf,stderr=subprocess.STDOUT)
        until(lambda:f":{port} " in ns(S,"ss","-ltn"),server)
        (O/(label+"-mangle.txt")).write_text(ns(R,"iptables","-t","mangle","-S"))
        tick=os.sysconf("SC_CLK_TCK")
        c0=proc_cpu(proxy.pid) if proxy else None;h0=host_cpu();t=time.monotonic()
        raw=O/(label+"-iperf.json"); err=O/(label+"-stderr.txt")
        with raw.open("w") as out,err.open("w") as ef:
            p=subprocess.Popen(["ip","netns","exec",C,"iperf3","-J","-c","10.219.2.2","-p",str(port),"-C","cubic","-P","1","-R","-t","20","-O","2"],stdout=out,stderr=ef,text=True)
        samples=[]
        while p.poll() is None:
            if time.monotonic()-t>65:
                p.kill();p.wait();raise RuntimeError("iperf timeout")
            if proxy:
                samples.append({"elapsed":time.monotonic()-t,"cpu_ticks":proc_cpu(proxy.pid)})
            time.sleep(.25)
        stdout,stderr=raw.read_text(),err.read_text()
        c1=proc_cpu(proxy.pid) if proxy else None;h1=host_cpu();elapsed=time.monotonic()-t
        (O/(label+"-iperf.json")).write_text(stdout)
        (O/(label+"-stderr.txt")).write_text(stderr)
        data=json.loads(stdout)
        assert p.returncode==0 and "error" not in data,(label,stderr,data.get("error"))
        row=data["end"]["sum_received"];sent=data["end"]["sum_sent"]
        assert row["bytes"]>0 and row["seconds"]>=18
        server.wait(10)
        assert server.returncode==0
        stop(proxy)
        log=pl.read_text()
        copied=[int(x) for x in re.findall(r"WBD_TCP_SPLICE_DONE .*?down=(\d+)",log)]
        if kind=="B":
            assert "cc=cubic" in log and f"target=10.219.2.2:{port}" in log and max(copied,default=0)>=row["bytes"],(label,copied,row)
            assert "WBD_TCP_SPLICE_STOP error=<nil>" in log
        else:assert not copied
        h=delta(h0,h1);gib=row["bytes"]/2**30
        pcpu=sum(delta(c0,c1))/tick if proxy else 0
        # Host active CPU includes iperf endpoints and forwarding; do not
        # attribute it all to proxy. Omitted warmup included in CPU window.
        active=sum(h[i] for i in (0,1,2,5,6))/tick
        r={"leg":kind,"index":idx,"port":port,"seconds":row["seconds"],"received_bytes":row["bytes"],"mbps":row["bits_per_second"]/1e6,"sender_retransmits":sent.get("retransmits"),"wall_seconds":elapsed,"proxy_cpu_s":pcpu,"proxy_cpu_s_per_measured_gib":pcpu/gib,"host_active_cpu_s":active,"host_active_cpu_s_per_measured_gib":active/gib,"host_ticks":h,"splice_down_bytes":copied,"samples":samples}
        save(label+"-result.json",r);print(json.dumps({k:v for k,v in r.items() if k!="samples"}),flush=True);return r
      finally:stop(server);stop(proxy)
try:
    make()
    rows=[measure(i,k) for i,k in enumerate("ABBA")]
    save("summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"scope":"same host local 3 netns, real Linux TPROXY+production Rust splice and Go cold owner; no WBD/physical WAN qualification","cc":"cubic","mtu":1500,"rtt_added_ms":0,"loss":0,"streams":1,"rows":rows,"native_module_sha256":hashlib.sha256(pathlib.Path("crates/wbd-engine/src/v4_linux_tcp_splice.rs").read_bytes()).hexdigest(),"go_wrapper_sha256":hashlib.sha256(pathlib.Path("r0/go_overlay/internal/v4productcli/tcp_splice_linux.go").read_bytes()).hexdigest()})
finally:
    for n in reversed(NS):
        subprocess.run(["ip","netns","del",n],check=False)
