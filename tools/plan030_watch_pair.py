#!/usr/bin/env python3
"""One ordinary paired A/B on the SAME live three-device original server.
No extra probe in product; use a genuine app socket plus real clients --watch.
"""
import json,os,signal,socket,subprocess,sys,tempfile,time
from pathlib import Path
exe,unix_socket,pid,local=sys.argv[1:]
def proc(p):
    raw=Path(f"/proc/{p}/stat").read_text().rsplit(")",1)[1].split()
    return (int(raw[11])+int(raw[12]),int(raw[21])*os.sysconf("SC_PAGE_SIZE"))
def phase(watch):
    p=None;output=None
    try:
        if watch:
            output=tempfile.TemporaryFile(mode="w+")
            p=subprocess.Popen([exe,"--manage","clients","--json","--watch","--socket",unix_socket],stdout=output,stderr=subprocess.STDOUT,text=True)
        begin=time.monotonic();cpu0,rss0=proc(pid);rtts=[];misses=0;rss=rss0;first=None
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.bind((local,0));s.settimeout(.20)
            for n in range(1200):
                due=begin+n*.01
                if due>time.monotonic():time.sleep(due-time.monotonic())
                msg=f"WBD_MIXED443/WATCH/{int(watch)}/{n}".encode()+bytes(384)
                t=time.monotonic();s.sendto(msg,("10.66.0.1",45901))
                try:
                    b,peer=s.recvfrom(4096)
                    if b!=b"WBD_MIXED_ECHO/"+msg or peer[0]!="10.66.0.1":misses+=1;continue
                    ms=(time.monotonic()-t)*1000
                    if first is None:first=ms
                    rtts.append(ms)
                except socket.timeout:misses+=1
                if n%100==0:rss=max(rss,proc(pid)[1])
        secs=time.monotonic()-begin;cpu1,rss1=proc(pid)
        rows=[]
        if p:
            if p.poll() is not None:raise RuntimeError("watch exited before paired workload")
            watch_ticks,watch_rss=proc(p.pid)
            p.send_signal(signal.SIGTERM);p.wait(timeout=5);output.seek(0)
            rows=[json.loads(l) for l in output]
            assert len(rows)>=5 and all(len(r["clients"])==3 for r in rows),len(rows)
        else:watch_ticks,watch_rss=0,0
        assert rtts and len(rtts)+misses==1200
        rtts.sort()
        return {"watch":watch,"seconds":secs,"offered":1200,"delivered":len(rtts),"misses":misses,
            "server_cpu_seconds":(cpu1-cpu0)/os.sysconf("SC_CLK_TCK"),
            "server_rss_peak_bytes":max(rss,rss1),"watch_cpu_seconds":watch_ticks/os.sysconf("SC_CLK_TCK"),
            "watch_rss_bytes":watch_rss,"watch_snapshots":len(rows),"first_echo_ms":first,
            "p99_echo_ms":rtts[min(len(rtts)-1,int(len(rtts)*.99))]}
    finally:
        if p and p.poll() is None:p.terminate();p.wait(timeout=5)
        if output is not None:output.close()
a=phase(False);b=phase(True)
print(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"scope":"ordinary_100pps_same_live_server_A_B","A":a,"B":b,
 "result":"MEASURED_NOT_AUTOMATIC_PERFORMANCE_PASS"},indent=2))
assert a["delivered"]>=1188 and b["delivered"]>=1188,(a,b)
