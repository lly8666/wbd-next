#!/usr/bin/env python3
"""H1310 original 10ms app gap vs genuine native Dave+Erin physical stage.

Read-only/source-frozen: preserve all authentic 750ms+ failures, even when
random losses fail to reproduce. Sampled kernel acceptance never == receipt.
"""
import argparse
import collections
import json
import pathlib
import re

NAMES=("alice","bob","carol","dave","erin")
STAGE=("packets","bytes","dropped","errors")
def load(root,name):
    return json.loads((root/name).read_text())
def top_gap(root,who,direction):
    client=load(root,"h1250-c-"+who+".json")
    server=load(root,"h1250-s-"+who+".json")
    assert client["start_ns"]==server["start_ns"]
    sender=server if direction=="downlink" else client
    receiver=client if direction=="downlink" else server
    sent=sender["tx_bytes_bins_10ms"]["udp"]
    recv=receiver["rx_bytes_bins_10ms"]["udp"]
    assert len(sent)==len(recv)
    spans=[];start=None
    for i,(a,b) in enumerate(zip(sent,recv)):
        if a>0 and b==0:
            if start is None:start=i
        elif start is not None:
            spans.append((i-start,start,i));start=None
    if start is not None:spans.append((len(sent)-start,start,len(sent)))
    d,a,b=max(spans,default=(0,0,0))
    return {"who":who,"direction":direction,"duration_ms":d*10,
        "app_start_seconds":round(a/100,3),
        "mono_start_ns":sender["start_ns"]+a*10_000_000,
        "mono_end_ns":sender["start_ns"]+b*10_000_000,
        "offered_business_bytes_during_gap":sum(sent[a:b]),
        "received_business_bytes_during_gap":sum(recv[a:b])}
def near_rows(rows,span):
    a,b=span["mono_start_ns"],span["mono_end_ns"]
    return [x for x in rows if a-300_000_000<=x["mono_ns"]<=b+300_000_000]
def deltas(rows,key,kind="packets",side="tx"):
    nums=[x.get(key,{}).get(side,{}).get(kind) for x in rows]
    nums=[x for x in nums if isinstance(x,int)]
    return nums[-1]-nums[0] if len(nums)>=2 else None
def qdisc_delta(rows,key,kind):
    nums=[x.get(key,{}).get(kind) for x in rows]
    nums=[x for x in nums if isinstance(x,int)]
    return nums[-1]-nums[0] if len(nums)>=2 else None
def state_count(rows,key):
    states=collections.Counter()
    for x in rows:
        val=x.get(key)
        if isinstance(val,list):
            if not val:states["ABSENT"]+=1
            for e in val:
                v=e.get("state")
                if isinstance(v,list):v=",".join(v)
                states[str(v or "UNKNOWN")]+=1
        else:states["NOT_MEASURED"]+=1
    return dict(states)
def host_cpu(rows):
    if len(rows)<2:return {}
    a,b=rows[0]["host_core_jiffies"],rows[-1]["host_core_jiffies"]
    result={}
    for name,first in a.items():
        if name not in b:continue
        d=[y-x for x,y in zip(first,b[name])]
        total=sum(d)
        if total>0:
            result[name]={"busy_pct":round(100*(total-d[3]-d[4])/total,1),
                "softirq_pct":round(100*d[6]/total,1),
                "steal_pct":round(100*d[7]/total,1)}
    return result
def analyze(root,source):
    report=load(root,"h1286-rapid-report.json")
    plan=load(root,"h1250-matrix-plan.json")
    assert plan["source_sha"]==report["source_sha"]==source
    assert report["server_single_port"]==443 and report["duration_seconds"]==180
    assert len(report["clients"])==5
    assert [(x["seconds"],x["rate_scale"]) for x in plan["capacity_phase_schedule"]]==[
        (30,.25),(60,.35),(30,.45),(50,.35)]
    dave=load(root,"h1310-dave-link-clock.json")["samples"]
    erin=load(root,"h1309-erin-neigh-clock.json")["samples"]
    clock=load(root,"h1301-netem-clock.json")["samples"]
    assert len(dave)>=100 and len(erin)>=100 and len(clock)>=100
    game=(root/"h1250-product-dave.log").read_text(errors="replace")
    m=re.findall(r"M0_GAME_M4_FEC_BACKEND_READBACK selected=(\S+) native_linked=(\d+) tx_native_quanta=(\d+) tx_scalar_quanta=(\d+)",game)
    assert m,"real Game4 original Rust Stop backend not observed"
    backend,linked,native,scalar=m[-1]
    native,scalar,linked=int(native),int(scalar),int(linked)
    # Native ISA-L is used on suitable k,r,block sizes. PreferNative
    # legitimately chooses scalar for small <64B input; scalar==0
    # incorrectly rejected a real native H1309 run.
    assert backend=="prefer-native" and linked==1 and native>0
    assert report["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"
    overflows={k:v["pending_overflow"] for k,v in
        report["server_per_authenticated_lease_tun"].items()}
    assert len(overflows)==5 and all(n==0 for n in overflows.values())
    gaps=[top_gap(root,who,direction) for who in NAMES
        for direction in ("uplink","downlink")]
    worst=max(gaps,key=lambda x:x["duration_ms"])
    dn=near_rows(dave,worst)
    en=near_rows(erin,worst)
    qt=near_rows(clock,worst)
    details={"worst":worst,"native_isal_quanta":native,
        "legitimate_scalar_short_block_quanta":scalar,
        "all_ten_direction_max_active_gaps":gaps,
        "all_five_rotations":report["rotation_verdict"],
        "all_five_per_lease_pending_overflow":overflows,
        "reported_real_alerts":report["alerts"],
        "reported_alert_count":report["alert_count"],
        "source_sha":source,"kind":"OBSERVATION_NOT_PRODUCT_PATCH",
        "erin_independent_control":{
            "samples":len(en),
            "NUD":state_count(en,"server_neighbor_erin"),
            "server_veth_tx_delta":deltas(en,"server_physical_veth"),
            "host_veth_tx_delta":deltas(en,"host_erin_downlink_veth"),
            "qdisc_sent_delta":qdisc_delta(qt,"host_downlink_netem","packets"),
            "qdisc_drop_delta":qdisc_delta(qt,"host_downlink_netem","drops")},
        "dave_physical":{
            "samples":len(dn),
            "NUD":state_count(dn,"server_neighbor_dave"),
            "server_shared_veth_tx_delta":deltas(dn,"server_shared_veth"),
            "host_dave_veth_rx_delta":deltas(dn,"host_dave_veth",side="rx"),
            "host_dave_veth_tx_delta":deltas(dn,"host_dave_veth"),
            "client_dave_veth_rx_delta":deltas(dn,"client_dave_veth",side="rx"),
            "host_dave_netem_sent_delta":qdisc_delta(dn,"host_dave_downlink_netem","packets"),
            "host_dave_netem_dropped_delta":qdisc_delta(dn,"host_dave_downlink_netem","drops"),
            "host_dave_netem_max_qlen":max(
                (x.get("host_dave_downlink_netem",{}).get("qlen") or 0)
                for x in dn) if dn else None,
            "client_dave_netem_sent_delta":qdisc_delta(dn,"client_dave_uplink_netem","packets")},
        "host_core_cpu_during_worst":host_cpu(qt),
        "limitations":["only Dave/Erin physical witness; no other clients' 500ms veth",
            "kernel send acceptance and netem counters are not peer AEAD",
            "single 180s run cannot prove H1308 Erin 5.36s causal repair",
            "75pct/100ms correlated blackholes and 30pct/125ms tested without mock"]}
    if worst["duration_ms"]>=750 and worst["who"]=="dave":
        assert len(dn)>=2 and isinstance(details["dave_physical"]["host_dave_netem_sent_delta"],int)
    if worst["duration_ms"]>=750 and worst["who"]=="erin":
        assert len(en)>=2 and isinstance(details["erin_independent_control"]["qdisc_sent_delta"],int)
    return details
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=analyze(pathlib.Path(args.art),args.source)
    pathlib.Path(args.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("M0_H1310_ARM64_ORIGINAL_TWO_PATH_GAP_STAGE_OBSERVED",
        json.dumps({"worst":result["worst"],"dave":result["dave_physical"],
            "native_quanta":result["native_isal_quanta"],
            "scalar_quanta":result["legitimate_scalar_short_block_quanta"]},
            sort_keys=True),flush=True)
    if result["reported_alert_count"] or result["worst"]["duration_ms"]>=750:
        raise SystemExit("STRICT_NATIVE_APP_GAP_FAIL_RETAINED")
    print("M0_H1310_NO_APP_ALERT_THIS_SOURCE_ONLY_NOT_CAUSAL_REPAIR",flush=True)
if __name__=="__main__": main()
