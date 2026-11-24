"""H2316 parse genuine original Rust M2 stop counters, not performance intent.

This parser cannot infer a loss/repair event from missing log output, and
does not turn copied native ciphertext into remote successful ACK.
"""
import re

FIELDS=(
    "authenticated_reverse_reports","repair_polls","shadow_outstanding",
    "candidate_first","expired_first","acked_first","repair_accepted",
    "repair_abandoned","preflight_stale","quota_rejected","queued",
)
CURSOR_FIELDS=(
    "unique_candidates","unique_candidate_cipher_bytes","checked_once",
    "burst_wait","fifo_left",
)
TAG="WBD_WINDOWS_NATIVE_M2_OPPORTUNITY_STOP "
CURSOR="WBD_WINDOWS_NATIVE_OUTER_CURSOR "
OUTER_REPAIR="WBD_WINDOWS_NATIVE_OUTER_REPAIR "
REPAIR_FIELDS=("source_wire_bytes","repair_accepted_wire_bytes",
               "repair_uncertain_wire_bytes","control_wire_bytes",
               "repair_packets","r_to_f_ppm","r_to_total_ppm")

def _one(line:str,tag:str,names):
    matches=[x for x in line.splitlines() if tag in x]
    if len(matches)!=1:
        return None
    tail=matches[0].split(tag,1)[1]
    pairs={k:int(v) for k,v in re.findall(r"([a-z_]+)=(\d+)",tail)}
    if any(k not in pairs for k in names):
        return None
    if "joined=true" not in tail:
        return None if tag==TAG else {k:pairs[k] for k in names}
    return {k:pairs[k] for k in names}

def parse_native_m2_stop(text:str):
    m=_one(text,TAG,FIELDS)
    # OUTER_CURSOR only ever counts actual exact owner gap nominations,
    # checked-once rate limits, and pending bounded queues.
    c=_one(text,CURSOR,CURSOR_FIELDS)
    r=_one(text,OUTER_REPAIR,REPAIR_FIELDS)
    if m is None or c is None or r is None:return None
    # Driver-copy count is independent of the shadow retirement count.
    # A real RX ACK may retire the shadow while TX is inside the driver.
    # Current sources explicitly account for those copies; old receipts
    # retain the original strict equality, never guess a missing cause.
    extra=_one(text,TAG,("repair_copied_shadow_stale","repair_broker_unresolved"))
    if extra is None:
        if "repair_copied_shadow_stale=" in text or "repair_broker_unresolved=" in text:
            return None
        extra={"repair_copied_shadow_stale":0,"repair_broker_unresolved":0}
    if (m["queued"]!=c["fifo_left"] or
        m["repair_accepted"]+extra["repair_copied_shadow_stale"]!=r["repair_packets"] or
        (r["repair_packets"]>0 and r["repair_accepted_wire_bytes"]==0)):
        return None
    return {**m,**c,**extra,
            "kernel_accepted_repair_packets":r["repair_packets"],
            "kernel_accepted_repair_wire_bytes":r["repair_accepted_wire_bytes"],
            "kernel_uncertain_repair_wire_bytes":r["repair_uncertain_wire_bytes"],
            "source_wire_bytes":r["source_wire_bytes"],
            "r_to_f_ppm":r["r_to_f_ppm"],
            "r_to_total_ppm":r["r_to_total_ppm"],
            "driver_copied_not_peer_receipt":True,
            "counter_scope":"original_windows_rust_owner_joined_stop_not_periodic_snapshot"}
