#!/usr/bin/env python3
"""M0 H2244: source-locked whole-chain drop/CPU/tail gate, NOT a product governor.

An upstream loss reduction is not success if the same loss moved into the
TUN driver, or if fairness destroyed native M4 batching. Each stage is
measured against *received* business GiB. Parent/child qdisc drop counters
may overlap, so report bounds instead of falsely adding both as facts.

This is an offline diagnostic of genuine frozen native experiment receipts,
not a new sender, kernel control loop, outer ACK/retransmission, or rate cap.
"""
import argparse
import json
import math
import pathlib
import re

SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = (
    "source_sha", "run_id", "duration_s", "receiver_goodput_mbps",
    "sharedtun_queue_full", "tun_link_tx_dropped", "root_qdisc_drops",
    "child_qdisc_drops", "m4_copied_per_batch", "tx_cpu_s_per_received_gib",
    "inner_tcp_retrans", "owned_stop", "kind"
)
METRICS = (
    "duration_s", "receiver_goodput_mbps", "sharedtun_queue_full",
    "tun_link_tx_dropped", "root_qdisc_drops", "child_qdisc_drops",
    "m4_copied_per_batch", "tx_cpu_s_per_received_gib", "inner_tcp_retrans"
)

def _finite_number(value, label, *, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("H2244_UNKNOWN_" + label)
    if not math.isfinite(value) or value < 0 or (strictly_positive and value == 0):
        raise ValueError("H2244_INVALID_" + label)
    return float(value)

def validate(stage):
    if not isinstance(stage, dict):
        raise ValueError("H2244_STAGE_NOT_OBJECT")
    for field in REQUIRED:
        if field not in stage:
            raise ValueError("H2244_MISSING_" + field)
    if not isinstance(stage["source_sha"], str) or not SHA.fullmatch(stage["source_sha"]):
        raise ValueError("H2244_UNQUALIFIED_SOURCE_SHA")
    if type(stage["run_id"]) is not int or stage["run_id"] <= 0:
        raise ValueError("H2244_UNQUALIFIED_RUN_ID")
    if stage["owned_stop"] is not True:
        raise ValueError("H2244_MISSING_REAL_OWNED_STOP")
    if stage["kind"] not in ("original", "candidate"):
        raise ValueError("H2244_UNQUALIFIED_KIND")
    for field in METRICS:
        _finite_number(stage[field], field, strictly_positive=field in (
            "duration_s", "receiver_goodput_mbps", "m4_copied_per_batch",
            "tx_cpu_s_per_received_gib"
        ))
    for field in ("sharedtun_queue_full", "tun_link_tx_dropped",
                  "root_qdisc_drops", "child_qdisc_drops",
                  "inner_tcp_retrans"):
        if not isinstance(stage[field], int) or isinstance(stage[field], bool):
            raise ValueError("H2244_COUNTER_MUST_BE_INTEGER_" + field)
    return stage

def _received_gib(stage):
    # Numeric receiver-goodput and measured duration must come from the
    # same native iperf receiver case. Never use sender bytes as denominator.
    return stage["receiver_goodput_mbps"] * 1_000_000.0 * stage["duration_s"] / (8 * 2**30)

def loss_bounds(stage):
    validate(stage)
    # Kernel root/child qdisc may count the same drop twice. We only know
    # bounds; the TUN link driver and downstream Rust ingress are distinct
    # drop sites, not a guarantee of identical offered packet populations.
    root, child = stage["root_qdisc_drops"], stage["child_qdisc_drops"]
    other = stage["tun_link_tx_dropped"] + stage["sharedtun_queue_full"]
    gib = _received_gib(stage)
    return {
        "local_drop_lower_per_received_gib": (other + max(root, child)) / gib,
        "local_drop_upper_per_received_gib": (other + root + child) / gib,
        "root_child_qdisc_not_additive": True,
        "kernel_tun_driver_drops": stage["tun_link_tx_dropped"],
        "rust_queue_full_drops": stage["sharedtun_queue_full"],
        "received_gib_from_real_receiver_rate": gib,
    }

def _tail_gate(tail):
    if tail is None:
        return ["CONCURRENT_SMALL_TCP_UDP_TAIL_NOT_RUN"]
    if not isinstance(tail, dict):
        raise ValueError("H2244_TAIL_RECEIPT_NOT_OBJECT")
    missing = [k for k in (
        "udp_replies", "udp_requests", "udp_p99_ms", "udp_baseline_p99_ms",
        "tcp_samples", "tcp_p99_ms", "tcp_baseline_p99_ms",
        "real_concurrent_with_bulk", "same_source_same_vm"
    ) if k not in tail]
    if missing:
        raise ValueError("H2244_MISSING_TAIL_" + missing[0])
    if tail["real_concurrent_with_bulk"] is not True or tail["same_source_same_vm"] is not True:
        raise ValueError("H2244_TAIL_NOT_REAL_SAME_SOURCE_CONCURRENT")
    for k in ("udp_replies", "udp_requests", "tcp_samples"):
        if type(tail[k]) is not int or tail[k] < 0:
            raise ValueError("H2244_BAD_TAIL_COUNT_" + k)
    for k in ("udp_p99_ms", "udp_baseline_p99_ms", "tcp_p99_ms",
              "tcp_baseline_p99_ms"):
        _finite_number(tail[k], k, strictly_positive=True)
    if tail["udp_replies"] > tail["udp_requests"]:
        raise ValueError("H2244_UDP_REPLIES_MORE_THAN_SENT")
    alerts = []
    if tail["udp_replies"] < 50 or tail["tcp_samples"] < 50:
        alerts.append("TAIL_P99_SCREEN_INSUFFICIENT_SAMPLES")
    if tail["udp_replies"] < tail["udp_requests"]:
        alerts.append("UDP_LOSS_MUST_BE_REPORTED_NOT_HIDDEN")
    # These are a preliminary p99 SCREEN only, not product p99 qualification.
    # Allow the larger of 1ms or 5% of baseline; use an explicit baseline.
    for typ in ("udp", "tcp"):
        tolerance = max(1.0, tail[typ + "_baseline_p99_ms"] * 0.05)
        if tail[typ + "_p99_ms"] > tail[typ + "_baseline_p99_ms"] + tolerance:
            alerts.append("SMALL_" + typ.upper() + "_P99_REGRESSION")
    if min(tail["udp_replies"], tail["tcp_samples"]) < 10_000:
        alerts.append("P99_PRODUCT_SAMPLE_SIZE_NOT_MET")
    return alerts

def assess(original, candidate, *, original_restored=None, tail=None):
    """Fail closed; product default promotion is never emitted by this gate."""
    a, b = validate(original), validate(candidate)
    if a["kind"] != "original" or b["kind"] != "candidate":
        raise ValueError("H2244_WRONG_AB_ORIENTATION")
    for stage in (b, original_restored):
        if stage is None: continue
        validate(stage)
        if stage["source_sha"] != a["source_sha"] or stage["run_id"] != a["run_id"]:
            raise ValueError("H2244_CROSS_SOURCE_OR_RUN_CAUSAL_COMPARISON")
        if stage["duration_s"] != a["duration_s"]:
            raise ValueError("H2244_UNPAIRED_DURATION")
    if b["source_sha"] != a["source_sha"] or b["run_id"] != a["run_id"]:
        raise ValueError("H2244_CROSS_SOURCE_OR_RUN_CAUSAL_COMPARISON")
    if b["duration_s"] != a["duration_s"]:
        raise ValueError("H2244_UNPAIRED_DURATION")
    if original_restored is not None and original_restored["kind"] != "original":
        raise ValueError("H2244_RESTORED_NOT_ORIGINAL")
    a_bounds, b_bounds = loss_bounds(a), loss_bounds(b)
    blockers = []
    open_gates = _tail_gate(tail)
    if original_restored is None:
        open_gates.append("NO_A_PRIME_ORIGINAL_DRIFT_REFERENCE")
    # Unambiguous relocation failure only when even B's lower bound exceeds
    # A's upper bound after normalizing by actually delivered business GiB.
    if b_bounds["local_drop_lower_per_received_gib"] > (
        a_bounds["local_drop_upper_per_received_gib"] * 1.05):
        blockers.append("TOTAL_LOCAL_LOSS_RELOCATED_OR_AMPLIFIED")
    if b["tun_link_tx_dropped"] > 0 and a["tun_link_tx_dropped"] == 0:
        open_gates.append("NEW_TUN_DRIVER_DROPS_REQUIRE_CAUSAL_REVIEW")
    # A product CPU regression is not excused by lower Rust drop counts.
    baseline_cpu = min(a["tx_cpu_s_per_received_gib"],
                       original_restored["tx_cpu_s_per_received_gib"]
                       if original_restored else a["tx_cpu_s_per_received_gib"])
    if b["tx_cpu_s_per_received_gib"] > baseline_cpu * 1.08:
        blockers.append("NATIVE_CPU_PER_RECEIVED_GIB_REGRESSION")
    if b["m4_copied_per_batch"] < a["m4_copied_per_batch"] * 0.60:
        blockers.append("ORIGINAL_M4_SENDMMSG_BATCH_COLLAPSE")
    min_baseline_mbps = min(a["receiver_goodput_mbps"],
                            original_restored["receiver_goodput_mbps"]
                            if original_restored else a["receiver_goodput_mbps"])
    if b["receiver_goodput_mbps"] < min_baseline_mbps * 0.95:
        blockers.append("RECEIVER_GOODPUT_REGRESSION")
    if b_bounds["local_drop_upper_per_received_gib"] >= (
        a_bounds["local_drop_lower_per_received_gib"]):
        open_gates.append("NO_PROVEN_STRICT_LOCAL_DROP_BOUND_IMPROVEMENT")
    # Even with no local blockers: native netns != Windows/physical WAN,
    # no-loss high line and multi-lease/Game/Stop still require full gates.
    open_gates.extend([
        "ZERO_LOSS_HIGH_CAPACITY_NOT_QUALIFIED_BY_THIS_COMPARISON",
        "WINDOWS_NORMAL_GAME_MULTILEASE_PHYSICAL_NOT_QUALIFIED",
        "NO_FIXED_450MBPS_PRODUCT_CAP_ALLOWED",
    ])
    verdict = ("REJECT_AS_PRODUCT_DEFAULT" if blockers else
               "MECHANISM_ONLY_FURTHER_QUALIFICATION_REQUIRED")
    return {
        "source_sha":a["source_sha"], "run_id":a["run_id"],
        "verdict":verdict,
        "blockers":sorted(set(blockers)),
        "open_gates":sorted(set(open_gates)),
        "original":a_bounds,
        "candidate":b_bounds,
        "receiver_mbps": {"original":a["receiver_goodput_mbps"],
                          "candidate":b["receiver_goodput_mbps"]},
        "m4_copied_per_batch": {"original":a["m4_copied_per_batch"],
                               "candidate":b["m4_copied_per_batch"]},
        "native_cpu_s_per_received_gib": {
            "original":a["tx_cpu_s_per_received_gib"],
            "candidate":b["tx_cpu_s_per_received_gib"]},
        "no_product_changes_authorized":True,
    }

def from_h2243(evidence, arch="x86_64", selected="TBF48K_fq_codel"):
    if evidence.get("checkpoint") != "H2243_TRUE_TUN_GLOBAL_TBF_BURST_FAIR_FQCODEL_NATIVE_TWO_ISA":
        raise ValueError("H2244_WRONG_EVIDENCE_SOURCE")
    if evidence.get("product_defaults_unchanged") is not True:
        raise ValueError("H2244_PRODUCT_SOURCE_ALREADY_MUTATED")
    if arch not in ("x86_64", "aarch64"):
        raise ValueError("H2244_UNSUPPORTED_ARCH")
    if evidence.get(arch,{}).get("real_app_and_stops") != "PASS_TRUE_ORIGINAL":
        raise ValueError("H2244_NO_GENUINE_NATIVE_APPLICATION_STOP")
    def sample(raw, kind):
        baseline = kind == "original"
        if not baseline and "kernel_fq_codel_child_qdisc_drops" not in raw:
            raise ValueError("H2244_MISSING_CHILD_QDISC_REAL_COUNTER")
        return {
            "source_sha":evidence["source_sha"],
            "run_id":int(evidence["run_id"]),
            "duration_s":evidence["cases"]["iperf_duration_s"],
            "receiver_goodput_mbps":raw["receiver_goodput_mbps"],
            "sharedtun_queue_full":raw["sharedtun_queue_full"],
            "tun_link_tx_dropped":raw["real_tun_link_tx_dropped"],
            "root_qdisc_drops":raw["kernel_root_qdisc_drops"],
            "child_qdisc_drops":0 if baseline else raw["kernel_fq_codel_child_qdisc_drops"],
            "m4_copied_per_batch":raw["m4_copied_per_batch"],
            "tx_cpu_s_per_received_gib":raw["m4_tx_cpu_s_per_delivered_GiB"],
            "inner_tcp_retrans":raw["inner_TCP_retrans"],
            "owned_stop":True, "kind":kind,
        }
    rows=evidence[arch]["stages"]
    if [x["name"] for x in rows] != [
        "original_A", "TBF16K_fq_codel", "TBF48K_fq_codel", "original_A_prime"]:
        raise ValueError("H2244_UNEXPECTED_STAGE_ORDER_OR_MISSING_A_PRIME")
    candidates=[s for s in rows if s["name"]==selected]
    if len(candidates)!=1 or selected not in ("TBF16K_fq_codel","TBF48K_fq_codel"):
        raise ValueError("H2244_UNKNOWN_CANDIDATE")
    return assess(sample(rows[0],"original"),sample(candidates[0],"candidate"),
                  original_restored=sample(rows[-1],"original"))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence",type=pathlib.Path,help="H2243 exact-source genuine Action JSON")
    parser.add_argument("--arch",choices=("x86_64","aarch64"),default="x86_64")
    parser.add_argument("--candidate",choices=("TBF16K_fq_codel","TBF48K_fq_codel"),
                        default="TBF48K_fq_codel")
    args=parser.parse_args()
    evidence=json.loads(args.evidence.read_text())
    print(json.dumps(from_h2243(evidence,args.arch,args.candidate),
                     sort_keys=True,indent=2))

if __name__=="__main__":
    main()
