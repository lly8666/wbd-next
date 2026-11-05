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
        }
    # Genuine Game4 stopped with at least a parity-codec call. Native
    # qualification must have real ISA-L calls, scalar an actual zero-native.
    game=observed["dave"]["backend"]
    assert game["observed"] and game["native_linked"]==1,game
    if choice=="native":
        assert game["tx_native_quanta"]>0 and game["tx_scalar_quanta"]==0,game
    else:
        assert game["tx_native_quanta"]==0 and game["tx_scalar_quanta"]>0,game
    assert observed["dave"]["tx_duration"]["observed"],"Game4 TX timing absent"
    assert observed["dave"]["rx_lock_sample"]["observed"],"Game4 RX lock timing absent"
    return {
        "result":"SCOPED_90S_AB_LEG_DIAGNOSTIC_COMPLETE",
        "source_sha":plan["source_sha"],
        "backend_choice":choice,
        "same_product_binary_isa_l_linked":True,
        "synchronized_two_clients":True,
        "real_load_seconds":90,"real_stress_seconds":85,
        "phases_seconds":{"warmup":5,"sustained":40,"overload":20,"recovery":25},
        "clients":observed,
        "server_fec_backend":fields(pathlib.Path(product_log).read_text(errors="replace"),
                                    "M0_GAME_M4_FEC_BACKEND_READBACK"),
        "scope_limit":"Single hosted x86 native netns; per-process STOP readback actual GF calls, 1/128 TX/RX sampling, performance AB confounded by sequential host CPU variability",
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
        print(f"H1253_{data['backend_choice'].upper()}_GAME4_{direction.upper()} "
              f"sustained={row['sustained']['udp_delivered_mbps']}Mbps "
              f"overload={row['overload']['udp_delivered_mbps']}Mbps "
              f"recovery={row['recovery']['udp_delivered_mbps']}Mbps",flush=True)
    print("M0_H1253_GAME4_SCALAR_OR_NATIVE_REAL_BACKEND_READBACK_PASS "
          +data["backend_choice"],flush=True)


if __name__=="__main__":
    main()
