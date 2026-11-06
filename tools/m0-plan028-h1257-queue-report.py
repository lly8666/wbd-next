#!/usr/bin/env python3
"""H1253 2-client native Game4 FEC6 / normal sibling, 90s each leg.

One actual original-Go TLS/Rust native product build with ISA-L linked; the
two short legs use only a cold process-level scalar/native choice. Report
real first application TX/RX and scalar/native RS calls from owned Rust Stop.
"""
import argparse
import json
import pathlib
import re


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def pct(n, d):
    return round(n/d, 6) if d else None


def mbps(n, seconds):
    return round(n * 8 / (seconds * 1e6), 4)


def fields(text, marker):
    matches=[x for x in text.splitlines() if marker in x]
    if not matches:
        return {"observed":False}
    out={"observed":True}
    for name,val in re.findall(r"([a-z_]+)=(\S+)",matches[-1].split(marker,1)[-1]):
        try:out[name]=int(val)
        except ValueError:out[name]=val
    return out


def phase_pair(tx,rx,index,duration):
    offered=tx["stats"]["udp"][index]
    received=rx["stats"]["udp"][index]
    tcp_offered=tx["stats"]["tcp"][index]
    tcp_received=rx["stats"]["tcp"][index]
    return {
        "duration_seconds":duration,
        "udp_tx_packets":offered["tx_packets"],
        "udp_rx_unique_packets":received["rx_packets"],
        "udp_delivery":pct(received["rx_packets"],offered["tx_packets"]),
        "udp_sent_mbps":mbps(offered["tx_bytes"],duration),
        "udp_delivered_mbps":mbps(received["rx_bytes"],duration),
        "udp_oneway_delivered_only_p99_ms":received["latency"]["p99_ms"],
        "generator_udp_p99_send_lag_ms":offered["send_lag"]["p99_ms"],
        "tcp_sent_mbps":mbps(tcp_offered["tx_bytes"],duration),
        "tcp_delivered_mbps":mbps(tcp_received["rx_bytes"],duration),
    }



def copy_abandon_reasons(log):
    marker="M0_GAME_M4_COPY_ABANDON_REASONS"
    lines=[line for line in log.splitlines() if marker in line]
    if not lines:
        return {"observed":False}
    line=lines[-1]
    out={"observed":True}
    names=("capacity_evicted","deadline_expired","dispatch_pressure",
           "admission_mtu_skipped","admission_queue_skipped","abandoned_total")
    for name in names:
        m=re.search(r"\b"+name+r"=\[([^\]]*)\]",line)
        assert m,(name,line)
        row=[int(x.strip()) for x in m.group(1).split(",")]
        assert len(row)==4,(name,row)
        out[name]=row
    stop=re.search(r"\bstop_canceled=(\d+)",line)
    assert stop,line
    out["stop_canceled"]=int(stop.group(1))
    expected=[sum(out[n][i] for n in names[:3]) for i in range(4)]
    assert expected==out["abandoned_total"],(expected,out)
    return out


def per_lease_shared_tun(log):
    out={}
    for line in log.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:continue
        ip=re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)",line)
        assert ip,line
        who=ip.group(1)
        assert who not in out,("duplicate lease diagnostic",who)
        data={"observed":True}
        names=("offered","direct_delivered","downstream_full",
               "pending_overflow","pending_byte_limit",
               "pending_peak_packets","pending_peak_bytes")
        for key in names:
            match=re.search(r"\b"+key+r"=(\d+)",line)
            assert match,(key,line)
            data[key]=int(match.group(1))
        assert data["direct_delivered"]<=data["offered"]
        assert data["pending_overflow"]<=data["offered"]
        assert data["pending_peak_packets"]<=8
        assert data["pending_peak_bytes"]<=65536
        out[who]=data
    return out


def physical_netem_dave(art):
    content=(art/"h1250-qdisc-after.txt").read_text()
    stats={}
    for direction in ("uplink","downlink"):
        match=re.search(r"== dave "+direction+r" loss=15% delay=100ms ==\s*"
          r"qdisc netem [^\n]*\blimit\s+(\d+)[^\n]*\n\s*"
          r"Sent \d+ bytes (\d+) pkt \(dropped (\d+)",content)
        assert match,("netem 15% 100ms not actually installed",direction,content[-1600:])
        limit,sent,drop=map(int,match.groups())
        assert limit==10000,("wrong native netem capacity",direction,limit)
        stats[direction]={"netem_limit_packets":limit,
                          "sent_underlay_packets":sent,
                          "dropped_underlay_packets":drop,
                          "observed_physical_loss_fraction":round(drop/(sent+drop),6)}
    return stats

def inspect(art,product_log):
    plan=load(art/"h1250-matrix-plan.json")
    assert len(plan["clients"])==2
    assert plan["application_load_seconds"]==90
    assert plan["simultaneous_stress_seconds"]==85
    choice=plan["backend_choice"]
    assert choice in ("scalar","native")
    observed={}
    for spec in plan["clients"]:
        who=spec["who"]
        client=load(art/f"h1250-c-{who}.json")
        server=load(art/f"h1250-s-{who}.json")
        assert client["start_ns"]==server["start_ns"]==plan["start_monotonic_ns"]
        assert client["end_ns"]-client["start_ns"]==90_000_000_000
        assert server["end_ns"]-server["start_ns"]==90_000_000_000
        assert not client["capacity_exceeded"] and not server["capacity_exceeded"]
        side={}
        for direction,tx,rx in (("uplink",client,server),("downlink",server,client)):
            rows={}
            for index,(name,seconds) in enumerate((("warmup",5),("sustained",40),
                                                     ("overload",20),("recovery",25))):
                rows[name]=phase_pair(tx,rx,index,seconds)
            assert all(rows[name]["udp_tx_packets"]>0 for name in rows)
            assert all(rows[name]["udp_rx_unique_packets"]>0 for name in rows)
            side[direction]=rows
        log=(art/f"h1250-product-{who}.log").read_text(errors="replace")
        observed[who]={
            "mode":spec["mode"],"network_loss_pct":spec["loss_pct"],
            "directions":side,
            "shared_tun_stop":fields(log,"V4_PUBLIC_SHARED_TUN_STOP"),
            "backend":fields(log,"M0_GAME_M4_FEC_BACKEND_READBACK"),
            "tx_duration":fields(log,"M0_GAME_M4_TX_DURATION_SAMPLE"),
            "rx_lock_sample":fields(log,"M0_GAME_M4_RX_LOCK_SAMPLE"),
            "tx_reject":fields(log,"M0_GAME_M4_TX_REJECT_BREAKDOWN"),
            "rx_stage":fields(log,"M0_GAME_M4_RX_STAGE_BOUNDARY"),
            "copy_abandon":copy_abandon_reasons(log),
            "game4_shared_tun_burst":fields(log,"M0_GAME_M4_SHARED_TUN_BURST_READBACK"),
        }
    # Genuine Game4 stopped with at least a parity-codec call. Native
    # qualification must have real ISA-L calls, scalar an actual zero-native.
    game=observed["dave"]["backend"]
    assert game["observed"] and game["native_linked"]==1,game
    if choice=="native":
        assert game["tx_native_quanta"]>0,game
        # PreferNative deliberately retains scalar for k<=1/small symbols;
        # observed fallback is a genuine backend result, not a failure.
    else:
        assert game["tx_native_quanta"]==0 and game["tx_scalar_quanta"]>0,game
    assert observed["dave"]["tx_duration"]["observed"],"Game4 TX timing absent"
    assert observed["dave"]["rx_lock_sample"]["observed"],"Game4 RX lock timing absent"
    assert observed["dave"]["copy_abandon"]["observed"],"Game4 copy abandon causes not observed"
    assert observed["dave"]["game4_shared_tun_burst"]["observed"],"Game4 bounded TUN burst proof missing"
    assert observed["dave"]["game4_shared_tun_burst"]["max_new_sources_per_turn"]==4
    assert observed["dave"]["game4_shared_tun_burst"]["extra_accepted"]>0, (
        "no additional original Game4 TUN sources consumed")
    server_log=pathlib.Path(product_log).read_text(errors="replace")
    routes=per_lease_shared_tun(server_log)
    expected={spec["lease"] for spec in plan["clients"]}
    assert set(routes)==expected,("missing actual per-lease bounded TUN readback",
                                  expected,routes)
    netem=physical_netem_dave(art)
    alerts=[]
    for spec in plan["clients"]:
        route=routes[spec["lease"]]
        if route["pending_overflow"]>0:
            alerts.append({"class":"PER_LEASE_TUN_OVERFLOW","client":spec["who"],
                           "pending_overflow":route["pending_overflow"]})
    game4_abandoned=observed["dave"]["copy_abandon"]
    if sum(game4_abandoned["capacity_evicted"])>0:
        alerts.append({"class":"GAME4_CAPACITY_EVICTION",
                       "events":sum(game4_abandoned["capacity_evicted"])})
    if sum(game4_abandoned["deadline_expired"])>0:
        alerts.append({"class":"GAME4_MISSED_COPY_DEADLINE",
                       "events":sum(game4_abandoned["deadline_expired"])})
    for direction,data in netem.items():
        if data["observed_physical_loss_fraction"]>.26:
            alerts.append({"class":"PHYSICAL_QDISC_EXCESS_DROP",
                           "direction":direction,"loss_fraction":data["observed_physical_loss_fraction"]})
    return {
        "result":"H1257_SCOPED_90S_AB_PER_LEASE_QUEUE_DIAGNOSTIC_COMPLETE",
        "source_sha":plan["source_sha"],
        "backend_choice":choice,
        "same_product_binary_isa_l_linked":True,
        "synchronized_two_clients":True,
        "real_load_seconds":90,"real_stress_seconds":85,
        "phases_seconds":{"warmup":5,"sustained":40,"overload":20,"recovery":25},
        "clients":observed,
        "per_authenticated_server_lease_shared_tun":routes,
        "server_shared_tun_stop":fields(server_log,"V4_PUBLIC_SHARED_TUN_STOP generation="),
        "actual_dave_physical_netem":netem,
        "diagnostic_alerts":alerts,
        "diagnostic_alert_count":len(alerts),
        "server_copy_abandon":copy_abandon_reasons(server_log),
        "server_game4_shared_tun_burst":fields(server_log,
            "M0_GAME_M4_SHARED_TUN_BURST_READBACK"),
        "server_fec_backend":fields(server_log,"M0_GAME_M4_FEC_BACKEND_READBACK"),
        "scope_limit":"Single native hosted x86 VM, two independently authenticated original TLS Go/Rust clients, genuine native netem/UDP and per-lease bounded shared TUN. Alerts diagnose pressure rather than test infrastructure failure; AB is not CPU causality or global throughput PASS.",
    }


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--art",required=True)
    a.add_argument("--product-log",required=True)
    a.add_argument("--output",required=True)
    q=a.parse_args()
    data=inspect(pathlib.Path(q.art),q.product_log)
    pathlib.Path(q.output).write_text(json.dumps(data,indent=2)+"\n")
    who=data["clients"]["dave"]
    for direction,row in who["directions"].items():
        print(f"H1257_{data['backend_choice'].upper()}_GAME4_{direction.upper()} "
              f"sustained={row['sustained']['udp_delivered_mbps']}Mbps "
              f"overload={row['overload']['udp_delivered_mbps']}Mbps "
              f"recovery={row['recovery']['udp_delivered_mbps']}Mbps",flush=True)
    print("M0_H1257_GAME4_SCALAR_OR_NATIVE_REAL_BACKEND_AND_PER_LEASE_QUEUE_READBACK_PASS "
          +data["backend_choice"],flush=True)


if __name__=="__main__":
    main()
