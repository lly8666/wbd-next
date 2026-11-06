#!/usr/bin/env python3
"""H1267 original Go TLS/Rust RAW M4 cold socket A/B diagnostic.

Uses real application and typed native M4 sendmmsg backpressure, not
cosmetic retransmission/outer first-send bytes as delivery success.
"""
import argparse
import json
import pathlib
import re

PHASES=(("warmup",10),("sustained",30),("overload",35),("recovery",45))


def load(p):
    return json.loads(p.read_text())


def parsed_marker(log, marker, fields):
    rows=[line for line in log.splitlines() if marker in line]
    assert rows,("missing actual original native marker",marker)
    out={"observed":True}
    line=rows[-1]
    for key in fields:
        m=re.search(r"\b"+key+r"=([^\s]+)",line)
        assert m,(key,line)
        try:out[key]=int(m.group(1))
        except ValueError:out[key]=m.group(1)
    return out


def qdisc(art,who,direction,pct,delay):
    content=(art/"h1250-qdisc-after.txt").read_text()
    match=re.search(
        r"== "+who+r" "+direction+r" loss="+str(pct)+r"% delay="+str(delay)+
        r"ms ==\s*qdisc netem [^\n]*\blimit\s+(\d+)[^\n]*\n\s*"
        r"Sent \d+ bytes (\d+) pkt \(dropped (\d+)",content)
    assert match,("missing original physical loss measurement",who,direction)
    limit,sent,dropped=map(int,match.groups())
    assert limit==10000 and dropped>0,(who,direction,limit,dropped)
    fraction=dropped/(sent+dropped)
    assert abs(fraction-pct/100)<.055,(who,direction,fraction)
    return {"netem_qdisc_limit":limit,"sent_underlay_packets":sent,
            "dropped_underlay_packets":dropped,
            "observed_total_qdisc_drop_fraction":round(fraction,6)}


def tx_m4_windows(log):
    rows=[]
    for line in log.splitlines():
        if "V4_PUBLIC_FEC2_EGRESS_DIAG role=client side=tx " not in line:
            continue
        found={}
        for key in ("ns","source_queued","m4_copied","m4_errors",
                    "m4_uncertain","backpressure"):
            m=re.search(r"\b"+key+r"=(\d+)",line)
            assert m,(key,line)
            found[key]=int(m.group(1))
        rows.append(found)
    stall=0
    best=None
    active=None
    for a,b in zip(rows,rows[1:]):
        condition=(b["m4_copied"]==a["m4_copied"] and
                   b["source_queued"]>a["source_queued"] and
                   b["backpressure"]>a["backpressure"])
        if condition:
            if active is None:active=a
            span=b["ns"]-active["ns"]
            if span>stall:
                stall=span
                best={"start_ns":active["ns"],"end_ns":b["ns"],
                      "duration_seconds":round(span/1e9,4),
                      "new_fec_sources":b["source_queued"]-active["source_queued"],
                      "backpressure_events":b["backpressure"]-active["backpressure"],
                      "zero_new_kernel_copied_packets":True}
        else:
            active=None
    return {"observed":bool(rows),"sample_count":len(rows),
            "max_contiguous_no_kernel_copy_while_new_FEC_source_and_EAGAIN":best,
            "max_duration_seconds":round(stall/1e9,4),
            "final":rows[-1] if rows else None}


def inspect(art,server_log):
    plan=load(art/"h1250-matrix-plan.json")
    assert plan["application_load_seconds"]==120
    assert plan["simultaneous_stress_seconds"]==110
    assert [x["who"] for x in plan["clients"]]==["alice","erin"]
    mode=plan["cold_socket_ab_mode"]
    assert mode in ("default","1048576")
    server_text=server_log.read_text(errors="replace")
    result={"schema_version":1,"source_sha":plan["source_sha"],
            "status":"SCOPED_NATIVE_FIXED30_120S_SOCKET_AB_DIAGNOSTIC_COMPLETE",
            "mode":mode,"phases_seconds":dict(PHASES),
            "application_seconds":120,"drain_seconds":10,"clients":{},
            "server_socket_open":parsed_marker(
                server_text,"V4_PUBLIC_RAW_TX_SOCKET_OPEN role=server",
                ("requested_bytes","effective_bytes","poll_writable","poll_error","outq_bytes")),
            "server_socket_stop":parsed_marker(
                server_text,"V4_PUBLIC_RAW_TX_SOCKET_STOP role=server",
                ("effective_bytes","eagain_turns","sampled","poll_writable",
                 "poll_not_writable","outq_supported","outq_high_water",
                 "snapshot_errors","no_reseal_or_retry")),
            "limitations":[
                "One native hosted x86 VM, two original TLS-authenticated clients and 30pct loss with 125ms netem, not all platforms.",
                "Physical tc qdisc drops contain configured random loss and any kernel qdisc overflow.",
                "POLLOUT is readiness at the sampled instant, not proof of a successful sendmmsg.",
                "No application/retransmission/FEC delivery credit for a frozen cosmetic repeat.",
                "Cold SO_SNDBUF might be clamped by wmem_max; only effective getsockopt values decide whether the experimental leg changed capacity.",
                "A single sequential same-VM AB cannot establish strict causal throughput or intermittent stall absence."
            ],"alerts":[]}
    routes={}
    for line in server_text.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:continue
        m=re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)",line)
        assert m,line
        ip=m.group(1)
        assert ip not in routes
        for key in ("offered","direct_delivered","pending_overflow"):
            n=re.search(r"\b"+key+r"=(\d+)",line)
            assert n,(ip,key,line)
            routes.setdefault(ip,{})[key]=int(n.group(1))
    assert set(routes)=={x["lease"] for x in plan["clients"]}
    result["server_per_authenticated_lease_tun"]=routes
    for spec in plan["clients"]:
        who=spec["who"]
        own=(art/("h1250-product-"+who+".log")).read_text(errors="replace")
        client=load(art/("h1250-c-"+who+".json"))
        server=load(art/("h1250-s-"+who+".json"))
        for p in (client,server):
            assert p["start_ns"]==plan["start_monotonic_ns"]
            assert p["end_ns"]-p["start_ns"]==120_000_000_000
            assert not p["capacity_exceeded"] and not p["errors"]
        peer={"config":spec,"directions":{},"tc_actual":{},
              "server_tun_route":routes[spec["lease"]],
              "socket_open":parsed_marker(own,"V4_PUBLIC_RAW_TX_SOCKET_OPEN role=client",
                ("requested_bytes","effective_bytes","poll_writable","poll_error","outq_bytes")),
              "socket_stop":parsed_marker(own,"V4_PUBLIC_RAW_TX_SOCKET_STOP role=client",
                ("effective_bytes","eagain_turns","sampled","poll_writable",
                 "poll_not_writable","outq_supported","outq_high_water",
                 "snapshot_errors","no_reseal_or_retry"))}
        assert peer["socket_stop"]["no_reseal_or_retry"]==1
        assert peer["socket_open"]["requested_bytes"]==(0 if mode=="default" else 1048576)
        if who=="erin":peer["original_m4_half_second"]=tx_m4_windows(own)
        for direction in ("uplink","downlink"):
            tx,rx=(client,server) if direction=="uplink" else (server,client)
            parts={}
            for i,(phase,secs) in enumerate(PHASES):
                sent=tx["stats"]["udp"][i]
                recv=rx["stats"]["udp"][i]
                count,got=sent["tx_packets"],recv["rx_packets"]
                assert count>0 and got>0
                parts[phase]={
                    "actual_sent_packets":count,
                    "actual_unique_udp_received":got,
                    "unique_delivery_fraction":round(got/count,6),
                    "actual_sent_mbps":round(sent["tx_bytes"]*8/(secs*1e6),5),
                    "actual_received_mbps":round(recv["rx_bytes"]*8/(secs*1e6),5),
                    "delivered_only_p99_ms":recv["latency"]["p99_ms"]
                }
                if got/count<.95:
                    result["alerts"].append({"who":who,"direction":direction,
                        "phase":phase,"class":"LOW_UNIQUE_UDP_DELIVERY",
                        "observed_unique_fraction":round(got/count,6)})
            peer["directions"][direction]=parts
            if spec["loss_pct"]:
                peer["tc_actual"][direction]=qdisc(
                    art,who,direction,spec["loss_pct"],spec["oneway_delay_ms"])
        result["clients"][who]=peer
    for who in ("alice","erin"):
        if result["clients"][who]["server_tun_route"]["pending_overflow"]>0:
            result["alerts"].append({"who":who,"class":"SHARED_TUN_PENDING_OVERFLOW"})
    if result["clients"]["erin"]["socket_stop"]["eagain_turns"]>0:
        result["alerts"].append({"who":"erin","class":"ORIGINAL_M4_SENDMMSG_BACKPRESSURE",
                                 "events":result["clients"]["erin"]["socket_stop"]["eagain_turns"]})
    result["alert_count"]=len(result["alerts"])
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--art",required=True)
    ap.add_argument("--product-log",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    r=inspect(pathlib.Path(args.art),pathlib.Path(args.product_log))
    pathlib.Path(args.output).write_text(json.dumps(r,indent=2)+"\n")
    fixed=r["clients"]["erin"]
    print("H1267_REAL_ORIGINAL_FIXED30_SOCKET_DIAGNOSTIC mode="+r["mode"]
          +" opened="+str(fixed["socket_open"])
          +" stop="+str(fixed["socket_stop"])
          +" tx_0p5s="+str(fixed.get("original_m4_half_second")),flush=True)
    print("M0_H1267_ORIGINAL_FIXED30_RAW_SOCKET_COLD_AB_SCOPED_DIAGNOSTIC_COMPLETE "
          +r["mode"]+" alerts="+str(r["alert_count"]),flush=True)


if __name__=="__main__":
    main()
