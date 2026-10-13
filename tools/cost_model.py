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
    return {"extra_per_fresh": p + p * p, "residual": p ** 3}


def timers(rtt_ms, rttvar_ms, feedback_ms):
    if rtt_ms <= 0 or rttvar_ms < 0 or feedback_ms < 0:
        raise ValueError("invalid timing inputs")
    reorder = min(20, max(2, rtt_ms / 32))
    pto = rtt_ms + max(4 * rttvar_ms, 2 * reorder, 4) + feedback_ms
    requested = max(2 * pto + 50, 2 * rtt_ms + 100)
    return {"reorder_ms": reorder, "pto_ms": pto, "cache_ms": min(3000, requested),
            "horizon_capped": requested > 3000}


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
            timing = timers(rtt, config["rttvar_ms"], config["feedback_ms"])
            rows.append(dict(packet_bytes=packet, rtt_ms=rtt, **timing, **capacity(
                config["inner_ip_mbps_per_direction"], packet, rtt, timing["cache_ms"],
                config["headroom_factor"], config["descriptor_bytes"], slab)))
    p, rate, packet = 0.05, config["inner_ip_mbps_per_direction"], 1200
    overhead = config["record_overhead"] + config["ip_tcp_overhead"]
    return {"scope": "THEORY_ONLY_NOT_PRODUCT_QUALIFICATION", "product_result": "NOT_RUN",
            "assumptions": ["IID unless otherwise stated", "inner-IP bytes per direction",
                            "no fragmentation", "timely feedback, adequate cache and host capacity",
                            "memory excludes other queues/FEC/allocator; slab size must fit actual wire"],
            "capacity": rows,
            "fec": [{"p": p, "k": config["fec_k"], "r": r,
                     "residual": fec_residual(config["fec_k"], r, p)}
                    for p in config["loss_probabilities"] for r in config["fec_parity"]],
            "repair": [dict(p=p, **repair_iid(p)) for p in config["loss_probabilities"]],
            "example_1200": {
                "off_p05_outer_ip_mbps": rate * (packet + overhead) / packet * (1 + p + p*p),
                "fec2020_first_outer_ip_mbps": rate * 2 * (packet + overhead + config["fec_header"]) / packet,
                "seq32_wrap_seconds_off": 2**32 / (rate * 1e6 / 8 * (packet + config["record_overhead"]) / packet),
                "cpu_budget_ns_event_07core_duplex_off": 0.7e9 / (2 * rate * 1e6 / (8 * packet) * (1 + p + p*p))}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="docs/architecture/model-inputs.json")
    args = parser.parse_args()
    print(json.dumps(model(json.loads(Path(args.input).read_text(encoding="utf-8"))), indent=2))
