#!/usr/bin/env python3
"""Owned Actions netns-only TUN link drop timeline, no payload/identifier output.

This is a diagnostic sampler, not a product fix or a performance success gate.
Sample Linux per-netdevice numeric sysfs counters every 25ms in the first 2s,
then every 100ms up to the end of declared warmup. One process per arm; no
per-sample ip/netns subprocess and no host/global sysctls.
"""
import argparse
import json
from pathlib import Path
import time

DEVICE = "wbntun0"
FIELDS = ("tx_dropped", "tx_packets", "tx_bytes", "rx_packets")
ROOT = Path("/sys/class/net") / DEVICE / "statistics"

def read_snapshot():
    return {field: int((ROOT / field).read_text().strip()) for field in FIELDS}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start-ns", type=int, required=True)
    p.add_argument("--warmup-s", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    opts = p.parse_args()
    if opts.warmup_s not in (10, 15, 20):
        raise ValueError("bounded startup diagnostic permits only 10,15,20s")
    if not ROOT.is_dir():
        raise RuntimeError("owned original TUN device does not exist")
    horizon = opts.start_ns + opts.warmup_s * 1_000_000_000
    count = 0
    rows = []
    period_ns = 25_000_000
    sample_ns = opts.start_ns
    while sample_ns <= horizon:
        now = time.monotonic_ns()
        if now < sample_ns:
            time.sleep(min(0.02, (sample_ns-now)/1e9))
            continue
        record = read_snapshot()
        record["monotonic_ns"] = time.monotonic_ns()
        record["from_start_ms"] = round((record["monotonic_ns"]-opts.start_ns)/1e6, 3)
        rows.append(record)
        count += 1
        if count > 1200:
            raise RuntimeError("startup sampler exceeded hard max samples")
        # 25ms resolution for first 2s cold burst, 100ms thereafter.
        period_ns = 25_000_000 if sample_ns < opts.start_ns + 2_000_000_000 else 100_000_000
        sample_ns += period_ns
    output = {
        "scope": "TEST_ONLY_ORIGINAL_TUN_KERNEL_LINK_COUNTERS",
        "interface": DEVICE,
        "initial_monotonic_ns": opts.start_ns,
        "warmup_seconds": opts.warmup_s,
        "counter_unit": "packets_or_bytes_as_named",
        "samples": rows,
        "sample_count": len(rows),
        "privacy": "no packet payload, ports, IP, packet ids, keys or secrets"
    }
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, indent=2)+"\n")
    print("TUN_STARTUP_DIAG", json.dumps({
        "samples":len(rows),
        "first_drop":rows[0]["tx_dropped"],
        "last_drop":rows[-1]["tx_dropped"],
        "first_drop_increase_ms":next((z["from_start_ms"] for z in rows
           if z["tx_dropped"] > rows[0]["tx_dropped"]), None)
    }))

if __name__ == "__main__":
    main()
