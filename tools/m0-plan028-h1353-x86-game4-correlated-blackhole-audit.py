#!/usr/bin/env python3
"""H1353: true kernel 100% correlated impairment vs actual original app recovery."""
import argparse,json,pathlib
SOURCE="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
NAMES=("alice","bob","carol","dave","erin")
def load(p):return json.loads(p.read_text())
def window(bins,a,b):return sum(bins[int(a*100):int(b*100)])
def gap(tx,rx,a,b):
    cur=peak=0
    for x,y in zip(tx[int(a*100):int(b*100)],rx[int(a*100):int(b*100)]):
        cur=cur+1 if x>0 and y==0 else 0
        peak=max(peak,cur)
    return peak*10
def assess(root):
    plan=load(root/"h1250-matrix-plan.json")
    assert plan["source_sha"]==SOURCE
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["h1353_specialization"]["profile"]=="H1353_CORRELATED_GAME4_DOUBLE_BLACKHOLE"
    assert plan["server_port"]==443 and plan["application_load_seconds"]==180
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert [x["loss_pct"] for x in plan["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==[0,50,100,150,0]
    assert all(x==600 for x in plan["rotation_seconds"].values())
    for stage in ("installed","after"):
        neighbours=load(root/("h1312-static-neighbour-"+stage+".json"))
        assert neighbours["native_owner_count"]==10
        assert len(neighbours["entries"])==10
        assert all(x["neighbor_state"]=="PERMANENT" for x in neighbours["entries"])
    event=load(root/"h1353-physical-game4-blackhole.json")
    assert event["kind"]=="ONE_GAME4_FOUR_LANE_SHARED_VETH_BOTH_DIRECTIONS"
    assert event["original_delay_ms"]==150 and event["original_loss_pct"]==0
    assert event["other_four_links_untouched"] and event["no_product_source_change"]
    start=(event["blackhole_start_ns"]-plan["start_monotonic_ns"])/1e9
    end=(event["restored_ns"]-plan["start_monotonic_ns"])/1e9
    assert 70<=start<71 and 78<=end<79,(start,end)
    drops=event["actual_kernel_drops_during_100pct"]
    assert drops["uplink"]["drops"]>100 and drops["downlink"]["drops"]>100,drops
    prior=load(root/"h1286-rapid-report.json")
    assert prior["source_sha"]==SOURCE and prior["server_single_port"]==443
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    queue=prior["server_per_authenticated_lease_tun"]
    assert set(queue)=={x["lease"] for x in plan["clients"]}
    failures=[];capacity=[];streams={};stop_ok=True
    for x in plan["clients"]:
        who=x["who"];c=load(root/("h1250-c-"+who+".json"));s=load(root/("h1250-s-"+who+".json"))
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==180_000_000_000
        assert s["end_ns"]-s["start_ns"]==180_000_000_000
        if c["errors"] or s["errors"]:failures.append({"client":who,"app_errors":[c["errors"],s["errors"]]})
        if c["capacity_exceeded"] or s["capacity_exceeded"]:capacity.append(who)
        log=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        stop_ok=stop_ok and "V4_PUBLIC_SHARED_TUN_STOP generation=" in log
        assert "V4_PUBLIC_LEASE_APPLIED role=client" in log
        if who=="dave":
            assert "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client" in log
            assert "M0_GAME_M4_FEC_BACKEND_READBACK" in log
        streams[who]=(c,s)
    if not stop_ok:failures.append({"exact_stop":"missing"})
    for q in queue.values():
        if q["pending_overflow"]!=0 or q["offered"]!=q["direct_delivered"]:
            failures.append({"per_lease_queue":q})
    app={}
    for who,(c,s) in streams.items():
        app[who]={}
        for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
            sent=tx["tx_bytes_bins_10ms"]["udp"]
            got=rx["rx_bytes_bins_10ms"]["udp"]
            assert len(sent)==len(got)==18000
            report={}
            for phase,a,b in (("pre",50,65),("blackhole",72,76),
                              ("post",82,102),("late",110,145)):
                n,m=window(sent,a,b),window(got,a,b)
                report[phase]={"tx_bytes":n,"rx_bytes":m,
                               "fraction":round(m/n,5) if n else None,
                               "max_10ms_active_no_rx_gap_ms":gap(sent,got,a,b)}
            if who=="dave":
                x=report["blackhole"]
                if x["tx_bytes"]<25000 or x["rx_bytes"]!=0:
                    failures.append({"dave_direction":direction,"blackhole_not_observed":x})
                for phase in ("pre","post","late"):
                    x=report[phase]
                    if (x["tx_bytes"]<10000 or x["fraction"] is None or
                            x["fraction"]<.97 or x["max_10ms_active_no_rx_gap_ms"]>=750):
                        failures.append({"dave_direction":direction,"phase":phase,"unexpected_stall":x})
                first=next((tick for tick in range(int((end+.05)*100),int((end+4.0)*100))
                            if got[tick]>0),None)
                first_ms=None if first is None else round(first*10-end*1000)
                report["first_app_receive_after_restore_ms"]=first_ms
                if first_ms is None or first_ms>2500:
                    failures.append({"dave_direction":direction,"late_first_app_receipt_ms":first_ms})
            else:
                x=report["blackhole"]
                if (x["tx_bytes"]<10000 or x["fraction"] is None or
                        x["fraction"]<.96 or x["max_10ms_active_no_rx_gap_ms"]>=750):
                    failures.append({"client":who,"direction":direction,"sibling_stall":x})
            app[who][direction]=report
    result=("FAIL" if failures else "CAPACITY_LIMITED" if capacity else
            "PASS_SCOPED_NATIVE_X86_GAME4_REAL_CORRELATED_BLACKHOLE_RECOVERY")
    return {"classification":result,"original_product_source":SOURCE,
       "wrapper_source":plan["h1353_specialization"]["wrapper_source"],
       "original_TLS_port":443,"original_clients":list(NAMES),
       "game4_common_underlay_real_blackhole_start_s":round(start,3),
       "game4_real_underlay_restore_s":round(end,3),
       "kernel_drops_during":drops,"original_app_10ms_windows":app,
       "original_exact_all_client_stop":stop_ok,"server_shared_tun_stop":True,
       "per_lease_queue":queue,"faults":failures,"generator_capacity_limit":capacity,
       "scope":["one physical veth shared across four Game4 lanes, not independent paths",
                "expected blackout explicitly excluded from pre/post recovery windows",
                "real kernel qdisc counters and original app delivery observed, no Windows/ARM/physical equivalence",
                "normal lane rotation intentionally NOT_TRIGGERED"]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();r=assess(pathlib.Path(a.art))
    pathlib.Path(a.out).write_text(json.dumps(r,indent=2)+"\n")
    print("H1353_TRUE_GAME4_BLACKHOLE_APP_AND_SIBLING_AUDIT",r["classification"],flush=True)
if __name__=="__main__":
    main()
