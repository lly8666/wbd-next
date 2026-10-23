"""Design arithmetic only; never certifies throughput, correctness or a target machine."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def fec_residual(k, r, p):
    """P(tagged systematic is lost AND fewer than k total shards arrive), IID only."""
    if not (type(k) is int and type(r) is int and k >= 1 and 0 <= r <= 255 - k
            and 0 <= p <= 1):
        raise ValueError("GF256 k/r or probability outside model domain")
    n = k + r - 1
    return p * math.fsum(math.comb(n, lost) * p ** lost * (1 - p) ** (n - lost)
                         for lost in range(r, n + 1))


def repair_iid(p):
    if not 0 <= p <= 1:
        raise ValueError("probability outside model domain")
    return {"policy": "outer-single-repair-v2", "repair_attempt_limit": 1,
            "extra_per_fresh": p, "residual": p ** 2}


def opportunistic_v3_iid(p, candidate_fraction=0.5, credit_fraction=0.09,
                         hard_fraction=0.10, fresh_fraction_of_line=0.8 / 1.1):
    """Ideal uniform-length IID *upper opportunity*, not a recovery guarantee.

    Only selected lost original DATA may be sent again, with confirmed
    authentic mature-gap feedback; the latter may be absent in reality.
    R/F is original DATA firstsend IP bytes; R/C is directional LINE bytes.
    """
    if not (0 <= p <= 1 and 0 <= candidate_fraction <= 1
            and 0 <= credit_fraction <= hard_fraction <= 1
            and 0 <= fresh_fraction_of_line <= 1):
        raise ValueError("v3 loss/selection/credit/line fractions invalid")
    eligible = p * candidate_fraction
    repair = min(eligible, credit_fraction, hard_fraction)
    return {"policy": "outer-opportunistic-v3",
            "repair_attempt_limit": 1, "data_pto": False,
            "loss_trigger": "authenticated_mature_gap",
            "candidate_fraction": candidate_fraction,
            "eligible_repair_over_fresh": eligible,
            "ideal_repair_over_fresh": repair,
            "ideal_repair_over_line": repair * fresh_fraction_of_line,
            "ideal_residual": p - repair * (1 - p),
            "control_and_feedback_capacity_not_modeled": True,
            "feedback_coverage_not_guaranteed": True}


def v3_timers(rtt_ms, rttvar_ms, feedback_ms=10):
    """Receipt-triggered only: never synthesize a DATA PTO deadline."""
    if rtt_ms <= 0 or rttvar_ms < 0 or feedback_ms < 0:
        raise ValueError("invalid timing inputs")
    guard = min(100, max(20, 4 * rttvar_ms))
    retain = min(1500, max(250, 1.5 * rtt_ms + 4 * rttvar_ms + 100))
    return {"data_pto": False, "reorder_guard_ms": guard,
            "receipt_feedback_budget_ms": feedback_ms,
            "earliest_since_firstsend_ms": rtt_ms + guard + 20,
            "earliest_since_authenticated_negative_ms": guard,
            "retain_ms": retain, "cache_ms": retain,
            "horizon_capped": retain >= 1500}


def v3_candidate_capacity(mbps, packet_bytes, retain_ms,
                          selection_fraction=0.5, admission_pps=32768,
                          total_slots=65536, payload_mib=128):
    """Global preselection/retention bound, not an eager malloc or benchmark."""
    if min(mbps, packet_bytes, retain_ms, admission_pps, total_slots, payload_mib) <= 0:
        raise ValueError("nonpositive v3 capacity inputs")
    initial_pps = mbps * 1e6 / (8 * packet_bytes)
    candidate_pps = min(initial_pps * selection_fraction, admission_pps)
    max_live = math.ceil(candidate_pps * retain_ms / 1000 * 1.25)
    return {"firstsend_pps": initial_pps,
            "candidate_admission_pps": candidate_pps,
            "theory_live_slots_with_25pct_margin": max_live,
            "process_slot_cap": total_slots, "payload_cap_mib": payload_mib,
            "candidate_slots_sufficient": max_live <= total_slots,
            "cold_detached_payload_not_eager_allocated": True}


def timers(rtt_ms, rttvar_ms, feedback_ms):
    if rtt_ms <= 0 or rttvar_ms < 0 or feedback_ms < 0:
        raise ValueError("invalid timing inputs")
    reorder = min(20, max(2, rtt_ms / 32))
    pto = rtt_ms + max(4 * rttvar_ms, 2 * reorder, 4) + feedback_ms
    requested = max(pto + 100, 1.25 * rtt_ms + 100)
    retain = min(1500, requested)
    return {"reorder_ms": reorder, "pto_ms": pto,
            "retain_ms": retain, "cache_ms": retain,
            "horizon_capped": requested > 1500}


def capacity(mbps, packet_bytes, rtt_ms, horizon_ms, headroom, descriptor_bytes, slab_bytes):
    if min(mbps, packet_bytes, rtt_ms, horizon_ms) <= 0 or headroom < 1:
        raise ValueError("invalid capacity inputs")
    if slab_bytes < packet_bytes or descriptor_bytes < 0:
        raise ValueError("invalid memory inputs")
    pps = mbps * 1e6 / (8 * packet_bytes)
    active = math.ceil(headroom * pps * horizon_ms / 1000)
    slots = 1 << (active - 1).bit_length()
    return {"pps": pps, "flight": pps * rtt_ms / 1000,
            "active_payload_budget": active, "slots": slots,
            "shadow_mib": (active * slab_bytes + slots * descriptor_bytes) / 2 ** 20,
            "slot4096_ms": 4096 / pps * 1000}


def model(config):
    rows = []
    if len(config["packet_bytes"]) != len(config["slab_bytes"]):
        raise ValueError("each packet size needs a slab size")
    for packet, slab in zip(config["packet_bytes"], config["slab_bytes"]):
        for rtt in config["rtt_ms"]:
            timing = v3_timers(rtt, config["rttvar_ms"], config["feedback_ms"])
            rows.append(dict(packet_bytes=packet, rtt_ms=rtt, **timing,
                             **v3_candidate_capacity(
                config["inner_ip_mbps_per_direction"], packet, timing["cache_ms"],
                config.get("candidate_fraction", 0.5),
                config.get("candidate_pps_cap", 32768),
                config.get("shadow_process_slots", 65536),
                config.get("repair_payload_mib", 128))))
    p, rate, packet = 0.05, config["inner_ip_mbps_per_direction"], 1200
    overhead = config["record_overhead"] + config["ip_tcp_overhead"]
    return {"scope": "THEORY_ONLY_NOT_PRODUCT_QUALIFICATION", "product_result": "NOT_RUN",
            "policy": "outer-opportunistic-v3", "repair_attempt_limit": 1,
            "loss_trigger": "authenticated_mature_gap", "data_pto": False,
            "max_one_way_ms_design": 300, "shadow_process_slots": 65536,
            "repair_payload_mib_process": 128, "candidate_pps_process": 32768,
            "repair_pps_process": 8192, "soft_credit_fraction": 0.09,
            "hard_repair_fraction": 0.10,
            "fresh_fraction_of_line_standard": 0.8 / 1.1,
            "assumptions": ["IID unless otherwise stated", "inner-IP bytes per direction",
                            "single outer repair; retransmit reuses original PN/ciphertext",
                            "no fragmentation", "timely feedback, adequate cache and host capacity",
                            "memory excludes other queues/FEC/allocator; slab size must fit actual wire"],
            "capacity": rows,
            "fec": [{"p": p, "k": config["fec_k"], "r": r,
                     "residual": fec_residual(config["fec_k"], r, p)}
                    for p in config["loss_probabilities"] for r in config["fec_parity"]],
            "repair": [dict(p=p, **opportunistic_v3_iid(p)) for p in config["loss_probabilities"]],
            "legacy_v2_reference_only": {"policy": "outer-single-repair-v2",
                "repair": [dict(p=p, **repair_iid(p)) for p in config["loss_probabilities"]]},
            "single_tcp_500_200ms_0loss": {"app_mbps": 500, "rtt_ms": 400,
                "bdp_bytes": 25_000_000, "window_margin_bytes": 37_500_000,
                "recommended_outer_mbps_per_direction": 700,
                "qualification": "PROJECTED_NOT_TESTED"},
            "example_1200": {
                "off_p05_outer_ip_mbps": rate * (packet + overhead) / packet * (1 + p),
                "fec2020_first_outer_ip_mbps": rate * 2 * (packet + overhead + config["fec_header"]) / packet,
                "seq32_wrap_seconds_off": 2**32 / (rate * 1e6 / 8 * (packet + config["record_overhead"]) / packet),
                "cpu_budget_ns_event_07core_duplex_off": 0.7e9 / (2 * rate * 1e6 / (8 * packet) * (1 + p))}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="docs/architecture/model-inputs.json")
    args = parser.parse_args()
    print(json.dumps(model(json.loads(Path(args.input).read_text(encoding="utf-8"))), indent=2))
