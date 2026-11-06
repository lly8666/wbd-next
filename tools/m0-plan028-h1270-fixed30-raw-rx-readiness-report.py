#!/usr/bin/env python3
"""H1270 original protected raw RX readiness vs worker activity at 30% loss.

Use original 500ms client source counters. Multi-lease server log may
interleave multiple RX workers; don't fabricate per-Erin server counters.
"""
import json
import pathlib
import re
import sys

MARK="V4_PUBLIC_FEC2_EGRESS_DIAG role=client side=rx "
KEYS=("ns","raw_batches","rx_err","fec_source","fec_parity",
      "fec_recovered","tun_failure","poll_ready","poll_idle",
      "processed","max_loop_gap_ns","max_processing_ns","worker_cpu_ns")


def parse(path):
    rows=[]
    for line in pathlib.Path(path).read_text(errors="replace").splitlines():
        if MARK not in line:continue
        row={}
        for name in KEYS:
            m=re.search(r"\b"+name+r"=(\d+)",line)
            assert m,(name,line)
            row[name]=int(m.group(1))
        rows.append(row)
    assert len(rows)>50,(path,len(rows))
    for a,b in zip(rows,rows[1:]):
        assert b["ns"]>a["ns"]
        assert all(b[key]>=a[key] for key in KEYS[1:]),(a,b)
    return rows


def summarize(rows):
    adv=[i for i in range(1,len(rows))
         if rows[i]["raw_batches"]>rows[i-1]["raw_batches"]]
    assert len(adv)>10,"no actual original client raw kernel batches"
    left,right=adv[0],adv[-1]
    candidates=[]
    start=None
    for i in range(left,right+1):
        a,b=rows[i-1],rows[i]
        if b["raw_batches"]==a["raw_batches"]:
            if start is None:start=i-1
            beginning=rows[start]
            span=(b["ns"]-beginning["ns"])/1e9
            evidence={
                "duration_seconds":round(span,4),
                "worker_clock_interval_ns":[beginning["ns"],b["ns"]],
                "raw_received_batch_delta":0,
                "poll_ready_delta":b["poll_ready"]-beginning["poll_ready"],
                "poll_idle_delta":b["poll_idle"]-beginning["poll_idle"],
                "processed_delta":b["processed"]-beginning["processed"],
                "receive_error_delta":b["rx_err"]-beginning["rx_err"],
                "worker_cpu_ns_delta":b["worker_cpu_ns"]-beginning["worker_cpu_ns"],
                "loop_iteration_gap_max_ns":b["max_loop_gap_ns"],
                "receive_processing_max_ns":b["max_processing_ns"],
            }
            if span>=0.75:candidates.append(evidence)
        else:start=None
    last=rows[right]
    return {
       "number_500ms_samples":len(rows),
       "active_first_last_sample_indices":[left,right],
       "original_kernel_raw_receive_batches":last["raw_batches"],
       "native_rx_poll_ready_total":last["poll_ready"],
       "native_rx_poll_idle_total":last["poll_idle"],
       "native_processed_total":last["processed"],
       "max_owner_loop_gap_ns":last["max_loop_gap_ns"],
       "max_native_rx_processing_ns":last["max_processing_ns"],
       "at_least_750ms_no_raw_rx_candidates_count":len(candidates),
       "at_least_750ms_no_raw_rx_candidates_last_12":candidates[-12:],
       "scope_note":"No RAW RX progress does not itself prove remote underlay arrived or kernel drops. CPU and poll readiness are sampled counters; server session RX logs are interleaved and not per-client attributable."
    }


def main():
    root=pathlib.Path(sys.argv[1])
    plan=json.loads((root/"h1250-matrix-plan.json").read_text())
    report=json.loads((root/"h1250-five-client-report.json").read_text())
    assert plan["application_load_seconds"]==120
    assert plan["cold_socket_ab_mode"]=="default"
    assert set(report["clients"])=={"alice","erin"}
    diag=summarize(parse(root/"h1250-product-erin.log"))
    output={
        "schema_version":1,
        "source_sha":plan["source_sha"],
        "status":"ORIGINAL_M4_RX_SCOPED_120S_DIAGNOSTIC_COMPLETE",
        "actual_application_seconds":120,
        "original_client_native_FIXED6_RAW_RX":diag,
        "original_client_M4_TX_EAGAIN":report["clients"]["erin"]["socket_stop"]["eagain_turns"],
        "original_Fixed6_app_unique_delivery":report["clients"]["erin"]["directions"],
        "original_native_tc_qdisc":report["clients"]["erin"]["tc_actual"],
        "original_server_send_socket":report["server_socket_stop"],
        "limits":[
            "Hosted x86_64 same-source original Go TLS/Rust 2-client experiment only.",
            "A missing poll readiness is an FD state, not proof that peer successfully put a packet into the kernel network path.",
            "No cosmetic replays, FEC repair attempts or kernel-copied bytes count as unique application delivery.",
            "If no intermittent RX-blackout is reproduced, do not declare this rare bug solved."
        ]
    }
    (root/"h1270-rx-readiness-report.json").write_text(json.dumps(output,indent=2)+"\n")
    print("M0_H1270_FIXED30_ORIGINAL_RAW_RX_LOOP_READINESS_DIAGNOSTIC_COMPLETE "
          +json.dumps({"source":output["source_sha"],"RX":diag,
                       "TX_EAGAIN":output["original_client_M4_TX_EAGAIN"]}),flush=True)


if __name__=="__main__":
    main()
