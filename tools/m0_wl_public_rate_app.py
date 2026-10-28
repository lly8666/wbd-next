#!/usr/bin/env python3
"""Real independent bidirectional OS UDP generator/receiver for public WL-N0.

Not a replacement for the original Go/Rust data path. Never echoes replies,
spoofs receipts, or infers per-direction one-way latency across OS clocks.
Both processes run concurrently against their native Wintun/TUN socket.
"""
import json
import os
import pathlib
import socket
import struct
import sys
import time
from m0_wl_business_latency import summarize_rtt
from m0_wl_impairment_profile import get_profile

local, remote, side, start_flag, output_dir = sys.argv[1:6]
out = pathlib.Path(output_dir)
out.mkdir(parents=True, exist_ok=True)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2 * 1024 * 1024)
sock.bind((local, 45903))
sock.setblocking(False)
print(json.dumps({"phase":"bound","side":side,"address":local}), flush=True)

wait_start = time.monotonic() + 25
while not pathlib.Path(start_flag).exists():
    if time.monotonic() > wait_start: raise RuntimeError("two-OS rate start barrier unavailable")
    time.sleep(.015)

prefix=b"WBD-WL-N0/"
probe_request=b"WBD-WL-RTT-Q/"
probe_reply=b"WBD-WL-RTT-R/"
probe_interval=.1 # ≤10 probes/s, separate from the original 10Mbps rate denominator
probes_sent=0
probe_next=None
probe_pending={}
probe_delivered=set()
probe_rtt_ms=[]
probe_send_errors=0
profile_name = sys.argv[7] if len(sys.argv)==8 else "n0"
profile = get_profile(profile_name)
sizes=(96, 288, 1060, 1200) if profile_name=="n0" else (1060,1200)
rate_bytes_per_sec=int(profile["offered_mbps"]*1_000_000/8)
stress=profile_name!="n0"
destination=(remote,45903)
reused={size:bytearray(prefix+bytes(8)+bytes(size-len(prefix)-8)) for size in sizes} if stress else None
# Explicit per-Actions single-scene duration; never let an env on one OS
# silently produce a different input horizon on the other OS.
duration = float(sys.argv[6]) if len(sys.argv) >= 7 else 60.0
if duration not in (60.0,240.0) or (profile_name!="n0" and duration!=profile["duration_s"]):
    raise ValueError("invalid declared impairment duration")
drain=5.0
start=time.monotonic()
cpu_start=time.process_time()
loop_count=0
probe_next=start
last_credit=start
last_heartbeat=start
credit=0.0
sent=0
sent_bytes=0
first=set()
recv_bytes=0
duplicate=0
invalid=0
last_delivery=None
# P200-only reusable receive slab: the original recvfrom() allocated one
# Python bytes object for every one of ~1 million observed native UDP frames.
recv_slabs=bytearray(2048) if stress else None
recv_view=memoryview(recv_slabs) if stress else None
max_interdelivery_ms=0
bins=[0] * int((duration+drain)*100)
err=None
while True:
    loop_count+=1
    now=time.monotonic()
    if now >= start + duration + drain: break
    if now < start + duration:
        credit=min(credit+(now-last_credit)*rate_bytes_per_sec,rate_bytes_per_sec/20)
        last_credit=now
        for _ in range(128 if stress else 32):
            size=sizes[sent % len(sizes)]
            if credit < size: break
            if stress:
                payload=reused[size]
                struct.pack_into("!Q",payload,len(prefix),sent)
            else:
                payload=prefix+struct.pack("!Q",sent)+bytes([sent%251])*(size-len(prefix)-8)
            try:
                n=sock.sendto(payload,destination)
                if n != size: raise RuntimeError("partial kernel UDP send")
            except (OSError, RuntimeError) as e:
                err=str(e)
                break
            credit-=size
            sent+=1
            sent_bytes+=size
        if err: break
    else:
        last_credit=now
    # A sparse real UDP request/reply shares the EXACT same original
    # Windows Wintun/Linux TUN business path during sustained load. Both
    # sides measure RTT on their own monotonic clock; no cross-OS offsets.
    if now<start+duration and now>=probe_next:
        seq=probes_sent
        try:
            n=sock.sendto(probe_request+struct.pack("!Q",seq),
                          (remote,45903))
            if n!=len(probe_request)+8:raise RuntimeError("partial probe")
            probe_pending[seq]=now
            probes_sent+=1
        except (OSError,RuntimeError):
            probe_send_errors+=1
        probe_next=now+probe_interval
    # Drain ready packets without blocking the sender. Count first arrival
    # only and keep 10ms first-delivery buckets.
    for _ in range(160):
        try:
            if stress:
                plen,peer=sock.recvfrom_into(recv_slabs)
                payload=recv_view
            else:
                payload,peer=sock.recvfrom(1600)
                plen=len(payload)
        except BlockingIOError: break
        if peer[0]!=remote:
            invalid+=1
            continue
        if plen==len(probe_request)+8 and payload[:len(probe_request)]==probe_request:
            # Genuine application echo, not a transport/FEC M2 ACK.
            try:sock.sendto(probe_reply+bytes(payload[len(probe_request):len(probe_request)+8]),peer)
            except OSError:probe_send_errors+=1
            continue
        if plen==len(probe_reply)+8 and payload[:len(probe_reply)]==probe_reply:
            seq=struct.unpack_from("!Q",payload,len(probe_reply))[0]
            sent_at=probe_pending.pop(seq,None)
            if sent_at is not None and seq not in probe_delivered:
                probe_delivered.add(seq)
                probe_rtt_ms.append((time.monotonic()-sent_at)*1000)
            continue
        if plen<len(prefix)+8 or payload[:len(prefix)]!=prefix:
            invalid+=1
            continue
        seq=struct.unpack_from("!Q",payload,len(prefix))[0]
        if seq in first:
            duplicate+=1
            continue
        first.add(seq)
        recv_bytes+=plen
        elapsed=now-start
        bucket=int(elapsed*100)
        if 0<=bucket<len(bins): bins[bucket]+=1
        if last_delivery is not None:
            max_interdelivery_ms=max(max_interdelivery_ms,int((now-last_delivery)*1000))
        last_delivery=now
    if now-last_heartbeat>=1:
        print(json.dumps({"phase":"progress_1hz","side":side,"sent":sent,
                          "sent_bytes":sent_bytes,"received_first":len(first),
                          "received_bytes":recv_bytes}), flush=True)
        last_heartbeat=now
    # High-offer mode uses reusable payload slabs and yields only when
    # pacing credit is insufficient; fixed 800us sleep throttled the
    # Python generator long before the 250Mbps native product was stressed.
    if stress:
        if credit < min(sizes):
            time.sleep(.00005)
        elif loop_count%8==0:
            time.sleep(0)
    else:
        time.sleep(.0008)
sock.close()
end=time.monotonic()
cpu_seconds=time.process_time()-cpu_start
result={
    "source":os.environ.get("GITHUB_SHA"),
    "scenario":"WL-N0" if profile_name=="n0" else "WL-P200-250M-30P",
    "kernel_impairment_profile":profile_name,
    "side":side,"kernel_bind":"PASS","measurement_duration_s":duration,
    "drain_s":drain,"actual_elapsed_s":round(end-start,3),
    "requested_payload_mbps":profile["offered_mbps"],
    "sender_cpu_seconds":round(cpu_seconds,4),
    "sender_cpu_pct_one_core":round(100*cpu_seconds/max(0.001,end-start),3),
    "generator_main_loop_iterations":loop_count,
    "reused_payload_buffer":stress,
    "reused_receive_slab":stress,
    "sent_packets":sent,"sent_payload_bytes":sent_bytes,
    "sent_payload_mbps":round(sent_bytes*8/(duration*1e6),4),
    "received_first_packets":len(first),
    "received_first_payload_bytes":recv_bytes,
    "received_payload_mbps":round(recv_bytes*8/(duration*1e6),4),
    "duplicate_packets":duplicate,"invalid_packets":invalid,
    "max_interdelivery_ms":max_interdelivery_ms,
    "arrival_10ms_bucket_counts":bins,
    "business_udp_rtt":summarize_rtt(probe_rtt_ms,probes_sent),
    "business_udp_rtt_send_errors":probe_send_errors,
    "application_oneway_p99":"NOT_MEASURED_UNCALIBRATED_WINDOWS_LINUX_CLOCKS",
    "sender_error":err
}
(out / ("wl-n0-"+side+"-app.json")).write_text(json.dumps(result)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="arrival_10ms_bucket_counts"}),flush=True)
sys.exit(1 if err else 0)
