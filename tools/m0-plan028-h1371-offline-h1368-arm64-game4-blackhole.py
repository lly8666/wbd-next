#!/usr/bin/env python3
"""H1371 OFFLINE audit: untouched H1368 ARM64 native 180s Game4 full common-underlay blackout.
H1368 real 180s business/Stop completed; raw CI failed on x86-style 18000
bins check for 19001-bin ARM app, and original event JSON was omitted by glob.
The ACTUAL original qdisc event and timestamps are present in the original run log.
Never rerun networking for reporter/archive presentation bugs.
"""
import argparse,ast,json,pathlib,re

SOURCE="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
WRAPPER="a4bfb7237be624442819a45c61c5455d4944e4e4"
NAMES=("alice","bob","carol","dave","erin")
DELAYS=(0,50,100,150,0)

def read(path):return json.loads(path.read_text())
def phase(tx,rx,start,end):
    a=int(start*100);b=int(end*100)
    sent=sum(tx[a:b]);received=sum(rx[a:b])
    now=maximum=0
    for x,y in zip(tx[a:b],rx[a:b]):
        now=now+1 if x>0 and y==0 else 0
        maximum=max(maximum,now)
    return {"sent_bytes":sent,"received_bytes":received,
            "delivery_ratio":round(received/sent,6) if sent else None,
            "max_active_10ms_no_receive_ms":maximum*10}

def audit(root):
    plan=read(root/"h1250-matrix-plan.json")
    rapid=read(root/"h1286-rapid-report.json")
    assert plan["source_sha"]==rapid["source_sha"]==SOURCE
    assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert plan["server_port"]==rapid["server_single_port"]==443
    assert plan["application_load_seconds"]==180
    spec=plan["h1368_specialization"]
    assert spec["product_source"]==SOURCE and spec["wrapper_source"]==WRAPPER
    assert spec["profile"]=="H1368_CORRELATED_GAME4_DOUBLE_BLACKHOLE"
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert [x["loss_pct"] for x in plan["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==list(DELAYS)
    assert [plan["rotation_seconds"][who] for who in NAMES]==[600]*5
    assert spec["base_inner_mbps_each_direction"]==[4,4,3,6,3]
    for stage in ("installed","after"):
        row=read(root/("h1312-static-neighbour-"+stage+".json"))
        assert row["native_owner_count"]==10 and len(row["entries"])==10
        assert all(x["neighbor_state"]=="PERMANENT" for x in row["entries"])
    traffic=(root/"h1368-native-game4-correlated-traffic.log").read_text(errors="replace")
    assert "H1368_NATIVE_GAME4_CORRELATED_REAL_BLACKHOLE_CAPTURED" in traffic
    m=re.search(r"(?m)^H1353_REAL_GAME4_TWO_DIRECTION_100PCT_BLACKHOLE_RESTORED\s+(\d+)\s+(\d+)\s+(\{[^\n]+\})$",traffic)
    assert m is not None,"original physical qdisc event was not printed"
    event_counts=ast.literal_eval(m.group(3))
    assert set(event_counts)=={"uplink","downlink"}
    start=(int(m.group(1))-plan["start_monotonic_ns"])/1e9
    end=(int(m.group(2))-plan["start_monotonic_ns"])/1e9
    assert 70<=start<71 and 78<=end<79,(start,end)
    assert 7.5<end-start<8.5,(start,end)
    assert all(event_counts[d]["drops"]>100 and event_counts[d]["packets"]>1000
               for d in ("uplink","downlink"))
    qdisc=(root/"h1250-qdisc-after.txt").read_text(errors="replace")
    for direction in ("uplink","downlink"):
        m2=re.search(r"== dave "+direction+r" loss=0% delay=150ms ==\s*\n(?:[^\n]*\n)?\s*Sent [^\n]*\(dropped (\d+)",qdisc)
        assert m2 is not None,direction
        assert int(m2.group(1))>=event_counts[direction]["drops"]
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=fixed profile=6" in server
    queue=rapid["server_per_authenticated_lease_tun"]
    assert set(queue)=={x["lease"] for x in plan["clients"]}
    assert all(x["pending_overflow"]==0 and x["offered"]==x["direct_delivered"]
               for x in queue.values())
    actual_alerts=rapid["alerts"]
    counts={}
    for item in actual_alerts:counts[item["kind"]]=counts.get(item["kind"],0)+1
    assert counts=={"ROTATION_CONTINUITY_NOT_PROVEN":5,
                    "APP_RX_GAP_WITH_ACTIVE_TX_GE750MS":2},counts
    # The original source intentionally parks all five rotation timers at
    # 600s in a 180s scenario. Its generic rotation alerts do not mean a
    # configured rotation was missed. The two gap alerts are both the
    # planned and independently OS-confirmed t70..78s 100% true blackout.
    gaps=[x for x in actual_alerts if x["kind"]=="APP_RX_GAP_WITH_ACTIVE_TX_GE750MS"]
    assert {x["direction"] for x in gaps}=={"uplink","downlink"}
    assert all(x["who"]=="dave" and 7500<=x["duration_ms"]<=8500 for x in gaps)
    faults=[];apps={};stops={}
    for item in plan["clients"]:
        who=item["who"]
        c=read(root/("h1250-c-"+who+".json"))
        s=read(root/("h1250-s-"+who+".json"))
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==s["end_ns"]-s["start_ns"]==180_000_000_000
        if c["errors"] or s["errors"]:faults.append({"who":who,"app_errors":[c["errors"],s["errors"]]})
        if c["capacity_exceeded"] or s["capacity_exceeded"]:faults.append({"who":who,"capacity_limit":True})
        who_log=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        stops[who]="V4_PUBLIC_SHARED_TUN_STOP generation=" in who_log
        if not stops[who]:faults.append({"who":who,"stop_missing":True})
        if "V4_PUBLIC_LEASE_APPLIED role=client" not in who_log:
            faults.append({"who":who,"original_authenticated_lease_missing":True})
        if who=="dave":
            assert "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client" in who_log
            assert "M0_GAME_M4_FEC_BACKEND_READBACK selected=scalar" in who_log
        apps[who]={}
        for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
            sent=tx["tx_bytes_bins_10ms"]["udp"]
            got=rx["rx_bytes_bins_10ms"]["udp"]
            assert len(sent)==len(got)==19001,("original native ARM 10ms bins",who,direction,len(sent),len(got))
            state={}
            for name,a,b in (("pre",50,65),("planned_blackout",72,76),
                              ("post",82,102),("late",110,145)):
                state[name]=phase(sent,got,a,b)
            if who=="dave":
                dark=state["planned_blackout"]
                if dark["sent_bytes"]<25000 or dark["received_bytes"]!=0:
                    faults.append({"who":who,"direction":direction,"missing_true_blackout":dark})
                for phase_name in ("pre","post","late"):
                    row=state[phase_name]
                    if (row["sent_bytes"]<10000 or row["delivery_ratio"] is None or
                        row["delivery_ratio"]<.97 or row["max_active_10ms_no_receive_ms"]>=750):
                        faults.append({"who":who,"direction":direction,"recover_stall":{phase_name:row}})
                first=next((tick for tick in range(int((end+.05)*100),int((end+4)*100))
                            if got[tick]>0),None)
                first_ms=None if first is None else round(first*10-end*1000)
                state["first_native_app_receive_after_restore_ms"]=first_ms
                if first_ms is None or first_ms>2500:
                    faults.append({"who":who,"direction":direction,"slow_after_restore_ms":first_ms})
            else:
                row=state["planned_blackout"]
                if (row["sent_bytes"]<10000 or row["delivery_ratio"] is None or
                    row["delivery_ratio"]<.96 or row["max_active_10ms_no_receive_ms"]>=750):
                    faults.append({"who":who,"direction":direction,"unexpected_sibling_stall":row})
            apps[who][direction]=state
    label=("FAIL_SCOPED_NATIVE_APP_OR_STOP" if faults else
           "PASS_SCOPED_NATIVE_ARM64_GAME4_TRUE_SHARED_PHYSICAL_BLACKHOLE_180S_SIBLINGS_RECOVERY")
    return {
      "schema_version":1,"original_action":42450177745,"original_ci_conclusion":"failure",
      "original_artifact_id":13605541335,"original_source":SOURCE,
      "wrapper_source":WRAPPER,"network_rerun":False,
      "classification":label,"original_server_tls_port":443,
      "original_five_clients":list(NAMES),
      "physical_100pct_both_direction_blackhole":{
          "start_s":round(start,4),"end_s":round(end,4),
          "duration_s":round(end-start,4),
          "original_kernel_qdisc_event_counts":event_counts,
          "native_event_original_source":"h1368-native-game4-correlated-traffic.log; real OS tc qdisc after counters",
      },
      "original_180s_10ms_app_samples":apps,
      "exact_five_client_Stop":stops,
      "server_shared_TUN_Stop":True,
      "server_per_lease_queue":queue,
      "native_app_or_owner_faults":faults,
      "original_unfiltered_generic_rapid":{"verdict":rapid["rotation_verdict"],
          "original_alert_count":rapid["alert_count"],
          "original_alert_breakdown":counts,
          "scope_of_expected_gaps":"t70-78 genuine 100% Game4 blackhole",
          "untriggered_rotation_timer_seconds":600},
      "original_ci_reporter_faults":[
          "copied x86 auditor required exactly 18000 bins but original ARM 180s app emits 19001 for drain",
          "original kernel blackhole event JSON h1353-physical-game4-blackhole.json omitted by new H1368 artifact glob, while untouched live timestamp+kernel drop counters survived in traffic.log and qdisc-after.txt"],
      "limitations":[
          "ARM64 source24e real native 5-client/180s one common physical veth for Game4 lanes, not independent physical paths or user hardware",
          "All five rotation timers deliberately parked at600s; this does not prove rotation (separate H1363 original covers two genuine turns)",
          "Expected 8s full OS network blackout is not stable network gap; post-recovery real native business independently audited",
          "Original CI failure preserved; no network workload replay or product patch; Windows dual authenticated devices still NOT_RUN"]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    args=p.parse_args()
    row=audit(pathlib.Path(args.art))
    path=pathlib.Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row,indent=2)+"\n")
    print("H1371_ORIGINAL_ARM64_GAME4_CORRELATED_TRUE_OS_BLACKHOLE_SIBLINGS_AND_STOP",row["classification"],flush=True)
if __name__=="__main__":main()
