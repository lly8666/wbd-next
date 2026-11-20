#!/usr/bin/env python3
"""H2231 measured application UDP RTT p50/p95/p99 + kernel TCP iperf3 tails.

No product/protocol changes. This is a separate, low-rate real app UDP
probe in parallel with TCP iperf3, distinguishing direct routed traffic
from WBD authenticated inner IPv4. Unknown/undersampled cannot be zero RTT.
The 20s case sends 120 UDP echo requests; 3s cases use 16 (p99 UNKNOWN).
All RTTs are end-to-end application elapsed monotonic_ns, not one-way
network delay, raw FakeTCP RTT or fabricated receive times.

Per-second TCP goodput percentiles reflect *time bins*, NOT packet P99.
TCP RTT samples from iperf's sender-stream interval telemetry are sparse
kernel sampled RTTs, and never substitute for real application UDP P99.
"""
import argparse
import json
import math
import pathlib
import re
import secrets
import select
import socket
import statistics
import sys
import time

MAGIC=b"H2231-UDP-APP-REQ/"
REPLY=b"H2231-UDP-APP-RESP/"
PORT={"direct":45902,"wbd":45901}
TARGET={"direct":"10.248.82.2","wbd":"10.66.0.1"}
APP_P99_MIN_SAMPLES=50
MAX_COUNT=256

def need(ok,message):
    if not ok:raise ValueError("H2231_FAIL_CLOSED_"+message)

def save(path,obj):
    dst=pathlib.Path(path)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")

def percentile(nums,p):
    need(bool(nums) and 0<=p<=100,"BAD_PERCENTILE_INPUT")
    sorted_values=sorted(nums)
    x=(len(nums)-1)*p/100.0
    lo=int(math.floor(x));hi=int(math.ceil(x))
    return sorted_values[lo]+(sorted_values[hi]-sorted_values[lo])*(x-lo)

def distribution(nums,min_for_p99=10,unit="ms"):
    values=[float(x) for x in nums if isinstance(x,(float,int)) and
            not isinstance(x,bool) and math.isfinite(float(x)) and x>=0]
    out={"source":"ACTUAL_OBSERVED_SAMPLES_NOT_MODEL",
         "unit":unit,"sample_count":len(values),
         "p50":None,"p95":None,"p99":None,"p01":None,
         "mean":None,"min":None,"max":None,
         "p99_quality":"UNKNOWN_INSUFFICIENT_SAMPLES",
         "percentile_method":"linear_type7_sorted_samples"}
    if not values:return out
    out.update(p50=round(percentile(values,50),3),
        p95=round(percentile(values,95),3),
        p01=round(percentile(values,1),3),
        mean=round(statistics.mean(values),3),
        min=round(min(values),3),max=round(max(values),3))
    if len(values)>=min_for_p99:
        out["p99"]=round(percentile(values,99),3)
        out["p99_quality"]="OBSERVED_SAMPLE_QUANTILE"
    return out

def iperf_tail(original,case):
    """Compute *honest* sampled tails from real iperf3 stdout JSON."""
    need(isinstance(original,dict) and isinstance(case,dict),"INVALID_IPERF_JSON")
    intervals=original.get("intervals",[])
    if not isinstance(intervals,list):intervals=[]
    goodput=[];sender_rtt_us=[];cwnd_bytes=[];seconds=[]
    for interval in intervals[:240]:
        if not isinstance(interval,dict):continue
        aggregate=interval.get("sum",{})
        if isinstance(aggregate,dict):
            bps=aggregate.get("bits_per_second")
            period=aggregate.get("seconds")
            if isinstance(bps,(int,float)) and math.isfinite(bps) and bps>=0 and \
                isinstance(period,(int,float)) and math.isfinite(period) and 0.25<=period<=4.0:
                goodput.append(float(bps)/1e6)
                seconds.append(float(period))
        streams=interval.get("streams",[])
        if isinstance(streams,list):
            for row in streams[:64]:
                if not isinstance(row,dict):continue
                # iperf3 Linux sender telemetry: rtt is microseconds.
                # Never invent sender RTT on download receiver-only reports.
                for key,target in (("rtt",sender_rtt_us),
                                   ("snd_cwnd",cwnd_bytes)):
                    value=row.get(key)
                    if isinstance(value,(int,float)) and not isinstance(value,bool) and \
                       math.isfinite(value) and value>0:
                        target.append(value)
    end=original.get("end",{})
    if not isinstance(end,dict):end={}
    sent=end.get("sum_sent",{})
    received=end.get("sum_received",{})
    if not isinstance(sent,dict):sent={}
    if not isinstance(received,dict):received={}
    retrans=sent.get("retransmits")
    retrans=int(retrans) if type(retrans) is int and retrans>=0 else None
    sentbytes=sent.get("bytes")
    retrans_per_gib=(round(retrans/(sentbytes/2**30),3)
        if isinstance(sentbytes,(int,float)) and sentbytes>0 and retrans is not None else None)
    # Cumulative bytes and a per-second TCP retrans rate are different units.
    peak=goodput[-1] if goodput else None
    long_run_peak=max(goodput,default=0)
    first_over_90=next((i for i,value in enumerate(goodput)
        if long_run_peak>0 and value>=.9*long_run_peak),None)
    peak_threshold="90pct_of_observed_peak_1s_bin_not_link_capacity"
    complete=case.get("status")=="PASS_REAL_KERNEL_IPERF3_TCP"
    return {
        "schema":"H2231_TCP_SAMPLE_TAIL_V1",
        "qualified_iperf3_completed":complete,
        "source":"ACTUAL_IPERF3_INTERVALS_AND_LINUX_KERNEL_TCP_SENDER",
        "business_goodput_per_interval_mbps":distribution(
            goodput,10,"Mbps_per_iperf_interval"),
        "business_goodput_p01_low_tail_mbps":(
            round(percentile(goodput,1),3) if goodput else None),
        "kernel_tcp_sender_rtt_ms":distribution(
            [x/1000.0 for x in sender_rtt_us],APP_P99_MIN_SAMPLES,"ms"),
        "kernel_tcp_sender_rtt_source":"IPERF3_INTERVAL_SENDER_SAMPLED_NOT_PACKET_RTT",
        "kernel_tcp_cwnd_bytes":distribution(cwnd_bytes,APP_P99_MIN_SAMPLES,"bytes"),
        "observed_first_interval_reaching_90pct_of_peak_index":first_over_90,
        "ramp_threshold_basis":peak_threshold,
        "last_interval_mbps":round(peak,3) if peak is not None else None,
        "transmission_stall_1s_bins_below_10pct_observed_median":sum(
            1 for x in goodput if goodput and
            x<.1*percentile(goodput,50)),
        "goodput_sample_intervals_s":seconds,
        "tcp_sum_sent_retransmits":retrans,
        "tcp_retransmits_per_gib_sent":retrans_per_gib,
        "rtt_p99_absent_reason":("NO_SENDER_INTERVAL_RTT_TELEMETRY"
            if not sender_rtt_us else
            "FEWER_THAN_50_SENDER_INTERVAL_RTT_SAMPLES"
            if len(sender_rtt_us)<APP_P99_MIN_SAMPLES else None),
        "note":"RTT/P99 samples are not proof of network one-way delay or QoS"
    }

def enrich_case(case_path,iperf_path):
    case_path=pathlib.Path(case_path)
    need(case_path.name.startswith("case-") and case_path.name.endswith(".json"),
         "IPERF_CASE_PATH_ONLY")
    case=json.loads(case_path.read_text())
    need(isinstance(case,dict) and case.get("kind") in ("wbd","direct"),
         "CASE_UNKNOWN_OR_NO_APP_ORIGIN")
    try:
        raw=json.loads(pathlib.Path(iperf_path).read_text())
        if not isinstance(raw,dict):raise ValueError("not real JSON object")
        sample=iperf_tail(raw,case)
    except (OSError,ValueError,TypeError) as exc:
        sample={"schema":"H2231_TCP_SAMPLE_TAIL_V1",
            "qualified_iperf3_completed":False,
            "status":"UNKNOWN_RAW_IPERF_NOT_PARSEABLE",
            "reason":type(exc).__name__,
            "business_goodput_per_interval_mbps":distribution([]),
            "kernel_tcp_sender_rtt_ms":distribution([])}
    case["h2231_tcp_tail"]=sample
    save(case_path,case)
    return sample

def echoed_payload(data):
    if len(data)>180 or not data.startswith(MAGIC):return None
    return REPLY+data[len(MAGIC):]

def serve(kind):
    need(kind in TARGET,"UNTRUSTED_ECHO_KIND")
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sock.bind((TARGET[kind],PORT[kind]))
        sock.settimeout(1.0)
        print("H2231_REAL_NATIVE_UDP_APP_SERVER_READY kind="+kind,flush=True)
        while True:
            try:packet,peer=sock.recvfrom(512)
            except socket.timeout:continue
            out=echoed_payload(packet)
            if out is not None:sock.sendto(out,peer)

def validate_probe_args(kind,count,interval_ms,deadline_s):
    need(kind in TARGET,"PROBE_TARGET_NOT_ALLOWLISTED")
    need(1<=count<=MAX_COUNT and interval_ms in (100,200) and
         2.0<=deadline_s<=24.0,"UNBOUNDED_APP_PROBE")
    need((count-1)*interval_ms/1000.0<deadline_s-.5,
         "INSUFFICIENT_TIME_TO_EMIT_ALL_PROBES")

def probe(kind,count,interval_ms,deadline_s,sock=None):
    validate_probe_args(kind,count,interval_ms,deadline_s)
    # This random ID is ephemeral and scoped only to the probe instance;
    # its value is NEVER written to uploaded artifacts or case receipts.
    nonce=secrets.token_hex(12)
    interval_ns=interval_ms*1_000_000
    owned=sock is None
    if owned:sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        sock.setblocking(False)
        first=time.monotonic_ns()
        end=first+int(deadline_s*1e9)
        index=0;send_at=first
        pending={};measured={};bad=0;duplicates=0
        expected_peer=(TARGET[kind],PORT[kind])
        while True:
            now=time.monotonic_ns()
            if now>=end:break
            if index<count and now>=send_at:
                payload=(nonce+"/"+str(index)).encode("ascii")
                sent_ns=time.monotonic_ns()
                packet=MAGIC+payload
                try:
                    sent=sock.sendto(packet,expected_peer)
                    if sent==len(packet):pending[payload]=sent_ns
                    else:bad+=1
                except OSError:bad+=1
                index+=1
                send_at=first+index*interval_ns
            now=time.monotonic_ns()
            wait_s=min(.08,max(0,(end-now)/1e9))
            if index<count:
                wait_s=min(wait_s,max(0,(send_at-now)/1e9))
            if wait_s<=0:continue
            readable,_,_=select.select([sock],[],[],wait_s)
            if not readable:continue
            try:data,source=sock.recvfrom(1024)
            except (BlockingIOError,OSError):continue
            received_ns=time.monotonic_ns()
            if source!=expected_peer or not data.startswith(REPLY):
                bad+=1;continue
            suffix=data[len(REPLY):]
            if suffix not in pending:
                bad+=1;continue
            if suffix in measured:
                duplicates+=1;continue
            rtt_ns=received_ns-pending[suffix]
            if rtt_ns<0:bad+=1;continue
            measured[suffix]=rtt_ns/1e6
        # Reception order is not send order under GE reordering. Compute
        # adjacent send-index RTT variation only where BOTH replies arrived.
        seq_and_rtt=sorted((int(key.split(b"/")[-1]),value)
                           for key,value in measured.items())
        values=[rtt for _,rtt in seq_and_rtt]
        variation=[abs(seq_and_rtt[i][1]-seq_and_rtt[i-1][1])
                   for i in range(1,len(seq_and_rtt))
                   if seq_and_rtt[i][0]==seq_and_rtt[i-1][0]+1]
        missing=[i for i in range(index)
                 if (nonce+"/"+str(i)).encode("ascii") not in measured]
        runs=[];previous=None
        for number in missing:
            if previous is not None and number==previous+1:
                runs[-1]+=1
            else:runs.append(1)
            previous=number
        received=len(values)
        return {
            "schema":"H2231_TRUE_APP_UDP_RTT_V1",
            "origin":"REAL_APP_UDP_ECHO_WITHIN_WBD_INNER_TUN" if kind=="wbd"
              else "REAL_APP_UDP_ECHO_DIRECT_ARM_RELAY_ONLY",
            "kind":kind,"sent_requests":index,
            "valid_unique_reply_count":received,
            "missing_unique_reply_count":index-received,
            "missing_unique_reply_pct":round(100*(index-received)/index,3) if index else None,
            "invalid_reply_count":bad,"duplicate_replies":duplicates,
            "elapsed_budget_s":deadline_s,
            "probe_interval_ms":interval_ms,
            "roundtrip_rtt_ms":distribution(values,APP_P99_MIN_SAMPLES,"ms"),
            "adjacent_sequence_rtt_abs_variation_ms":distribution(
                variation,APP_P99_MIN_SAMPLES,"ms"),
            "observed_missing_burst_length_packets":distribution(runs,10,"packets"),
            "max_consecutive_missing_requests":max(runs,default=0),
            "rtt_p99_status":"OBSERVED_SAMPLE_QUANTILE" if received>=APP_P99_MIN_SAMPLES
              else "UNKNOWN_INSUFFICIENT_REAL_APP_ECHOS",
            "not_exact_wire_rtt":True,
            "not_equivalent_to_windows_physical_tcp":True,
            "raw_rtt_samples_ms":[round(x,3) for x in values],
            "qualified_for_lowrate_udp_p99":received>=APP_P99_MIN_SAMPLES}
    finally:
        if owned:sock.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    a=sub.add_parser("echo-server");a.add_argument("kind",choices=tuple(TARGET))
    a=sub.add_parser("udp-probe");a.add_argument("kind",choices=tuple(TARGET))
    a.add_argument("output");a.add_argument("--count",type=int,default=120)
    a.add_argument("--interval-ms",type=int,default=100)
    a.add_argument("--deadline",type=float,default=15.0)
    a=sub.add_parser("iperf-enrich");a.add_argument("case");a.add_argument("iperf_json")
    a=sub.add_parser("smoke")
    args=parser.parse_args()
    if args.command=="echo-server":serve(args.kind)
    elif args.command=="udp-probe":
        result=probe(args.kind,args.count,args.interval_ms,args.deadline)
        save(args.output,result)
        print("H2231_REAL_APP_UDP_RTT "+json.dumps({
            k:result[k] for k in ("kind","valid_unique_reply_count",
             "missing_unique_reply_count","rtt_p99_status")}),flush=True)
    elif args.command=="iperf-enrich":
        sample=enrich_case(args.case,args.iperf_json)
        print("H2231_TCP_TAIL_METRIC "+json.dumps({
           "qualified_iperf3_completed":sample["qualified_iperf3_completed"],
           "throughput":sample["business_goodput_per_interval_mbps"],
           "tcp_rtt":sample["kernel_tcp_sender_rtt_ms"]}),flush=True)
    else:
        need(echoed_payload(MAGIC+b"test/0")==REPLY+b"test/0","ECHO_FORMAT")
        print("H2231_METRICS_STATIC_SMOKE_NOT_REAL_NETWORK")

if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TimeoutError) as exc:
        print("H2231_METRIC_FAILURE "+str(exc),file=sys.stderr)
        sys.exit(2)
