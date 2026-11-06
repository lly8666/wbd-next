#!/usr/bin/env python3
"""H1262: original Go TLS/Rust 3-client Game2 OFF outer appearance + Fixed6 30% recovery.

Outcome is a diagnostic, never a universal performance qualification.
Every counter is from the original native product or actual app/tc, not
configured desired throughput. Outer cosmetic copies count separately from
application unique receipts and FEC recoveries.
"""
import argparse
import json
import pathlib
import re

PHASES=(("warmup",10),("sustained",45),("overload",35),("recovery",90))
NAMES=("alice","carol","erin")


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def extract(log, marker, names):
    lines=[x for x in log.splitlines() if marker in x]
    if not lines:
        return {"observed":False}
    s=lines[-1]
    out={"observed":True}
    for name in names:
        val=re.search(r"\b"+name+r"=(\d+)",s)
        assert val,(marker,name,s)
        out[name]=int(val.group(1))
    return out


def mbps(n,secs):
    return round(n*8/(secs*1e6),4)


def qdisc(art, who, direction,loss,delay):
    text=(art/"h1250-qdisc-after.txt").read_text()
    pattern=(r"== "+who+r" "+direction+r" loss="+str(loss)+
             r"% delay="+str(delay)+r"ms ==\s*"
             r"qdisc netem [^\n]*\blimit\s+(\d+)[^\n]*\n\s*"
             r"Sent \d+ bytes (\d+) pkt \(dropped (\d+)")
    m=re.search(pattern,text)
    assert m,("missing physically installed native netem counter",who,direction)
    limit,sent,dropped=map(int,m.groups())
    assert limit==10000,(who,direction,"netem capacity wrong",limit)
    assert dropped>0,(who,direction,"no real qdisc loss injected")
    return {"netem_limit_packets":limit,
            "actually_sent_underlay_packets":sent,
            "actually_dropped_underlay_packets":dropped,
            "observed_qdisc_drop_fraction":round(dropped/(sent+dropped),6),
            "includes_intended_random_loss_and_any_kernel_queue_overflow":True}


def fec_egress_windows(log,start_ns):
    """The existing 0.5s original RX diagnostic: no new product timer."""
    rows=[]
    for line in log.splitlines():
        if "V4_PUBLIC_FEC2_EGRESS_DIAG role=client side=rx " not in line:
            continue
        fields={}
        for name in ("ns","raw_batches","rx_err","fec_source","fec_parity",
                     "fec_recovered","tun_failure"):
            m=re.search(r"\b"+name+r"=(\d+)",line)
            assert m,(name,line)
            fields[name]=int(m.group(1))
        rows.append(fields)
    if not rows:return {"observed":False}
    # IMPORTANT: this product's Rust loop_now() is RELATIVE to its own
    # process-local Instant origin, NOT the absolute CLOCK_MONOTONIC ns
    # reported by Python traffic.py. H1263's first report falsely showed
    # zero rows in all nine windows despite 489 authentic 500ms samples.
    # Anchor approximately to the first nonzero authenticated FEC2 source
    # sample (true business began just before that sample), not to the
    # unrelated Python absolute start_ns. The 10s bins are diagnostic
    # approximately aligned, not exact sub-500ms latency evidence.
    _ = start_ns
    source_anchor=next((r["ns"] for r in rows if r["fec_source"]>0),None)
    assert source_anchor is not None,"no real original FEC2 source received"
    segments=[]
    for offset in range(90,180,10):
        entries=[r for r in rows
                 if source_anchor+offset*1_000_000_000 <=r["ns"]
                 < source_anchor+(offset+10)*1_000_000_000]
        diffs={}
        if len(entries)>=2:
            diffs={k:entries[-1][k]-entries[0][k] for k in
                   ("raw_batches","rx_err","fec_source","fec_parity",
                    "fec_recovered","tun_failure")}
            assert all(n>=0 for n in diffs.values()),"negative RX snapshots"
        segments.append({"window_s":[offset,offset+10],
                         "observations":len(entries),"counter_deltas":diffs})
    assert all(x["observations"]>=5 for x in segments),(
        "FEC2 500ms recovery windows not actually populated",segments)
    return {"observed":True,"sample_count":len(rows),
            "source_first_active_ns_process_relative":source_anchor,
            "time_alignment":"approx first positive FEC2 source; NOT Python absolute monotonic, not an exact packet timestamp",
            "recovery_10s_windows":segments,
            "scope":"client RX process original FEC2 data, not server shared TUN"}


def inspect(art,server_log):
    plan=read(art/"h1250-matrix-plan.json")
    assert plan["application_load_seconds"]==180
    assert plan["simultaneous_stress_seconds"]==170
    assert tuple(x["who"] for x in plan["clients"])==NAMES
    server_text=pathlib.Path(server_log).read_text(errors="replace")
    routes={}
    for line in server_text.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:continue
        addr=re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)",line).group(1)
        assert addr not in routes
        routes[addr]={}
        for name in ("offered","direct_delivered","downstream_full",
                     "pending_overflow","pending_peak_packets"):
            routes[addr][name]=int(re.search(r"\b"+name+r"=(\d+)",line).group(1))
        assert routes[addr]["pending_peak_packets"]<=8
    assert set(routes)=={x["lease"] for x in plan["clients"]}
    report={
        "schema_version":1,"result":"DIAGNOSTIC_COMPLETE",
        "source_sha":plan["source_sha"],
        "native_original_tls_data_plane":True,"same_start_ns":plan["start_monotonic_ns"],
        "real_business_seconds":180,"real_drained_seconds":10,
        "physical_tiers":["normal0","game2off5","normal_fixed6_30"],
        "phases_seconds":dict(PHASES),
        "per_authenticated_server_lease_shared_tun":routes,
        "server_game2_off_cosmetic":extract(server_text,
            "WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP",
            ("copied_appearance",)),
        "clients":{},"alerts":[],"limitations":[
          "Hosted x86_64 one-VM netns, not Windows/ARM or physical multi-host.",
          "This is short real behavior diagnostic, not a reproduction guarantee for an intermittent late 430s failure.",
          "Outer appearance copies preserve PN/SEQ/ciphertext, not new app delivery or FEC repair.",
        ],
    }
    starts=set()
    for spec in plan["clients"]:
        who=spec["who"]
        client=read(art/("h1250-c-"+who+".json"))
        server=read(art/("h1250-s-"+who+".json"))
        assert client["role"]=="client" and server["role"]=="server"
        assert client["start_ns"]==server["start_ns"]==plan["start_monotonic_ns"]
        assert client["end_ns"]-client["start_ns"]==180_000_000_000
        assert server["end_ns"]-server["start_ns"]==180_000_000_000
        assert not client["capacity_exceeded"] and not server["capacity_exceeded"]
        starts.add(client["start_ns"])
        log=(art/("h1250-product-"+who+".log")).read_text(errors="replace")
        peer={"config":spec,"directions":{},
              "server_owned_tun_lease":routes[spec["lease"]],
              "real_native_outer":{},"native_fec2_rx":{},
              "physical_qdisc":{}}
        for direction in ("uplink","downlink"):
            tx,rx=(client,server) if direction=="uplink" else (server,client)
            phases={}
            assert len(tx["stats"]["udp"])==len(rx["stats"]["udp"])==len(PHASES)
            for i,(name,sec) in enumerate(PHASES):
                sent=tx["stats"]["udp"][i]
                got=rx["stats"]["udp"][i]
                a,b=sent["tx_packets"],got["rx_packets"]
                phases[name]={
                    "duration_s":sec,"actual_sent_packets":a,
                    "real_unique_udp_received":b,
                    "delivery_fraction":round(b/a,6) if a else None,
                    "actual_sent_mbps":mbps(sent["tx_bytes"],sec),
                    "real_received_mbps":mbps(got["rx_bytes"],sec),
                    "sender_errors":sent["send_errors"],
                    "sender_backpressure":sent["backpressure"],
                    "delivered_only_oneway_p99_ms":got["latency"]["p99_ms"],
                }
                assert a>0 and b>0,(who,direction,name,"no original business")
                if b/a<.95:
                    report["alerts"].append({
                        "class":"LOW_UNIQUE_UDP_DELIVERY",
                        "who":who,"direction":direction,"phase":name,
                        "fraction":round(b/a,6)})
            peer["directions"][direction]=phases
            if spec["loss_pct"]:
                physical=qdisc(art,who,direction,spec["loss_pct"],
                               spec["oneway_delay_ms"])
                peer["physical_qdisc"][direction]=physical
                if physical["observed_qdisc_drop_fraction"]>spec["loss_pct"]/100+.05:
                    report["alerts"].append({"class":"QDISC_EXCESS_DROP","who":who,
                                             "direction":direction})
        if who=="carol":
            peer["real_native_outer"]["game2_off_policy"]=extract(log,
                "V4_PUBLIC_GAME_OUTER role=client lanes=2",
                ("repair_enabled","outer_data_retransmitted",
                 "blocked_duplicate","first_lane_copied"))
            peer["real_native_outer"]["same_original_frozen_ciphertext"]=extract(log,
                "WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP",("copied_appearance",))
            own=peer["real_native_outer"]
            assert own["game2_off_policy"]["repair_enabled"]==1
            assert own["game2_off_policy"]["outer_data_retransmitted"]>0,(
                "Game2 Off nominal outer ON is not actually replaying",own)
            assert own["same_original_frozen_ciphertext"]["copied_appearance"]>0
        else:
            peer["real_native_outer"]["normal_m2"]=extract(log,
                "V4_PUBLIC_M2_OUTER role=client",
                ("repair_enabled","first_wire_bytes",
                 "repair_accepted_wire_bytes"))
            normal=peer["real_native_outer"]["normal_m2"]
            assert normal["observed"] and normal["repair_enabled"]==1,(
                "Normal outer route disabled or unobserved",who)
            if who=="erin" and normal["repair_accepted_wire_bytes"]==0:
                report["alerts"].append({"class":"NORMAL_FIXED30_OUTER_ZERO_ACTUAL_REPAIR",
                                         "who":who})
        if who=="erin":
            peer["native_fec2_rx"]["live_half_second"]=fec_egress_windows(
                log,plan["start_monotonic_ns"])
            peer["native_fec2_rx"]["stop_capacity"]=extract(log,
                "V4_PUBLIC_FEC2_RX_CAP role=client",
                ("peak_active","age_evicted","reorder_evicted",
                 "invalid_retired","reject_invalid","reject_capacity",
                 "reject_codec"))
            peer["native_fec2_tx"]=extract(log,"V4_PUBLIC_FEC2_TX role=client",
                                         ("accepted","full","rplanned","rsent"))
            assert peer["native_fec2_rx"]["live_half_second"]["observed"],(
                "original periodic FEC2 RX source/parity/recovered diagnostics missing")
            if peer["directions"]["downlink"]["recovery"]["delivery_fraction"]<.95:
                report["alerts"].append({"class":"FIXED30_POST_OVERLOAD_DOWNLINK_DEFICIT",
                                         "fraction":peer["directions"]["downlink"]["recovery"]["delivery_fraction"]})
        report["clients"][who]=peer
    assert len(starts)==1
    assert report["server_game2_off_cosmetic"]["observed"] and (
        report["server_game2_off_cosmetic"]["copied_appearance"]>0),(
            "server Game2 Off appearance not actually sent")
    report["alert_count"]=len(report["alerts"])
    report["result"]="DIAGNOSTIC_COMPLETE_WITH_ALERTS" if report["alerts"] \
        else "DIAGNOSTIC_COMPLETE_NO_CONFIGURED_ALERTS"
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True)
    p.add_argument("--product-log",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    data=inspect(pathlib.Path(a.art),a.product_log)
    pathlib.Path(a.output).write_text(json.dumps(data,indent=2)+"\n")
    print("H1262_GAME2_OFF_REAL_OUTER_APPEARANCE client="+str(
        data["clients"]["carol"]["real_native_outer"])+" server="+str(
        data["server_game2_off_cosmetic"]),flush=True)
    print("H1262_FIXED30_RECOVERY "+json.dumps(
        data["clients"]["erin"]["directions"]["downlink"]["recovery"]),flush=True)
    print("M0_H1262_ORIGINAL_TLS_GAME2_OFF_OUTER_COSMETIC_AND_FEC2_30PCT_RX_DIAGNOSTIC_COMPLETE "
          +"alerts="+str(data["alert_count"])+" source="+data["source_sha"],flush=True)


if __name__=="__main__":
    main()
