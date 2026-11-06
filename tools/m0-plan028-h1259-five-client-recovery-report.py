#!/usr/bin/env python3
"""H1259 exact-SOURCE five-client 430s recovery-after-overload diagnosis.

The product's actual inner application TX is the denominator, not the
configured offered rate. Intentional physical netem loss is independently
counted and never reported as the product's own measured drop fraction.
"""
import argparse
import json
import math
import pathlib
import re
import statistics


PHASES = (
    ("warmup", 10, .3), ("first_wave", 60, .6),
    ("sustained", 240, 1.0), ("overload", 60, 1.3),
    ("recovery", 60, 1.0),
)


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def mbps(byte_count, seconds):
    return round(8 * byte_count / seconds / 1e6, 4)


def first_nonzero(bins):
    return next((i * 10 for i, n in enumerate(bins) if n), None)


def windows(src, dst, start_s, seconds=240, step=30):
    """30s bins of actual application offered/delivered bytes, same clock."""
    rows = []
    for offset in range(start_s, start_s + seconds, step):
        a, b = offset * 100, (offset + step) * 100
        tx = sum(src[a:b])
        rx = sum(dst[a:b])
        rows.append({
            "window_s": [offset, offset + step],
            "actual_offered_mbps": mbps(tx, step),
            "delivered_mbps": mbps(rx, step),
            "delivery_ratio": round(rx / tx, 5) if tx else None,
        })
    return rows


def netem_counters(path):
    output = pathlib.Path(path).read_text()
    blocks = re.split(r"(?m)^== (.+?) (uplink|downlink)(?:.*?) ==$", output)
    found = {}
    for i in range(1, len(blocks), 3):
        who, direction, content = blocks[i:i+3]
        line = re.search(r"Sent\s+\d+\s+bytes\s+(\d+)\s+pkt\s+\(dropped\s+(\d+)", content)
        limit = re.search(r"qdisc netem .*?\blimit\s+(\d+)", content)
        if line:
            sent, dropped = map(int, line.groups())
            found.setdefault(who, {})[direction] = {
                "sent_underlay_packets": sent,
                "dropped_underlay_packets": dropped,
                "observed_underlay_drop_fraction": round(
                    dropped / (sent + dropped), 6) if (sent + dropped) else None,
                "netem_qdisc_limit_packets": int(limit.group(1)) if limit else None,
                "drop_counter_includes_random_loss_and_queue_overflow": True,
            }
        else:
            found.setdefault(who, {})[direction] = None
    return found


def product_counters(server_log):
    text = pathlib.Path(server_log).read_text(errors="replace")
    lines = [x for x in text.splitlines()
             if "V4_PUBLIC_SHARED_TUN_STOP generation=" in x]
    if not lines:
        return {"status": "NOT_OBSERVED"}
    line = lines[-1]
    counters = {}
    for key in ("generation", "routed", "unrouted", "backpressure",
                "queue_full_drops", "queue_byte_drops", "queue_age_drops",
                "retired_drops"):
        m = re.search(r"\b" + key + r"=(\d+)", line)
        counters[key] = int(m.group(1)) if m else None
    return {"status": "OBSERVED", **counters,
            "scope": "server process shared TUN, aggregated across all 5 clients"}



def parse_lease_queue(log_path):
    text=pathlib.Path(log_path).read_text(errors="replace")
    out={}
    for line in text.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:
            continue
        ip=re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)",line)
        assert ip,line
        addr=ip.group(1)
        assert addr not in out,("duplicate authenticated lease diagnostic",addr)
        stats={}
        for key in ("offered","direct_delivered","downstream_full",
                    "pending_overflow","pending_byte_limit",
                    "pending_peak_packets","pending_peak_bytes"):
            value=re.search(r"\b"+key+r"=(\d+)",line)
            assert value,(key,line)
            stats[key]=int(value.group(1))
        assert stats["pending_peak_packets"]<=8
        assert stats["pending_peak_bytes"]<=65536
        out[addr]=stats
    return out


def game_m4_burst_and_fec(log_path):
    text=pathlib.Path(log_path).read_text(errors="replace")
    out={}
    for key,marker,fields in (
        ("bounded_game4_tun_ingress","M0_GAME_M4_SHARED_TUN_BURST_READBACK",
            ("extra_accepted","max_new_sources_per_turn")),
        ("actual_fec_backend","M0_GAME_M4_FEC_BACKEND_READBACK",
            ("native_linked","tx_native_quanta","tx_scalar_quanta",
             "rx_native_decodes","rx_scalar_decodes","late_complete_repair_skips")),
    ):
        matched=[line for line in text.splitlines() if marker in line]
        if not matched:
            out[key]={"observed":False}
            continue
        last=matched[-1]
        payload={"observed":True}
        for field in fields:
            m=re.search(r"\b"+field+r"=(\d+)",last)
            assert m,(field,last)
            payload[field]=int(m.group(1))
        out[key]=payload
    return out

def analyze(art, product_log):
    plan = read(art / "h1250-matrix-plan.json")
    assert plan["application_load_seconds"] == 430
    assert plan["simultaneous_stress_seconds"] == 420
    assert len(plan["clients"]) == 5
    net_after = netem_counters(art / "h1250-qdisc-after.txt")
    net_before = netem_counters(art / "h1250-qdisc-before.txt")
    cpu = read(art / "h1250-cpu-rss.json")
    result = {
        "schema_version": 1, "source_sha": plan["source_sha"],
        "test_id": "M0-H1259-X86-5CLIENT-HETEROGENEOUS-430S-OVERLOAD-RECOVERY",
        "result": "DIAGNOSTIC_COMPLETE",
        "qualification": "NATIVE_ORIGINAL_GO_TLS_RUST_TUN_PERFORMANCE_OBSERVATION_ONLY",
        "network_scope": plan["network_scope"], "server_port": 443,
        "shared_server_tun": "one true native original Rust TUN reader",
        "start_monotonic_ns": plan["start_monotonic_ns"],
        "stress_duration_seconds": plan["simultaneous_stress_seconds"],
        "total_application_load_seconds": plan["application_load_seconds"],
        "phase_seconds": {n: sec for n, sec, _ in PHASES},
        "method": {
            "business": "10 same-monotonic-start native TUN application workers, 5 bidirectional real UDP and 2 TCP pairs",
            "offered_denominator": "real successful application sends, not configured Mbps",
            "generator_quality": "actual sent vs target + send lag/backpressure, separate from tunnel delivery",
            "loss": "tc physical underlay qdisc both egress directions, per peer; kernel counters readback",
            "latency": "same-runner monotonic embedded send timestamps, one-way delivered-only p99; 2Hz sparse probes",
            "no_application_retries": True,
            "tcp_note": "TCP sizes are application framed records, not independent IP packets; TCP loss recovery is by stack",
            "cpu": "low-frequency /proc process CPU ticks and peak RSS, no causal A/B baseline",
            "limits": "hosted x86_64 virtualized netns, not external line-speed or Windows/ARM physical capacity",
        },
        "clients": {}, "alerts": [], "aggregate": {},
        "server_shared_tun_per_authenticated_lease": parse_lease_queue(product_log),
        "server_game4_live_backend_and_burst": game_m4_burst_and_fec(product_log),
        "tc_netem_before": net_before, "tc_netem_after": net_after,
        "shared_tun": product_counters(product_log),
        "process_cpu_rss": cpu,
        "netem_qdisc_limit_intent": plan.get("netem_qdisc_limit_packets", "UNSPECIFIED"),
    }
    all_starts = set()
    agg = {phase: {"actual_tx_bytes": 0, "delivered_rx_bytes": 0,
                   "observed_udp_tx_packets": 0, "observed_udp_rx_packets": 0}
           for phase, _, _ in PHASES}
    for spec in plan["clients"]:
        who = spec["who"]
        client = read(art / ("h1250-c-" + who + ".json"))
        server = read(art / ("h1250-s-" + who + ".json"))
        assert client["role"] == "client" and server["role"] == "server", who
        assert client["start_ns"] == server["start_ns"] == plan["start_monotonic_ns"], who
        assert client["end_ns"] - client["start_ns"] == 430_000_000_000
        assert server["end_ns"] - server["start_ns"] == 430_000_000_000
        assert not client["capacity_exceeded"] and not server["capacity_exceeded"], who
        all_starts.add(client["start_ns"])
        for direction in ("uplink", "downlink"):
            if direction == "uplink":
                tx, rx = client, server
            else:
                tx, rx = server, client
            assert len(tx["stats"]["udp"]) == len(rx["stats"]["udp"]) == len(PHASES)
        client_log = art / ("h1250-product-" + who + ".log")
        client_owner = (product_counters(client_log) if client_log.exists()
                        else {"status": "NOT_OBSERVED"})
        peer = {"config": spec, "directions": {}, "generator_errors": {},
                "tc_egress_counters": net_after.get(who, {}),
                "client_shared_tun": client_owner,
                "game4_backend_and_burst": game_m4_burst_and_fec(client_log),
                "cpu": {key: cpu.get(key) for key in (
                    who, "s-" + who, "c-" + who)}}
        if client_owner.get("queue_full_drops", 0) > 0:
            result["alerts"].append({
                "client": who, "class": "CLIENT_SHARED_TUN_QUEUE_OVERFLOW",
                "queue_full_drops": client_owner["queue_full_drops"],
                "note": "Direct product drop counter; cannot equate this to lost application UDP or a configured tc loss fraction.",
            })
        for side, data in (("client", client), ("server", server)):
            peer["generator_errors"][side] = {
                "errors": data["errors"], "socket_drops": data["socket_drops"],
                "effective_buffers": data["effective_buffers"],
                "tcp_pending_at_deadline": data["tcp_pending_at_deadline"],
            }
        for direction in ("uplink", "downlink"):
            tx, rx = (client, server) if direction == "uplink" else (server, client)
            phases = []
            for index, (name, seconds, scale) in enumerate(PHASES):
                stats = {}
                for proto in ("udp", "tcp"):
                    sent = tx["stats"][proto][index]
                    received = rx["stats"][proto][index]
                    actual = sent["tx_packets"]
                    delivered = received["rx_packets"]
                    target = spec["c2s_target_mbps" if direction == "uplink"
                                  else "s2c_target_mbps"]
                    share = spec["udp_share"] if proto == "udp" else 1-spec["udp_share"]
                    requested = target * share * scale
                    sent_rate = mbps(sent["tx_bytes"], seconds)
                    rx_rate = mbps(received["rx_bytes"], seconds)
                    stats[proto] = {
                        "scheduled": sent["scheduled"],
                        "actual_sent_packets": actual,
                        "received_unique_packets": delivered,
                        "observed_missing_packets": max(0, actual - delivered),
                        "observed_delivery_fraction": (
                            round(delivered / actual, 6) if actual else None),
                        "target_mbps": round(requested, 3),
                        "actual_sent_mbps": sent_rate,
                        "received_mbps": rx_rate,
                        "generator_target_fraction": (
                            round(sent_rate/requested, 4) if requested else None),
                        "sender_errors": sent["send_errors"],
                        "emsgsize": sent["emsgsize"],
                        "sender_backpressure": sent["backpressure"],
                        "sender_lag_p99_ms": sent["send_lag"]["p99_ms"],
                        "delivered_only_oneway_p99_ms": received["latency"]["p99_ms"],
                        "delivered_only_oneway_max_ms": received["latency"]["max_ms"],
                        "received_duplicate_packets": received["duplicates"],
                        "received_invalid_packets": received["invalid"],
                    }
                    agg[name]["actual_tx_bytes"] += sent["tx_bytes"]
                    agg[name]["delivered_rx_bytes"] += received["rx_bytes"]
                    if proto == "udp":
                        agg[name]["observed_udp_tx_packets"] += actual
                        agg[name]["observed_udp_rx_packets"] += delivered
                    if requested and sent_rate < requested * .7:
                        result["alerts"].append({
                            "client": who, "direction": direction, "phase": name,
                            "protocol": proto, "class": "OFFERED_RATE_NOT_ACHIEVED",
                            "note": "Generator or transport backpressure; not proof of product packet loss.",
                            "actual_mbps": sent_rate, "target_mbps": requested,
                        })
                    if proto == "udp" and actual and delivered < .90 * actual:
                        result["alerts"].append({
                            "client": who, "direction": direction, "phase": name,
                            "protocol": proto, "class": "LOW_DELIVERED_FRACTION",
                            "note": "Includes intentional qdisc loss and possible path/CPU/queue loss; inspect tc and per-process stats.",
                            "fraction": round(delivered/actual, 5),
                        })
                phases.append({"name": name, "duration_seconds": seconds, "protocols": stats})
            sent_bytes = tx["tx_bytes_bins_10ms"]["udp"]
            got_bytes = rx["rx_bytes_bins_10ms"]["udp"]
            assert len(sent_bytes) == len(got_bytes), who
            sustained_windows = windows(sent_bytes, got_bytes, 70)
            if any(w["actual_offered_mbps"] >= 1 and w["delivered_mbps"] < .25
                   for w in sustained_windows):
                result["alerts"].append({
                    "client": who, "direction": direction,
                    "phase": "sustained", "class": "SUSTAINED_30S_DELIVERY_STALL",
                    "note": "True 30s zero/near-zero business receive while sender still offered.",
                })
            peer["directions"][direction] = {
                "phases": phases,
                "first_UDP_send_offset_ms": first_nonzero(
                    tx["tx_bins_10ms"]["udp"]),
                "first_UDP_receive_offset_ms": first_nonzero(
                    rx["rx_bins_10ms"]["udp"]),
                "sustained_30s_windows": sustained_windows,
                "sender_probe_rtt_p99_ms": [
                    tx["stats"]["udp"][i]["rtt"]["p99_ms"]
                    for i in range(len(PHASES))],
            }
            # Fundamental diagnostic: observe at least some business in every
            # phase/direction. An under-load stall is not a made-up success.
            for ph in phases:
                u = ph["protocols"]["udp"]
                if not u["actual_sent_packets"] or not u["received_unique_packets"]:
                    result["alerts"].append({
                        "client": who, "direction": direction,
                        "phase": ph["name"], "class": "NO_UDP_BUSINESS_PROGRESS"})
        # Application UDP after overloading must recover when back at
        # the SAME 1.0x steady input rate; flag failure without rewriting
        # the completed diagnostics as an Actions infrastructure failure.
        if spec["loss_pct"]<=15:
            for direction in ("uplink","downlink"):
                recovery=next(p for p in peer["directions"][direction]["phases"]
                              if p["name"]=="recovery")["protocols"]["udp"]
                if recovery["observed_delivery_fraction"] is not None and (
                    recovery["observed_delivery_fraction"] < .95):
                    result["alerts"].append({
                        "client":who,"direction":direction,"phase":"recovery",
                        "class":"POST_OVERLOAD_RECOVERY_DELIVERY_UNDER_95PCT",
                        "observed_fraction":recovery["observed_delivery_fraction"],
                        "note":"Recovered application delivery at sustained 1.0x input rate; not a synthetic retransmission.",
                    })
        for direction in ("uplink", "downlink"):
            if spec["loss_pct"]:
                counter = net_after.get(who, {}).get(direction)
                assert isinstance(counter, dict) and counter["dropped_underlay_packets"] > 0, (
                    who, direction, "physical netem loss not actually observed", net_after)
                if plan.get("netem_qdisc_limit_packets"):
                    assert counter["netem_qdisc_limit_packets"] == plan["netem_qdisc_limit_packets"], (
                        who, direction, "wrong installed netem queue limit", counter)
                fraction = counter["observed_underlay_drop_fraction"]
                if fraction is not None and fraction > (spec["loss_pct"] / 100) * 1.4 + .03:
                    result["alerts"].append({
                        "client": who, "direction": direction,
                        "class": "PHYSICAL_QDISC_DROPS_EXCEED_RANDOM_LOSS",
                        "observed_underlay_drop_fraction": fraction,
                        "configured_random_loss_pct": spec["loss_pct"],
                        "note": "tc dropped includes random loss plus kernel qdisc capacity overflow; cannot attribute excess to Rust.",
                    })
        result["clients"][who] = peer
    assert len(all_starts) == 1, "non-synchronous business start"
    all_leases={spec["lease"] for spec in plan["clients"]}
    per_lease=result["server_shared_tun_per_authenticated_lease"]
    assert set(per_lease)==all_leases, (
        "five original authenticated /32 lease queue receipts missing",all_leases,per_lease)
    for who,peer in result["clients"].items():
        lease=peer["config"]["lease"]
        own=per_lease[lease]
        peer["server_per_lease_tun_queue"]=own
        if own["pending_overflow"]>0:
            result["alerts"].append({
                "client":who,"class":"SERVER_LEASE_TUN_QUEUE_OVERFLOW",
                "pending_overflow":own["pending_overflow"]})
    game=result["clients"]["dave"]["game4_backend_and_burst"]
    assert game["actual_fec_backend"]["observed"],"Game4 original TLS FEC backend Stop missing"
    assert game["actual_fec_backend"]["native_linked"]==1
    assert game["actual_fec_backend"]["tx_native_quanta"]>0
    assert game["bounded_game4_tun_ingress"]["observed"],"bounded ingress Stop missing"
    assert game["bounded_game4_tun_ingress"]["max_new_sources_per_turn"]==4
    assert game["bounded_game4_tun_ingress"]["extra_accepted"]>0
    for name, seconds, _ in PHASES:
        vals = agg[name]
        vals["actual_sent_mbps_both_directions"] = mbps(vals["actual_tx_bytes"], seconds)
        vals["delivered_mbps_both_directions"] = mbps(vals["delivered_rx_bytes"], seconds)
        vals["observed_UDP_delivery_fraction"] = round(
            vals["observed_udp_rx_packets"] / vals["observed_udp_tx_packets"], 6)
        vals["loss_interpretation"] = "INCLUDES_REAL_TC_INJECTION;_NOT_CAUSAL_PRODUCT_LOSS"
    result["aggregate"] = agg
    if result["shared_tun"].get("queue_full_drops", 0) > 0:
        result["alerts"].append({
            "class": "SERVER_SHARED_TUN_QUEUE_OVERFLOW",
            "queue_full_drops": result["shared_tun"]["queue_full_drops"],
            "backpressure_events": result["shared_tun"].get("backpressure"),
            "scope": "server shared TUN aggregate, not one specific client",
        })
    for name, duration, scale in PHASES:
        expected = sum(2*spec["c2s_target_mbps"]*scale for spec in plan["clients"])
        observed = agg[name]["actual_sent_mbps_both_directions"]
        if expected > 0 and observed < .9*expected:
            result["alerts"].append({
                "phase": name, "class": "AGGREGATE_OFFERED_RATE_SHORTFALL",
                "target_mbps": round(expected, 3), "actual_mbps": observed,
                "note": "The Python load generator or downstream transport could not supply the full target; no product ceiling inferred without isolation.",
            })
    result["alert_count"] = len(result["alerts"])
    result["performance_verdict"] = ("BOTTLENECK_OR_LOSS_ALERTS_PRESENT"
                                     if result["alerts"] else
                                     "NO_CONFIGURED_ALERTS_IN_THIS_SCOPED_SCENE")
    # CI success means this real workload ran and yielded inspectable evidence.
    # It does NOT magically mean the software met every performance target.
    result["result"] = (
        "DIAGNOSTIC_COMPLETE_WITH_ALERTS" if result["alerts"]
        else "DIAGNOSTIC_COMPLETE_NO_CONFIGURED_ALERTS")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--product-log", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    result = analyze(pathlib.Path(a.art), pathlib.Path(a.product_log))
    pathlib.Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    for phase, stats in result["aggregate"].items():
        print(f"H1259_LOAD_{phase.upper()} sent={stats['actual_sent_mbps_both_directions']}"
              f"Mbps received={stats['delivered_mbps_both_directions']}Mbps"
              f" UDP_delivery={stats['observed_UDP_delivery_fraction']}", flush=True)
    print(f"H1259_PERFORMANCE_VERDICT={result['performance_verdict']}"
          f" alerts={result['alert_count']} source={result['source_sha']}", flush=True)


if __name__ == "__main__":
    main()
