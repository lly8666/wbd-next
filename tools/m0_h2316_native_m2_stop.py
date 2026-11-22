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
    if m is None or c is None:return None
    if m["queued"]!=c["fifo_left"]:
        return None
    return {**m,**c,
            "driver_copied_not_peer_receipt":True,
            "counter_scope":"original_windows_rust_m2_owned_stop"}
