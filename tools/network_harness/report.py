"""Conservative result classification. Observation is never product qualification."""
import json
import math
from pathlib import Path
from .config import fec_residual


def snmp_counters(text):
    rows = text.splitlines()
    counters = {}
    for names, values in zip(rows[::2], rows[1::2]):
        a, b = names.split(), values.split()
        if a and b and a[0] == b[0]:
            counters.update({a[0].rstrip(":") + "." + k: int(v) for k, v in zip(a[1:], b[1:])})
    return counters


def network_accounting(snapshots):
    """Leaf netem only (do not double-count prio parents); all traffic, not DATA-only."""
    out = []
    stages = [s for s in snapshots if s["name"].startswith("before-") or s["name"] == "measurement-end"]
    for before, after in zip(stages, stages[1:]):
        for role in ["client", "server"]:
            a, b = before["network"][role], after["network"][role]
            qa = {q["handle"]: q for q in a["qdisc"] if q["kind"] == "netem"}
            qb = {q["handle"]: q for q in b["qdisc"] if q["kind"] == "netem"}
            leaf = []
            for handle, end in qb.items():
                start = qa.get(handle, {})
                packets = end.get("packets", 0) - start.get("packets", 0)
                dropped = end.get("drops", 0) - start.get("drops", 0)
                leaf.append({"handle": handle, "forwarded_packets": packets, "drops": dropped,
                             "counter_reset": packets < 0 or dropped < 0,
                             "approx_loss_pct": 100*dropped/(packets+dropped) if packets+dropped > 0 and dropped >= 0 else None,
                             "end_backlog_bytes": end.get("backlog"), "end_qlen": end.get("qlen")})
            sa, sb = snmp_counters(a["snmp"]), snmp_counters(b["snmp"])
            fields = ["Udp.RcvbufErrors", "Udp.SndbufErrors", "Udp.InErrors", "Ip.ReasmFails", "Ip.FragFails", "Tcp.RetransSegs"]
            out.append({"phase": before["name"][7:], "role": role, "netem": leaf,
                        "kernel_delta": {k: sb[k]-sa[k] for k in fields if k in sb and k in sa},
                        "interpretation": "all outer traffic incl ACK/control/repair; duplicates/backlog/queue overflow can bias netem ratio; inner TCP retrans separate"})
    return out


def active_gap(tx, rx, allowance_bins=0):
    """Only bins with ongoing offered business count; sparse silence is not HOL.

    Delay is separately reported; this metric is NOT a proof of protocol HOL.
    Sustained TX windows are compared with delayed RX bins, never compress time.
    """
    longest = run = 0
    for i, offered in enumerate(tx):
        j = i + allowance_bins
        if offered and j < len(rx) and not rx[j]:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest * 10


def summarize(config, client, server, telemetry, host):
    failures, limits, observed, warnings = [], [], [], []
    phases = [{"name": "warmup", "seconds": config["warmup_s"], "rate_scale": 1}] + config["phases"]
    a = config["acceptance"]
    for direction, sender, receiver, rate in [("c2s", client, server, config["traffic"]["c2s_mbps"]),
                                               ("s2c", server, client, config["traffic"]["s2c_mbps"])]:
        for proto, share in [("udp", config["traffic"]["udp_share"]), ("tcp", 1-config["traffic"]["udp_share"])]:
            if not share:
                continue
            for i, ph in enumerate(phases):
                if not i:
                    continue
                tx, rx = sender["stats"][proto][i], receiver["stats"][proto][i]
                target = rate * share * ph["rate_scale"]
                injected = tx["tx_bytes"] * 8 / ph["seconds"] / 1e6
                # Cohort goodput counts late arrivals through drain. Do not call it in-phase wire rate.
                delivered = rx["rx_bytes"] * 8 / ph["seconds"] / 1e6
                missing = tx["tx_packets"] - rx["rx_packets"]
                loss = 100 * missing / tx["tx_packets"] if tx["tx_packets"] else None
                deadline_bad = missing + rx["late"]
                first_bin = round(sum(p["seconds"] for p in phases[:i]) * 100)
                last_bin = first_bin + round(ph["seconds"] * 100)
                arrival_bytes = receiver.get("rx_bytes_bins_10ms", {}).get(proto)
                row = {"direction": direction, "protocol": proto, "phase": ph["name"],
                       "target_app_mbps": target, "injected_app_mbps": injected,
                       "cohort_delivered_app_mbps": delivered, "sent": tx["tx_packets"],
                       "arrival_window_app_mbps": sum(arrival_bytes[first_bin:last_bin])*8/ph["seconds"]/1e6 if arrival_bytes is not None else None,
                       "delivered": rx["rx_packets"], "missing_after_drain": missing,
                       "loss_pct": loss, "late_or_missing": deadline_bad,
                       "first_arrival_ms": rx["latency"], "send_lag_ms": tx["send_lag"],
                       "tcp_backpressure_slots": tx["backpressure"],
                       "duplicates": rx["duplicates"], "reordered": rx["reordered"],
                       "send_errors": tx["send_errors"], "emsgsize": tx["emsgsize"]}
                observed.append(row)
                tag = f'{direction}/{proto}/{ph["name"]}'
                if missing < 0 or rx["invalid"] or rx["duplicates"]:
                    failures.append(tag + ": invalid/duplicate delivery or count nonconservation")
                if target and abs(injected / target - 1) > a["injection_tolerance_pct"] / 100:
                    # TCP congestion/backpressure is a transport result, not automatically an injector defect.
                    limits.append(tag + (": TCP_BACKPRESSURED" if proto == "tcp" and tx["backpressure"]
                                         else ": INVALID_INJECTOR_RATE"))
                if tx["send_errors"]:
                    limits.append(tag + ": APP_SEND_ERRORS_OR_MTU_REJECTION")
                if loss is not None and "max_loss_pct" in a and loss > a["max_loss_pct"]:
                    failures.append(tag + ": declared loss allowance exceeded")
                if "max_p99_ms" in a and rx["latency"]["n"]:
                    if rx["latency"]["p99_ms"] is None or rx["latency"]["p99_ms"] > a["max_p99_ms"]:
                        failures.append(tag + ": declared one-way p99 allowance exceeded")
    gaps = {}
    for direction, sender, receiver in [("c2s", client, server), ("s2c", server, client)]:
        for proto in ["udp", "tcp"]:
            # Include raw bins in artifact, so variable delay/phase transitions can be reanalyzed.
            gap = active_gap(sender["tx_bins_10ms"][proto], receiver["rx_bins_10ms"][proto])
            gaps[f"{direction}_{proto}"] = gap
            if "max_active_gap_ms" in a and gap > a["max_active_gap_ms"]:
                failures.append(f"{direction}/{proto}: declared active delivery gap allowance exceeded")
    for role, data in [("client", client), ("server", server)]:
        if data["capacity_exceeded"] or data["socket_drops"]:
            limits.append(role + ": HARNESS_CAPACITY_LIMITED")
        if data["errors"]:
            # Duplicate probe echoes from deliberate underlay duplication are informational.
            serious = {k: v for k, v in data["errors"].items() if k != "duplicate_or_unknown_probe_echo"}
            if serious:
                limits.append(role + ": " + json.dumps(serious, sort_keys=True))
    if not telemetry["stop_drained_both"]:
        failures.append("public Rust Stop not drained on both sides")
    if not telemetry["effective_config_verified"]:
        failures.append("requested mode/profile/recovery policy has no matching product readback")
    if a["require_retransmission"] and (telemetry["repair_packets"] is None or telemetry["repair_packets"] <= 0):
        failures.append("requested retransmission observation absent")
    if any(row["target_app_mbps"] > 0 and row["delivered"] == 0 for row in observed):
        # Blackout phase can legitimately deliver zero. Recovery is assessed in later phases.
        for row in observed:
            ph = next(p for p in config["phases"] if p["name"] == row["phase"])
            d = ph[row["direction"]]
            lanes = {"game2": 2, "game4": 4}.get(config["product"]["mode"], 1)
            if row["target_app_mbps"] and not row["delivered"] and d["loss_pct"] < 100 and len(d["blackhole_lanes"]) < lanes:
                failures.append(f'{row["direction"]}/{row["phase"]}: no real delivery')
    # Host evidence is separate; high product CPU alone cannot excuse a product bottleneck.
    host_risk = host.get("steal_pct_peak", 0) > 5 or (host.get("cpu_psi_some_mean") or 0) > 20
    if host_risk or host.get("cpu_psi_some_peak", 0) > 20:
        warnings.append("HOST_CONTENTION_OBSERVED; inspect time series, not a capacity verdict from one CPU/PSI number")
    status = "FAIL" if failures else ("INCONCLUSIVE" if limits else "PASS_SCOPED_OBSERVATION")
    return {"result": status, "failures": failures, "limits": limits, "warnings": warnings, "observed": observed,
            "performance_comparison": "INCONCLUSIVE_HOST_CONTENTION" if host_risk else "REQUIRES_MATCHED_VALID_AB_LEGS",
            "active_zero_delivery_ms": gaps, "telemetry": telemetry, "host": host,
            "probes": {role: [{"phase": ph["name"], "sent": st["probe_sent"],
                                "received": st["probe_received"], "missing": st["probe_sent"]-st["probe_received"],
                                "rtt_ms": st["rtt"]}
                               for ph, st in zip(phases, d["stats"]["udp"])]
                       for role, d in [("client", client), ("server", server)]},
            "qualification": "Linux public path in this scenario only; NOT Windows/physical/full product",
            "stop_heavier_resource_cases": bool(limits),
            "model": {"assumptions": "IID independent losses, timely repairs, no queue/correlation; NOT acceptance gates",
                      "two_retry_ideal_at_5pct": {"residual": .05**3, "repair_over_first_bytes": .05+.05**2},
                      "RS16_at_5pct": {str(r): fec_residual(16, r, .05) for r in [2, 4, 6, 8, 12, 16, 20]},
                      "actual_partial_blocks_and_repair_timing": "NOT_OBSERVED"}}


def markdown(result):
    lines = ["# Network scenario result", "", "Result: **" + result["result"] + "**", "",
             "Rates are application bytes, first-arrival delay uses the same Linux monotonic clock.", "",
             "|Direction|Protocol|Phase|Offered Mbps|Arrival Mbps|Delivered cohort Mbps|Missing|One-way p99 ms|",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in result.get("observed", []):
        lines.append(f'|{r["direction"]}|{r["protocol"]}|{r["phase"]}|{r["injected_app_mbps"]:.3f}|'
                     f'{r.get("arrival_window_app_mbps")}|{r["cohort_delivered_app_mbps"]:.3f}|{r["missing_after_drain"]}|{r["first_arrival_ms"]["p99_ms"]}|')
    lines += ["", "Failures: " + json.dumps(result.get("failures", [])),
              "", "Limits: " + json.dumps(result.get("limits", [])),
              "", "Warnings: " + json.dumps(result.get("warnings", [])),
              "", "Lost/undelivered records are NOT removed from deadline metrics. Surviving-sample p99 alone is not success."]
    return "\n".join(lines) + "\n"
