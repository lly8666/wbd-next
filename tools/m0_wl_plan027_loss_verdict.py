"""Strict PLAN027 first-source integrity: do not mistake >=99.9% for zero loss."""
import json
import sys

def verdict(report):
    v=report.get("WL_V2") or {}
    if report.get("stop")!="PASS_BOTH_OWNED" or v.get("owned_stop")!="PASS_BOTH_OWNED":
        return {"status":"INCONCLUSIVE_NO_OWNED_STOP"}
    if v.get("status")!="MEASURED_BOTH_OS_KERNEL":
        return {"status":"INCONCLUSIVE_NO_TWO_OS_KERNEL_MEASUREMENT"}
    c=v.get("declared") or {}
    if not c or not all(c.get(direction,{}).get("loss_pct")==0 for direction in ("windows_to_linux","linux_to_windows")):
        return {"status":"NOT_LOSSLESS_CASE"}
    rows=report.get("wl_n0_measured") or {}
    if not all(side in rows for side in ("windows","linux")):
        return {"status":"INCONCLUSIVE_MISSING_NATIVE_GENERATORS"}
    w,l=rows["windows"],rows["linux"]
    missing={"windows":l["sent_packets"]-w["received_first_packets"],
             "linux":w["sent_packets"]-l["received_first_packets"]}
    if any(v<0 for v in missing.values()):
        return {"status":"FAIL_IMPOSSIBLE_FIRST_COUNT","missing":missing}
    errors={side:row.get("invalid_packets") for side,row in rows.items()}
    if any(v is None or v!=0 for v in errors.values()):
        return {"status":"FAIL_INVALID_BUSINESS_DATAGRAM","invalid":errors,"missing":missing}
    result={"status":"PASS_ZERO_INJECTED_LOSS_EXACT_FIRST" if all(v==0 for v in missing.values())
            else "FAIL_ZERO_INJECTED_LOSS_FIRST_SOURCE_GAP",
            "scenario_id":v["scenario_id"],"missing":missing,
            "source":report.get("linux_binary_source"),
            "stop":"PASS_BOTH_OWNED",
            "scope":"EXACT_FIRST_RECEIVED_APPLICATION_UDP_NOT_CROSS_OS_P99",
            "windows_host_ipv4_udp_global_errors":w.get("udp_socket_probe_deltas",{}).get("windows_host_ipv4_udp_deltas")}
    return result

if __name__=="__main__":
    with open(sys.argv[1],encoding="utf-8") as f:report=json.load(f)
    result=verdict(report)
    print(json.dumps(result,sort_keys=True))
    sys.exit(0 if result["status"]=="PASS_ZERO_INJECTED_LOSS_EXACT_FIRST" else 1)
