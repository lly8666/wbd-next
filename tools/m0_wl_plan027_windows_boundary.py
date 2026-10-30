"""Aggregate-only same-source Windows Rust M3/Wintun versus Windows UDP first.

No individual packet boundary inference, no cross-OS clocks; Windows UDP MIB
counts are machine-global, not a particular socket.
"""
import json

MARKER = "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "

def last_native(log):
    value=None
    for line in log.splitlines():
        if MARKER not in line:continue
        try:
            row=json.loads(line.split(MARKER,1)[1])
        except (ValueError,TypeError):continue
        if isinstance(row,dict) and type(row.get("rx_first_delivered_ipv4")) is int:
            value=row
    return value

def windows_boundary(result,client_log,control,control_log):
    rows=[]
    for report,log in ((result,client_log),(control,control_log)):
        v=report.get("WL_V2") or {}
        w=(report.get("wl_n0_measured") or {}).get("windows") or {}
        l=(report.get("wl_n0_measured") or {}).get("linux") or {}
        native=last_native(log)
        host=((w.get("udp_socket_probe_deltas") or {}).get(
            "windows_host_ipv4_udp_deltas") or {})
        if report.get("stop")!="PASS_BOTH_OWNED" or v.get("owned_stop")!="PASS_BOTH_OWNED" or v.get("status")!="MEASURED_BOTH_OS_KERNEL" or not native or type(w.get("received_first_packets")) is not int or type(l.get("sent_packets")) is not int or type(host.get("in_datagrams_delta")) is not int or host["in_datagrams_delta"]<0:
            return {"status":"INCONCLUSIVE_MISSING_REAL_NATIVE_WINTUN_OR_UDP_COUNTERS"}
        if not all((v.get("declared") or {}).get(direction,{}).get("loss_pct")==0 for direction in ("windows_to_linux","linux_to_windows")):
            return {"status":"INCONCLUSIVE_NONZERO_INJECTED_LOSS"}
        app=w["received_first_packets"]
        m3=native["rx_first_delivered_ipv4"]
        udp=host["in_datagrams_delta"]
        offered=l["sent_packets"]
        if not 0<=app<=offered or m3<app or udp<app:
            return {"status":"INCONCLUSIVE_BAD_NATIVE_OR_APP_TOTALS"}
        rows.append({"source":report.get("linux_binary_source"),
                     "scenario_id":v.get("scenario_id"),
                     "offered_original_sources":offered,
                     "windows_first":app,
                     "original_source_first_missing":offered-app,
                     "windows_native_authenticated_wintun_ipv4":m3,
                     "native_minus_app_business":m3-app,
                     "host_udp_all_in_datagrams":udp,
                     "host_udp_minus_app_business":udp-app})
    candidate,baseline=rows
    if candidate["source"]!=baseline["source"] or not candidate["source"]:
        return {"status":"INCONCLUSIVE_BINARY_SOURCE_NOT_SAME"}
    if candidate["scenario_id"]!="plan027-c-normal-100m-25ms-loss0-60s" or baseline["scenario_id"]!="plan027-c-normal-10m-25ms-loss0-60s":
        return {"status":"INCONCLUSIVE_NOT_EXACT_10M_CONTROL_100M_CASE"}
    return {"status":"MEASURED_AGGREGATE_WINTUN_APP_COMPARISON_ONLY",
            "candidate":candidate,"control":baseline,
            "non_business_native_delta_vs_control":candidate["native_minus_app_business"]-baseline["native_minus_app_business"],
            "non_business_host_udp_delta_vs_control":candidate["host_udp_minus_app_business"]-baseline["host_udp_minus_app_business"],
            "interpretation":"SOURCE_GAP_OBSERVED_BUT_PRE_OR_POST_M3_NOT_PROVEN_BY_AGGREGATES",
            "host_udp_scope":"WINDOWS_GLOBAL_IPV4_NOT_PER_SOCKET",
            "oneway_latency":"NOT_MEASURED_CROSS_OS_CLOCKS"}
