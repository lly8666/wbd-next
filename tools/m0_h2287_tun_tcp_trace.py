#!/usr/bin/env python3
"""H2287: strictly PASSIVE actual ARM original Linux TUN TCP header witness.

No packets sent, no ACK fabricated, no product source/driver interception.
Run inside the SAME actual ARM server netns on original Rust-owned wbds0.
Captures only TCP IPv4 headers (no payload/credentials) for port45902 and
read-only ss listener/attempt-fail/out-reset kernel counters in actual netns.
"""
import collections
import json
import os
import pathlib
import signal
import socket
import struct
import subprocess
import sys
import time

IFACE="wbds0"
PORT=45902
keep=True


def stop(*_):
    global keep
    keep=False


def kernel_tcp():
    p=subprocess.run(["ss","-H","-ltnp"],capture_output=True,text=True,timeout=8)
    if p.returncode:
        raise RuntimeError("H2287_ORIGINAL_ARM_KERNEL_SS_FAILED "+p.stderr[-200:])
    listeners=[x for x in p.stdout.splitlines() if ":"+str(PORT) in x]
    snmp=pathlib.Path("/proc/net/snmp").read_text()
    values={}
    for line,entry in zip(snmp.splitlines()[::2],snmp.splitlines()[1::2]):
        if line.startswith("Tcp:") and entry.startswith("Tcp:"):
            d=dict(zip(line.split()[1:],entry.split()[1:]))
            for key in ("AttemptFails","OutRsts","InErrs","InSegs","OutSegs"):
                values[key]=int(d.get(key,"0"))
    return {"listener_45902_actual_ss":listeners[:5],
            "tcp_snmp":values}


def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: m0_h2287_tun_tcp_trace.py OUTPUT.json")
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    out=pathlib.Path(sys.argv[1])
    require= lambda x,msg: x or (_ for _ in ()).throw(RuntimeError(msg))
    require(os.name=="posix","H2287_LINUX_ONLY")
    require("wbds0" in subprocess.check_output(
        ["ip","link","show",IFACE],text=True,timeout=8),
        "H2287_REAL_RUST_OWNED_TUN_MISSING")
    s=socket.socket(socket.AF_PACKET,socket.SOCK_DGRAM,socket.htons(0x0800))
    s.bind((IFACE,0))
    s.settimeout(.6)
    initial=kernel_tcp()
    require(initial["listener_45902_actual_ss"],
            "H2287_REAL_ARM_TUN_TCP45902_NOT_LISTENING_BEFORE_WINDOWS")
    print("H2287_REAL_ARM_RUST_TUN_TCP_LISTENING_AND_PASSIVE_CAPTURE_READY",
          flush=True)
    counts=collections.Counter()
    samples=[]
    snapshots=[{"elapsed_s":0.0,**initial}]
    t0=time.monotonic()
    next_sample=t0+2
    try:
        while keep and time.monotonic()-t0 < 150:
            try:dat,addr=s.recvfrom(4096)
            except socket.timeout:dat=b"";addr=()
            if len(dat)>=40 and dat[0]>>4==4 and dat[9]==6:
                ihl=(dat[0]&15)*4
                if ihl>=20 and len(dat)>=ihl+20:
                    sp,dp=struct.unpack("!HH",dat[ihl:ihl+4])
                    if sp==PORT or dp==PORT:
                        src=".".join(map(str,dat[12:16]))
                        dst=".".join(map(str,dat[16:20]))
                        flags=dat[ihl+13]
                        packtype=addr[2] if len(addr)>2 else None
                        kind=("S" if flags&2 else "R" if flags&4 else
                              "A" if flags&16 else "O")
                        label=f"{src}:{sp}>{dst}:{dp}/{kind}/p{packtype}"
                        counts[label]+=1
                        if len(samples)<160:
                            samples.append({
                                "ms":round((time.monotonic()-t0)*1000,2),
                                "src":src,"dst":dst,
                                "sport":sp,"dport":dp,
                                "tcp_flags":flags,
                                "packet_type":packtype,
                                "tcp_seq":struct.unpack("!I",dat[ihl+4:ihl+8])[0],
                                "tcp_ack":struct.unpack("!I",dat[ihl+8:ihl+12])[0],
                                "ipv4_len":len(dat),
                                "tcp_payload_not_collected":True})
            if time.monotonic()>=next_sample:
                next_sample=time.monotonic()+2
                snapshots.append({"elapsed_s":round(time.monotonic()-t0,3),
                                  **kernel_tcp()})
    finally:
        s.close()
        receipt={"scope":"READ_ONLY_GENUINE_ARM_RUST_TUN_IP_PACKET_HEADERS_ONLY",
                 "interface":IFACE,"port":PORT,
                 "no_tcp_payload_or_tls_or_product_secrets":True,
                 "all_physical_capture":False,
                 "elapsed_s":round(time.monotonic()-t0,3),
                 "tcp_flag_counts":dict(counts),
                 "header_samples":samples,
                 "actual_arm_kernel_listening_snapshots":snapshots}
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(receipt,indent=2)+"\n")
        print("H2287_REAL_ARM_TUN_TCP_PASSIVE_HEADERS_AND_SS_RECORDED "
              +json.dumps({"frame_count":sum(counts.values()),
                           "unique_paths":len(counts)}),flush=True)


if __name__=="__main__":
    main()
