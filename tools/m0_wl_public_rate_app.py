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
from m0_wl_udp_socket_telemetry import snapshot as udp_socket_probe, delta as udp_socket_delta

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
profile_name = sys.argv[7] if len(sys.argv)>=8 else "n0"
scenario_path=sys.argv[8] if len(sys.argv)>8 else None
profile = get_profile(profile_name,side=side,configfile=scenario_path)
sizes=(96, 288, 1060, 1200) if profile_name=="n0" else (1060,1200)
if profile_name=="v2":
    sizes=tuple(row["udp_payload_bytes"] for row in profile["packet_mix"] for _ in range(row["packets_weight"]))
rate_bytes_per_sec=int(profile["offered_mbps"]*1_000_000/8)
stress=profile_name!="n0"
destination=(remote,45903)
reused={size:bytearray(prefix+bytes(8)+bytes(size-len(prefix)-8)) for size in sizes} if stress else None
# Explicit per-Actions single-scene duration; never let an env on one OS
# silently produce a different input horizon on the other OS.
duration = float(sys.argv[6]) if len(sys.argv) >= 7 else 60.0
if (profile_name=="v2" and duration!=profile["duration_s"]) or (profile_name!="v2" and
        (duration not in (60.0,240.0) or (profile_name!="n0" and duration!=profile["duration_s"]))):
    raise ValueError("invalid declared impairment duration")
drain=5.0
start=time.monotonic()
# Linux socket inode/proc UDP global counters are scoped to this real socket
# (except explicitly named guest-global MIB). Read 1Hz, never per frame.
socket_start=udp_socket_probe(sock) if profile_name=="v2" else None
socket_timeline=[]
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
# Diagnostic-only V2 timing: receive bins are loop-observation timestamps,
# never kernel arrival timestamps or cross-OS one-way latency.
send_bins=[0]*int((duration+drain)*100) if profile_name=="v2" else None
send_bytes_bins=[0]*int((duration+drain)*100) if profile_name=="v2" else None
last_loop_tick=start
long_loop_pauses=[]
max_loop_pause_ms=0.0
err=None
while True:
    loop_count+=1
    now=time.monotonic()
    if send_bins is not None and now<start+duration:
        gap_ms=(now-last_loop_tick)*1000
        if gap_ms>max_loop_pause_ms:max_loop_pause_ms=gap_ms
        if gap_ms>=20 and len(long_loop_pauses)<32:
            long_loop_pauses.append({"end_rel_s":round(now-start,4),
                                     "loop_gap_ms":round(gap_ms,3)})
    last_loop_tick=now
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
            if send_bins is not None:
                sb=int((now-start)*100)
                if 0<=sb<len(send_bins):
                    send_bins[sb]+=1
                    send_bytes_bins[sb]+=size
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
        if socket_start is not None:
            snap=udp_socket_probe(sock)
            socket_timeline.append({
                "elapsed_s":round(now-start,3),
                "socket_udp_drops":snap["linux_socket_udp_drops"],
                "socket_rx_queue_bytes":snap["linux_socket_rx_queue_bytes"],
                "guest_global_udp_rcvbuf_errors":snap["linux_guest_global_udp_rcvbuf_errors"],
                "linux_raw_sockets":snap["linux_raw_socket_snapshot"]})
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
socket_end=udp_socket_probe(sock,include_raw_owners=True) if socket_start is not None else None
sock.close()
end=time.monotonic()
cpu_seconds=time.process_time()-cpu_start
# Snapshot only bounded diagnostic distributions after measurement.
# Sequence 0..max(received) may contain gaps; the post-run last-source
# sequence beyond max is recovered from the opposite sender's exact total.
sequence_sample=None
if send_bins is not None:
    hi=max(first) if first else -1
    seq_missing_windows=[]
    missing_count=0
    gap_start=None
    groups=[]
    for window_start in range(0,hi+1,4096):
        window_end=min(hi+1,window_start+4096)
        nmissing=0
        for seq in range(window_start,window_end):
            if seq not in first:
                nmissing+=1
                if gap_start is None:gap_start=seq
            elif gap_start is not None:
                if len(seq_missing_windows)<64:
                    seq_missing_windows.append({"start":gap_start,"end_exclusive":seq,
                                                "missing_packets":seq-gap_start})
                gap_start=None
        groups.append(nmissing)
        missing_count+=nmissing
    if gap_start is not None and len(seq_missing_windows)<64:
        seq_missing_windows.append({"start":gap_start,"end_exclusive":hi+1,
                                    "missing_packets":hi+1-gap_start})
    sequence_sample={"first_received_seq":min(first) if first else None,
                     "last_received_seq":hi if hi>=0 else None,
                     "missing_inside_observed_sequence_span":missing_count,
                     "missing_packet_count_by_4096_sequence_window":groups,
                     "first_64_missing_sequence_ranges":seq_missing_windows,
                     "source_tail_beyond_highest_received":"NOT_KNOWN_FROM_RECEIVER"}
result={
    "source":os.environ.get("GITHUB_SHA"),
    "scenario_sha256":profile.get("scenario_sha256"),
    "measurement_start_monotonic_s":round(start,6),
    "measurement_end_monotonic_s":round(start+duration,6),
    "scenario":"WL-N0" if profile_name=="n0" else "WL-PERF-V2" if profile_name=="v2" else "WL-P200-250M-30P",
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
    "send_10ms_bucket_counts":send_bins,
    "send_10ms_bucket_bytes":send_bytes_bins,
    "arrival_bucket_scope":"USERSPACE_LOOP_TICK_NOT_KERNEL_TIMESTAMP",
    "max_generator_loop_gap_ms":round(max_loop_pause_ms,3) if send_bins is not None else None,
    "first_32_generator_loop_gaps_ge_20ms":long_loop_pauses if send_bins is not None else None,
    "received_sequence_gap_summary":sequence_sample,
    "udp_socket_probe_start":socket_start,
    "udp_socket_probe_end":socket_end,
    "udp_socket_probe_deltas":udp_socket_delta(socket_start,socket_end) if socket_start is not None else None,
    "udp_socket_1hz":socket_timeline if socket_start is not None else None,
    "udp_probe_scope":"LINUX_SOCKET_INODE_AND_GUEST_GLOBAL_MIB_EXCLUDES_WINDOWS"
                      if socket_start is not None else "NOT_MEASURED_LEGACY",
    "business_udp_rtt":summarize_rtt(probe_rtt_ms,probes_sent),
    "business_udp_rtt_send_errors":probe_send_errors,
    "application_oneway_p99":"NOT_MEASURED_UNCALIBRATED_WINDOWS_LINUX_CLOCKS",
    "sender_error":err
}
(out / ("wl-n0-"+side+"-app.json")).write_text(json.dumps(result)+"\n")
print(json.dumps({k:v for k,v in result.items()
    if k not in ("arrival_10ms_bucket_counts","send_10ms_bucket_counts",
                 "send_10ms_bucket_bytes","received_sequence_gap_summary",
                 "udp_socket_1hz")}),flush=True)
sys.exit(1 if err else 0)
