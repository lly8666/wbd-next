#!/usr/bin/env python3
"""H1361: native ARM64 true one-way original Go TLS/Rust M4 physical loss."""
import argparse,json,pathlib,re,statistics
SOURCE="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
ACTIVE={"alice":"uplink","bob":"downlink","carol":"uplink","dave":"downlink","erin":"uplink"}
PHASES=(("first_wave",30,.2),("sustained",60,.35),("overload",30,.45),("recovery",50,.35))
def read(path):return json.loads(path.read_text())
def gap(tx,rx):
    cur=maximum=0
    for a,b in zip(tx,rx):
        cur=cur+1 if a>0 and b==0 else 0
        maximum=max(maximum,cur)
    return maximum*10
def assess(root):
    plan=read(root/"h1250-matrix-plan.json")
    assert plan["source_sha"]==SOURCE and plan["server_port"]==443
    assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    spec=plan["h1361_specialization"]
    assert spec["profile"]=="H1361_NATIVE_ARM_ONEWAY_30PCT125MS_SOURCE24E1"
    assert len(spec["wrapper_source"])==40
    assert plan["application_scene"]=="strict_oneway" and plan["application_directionality"]==ACTIVE
    assert [x["who"] for x in plan["clients"]]==list(ACTIVE)
    assert [x["loss_pct"] for x in plan["clients"]]==[0,1,5,15,30]
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==[0,15,50,100,125]
    assert [x["c2s_target_mbps"] for x in plan["clients"]]==[5,0,4,0,4]
    assert [x["s2c_target_mbps"] for x in plan["clients"]]==[0,5,0,4,0]
    assert [(x["name"],x["seconds"],x["rate_scale"]) for x in plan["capacity_phase_schedule"]]==list(PHASES)
    assert all(v==600 for v in plan["rotation_seconds"].values())
    assert plan["application_load_seconds"]==180
    for stage in ("installed","after"):
        n=read(root/("h1312-static-neighbour-"+stage+".json"))
        assert n["native_owner_count"]==10 and len(n["entries"])==10
        assert n["data_netem_unchanged"] and not n["product_or_route_key_modified"]
        assert all(x["neighbor_state"]=="PERMANENT" and x["lladdr_present"] for x in n["entries"])
    samples=read(root/"h1301-netem-clock.json")["samples"]
    assert len(samples)>100
    qdisc={}
    for direct,key in (("uplink","client_uplink_netem"),("downlink","host_downlink_netem")):
        ticks=[x[key] for x in samples if x.get(key,{}).get("kind")=="netem"]
        assert len(ticks)>80
        sent=ticks[-1]["packets"]-ticks[0]["packets"]
        dropped=ticks[-1]["drops"]-ticks[0]["drops"]
        pct=100*dropped/(sent+dropped) if sent+dropped else None
        qdisc[direct]={"sent":sent,"dropped":dropped,"loss_pct":round(pct,3) if pct is not None else None}
    # Erin reverse user data is silent; only uplink has statistically
    # representative physical qdisc DATA (native reverse Health remains).
    assert qdisc["uplink"]["sent"]>1000 and qdisc["uplink"]["dropped"]>100
    assert 28<=qdisc["uplink"]["loss_pct"]<=32,qdisc
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=fixed profile=6" in server
    faults=[];caps=[];app={};stops={}
    for x in plan["clients"]:
        who=x["who"];c=read(root/("h1250-c-"+who+".json"));s=read(root/("h1250-s-"+who+".json"))
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==s["end_ns"]-s["start_ns"]==180_000_000_000
        if c["errors"] or s["errors"]:faults.append({"who":who,"app_errors":[c["errors"],s["errors"]]})
        if c["capacity_exceeded"] or s["capacity_exceeded"]:caps.append(who)
        log=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        stops[who]="V4_PUBLIC_SHARED_TUN_STOP generation=" in log
        if not stops[who]:faults.append({"who":who,"owned_stop_missing":True})
        lease=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",log)
        assert lease and set(lease)=={x["lease"]},(who,lease,x["lease"])
        if who=="dave":
            assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" in log
            assert "M0_GAME_M4_FEC_BACKEND_READBACK" in log
        app[who]={}
        for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
            u=tx["tx_bytes_bins_10ms"]["udp"];v=rx["rx_bytes_bins_10ms"]["udp"]
            tu=tx["tx_bytes_bins_10ms"]["tcp"];tv=rx["rx_bytes_bins_10ms"]["tcp"]
            assert len(u)==len(v)==len(tu)==len(tv)==19001
            assert sum(tu)==sum(tv)==0,(who,direction)
            n,m=sum(u[:18000]),sum(v[:18000])
            ratio=m/n if n else None;g=gap(u[:18000],v[:18000])
            row={"real_sent_bytes":n,"real_unique_received_bytes":m,
                 "delivery_fraction":round(ratio,6) if ratio is not None else None,
                 "max_active_no_receive_ms":g}
            app[who][direction]=row
            if direction==ACTIVE[who]:
                if n<100000 or m<100000 or ratio is None or ratio<.94 or g>=750:
                    faults.append({"who":who,"direction":direction,"app_loss_or_stall":row})
            elif n or m:
                faults.append({"who":who,"direction":direction,"reverse_app_not_silent":row})
    queue={}
    for line in server.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:continue
        k=re.search(r"ip=(10\.66\.0\.\d+)",line)
        if k is None:continue
        row={}
        for key in ("offered","direct_delivered","pending_overflow"):
            v=re.search(r"\b"+key+r"=(\d+)",line)
            assert v is not None,(key,line)
            row[key]=int(v.group(1))
        queue[k.group(1)]=row
    assert all(x["lease"] in queue for x in plan["clients"] if ACTIVE[x["who"]]=="downlink")
    if any(x["pending_overflow"] or x["offered"]!=x["direct_delivered"] for x in queue.values()):
        faults.append({"server_queue":queue})
    cpu={};start=10;anchor=plan["start_monotonic_ns"]
    for name,seconds,scale in PHASES:
        ticks=[x for x in samples if start<=(x["mono_ns"]-anchor)/1e9<start+seconds]
        cores={}
        for first,second in zip(ticks,ticks[1:]):
            for k,a in first.get("host_core_jiffies",{}).items():
                b=second.get("host_core_jiffies",{}).get(k)
                if b is None:continue
                diff=[y-x for x,y in zip(a,b)]
                total=sum(diff)
                if total>0:cores.setdefault(k,[]).append(100*(total-diff[3]-diff[4])/total)
        assert 1<=len(cores)<=256 and all(len(z)>10 for z in cores.values())
        cpu[name]={"vcpus":len(cores),
          "mean_guest_busy_pct":round(statistics.mean(z for xs in cores.values() for z in xs),2),
          "max_core_mean_busy_pct":round(max(statistics.mean(xs) for xs in cores.values()),2)}
        start+=seconds
    assert start==180
    near=[k for k,x in cpu.items() if x["mean_guest_busy_pct"]>=95 or x["max_core_mean_busy_pct"]>=95]
    label=("FAIL_NATIVE_ONEWAY_APP_OR_OWNER" if faults else
           "CAPACITY_LIMITED" if caps or near else
           "PASS_SCOPED_NATIVE_ARM64_ORIGINAL_ONEWAY_30PCT125MS_FIVE_USER")
    return {"schema_version":1,"source_sha":SOURCE,"classification":label,
      "original_source":SOURCE,"wrapper_source":spec["wrapper_source"],"TLS443":True,
      "oneway_real_original_udp_app":app,"physical_erin_qdisc":qdisc,
      "native_guest_cpu_phases":cpu,"client_exact_owned_Stop":stops,
      "server_shared_TUN_exact_Stop":True,"per_lease_queue":queue,
      "app_or_owner_faults":faults,"capacity_limit":caps,"host_limit_phases":near,
      "no_H1318_reverse_health_blackhole_rerun":True,"rotations_not_triggered":True,
      "limitations":["Old H1317 5.18s failure remains intact, this one static case is not a causal fix",
        "Actual original encrypted reverse Health allowed, no reverse user UDP/TCP/probes",
        "30pct125ms original native ARM virtual underlay, not physical WAN/Windows/Android",
        "No active rotation due600s timers and no L3 1800s"]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    v=p.parse_args();r=assess(pathlib.Path(v.art))
    pathlib.Path(v.out).write_text(json.dumps(r,indent=2)+"\n")
    print("M0_PLAN028_H1361_ARM64_TRUE_ONEWAY_ORIGINAL_APP_AUDIT",r["classification"],flush=True)
if __name__=="__main__":main()
