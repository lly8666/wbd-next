"""Exact source-sequence missing windows on the SENDER clock only.

No cross-Windows/Linux one-way latency, no source spoofing, no reconstructed
M2 ACKs or product change. Consumes already measured 10ms sender bins.
"""
import bisect

def burst_windows(report):
    data=report.get("wl_n0_measured") or {}
    out={}
    for receiver,sender in (("windows","linux"),("linux","windows")):
        recv=data.get(receiver) or {}
        sent=data.get(sender) or {}
        bins=sent.get("send_10ms_bucket_counts")
        count=sent.get("sent_packets")
        durations=sent.get("measurement_duration_s")
        if not isinstance(bins,list) or not bins or type(count) is not int or \
           type(durations) not in (int,float):
            out[receiver]={"status":"NOT_MEASURED_SOURCE_BINS"};continue
        if any(type(x) is not int or x<0 for x in bins) or sum(bins)!=count:
            out[receiver]={"status":"INCONCLUSIVE_BINS_SENT_TOTAL_MISMATCH"};continue
        prefix=[];total=0
        for n in bins:
            total+=n;prefix.append(total)
        gaps=(recv.get("received_sequence_gap_summary") or {}).get("first_64_missing_sequence_ranges")
        if gaps is None:
            out[receiver]={"status":"NOT_MEASURED_RECEIVER_SEQUENCE_GAPS"};continue
        nominal=count/(float(durations)*100) if durations>0 else 0
        windows=[];valid=True
        for g in gaps[:64]:
            lo=g.get("start");hi=g.get("end_exclusive")
            if type(lo) is not int or type(hi) is not int or not 0<=lo<hi<=count:
                valid=False;break
            a=bisect.bisect_right(prefix,lo)
            b=bisect.bisect_right(prefix,hi-1)
            area=bins[max(0,a-3):min(len(bins),b+4)]
            peak=max(area) if area else 0
            windows.append({"source_seq_start":lo,"source_seq_end_exclusive":hi,
                            "missing_packets":hi-lo,
                            "sender_clock_first_bin_s":round(a/100,2),
                            "sender_clock_end_bin_exclusive_s":round((b+1)/100,2),
                            "nearby_sender_peak_pkts_per_10ms":peak,
                            "peak_vs_nominal_10ms_ratio":round(peak/nominal,3) if nominal else None})
        out[receiver]=({"status":"SENDER_RELATIVE_10MS_OBSERVED_ONLY",
                        "source_sender":sender,"gaps":windows,
                        "no_cross_os_clock_or_loss_location_inference":True}
                       if valid else {"status":"INCONCLUSIVE_SOURCE_SEQUENCE_OUT_OF_RANGE"})
    return out
