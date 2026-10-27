"""Source-locked real-kernel business RTT summary, never one-way p99."""
import math

def summarize_rtt(samples_ms:list[float], sent:int,
                  minimum:int=200, late_ms:float=2000.0)->dict:
    if sent<0 or minimum<1 or any(x<0 or not math.isfinite(x) for x in samples_ms):
        raise ValueError("invalid business RTT observations")
    if len(samples_ms)>sent:
        raise ValueError("more probe replies than actual kernel sends")
    good=sorted(samples_ms)
    p99=round(good[math.ceil(.99*len(good))-1],3) if len(good)>=minimum else (
        "NOT_MEASURED_INSUFFICIENT_REAL_RTT_SAMPLES")
    return {
        "measurement":"SAME_ORIGIN_MONOTONIC_REAL_OS_UDP_ROUNDTRIP_NOT_ONEWAY",
        "p99_ms":p99,
        "real_sent":sent,"real_replied":len(good),
        "not_returned":sent-len(good),
        "late_over_2s":sum(v>late_ms for v in good),
        "max_delivered_rtt_ms":round(good[-1],3) if good else None,
        "minimum_required":minimum,
    }
