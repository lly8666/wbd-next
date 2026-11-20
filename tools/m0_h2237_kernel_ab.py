#!/usr/bin/env python3
"""H2237 isolated kernel primitive A/B. Never claims WBD TLS or throughput.

Same one x86/ARM VM, 3 REAL Linux netns, exact deterministic IPv4/TCP bytes
emitted by sendmmsg through raw IP_HDRINCL vs AF_PACKET/SOCK_DGRAM. A,B,B,A.
Kernel-accepted counts cannot substitute for interface-delivered packets;
pcap structural receipts have only locally generated test payloads.
"""
import hashlib
import json
import os
import pathlib
import re
import struct
import subprocess
import sys
import time

REPO=pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools.m0_h2234_local_netns import OwnedLocal,root,ns,save

MAX_CAPTURE=4
def interface_stats(nsname,name):
    j=json.loads(ns(nsname,"ip","-s","-j","link","show","dev",name).stdout)[0]
    s=j.get("stats64") or j.get("stats")
    if not s:raise RuntimeError("H2237_KERNEL_INTERFACE_STATS_MISSING")
    return {
        "rx_packets":int(s["rx"]["packets"]),
        "rx_dropped":int(s["rx"]["dropped"]),
        "tx_packets":int(s["tx"]["packets"]),
        "tx_dropped":int(s["tx"]["dropped"]),
        "tx_bytes":int(s["tx"]["bytes"]),
        "rx_bytes":int(s["rx"]["bytes"]),
    }

def stats(node):
    return {
        "client":interface_stats(node.client,"wan0"),
        "router_in":interface_stats(node.router,"rcli0"),
        "router_out":interface_stats(node.router,"rsrv0"),
        "server":interface_stats(node.server,"wan0")
    }

def delta(before,after):
    out={}
    for name in before:
        out[name]={k:after[name][k]-v for k,v in before[name].items()}
        if any(v<0 for v in out[name].values()):
            raise RuntimeError("H2237_KERNEL_COUNTER_RESET")
    return out

def csum(data):
    total=sum((data[i]<<8)+data[i+1] for i in range(0,len(data)-len(data)%2,2))
    if len(data)%2:total+=data[-1]<<8
    while total>>16:total=(total&65535)+(total>>16)
    return (~total)&65535

def parse_pcap(path):
    raw=path.read_bytes()
    if len(raw)<40:raise ValueError("H2237_PCAP_TOO_SHORT")
    magic=raw[:4]
    if magic==b"\xd4\xc3\xb2\xa1":endian="<"
    elif magic==b"\xa1\xb2\xc3\xd4":endian=">"
    else:raise ValueError("H2237_PCAP_MAGIC_UNKNOWN")
    linktype=struct.unpack(endian+"I",raw[20:24])[0]
    if linktype!=1:raise ValueError("H2237_EXPECT_ETHERNET_DLT")
    off=24
    selected={}
    while off+16<=len(raw):
        _,_,cap,full=struct.unpack(endian+"IIII",raw[off:off+16]);off+=16
        if cap<=0 or off+cap>len(raw):raise ValueError("H2237_PCAP_TRUNCATED")
        eth=raw[off:off+cap];off+=cap
        if len(eth)<14+40+1024 or eth[12:14]!=b"\x08\x00":continue
        ip=eth[14:]
        if ip[0]!=0x45 or ip[9]!=6:continue
        n=struct.unpack(">H",ip[2:4])[0]
        if n!=1064 or len(ip)<n:continue
        ip=ip[:n]
        if ip[12:16]!=b"\x0a\xf8\x51\x02" or ip[16:20]!=b"\x0a\xf8\x52\x02":
            continue
        if csum(ip[:20])!=0:raise ValueError("H2237_IP_CHECKSUM_INVALID")
        pseudo=ip[12:20]+b"\x00\x06"+struct.pack(">H",len(ip)-20)
        if csum(pseudo+ip[20:])!=0:raise ValueError("H2237_TCP_CHECKSUM_INVALID")
        seq=struct.unpack(">I",ip[24:28])[0]
        selected[str(seq)]={"sha256":hashlib.sha256(ip).hexdigest(),"len":len(ip),
            "seq":seq,"tcp_checksum_valid":True,"ipv4_checksum_valid":True}
    if not selected:raise ValueError("H2237_NO_EXACT_TEST_WIRE_CAPTURED")
    return selected

def run():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    sha=os.environ["GITHUB_SHA"];runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",sha):raise RuntimeError("H2237_BAD_SOURCE_SHA")
    out=workspace/"h2237-kernel-result";out.mkdir(exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2237-"+runid)
    tmp.mkdir(parents=True,exist_ok=False,mode=0o700)
    build=workspace/"h2237-tx-primitive"
    subprocess.run(["gcc","-O3","-std=c11","-Wall","-Wextra","-Werror",
         str(workspace/"tools/m0_h2237_linux_tx_primitive.c"),"-o",str(build)],
         capture_output=True,text=True,check=True)
    node=OwnedLocal(workspace,out,tmp)
    result={
       "schema_version":1,"source_sha":sha,"run_id":runid,
       "kind":"TEST_ONLY_SAME_VM_LINUX_KERNEL_PACKET_PRIMITIVE_BENCH",
       "not_product_go_tls_or_rust":True,
       "no_wbd_packet_or_real_data":True,
       "host_arch":os.uname().machine,
       "original_af_inet_raw_ip_hdrincl":"raw",
       "candidate_af_packet_sock_dgram":"packet",
       "m4_crypto_and_original_stop":"NOT_RUN",
       "cross_platform_product_gain":"NOT_PROVEN",
       "runs":[]
    }
    try:
        node.start_network()
        # Stop kernel TCP from generating many RST replies to the local
        # synthetic packet's unbound test-only TCP destination port.
        ns(node.server,"iptables","-w","-A","OUTPUT","-o","wan0",
           "-p","tcp","--sport","44331","--tcp-flags","RST","RST","-j","DROP")
        mac=json.loads(ns(node.router,"ip","-j","link","show","rcli0").stdout)[0]["address"]
        if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}",mac):
            raise RuntimeError("H2237_REAL_ROUTER_MAC_UNAVAILABLE")
        # Prime the same genuine Linux route/neighbor without fake WBD auth.
        ns(node.client,"ping","-c","1","-W","2","10.248.81.1")
        save(out/"topology-test-only.json",{
            "source_sha":sha,"real_linux_kernel_l3_netns":True,
            "no_tailscale_or_derp":True,"not_original_go_tls_rust_product":True,
            "router_mac_readback":mac,"link_mtu":1200})
        # Controlled 100kpps same-offered-rate CPU/GiB comes first; unpaced
        # ceilings never qualify if kernel delivery actually drops packets.
        legs=[(100000,"raw"),(100000,"packet"),(100000,"packet"),(100000,"raw"),
              (0,"raw"),(0,"packet"),(0,"packet"),(0,"raw")]
        for idx,(target_pps,mode) in enumerate(legs):
            capture=out/("source-"+str(idx)+"-"+mode+".pcap")
            log=(out/("capture-"+str(idx)+".stderr")).open("wb")
            proc=subprocess.Popen(["sudo","-n","ip","netns","exec",node.router,
              "tcpdump","-U","-i","rcli0","-c",str(MAX_CAPTURE),
              "-s","2048","-w",str(capture),
              "src host 10.248.81.2 and dst host 10.248.82.2 and tcp dst port 44331"],
              stdout=subprocess.DEVNULL,stderr=log)
            try:
                time.sleep(.3)
                before=stats(node)
                cmd=ns(node.client,str(build),mode,mac,str(target_pps),timeout=9)
                bench=json.loads(cmd.stdout.strip())
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.terminate();proc.wait(timeout=2)
                time.sleep(.35)
                after=stats(node)
                d=delta(before,after)
                wire=parse_pcap(capture)
                row={
                    "mode":mode,"order_index":idx,"target_pps":target_pps,
                    "kernel_send":bench,
                    "link_delta":d,
                    "test_wire":wire,
                    "real_router_ingress_packets":d["router_in"]["rx_packets"],
                    "real_server_rx_packets":d["server"]["rx_packets"],
                    "source_run_lock":sha
                }
                sent=int(bench["accepted_kernel_prefix_packets"])
                delivered=d["server"]["rx_packets"]
                row["delivered_per_accepted_ratio"]=round(delivered/sent,4) if sent else None
                row["real_rx_qualified"]=sent>0 and delivered>=.90*sent
                result["runs"].append(row)
            finally:
                if proc.poll() is None:proc.terminate();proc.wait(timeout=3)
                log.close()
                capture.unlink(missing_ok=True)
        # The 4 real captures must contain an overlapping identical IPv4
        # template sequence in each mode, otherwise no wire-equivalence claim.
        raw={k:v["sha256"] for row in result["runs"] if row["mode"]=="raw"
             for k,v in row["test_wire"].items()}
        pkt={k:v["sha256"] for row in result["runs"] if row["mode"]=="packet"
             for k,v in row["test_wire"].items()}
        common=set(raw)&set(pkt)
        wire_ok=bool(common) and all(raw[k]==pkt[k] for k in common)
        paced=[x for x in result["runs"] if x["target_pps"]==100000]
        unpaced=[x for x in result["runs"] if x["target_pps"]==0]
        paced_ok=len(paced)==4 and all(x["real_rx_qualified"] for x in paced)
        result["verified_equal_IPv4_TCP_bytes"]=wire_ok
        result["capture_shared_sequences"]=len(common)
        result["paced_100kpps_real_Rx_qualification"]=paced_ok
        result["unpaced_real_Rx_qualification"]=len(unpaced)==4 and all(
            x["real_rx_qualified"] for x in unpaced)
        result["status"]="PASS_GENUINE_KERNEL_TEST_ONLY" if wire_ok and paced_ok else (
             "FAIL_PACED_KERNEL_WIRE_OR_RECEIPT_QUALIFICATION")
        for offered in (100000,0):
            for mode in ("raw","packet"):
                rows=[x for x in result["runs"] if x["mode"]==mode and
                      x["target_pps"]==offered and x["real_rx_qualified"]]
                name=("paced100k_" if offered else "unpaced_")+mode
                if len(rows)!=2:
                    result[name+"_status"]="UNKNOWN_UNQUALIFIED_REAL_RX"
                    continue
                result[name+"_status"]="REAL_RX_SOURCE_QUALIFIED"
                result[name+"_delivered_kpps_mean"]=round(
                    sum(x["real_server_rx_packets"]/x["kernel_send"]["wall_seconds"]
                    for x in rows)/len(rows)/1000,3)
                result[name+"_cpu_s_per_received_gib_mean"]=round(
                    sum(x["kernel_send"]["cpu_seconds"]/(max(1,x["real_server_rx_packets"])*1064/1073741824)
                    for x in rows)/len(rows),3)
    finally:
        node.cleanup()
        save(out/"summary.json",result)
    if result.get("status")!="PASS_GENUINE_KERNEL_TEST_ONLY":
        raise RuntimeError("H2237_UNQUALIFIED_TEST_ONLY_KERNEL_RECEIPT")
    print("H2237_REAL_KERNEL_PRIMITIVE_ABBA_PASS_NOT_PRODUCT_OPTIMIZATION",flush=True)

if __name__=="__main__":run()
