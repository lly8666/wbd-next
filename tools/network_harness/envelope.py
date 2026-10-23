"""Capacity arithmetic, not measured performance or automatic product tuning.

UDP sizes are application bytes; weights count packets. TCP writes are NOT
wire packets. Keep this report outside the measured loop and never change a
request, a kernel queue or a product verdict from this estimate.
"""
import argparse
import json
import math

from tools.cost_model import fec_residual, timers

MIB = 2 ** 20
RATIOS = (1/8, 1/4, 3/8, 1/2, 3/4, 1, 5/4)
PROFILES = {
    "small64": [[64, 1]], "medium256": [[256, 1]],
    "near_mtu1172": [[1172, 1]],
    "mixed": [[64, 2], [256, 2], [1024, 3], [1172, 3]],
}


def power2(n):
    return 1 << (max(1, math.ceil(n)) - 1).bit_length()


def slab(n):
    return next(s for s in (256, 512, 768, 1536, 2048, 4096, 8192, 16384, 65536) if s >= n)


def packet_cost(sizes, ratio=0, k=16, lanes=1, inner_mtu=1200):
    if not 1 <= k <= 16 or ratio not in (0, *RATIOS) or lanes not in (1, 2, 4):
        raise ValueError("unsupported FEC/lane model")
    if not 576 <= inner_mtu <= 9000 or not sizes or any(s < 1 or s > inner_mtu-28 or w <= 0 for s, w in sizes):
        raise ValueError("model requires unfragmented IPv4 UDP, payload <= inner_mtu-28")
    weight = sum(w for _, w in sizes)
    game = 16 if lanes > 1 else 0
    repair = math.ceil(k * ratio) / k
    source_header = 10 if ratio else 0
    mean_app = sum(s*w for s, w in sizes) / weight
    fresh_bytes = source_slabs = 0
    classes = {}
    for s, w in sizes:
        frame = s + 28 + game  # inner IPv4/UDP plus one logical Game envelope
        fraction = w / weight
        source = frame + source_header + 31  # complete AEAD record
        fresh_bytes += fraction * (source + 40)  # outer IPv4/TCP, no options/L2
        source_slabs += fraction * slab(source)
        cls = 256 if frame <= 256 else 512 if frame <= 512 else 65535
        count, longest = classes.get(cls, (0, 0))
        classes[cls] = (count + fraction, max(longest, frame))
    # Conservative within each size class: parity protects its largest frame.
    parity_bytes = sum(f*(longest+14+31+40) for f, longest in classes.values())
    parity_slabs = sum(f*slab(longest+14+31) for f, longest in classes.values())
    return {
        "app_bytes_per_logical_packet": mean_app,
        "fresh_outer_bytes_per_logical_packet": lanes*(fresh_bytes+repair*parity_bytes),
        "fresh_records_per_logical_packet": lanes*(1+repair),
        "mean_frozen_slab_bytes": (source_slabs+repair*parity_slabs)/(1+repair),
        "k": k, "r": math.ceil(k*ratio), "lanes": lanes,
        "inner_mtu": inner_mtu,
    }


def envelope(line_mbps, one_way_ms, sizes, ratio=0, k=16, lanes=1,
             utilization=.8, repair_allowance=.1, rttvar_ms=5, inner_mtu=1200):
    if line_mbps <= 0 or one_way_ms <= 0 or not 0 < utilization <= 1:
        raise ValueError("invalid capacity envelope")
    c = packet_cost(sizes, ratio, k, lanes, inner_mtu)
    timing = timers(2*one_way_ms, rttvar_ms, 10)
    fresh_bps = line_mbps*1e6/8*utilization/(1+repair_allowance)
    logical_pps = fresh_bps/c["fresh_outer_bytes_per_logical_packet"]
    pps = logical_pps*c["fresh_records_per_logical_packet"]
    retained = math.ceil(1.25*pps*timing["retain_ms"]/1000)
    slots = power2(retained)
    fixed_shadow_limit = 131072
    # Receiver replay history is independent from sender payload retention.
    # One repair reuses PN; 3s is the initial authenticated late-arrival horizon.
    replay = power2(1.25*pps*1.05*3.0)
    rx_blocks = math.ceil(1.25*logical_pps/k*timing["retain_ms"]/1000)+3 if ratio else 0
    per_lane = pps/lanes
    return dict(c, **timing,
        line_mbps=line_mbps, one_way_ms=one_way_ms,
        safe_app_mbps=logical_pps*c["app_bytes_per_logical_packet"]*8/1e6,
        logical_source_pps=logical_pps, aggregate_fresh_record_pps=pps,
        outer_bdp_bytes=line_mbps*1e6/8*2*one_way_ms/1000,
        policy="outer-single-repair-v2", repair_attempt_limit=1,
        shadow_slots_aggregate=slots,
        fixed_shadow_slots_per_direction=fixed_shadow_limit,
        shadow_capacity_limited=retained>fixed_shadow_limit,
        payload_pool_direction_hard_mib=192,
        endpoint_repair_pool_hard_mib=384, endpoint_total_hard_mib=512,
        shadow_worst_mib=(retained*c["mean_frozen_slab_bytes"]+slots*96)/MIB,
        shadow_current_2048_slab_worst_mib=(retained*2048+slots*96)/MIB,
        replay_pn_aggregate=replay, replay_metadata_mib=(replay/256+lanes)*40/MIB,
        fresh_queue_slots=max(64, min(8192, math.ceil(pps*.002))),
        fec_rx_worst_active_blocks=rx_blocks,
        fec_rx_horizon_model_ms=timing["retain_ms"] if ratio else 0,
        feedback_pages_per_lane=math.ceil(1.25*per_lane*1.05*2.0/256)+1,
        # Delay emulator has to hold the bandwidth-delay product. It is NOT a product queue.
        netem_shared_queue_packets=math.ceil(1.25*pps*(1+repair_allowance)*1.05*one_way_ms/1000),
        wire_repair_cap_bytes_s=fresh_bps*.1,
        cpu_us_per_outer_event_at_one_core_duplex=1e6/(2*pps*(1+repair_allowance)),
    )


def suite():
    rows = []
    for c, d, p, ratio, lanes in [(500, 200, .02, 0, 1), (50, 300, .30, 1.25, 1),
                                 (50, 300, .30, 1, 4)]:
        # New public CLI: outer1500, MSS1360. Reference1200 remains comparable
        # with historic runs; this extra case is the automatic MTU large-packet target.
        automatic_inner = 1360-31-(14 if ratio else 0)-(16 if lanes>1 else 0)
        profiles = [(name,sizes,1200) for name,sizes in PROFILES.items()]
        profiles.append(("auto_mtu_large",[[automatic_inner-28,1]],automatic_inner))
        for name, sizes, inner in profiles:
            for k in ([16, 1] if ratio else [16]):
                e = envelope(c, d, sizes, ratio, k, lanes, inner_mtu=inner)
                e.update(packet_profile=name, loss=p,
                         iid_source_residual_pct=100*fec_residual(k, math.ceil(k*ratio), p**lanes),
                         loss_model="IID copies independent; OFF value is before outer repair")
                rows.append(e)
    return {"qualification": "MODEL_ONLY_NOT_RUN",
            "policy": "outer-single-repair-v2", "repair_attempt_limit": 1,
            "fixed_shadow_slots_per_direction": 131072,
            "max_one_way_ms_design": 300,
            "assumptions": ["80% line utilization incl 10% repair allowance; 20% left for control/options/model error",
                "single outer repair: ideal IID residual p^2 and repair/fresh about p",
                "sender retain <=1.5s; receiver replay/receipt history is independent",
                "IPv4 UDP; outer headers40, record31, FEC source10/repair14, Game16",
                "1200B reference plus auto MTU/MSS1360 large-packet target; pure-small is PPS diagnosis, not500M acceptance",
                "FEC k=1 and k=16 are separate envelopes, not actual histograms",
                "Memory uses worst full lifetime retention plus25%; normal ACK release lowers occupancy",
                "512MiB endpoint total is shared, never granted independently to each client/lane",
                "RX FEC horizon equal cache is an optional repair-inclusive model, not implemented policy",
                "TCP segmentation/ACK, fragmentation, correlated loss, host speed need actual observations"],
            "rows": rows}


def request_envelope(request, inner_mtu=1200):
    t = request["traffic"]
    if t["allow_fragmentation"] or max(s for s, _ in t["sizes"]) > inner_mtu-28:
        return {"qualification": "NOT_MODELED_FRAGMENTATION_OR_LARGER_TUN", "rows": []}
    mode = request["product"]["mode"]
    lanes = {"game2": 2, "game4": 4}.get(mode, 1)
    ratios = [RATIOS[request["product"]["fec_profile"]]] if mode == "fec-fixed" else (
        [RATIOS[0], RATIOS[-1]] if mode == "fec-auto" else [0])
    rows = []
    for ph in request["phases"]:
        for direction in ("c2s", "s2c"):
            d = ph[direction]
            for ratio in ratios:
                for k in ([16, 1] if ratio else [16]):
                    c = packet_cost(t["sizes"], ratio, k, lanes, inner_mtu)
                    logical = t[direction+"_mbps"]*ph["rate_scale"]*t["udp_share"]*1e6/8/c["app_bytes_per_logical_packet"]
                    pps = logical*c["fresh_records_per_logical_packet"]
                    divisor = lanes if request["network"]["lane_loss"] == "independent" else 1
                    need = math.ceil(1.25*pps*1.1*1.05*(d["delay_ms"]+d["jitter_ms"])/1000/divisor)
                    rows.append(dict(phase=ph["name"], direction=direction, k=k, ratio=ratio,
                        udp_first_record_pps=pps, udp_wire_with10pctrepair_mbps=logical*c["fresh_outer_bytes_per_logical_packet"]*8*1.1/1e6,
                        estimated_queue_per_netem=need,
                        requested_queue=request["network"]["queue_packets"],
                        queue_model_short=need>request["network"]["queue_packets"]))
    return {"qualification": "ESTIMATE_ONLY_NO_VERDICT_CHANGE",
        "policy": request.get("policy", "legacy-two-repair-v1"),
        "repair_attempt_limit": 1 if request.get("policy") == "outer-single-repair-v2" else 2,
        "inner_mtu_input": inner_mtu, "rows": rows,
        "limits": ["UDP portion only; TCP write sizes are not TCP segment sizes",
                   "Measure control/ACK/parity k/r_sent; independent netem rate is per lane, not a shared line cap",
                   "Queue short is a preflight warning to review, never proof of product failure"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request")
    a = p.parse_args()
    if a.request:
        from .config import validate
        with open(a.request, encoding="utf-8") as f:
            result = request_envelope(validate(json.load(f)))
    else:
        result = suite()
    print(json.dumps(result, indent=2))
