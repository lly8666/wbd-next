#!/usr/bin/env python3
"""Read-only, SOURCE-aware Rust WL V2 10ms arrival-gap audit.

No uncalibrated Windows/Linux one-way timestamp assertion, no packet capture.
The legacy 10ms arrival histogram uses the generator's userspace loop tick,
not a kernel receive timestamp. New source adds separate send buckets and
loop-gap/sequence distributions to distinguish generator vs native stalls.
"""
import json,pathlib,sys

def longest_steady_gaps(bins,duration_s,min_ms=100):
    if bins is None:return []
    if not isinstance(bins,list) or len(bins)<int(duration_s*100):
        raise ValueError("missing complete 10ms observation histogram")
    # Exclude first second's genuine 300ms propagation and last second's
    # sender Stop / application drain. Keep original (not synced) time axes.
    lo=100;hi=int((duration_s-1)*100)
    gaps=[];begin=None
    for i in range(lo,hi+1):
        val=bins[i] if i<hi else 1
        if type(val) is not int or val<0:raise ValueError("bad bucket")
        if val==0 and begin is None:begin=i
        elif val!=0 and begin is not None:
            if 10*(i-begin)>=min_ms:
                gaps.append({"start_rel_s":round(begin/100,2),
                             "end_rel_s":round(i/100,2),
                             "duration_ms":10*(i-begin)})
            begin=None
    return sorted(gaps,key=lambda x:-x["duration_ms"])[:16]

def qdisc_delta(before,after,key):
    def netem(d):
        rows=[r for r in d[key] if r.get("kind")=="netem"]
        if len(rows)!=1:raise ValueError("ambiguous real tc netem qdisc")
        return rows[0]
    b=netem(before);a=netem(after)
    if b.get("handle")!=a.get("handle"):raise ValueError("tc handle changed")
    d={}
    for k in ("packets","bytes","drops","overlimits","requeues"):
        if type(a.get(k)) is not int or type(b.get(k)) is not int or a[k]<b[k]:
            raise ValueError("tc counter missing or reset "+k)
        d[k]=a[k]-b[k]
    return d

def audit(folder):
    folder=pathlib.Path(folder)
    windows=json.loads((folder/"wl-n0-windows-app.json").read_text())
    linux=json.loads((folder/"wl-n0-linux-app.json").read_text())
    b=json.loads((folder/"wl-n0-netem-before.json").read_text())
    a=json.loads((folder/"wl-n0-netem-after.json").read_text())
    if windows["scenario_sha256"]!=linux["scenario_sha256"]:
        raise ValueError("two OS scenes differ")
    duration=float(windows["measurement_duration_s"])
    if duration!=float(linux["measurement_duration_s"]):raise ValueError("different measurement horizons")
    sides={"windows":windows,"linux":linux}
    reports={}
    for role,receiver in sides.items():
        source=sides["linux" if role=="windows" else "windows"]
        offered=int(source["sent_packets"])
        observed=int(receiver["received_first_packets"])
        if observed>offered:raise ValueError("receiver got more unique DATA than other sender")
        reports[role]={
            "opposite_sender_packets":offered,
            "first_received_packets":observed,
            "missing_unique_packets":offered-observed,
            "fraction_first_delivered":round(observed/max(1,offered),7),
            "arrival_long_zero_10ms_bucket_runs":longest_steady_gaps(
                receiver["arrival_10ms_bucket_counts"],duration),
            "send_long_zero_10ms_bucket_runs":longest_steady_gaps(
                receiver.get("send_10ms_bucket_counts"),duration)
                if receiver.get("send_10ms_bucket_counts") is not None else "NOT_MEASURED_OLD_FIXTURE",
            "sender_loop_pause_ms":receiver.get("max_generator_loop_gap_ms","NOT_MEASURED_OLD_FIXTURE"),
            "receiver_sequence_gaps":receiver.get("received_sequence_gap_summary","NOT_MEASURED_OLD_FIXTURE")
        }
    return {"schema_version":1,
            "source":windows.get("source"),
            "scenario_sha256":windows["scenario_sha256"],
            "measurement_duration_s":duration,
            "arrival_clock":"PER_GENERATOR_MONOTONIC_UNSYNCED_USERSPACE_LOOP_TICK",
            "kernel_qdisc_deltas":{
                "windows_to_linux":qdisc_delta(b,a,"ifb"),
                "linux_to_windows":qdisc_delta(b,a,"eth0")},
            "receivers":reports,
            "interpretation":"No tc drops does not prove 0 kernel/socket/driver/application loss; do not infer AEAD or one-way latency."}

def main():
    if len(sys.argv)!=2:raise SystemExit("usage: python tools/m0_wl_v2_gap_audit.py <unpacked-leg-B-directory>")
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
if __name__=="__main__":main()
