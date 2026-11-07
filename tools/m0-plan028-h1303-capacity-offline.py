#!/usr/bin/env python3
"""Correct H1302 native ARM64 capacity phases from existing Action artifact only.

traffic.py's start_ns includes a 10s warmup BEFORE the four configured phases.
Original H1302 ledger accidentally attributed warmup to the first 0.6x phase.
No network work or modification of the historical artifact.
"""
import argparse
import json
from pathlib import Path
import statistics


def audit(root):
    root = Path(root)
    plan = json.loads((root / "h1250-matrix-plan.json").read_text())
    old = json.loads((root / "h1302-capacity-phases.json").read_text())
    reports = [json.loads((root / f"h1250-{side}-erin.json").read_text())
               for side in ("c", "s")]
    client, server = reports
    test = json.loads((root / "h1286-rapid-report.json").read_text())
    ticks = json.loads((root / "h1301-netem-clock.json").read_text())["samples"]
    start = plan["start_monotonic_ns"]
    assert start == client["start_ns"] == server["start_ns"]
    assert test["source_sha"] == plan["source_sha"] == old["source"]
    assert test["duration_seconds"] == plan["application_load_seconds"] == 180
    assert plan["warmup_seconds"] == 10
    expected = [("first_wave", 30, 0.6), ("sustained", 60, 0.85),
                ("overload", 30, 1.0), ("recovery", 50, 0.85)]
    phases = plan["capacity_phase_schedule"]
    assert [(p["name"], p["seconds"], p["rate_scale"]) for p in phases] == expected
    assert len(old["phases"]) == len(expected)
    elapsed = plan["warmup_seconds"]
    corrected = []
    for phase in phases:
        duration = phase["seconds"]
        subset = [tick for tick in ticks
                  if elapsed * 10**9 <= tick["mono_ns"] - start
                  < (elapsed + duration) * 10**9]
        assert len(subset) >= duration, (phase["name"], len(subset))
        busy, softirq, cores = [], [], {}
        for first, last in zip(subset, subset[1:]):
            for name, before in first["host_core_jiffies"].items():
                after = last["host_core_jiffies"].get(name)
                if after is None or len(before) < 8 or len(after) < 8:
                    continue
                delta = [b - a for a, b in zip(before, after)]
                total = sum(delta)
                if total <= 0:
                    continue
                value = 100 * (total - delta[3] - delta[4]) / total
                busy.append(value)
                softirq.append(100 * delta[6] / total)
                cores.setdefault(name, []).append(value)
        assert busy and len(cores) == 4
        lo, hi = int(elapsed * 100), int((elapsed + duration) * 100)

        def business(tx, rx):
            sent = sum(tx["tx_bytes_bins_10ms"]["udp"][lo:hi])
            received = sum(rx["rx_bytes_bins_10ms"]["udp"][lo:hi])
            assert sent > 0
            return {"offered_mbps": round(8 * sent / duration / 1e6, 3),
                    "received_mbps": round(8 * received / duration / 1e6, 3),
                    "delivery_fraction": round(received / sent, 5)}

        qdisc = [tick["client_uplink_netem"] for tick in subset]
        assert all(x["kind"] == "netem" for x in qdisc)
        corrected.append({
            "name": phase["name"], "scale": phase["rate_scale"],
            "start_s": elapsed, "end_s": elapsed + duration,
            "cpu_mean_busy_pct": round(statistics.mean(busy), 2),
            "cpu_mean_softirq_pct": round(statistics.mean(softirq), 2),
            "cpu_per_core_mean_busy_pct": {
                name: round(statistics.mean(values), 2)
                for name, values in sorted(cores.items())},
            "erin_ul": business(client, server),
            "erin_dl": business(server, client),
            "netem_ul_sent_delta": qdisc[-1]["packets"] - qdisc[0]["packets"],
            "netem_ul_dropped_delta": qdisc[-1]["drops"] - qdisc[0]["drops"],
            "netem_ul_peak_qlen": max(x["qlen"] for x in qdisc)
        })
        elapsed += duration
    assert elapsed == 180
    return {
        "kind": "H1303_OFFLINE_CORRECTION_NOT_NEW_PRODUCT_TEST",
        "original_source_sha": test["source_sha"],
        "original_action_alerts": test["alert_count"],
        "original_rotation": test["rotation_verdict"],
        "warmup_skipped_seconds": plan["warmup_seconds"],
        "original_incorrect_ledger_retained": "h1302-capacity-phases.json",
        "reason": "H1302 phases sampled t=0 rather than warmup+phase t=10",
        "corrected_phases": corrected,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--art", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = audit(args.art)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("H1303_OFFLINE_CORRECTED_PHASES",
          json.dumps(result["corrected_phases"], sort_keys=True))


if __name__ == "__main__":
    main()
