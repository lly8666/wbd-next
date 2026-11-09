#!/usr/bin/env python3
"""H1478: original product unchanged; bounded physical TCP header observer.

Two same-host Linux AF_PACKET pcap snapshots of Alice s2c underlay, analyzed
offline. Raw pcap (64-byte snaplen) lives only in RUNNER_TEMP and is destroyed.
Only counts, monotonic times and truncated header digests enter the artifact.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

SOURCE = "66fb6b4454b1ce4297ab04efa20c7f931ff12383"
WINDOWS = ((28,60), (119,151))
BPF = "ip and tcp and src host 10.25.0.1 and dst host 10.25.0.2 and src port 443"

def read_pcap(path, offset_ns):
    b=path.read_bytes()
    magic=b[:4]
    formats={b"\xd4\xc3\xb2\xa1":("<",1000),b"\xa1\xb2\xc3\xd4":(">",1000),
             b"\x4d\x3c\xb2\xa1":("<",1),b"\xa1\xb2\x3c\x4d":(">",1)}
    if magic not in formats or len(b)<24:
        raise RuntimeError("invalid pcap format")
    endian,mult=formats[magic]
    _,_,_,_,snap,link=struct.unpack_from(endian+"HHiIII",b,4)
    if link!=1 or snap<54:
        raise RuntimeError("expected native Ethernet 64B header snapshot")
    out=[];off=24
    while off<len(b):
        if off+16>len(b):
            raise RuntimeError("pcap truncated record")
        sec,frac,n,original=struct.unpack_from(endian+"IIII",b,off)
        off+=16
        if n>snap or off+n>len(b):
            raise RuntimeError("pcap truncated frame")
        frame=b[off:off+n]
        off+=n
        if len(frame)<54 or frame[12:14]!=b"\x08\x00":
            continue
        ip=14;ihl=(frame[ip]&15)*4
        if frame[ip]>>4 !=4 or ihl<20 or len(frame)<ip+ihl+20 or frame[ip+9]!=6:
            continue
        if struct.unpack_from("!H",frame,ip+6)[0]&0x3fff:
            continue
        total=struct.unpack_from("!H",frame,ip+2)[0]
        ipid=struct.unpack_from("!H",frame,ip+4)[0]
        tcp=ip+ihl
        sport,dport,seq,ack=struct.unpack_from("!HHII",frame,tcp)
        tlen=(frame[tcp+12]>>4)*4
        if tlen<20 or total<ihl+tlen or sport!=443 or total==ihl+tlen:
            continue
        # Exact header signature, not payload, AEAD, plaintext or credentials.
        key=(dport,ipid,seq,ack,frame[tcp+13],total,ihl,tlen)
        ts=sec*1_000_000_000+frac*mult-offset_ns
        out.append((ts,key))
    if off!=len(b):
        raise RuntimeError("pcap invalid tail")
    return out

def compare(left,right,window,origin):
    start,end=(origin+x*1_000_000_000 for x in window)
    s=Counter(k for t,k in left if start+1_000_000_000<=t<=end-1_000_000_000)
    r=Counter(k for t,k in right if start<=t<=end)
    byport=defaultdict(lambda:{"outer_sent":0,"outer_matched":0,"outer_missing_at_client_capture":0})
    missing=[]
    for key,num in s.items():
        matched=min(num,r[key])
        d=byport[key[0]]
        d["outer_sent"]+=num
        d["outer_matched"]+=matched
        d["outer_missing_at_client_capture"]+=num-matched
        if num>matched and len(missing)<32:
            t=next(t for t,k in left if k==key and start<t<end)
            missing.append({"app_s":round((t-origin)/1e9,4),"client_port":key[0],
                            "count":num-matched,
                            "header_digest":hashlib.sha256(repr(key).encode()).hexdigest()[:16]})
    for x in byport.values():
        assert x["outer_sent"]==x["outer_matched"]+x["outer_missing_at_client_capture"]
    return {"window_app_s":list(window),"trim_each_boundary_seconds":1,
            "server_physical_captured":len(left),"client_physical_captured":len(right),
            "by_client_tcp_port":{str(p):v for p,v in sorted(byport.items())},
            "first_missing_header_digests":missing}

def app_deficits(out):
    a=json.loads((out/"h1250-s-alice.json").read_text())
    b=json.loads((out/"h1250-c-alice.json").read_text())
    assert a["start_ns"]==b["start_ns"]
    tx=a["tx_bins_10ms"]["udp"];rx=b["rx_bins_10ms"]["udp"]
    assert len(tx)==len(rx)==19001
    d=0;cumulative=[]
    for x,y in zip(tx,rx):
        d+=int(x)-int(y);cumulative.append(d)
    floor=10**20;events=[];final=[0]*len(cumulative)
    for i in range(len(final)-1,-1,-1):
        floor=min(floor,cumulative[i]);final[i]=floor
    old=0
    for i,val in enumerate(final):
        if val>old:
            events.append({"app_s":round(i/100,2),"additional_missing":val-old})
            old=val
    assert old==d
    return d,events

def wait_until(child,deadline_ns):
    while time.monotonic_ns()<deadline_ns:
        if child.poll() is not None:
            raise RuntimeError("original native workload exited before header window")
        time.sleep(min(.2,max(.01,(deadline_ns-time.monotonic_ns())/1e9)))

def snapshot(child,tmp,tag,w,origin):
    a,b=w
    wait_until(child,origin+a*1_000_000_000)
    jobs=[]
    for name,ns,iface in (("server","sv"+tag,"p9"+tag),("client","n0"+tag,"p0"+tag)):
        path=tmp/f"{name}-{a}-{b}.pcap"
        errfile=tmp/f"{name}-{a}-{b}.stderr"
        h=errfile.open("wb")
        cmd=["sudo","-n","ip","netns","exec",ns,"tcpdump","-i",iface,
             "-s","64","-U","-nn","-w",str(path),BPF]
        p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=h,stderr=subprocess.STDOUT,
                           start_new_session=True)
        jobs.append((name,path,errfile,p,h))
    try:
        wait_until(child,origin+b*1_000_000_000)
    finally:
        for _,_,_,p,_ in jobs:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGINT)
        for _,_,_,p,h in jobs:
            try:p.wait(timeout=8)
            finally:h.close()
    results={}
    for name,path,stderr,p,_ in jobs:
        if not path.exists() or path.stat().st_size<=24:
            raise RuntimeError(f"{name} did not capture native physical TCP")
        log=stderr.read_text(errors="replace")
        dropped=re.findall(r"(\d+) packets dropped by kernel",log)
        results[name]={"path":path,"stats":log[-1500:],
                       "observer_kernel_dropped":int(dropped[-1]) if dropped else None,
                       "observer_returncode":p.returncode}
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--build",type=Path);p.add_argument("--out",type=Path)
    p.add_argument("--selftest",action="store_true")
    opts=p.parse_args()
    if opts.selftest:
        key=(41031,3,100,200,24,44,20,20)
        s=[(10_000_000_000,key),(11_000_000_000,key)]
        c=[(10_001_000_000,key)]
        report=compare(s,c,(0,20),0)
        assert report["by_client_tcp_port"]["41031"]["outer_missing_at_client_capture"]==1
        ip=bytearray(20);ip[0]=0x45;ip[2:4]=struct.pack("!H",44)
        ip[4:6]=struct.pack("!H",3);ip[9]=6
        tcp=struct.pack("!HHII",443,41031,100,200)+bytes([0x50,24])+bytes(6)
        frame=bytes(12)+b"\x08\x00"+ip+tcp+b"data"
        glob=struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,64,1)
        rec=struct.pack("<IIII",10,100000,len(frame),len(frame))+frame
        with TemporaryDirectory() as d:
            path=Path(d)/"test.pcap";path.write_bytes(glob+rec)
            rows=read_pcap(path,0)
            assert rows==[(10_100_000_000,key)]
        print("H1478_HEADER_ONLY_PCAP_AND_MATCH_SELFTEST_PASS")
        return
    if not opts.build or not opts.out:
        p.error("--build and --out required")
    assert os.environ["GITHUB_SHA"]==SOURCE
    assert os.environ["WBD_PLAN028_H1467_CASE"]=="rotating12"
    out=opts.out.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((opts.build/"manifest.json").read_text())
    assert manifest["source_sha"]==SOURCE and manifest["architecture"]=="native_x86_64"
    tag=os.environ["GITHUB_RUN_ID"][-6:]
    fixture=Path(__file__).parent/"m0_plan028_h1467_fiveclient_ab_netns.py"
    cmd=[sys.executable,"-u",str(fixture),str(opts.build.resolve())]
    with TemporaryDirectory(prefix="h1478-header-only-",dir=os.environ["RUNNER_TEMP"]) as d:
        tmp=Path(d)
        with (out/"h1478-native-driver.log").open("wb") as stream:
            child=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,env=os.environ.copy())
            try:
                plan_path=out/"h1250-matrix-plan.json"
                limit=time.monotonic()+90
                while not plan_path.exists() and time.monotonic()<limit:
                    if child.poll() is not None:
                        raise RuntimeError("original Go/Rust fixture stopped before native app")
                    time.sleep(.2)
                if not plan_path.exists():
                    raise RuntimeError("native fixture did not establish real app plan")
                plan=json.loads(plan_path.read_text())
                assert plan["source_sha"]==SOURCE and plan["application_load_seconds"]==180
                assert plan["h1467_short_ab_case"]=="rotating12"
                assert all(x["loss_pct"]==0 for x in plan["clients"])
                origin=int(plan["start_monotonic_ns"])
                offset_ns=time.time_ns()-time.monotonic_ns()
                raw=[snapshot(child,tmp,tag,w,origin) for w in WINDOWS]
                if child.wait(timeout=160)!=0:
                    raise RuntimeError("original genuine native five-client workload failure")
                loss,events=app_deficits(out)
                windows=[]
                for w,pair in zip(WINDOWS,raw):
                    left=read_pcap(pair["server"]["path"],offset_ns)
                    right=read_pcap(pair["client"]["path"],offset_ns)
                    result=compare(left,right,w,origin)
                    result["observer"]={name:{k:v for k,v in row.items() if k!="path"}
                                        for name,row in pair.items()}
                    windows.append(result)
                receipt={
                    "schema_version":1,"plan":"PLAN028","source_sha":SOURCE,
                    "scope":"Genuine native x86/x86 five-client original Go TLS/Rust M4 180s rotating12",
                    "original_app_alice_s2c_unique_udp_missing":loss,
                    "original_10ms_permanent_missing_events":events,
                    "underlay_outer_headers":windows,
                    "raw_pcap_persisted":False,"packet_body_persisted":False,
                    "original_binary_modified":False,
                    "limits":["Observer sees physical AF_PACKET headers, not Rust socket receive/AEAD/TUN.",
                              "Sender egress capture precedes qdisc; only compare trimmed interior.",
                              "Observer packet drops can invalidate a no-missing conclusion.",
                              "No application loss recurrence means NOT_REPRODUCED, not repaired.",
                              "Outer TLS ciphertext cannot identify a specific inner UDP packet."]}
                (out/"h1478-wire-boundary.json").write_text(json.dumps(receipt,indent=2)+"\n")
                print("H1478_REAL_NATIVE_HEADER_OBSERVATION",
                      json.dumps({"app_missing":loss,"events":events,
                        "outer_unmatched":[sum(v["outer_missing_at_client_capture"]
                           for v in x["by_client_tcp_port"].values()) for x in windows]}),flush=True)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        child.kill();child.wait()

if __name__=="__main__":
    main()
