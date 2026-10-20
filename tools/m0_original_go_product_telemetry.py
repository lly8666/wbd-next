#!/usr/bin/env python3
"""Read REAL original public client/server product --diagnostic-jsonl.

No simulation of ACK, application delivery, configured parity or lane ID.
Summarize original Go V3 live owner counters, never promote new Rust V4.
"""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--root", type=Path, required=True)
p.add_argument("--mode", choices=("fixed", "auto", "game2", "game4"), required=True)
a = p.parse_args()
expected = {"fixed": 1, "auto": 1, "game2": 2, "game4": 4}[a.mode]
result = {"schema_version": 1, "mode": "original-Go-V3-" + a.mode,
          "new_Rust_V4_retrans_FEC2_Game": "NOT_ATTACHED"}
for side in ("client", "server"):
    path = a.root / (side + "-diag.jsonl")
    if not path.exists():
        p.error("missing actual original " + side + " diagnostic samples")
    samples = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not samples:
        p.error("empty original public process diagnostics")
    maximum_live_lanes = 0
    actual_parity = set()
    revision = set()
    record_suites = set()
    retransmitted_max = 0
    repair_attempts_max = 0
    repair_failures_max = 0
    evidence = 0
    for sample in samples:
        obj = sample.get("product", {})
        if side == "server":
            snap = obj.get("tunnel", {})
            if "tunnels" in obj:
                tunnels = obj["tunnels"]
                snap = tunnels[0] if tunnels else {}
        else:
            snap = obj
        lanes = snap.get("lanes", [])
        if not isinstance(lanes, list):
            p.error("invalid actual original Go lane snapshot")
        if not lanes:
            continue
        evidence += 1
        maximum_live_lanes = max(maximum_live_lanes, len(lanes))
        refs = [json.dumps(lane.get("ref", {}), sort_keys=True) for lane in lanes]
        if len(refs) != len(set(refs)):
            p.error("duplicate live original Go authenticated lane reference")
        for lane in lanes:
            actual_parity.add(lane.get("actual_tx_parity"))
            tr = lane.get("transport", {})
            repair_attempts_max = max(repair_attempts_max, int(tr.get("RepairAttempts", 0)))
            retransmitted_max = max(retransmitted_max, int(tr.get("Retransmitted", 0)))
            repair_failures_max = max(repair_failures_max, int(tr.get("RepairFailures", 0)))
        policy = snap.get("admission_policy")
        if policy:
            record_suites.add(policy.get("Cipher"))
            revision.add(policy.get("FECMode"))
    if maximum_live_lanes < expected:
        p.error(f"REAL {side} qualified live lanes {maximum_live_lanes} < required {expected}")
    if evidence == 0:
        p.error("no actual Go TLS-qualified live snapshot for " + side)
    result[side] = {
        "actual_lanes_max": maximum_live_lanes,
        "real_samples": len(samples),
        "real_active_samples": evidence,
        "actual_tx_parity_observed": sorted(x for x in actual_parity if x is not None),
        "actually_negotiated_FEC_modes": sorted(x for x in revision if x is not None),
        "actual_record_cipher_codes": sorted(x for x in record_suites if x is not None),
        "actual_RepairAttempts_counter_max_across_lanes": repair_attempts_max,
        "actual_Retransmitted_counter_max_across_lanes": retransmitted_max,
        "actual_RepairFailures_counter_max_across_lanes": repair_failures_max,
    }
if a.mode == "fixed":
    for side in ("client", "server"):
        if 4 not in result[side]["actual_tx_parity_observed"]:
            p.error("fixed parity configured but not ACTUALLY APPLIED by " + side)
if a.mode == "auto":
    if not result["client"]["actually_negotiated_FEC_modes"]:
        p.error("client real auto admission policy not observable")
if a.mode.startswith("game"):
    for side in ("client", "server"):
        if result[side]["actual_lanes_max"] != expected:
            p.error("wrong real qualified Go Game lane cardinality on " + side)
out = a.root / "mode-telemetry.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print("M0_ACTUAL_ORIGINAL_GO_PUBLIC_TLS_OWNER_LANE_FEC_AND_RETRANSMISSION_COUNTERS_READBACK")
print(json.dumps(result, sort_keys=True))
