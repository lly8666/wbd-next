#!/usr/bin/env python3
"""Offline PLAN029 Windows Rust TX/RX CPU attribution from original Action ZIP.

The original Go EXE loads Rust DLL IN THE SAME PROCESS. GetProcessTimes is
NOT Go-language CPU. Native Rust itself logs the real Win32 TIDs at worker
start, so match those IDs to the existing 1Hz GetThreadTimes snapshots.
This is a read-only, lower-bound THREAD attribution, NOT flamegraph, ETW,
full driver/DPC CPU, or evidence of a new product run.
"""
import argparse
import json
import math
import pathlib
import re
import sys
import zipfile

SHA = re.compile(r"[0-9a-f]{40}\Z")
MARK = re.compile(r"WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=(TX|RX) tid=([1-9][0-9]*)\Z")
SAMPLES = "mode-results/normal/windows-original-go-rust-process-1hz.jsonl"
LOG = "mode-results/normal/client.log"


class EvidenceError(Exception):
    pass


def require(ok, detail):
    if not ok:
        raise EvidenceError(detail)


def _number(x, field):
    require(isinstance(x, (int, float)) and not isinstance(x, bool)
            and math.isfinite(x) and x >= 0, "invalid " + field)
    return float(x)


def worker_ids(original_client_log):
    tids = {}
    for line in original_client_log.splitlines():
        line = line.strip()  # original Windows logs can use CRLF
        m = MARK.fullmatch(line)
        if m:
            role, tid = m.group(1), int(m.group(2))
            require(role not in tids, "duplicate original Rust " + role + " TID")
            tids[role] = tid
    require(set(tids) == {"TX", "RX"} and tids["TX"] != tids["RX"],
            "missing/identical original Rust worker TIDs")
    return tids


def _read(z, name):
    try:
        return z.read(name).decode("utf-8")
    except (KeyError, UnicodeError) as e:
        raise EvidenceError("missing/invalid original artifact file: " + name) from e


def _sum_samples(rows, tids, begin=None, end=None):
    totals = {"TX": 0.0, "RX": 0.0}
    by_kernel = {"TX": 0.0, "RX": 0.0}
    by_user = {"TX": 0.0, "RX": 0.0}
    matched_counts = {"TX": 0, "RX": 0}
    all_threads = 0.0
    seen = 0
    for row in rows:
        when = row["monotonic_s"]
        if begin is not None and not (begin <= when <= end):
            continue
        seen += 1
        snapshot = row["thread_cpu"]
        require(snapshot["status"] == "MEASURED", "missing Win32 thread sample")
        all_threads += _number(snapshot["all_thread_cpu_delta_s"], "all-thread CPU")
        unique = set()
        for sample in snapshot["hottest_threads"]:
            tid = sample["tid"]
            require(tid not in unique, "duplicate TID within snapshot")
            unique.add(tid)
            for role in ("TX", "RX"):
                if tid == tids[role]:
                    total = _number(sample["cpu_delta_s"], role + " CPU")
                    user = _number(sample["cpu_user_delta_s"], role + " user CPU")
                    kernel = _number(sample["cpu_kernel_delta_s"], role + " kernel CPU")
                    require(abs(total - user - kernel) < 0.0001,
                            role + " kernel/user CPU does not sum to total")
                    totals[role] += total
                    by_kernel[role] += kernel
                    by_user[role] += user
                    matched_counts[role] += 1
    rust = totals["TX"] + totals["RX"]
    require(rust <= all_threads + 0.005, "matched Rust CPU exceeds all sampled threads")
    return {"samples": seen,
            "rust_tx_cpu_s_lower_bound": round(totals["TX"], 6),
            "rust_rx_cpu_s_lower_bound": round(totals["RX"], 6),
            "rust_tx_kernel_cpu_s_lower_bound": round(by_kernel["TX"], 6),
            "rust_tx_user_cpu_s_lower_bound": round(by_user["TX"], 6),
            "rust_rx_kernel_cpu_s_lower_bound": round(by_kernel["RX"], 6),
            "rust_rx_user_cpu_s_lower_bound": round(by_user["RX"], 6),
            "rust_combined_cpu_s_lower_bound": round(rust, 6),
            "all_thread_cpu_s_sampled": round(all_threads, 6),
            "rust_share_of_sampled_pct_lower_bound": round(100*rust/all_threads, 2)
                if all_threads else None,
            "worker_present_in_top_six_samples": matched_counts}


def analyse_zip(artifact, expected_source, action_conclusion="unknown"):
    require(SHA.fullmatch(expected_source) is not None,
            "expected 40-character lowercase SOURCE SHA")
    require(action_conclusion in ("success", "failure", "cancelled", "timed_out", "unknown"),
            "invalid GitHub Action conclusion")
    with zipfile.ZipFile(artifact) as z:
        report = json.loads(_read(z, "report.json"))
        require(report["source"] == expected_source, "original product SOURCE mismatch")
        require(report.get("mode_public") == "PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal",
                "original native Windows/WSL2 product mode not PASS")
        logs = _read(z, LOG)
        tids = worker_ids(logs)
        raw = _read(z, SAMPLES)
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    require(len(rows) >= 3, "insufficient 1Hz original process samples")
    require(len({row["native_pid"] for row in rows}) == 1,
            "multiple original Windows product PIDs")
    require(all(row["scope"] == "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
                for row in rows), "not original Go EXE and Rust DLL process")
    times = [row["monotonic_s"] for row in rows]
    require(all(a < b for a, b in zip(times, times[1:])),
            "original process samples not strictly ordered")
    cpu_total = _number(rows[-1]["cpu_total_s"] - rows[0]["cpu_total_s"],
                        "process lifetime sampled CPU delta")
    full = _sum_samples(rows, tids)
    require(full["rust_combined_cpu_s_lower_bound"] <= cpu_total + 0.05,
            "Rust thread CPU greater than process CPU")
    phases = {}
    rate = report.get("plan029_p2_mixed_real", {}).get("highrate_direct_tcp")
    if isinstance(rate, dict) and isinstance(rate.get("phase_windows"), dict):
        windows = rate["phase_windows"]
        require(windows["source_sha"] == expected_source,
                "high-rate phase source mismatch")
        for name, window in windows["windows"].items():
            begin, end = window["start_monotonic_s"], window["end_monotonic_s"]
            require(begin < end, "invalid phase times for " + name)
            phases[name] = _sum_samples(rows, tids, begin, end)
    # The Windows thread description API has historically failed on these
    # runners. TIDs are from the real Rust start log; never infer Go CPU
    # from a blank Win32 name or the label "other_threads".
    return {
        "scope": "EXACT_ORIGINAL_RUST_TX_RX_WINDOWS_TID_AND_1HZ_THREAD_CPU",
        "verdict": ("PASS_SCOPED_CPU_ATTRIBUTION" if action_conclusion == "success"
                    else "ACTION_RESULT_NOT_ATTESTED" if action_conclusion == "unknown"
                    else "ACTION_NOT_SUCCESS_REVIEW_REQUIRED"),
        "source_sha": expected_source,
        "action_conclusion": action_conclusion,
        "original_windows_product_pid": rows[0]["native_pid"],
        "rust_worker_windows_thread_ids": tids,
        "thread_names_usable": any(
            row["thread_cpu"].get("named_rust_workers", 0) > 0 for row in rows),
        "total": {**full, "original_process_cpu_s_in_sample_window": round(cpu_total, 6),
                  "rust_share_of_original_process_cpu_pct_lower_bound": round(
                      100*full["rust_combined_cpu_s_lower_bound"]/cpu_total, 2)
                      if cpu_total else None},
        "windows_highrate_phases": phases,
        "limits": ["THREAD_TOP_SIX_SNAPSHOT_LOWER_BOUND_NOT_ALL_THREADS",
                   "ONE_HZ_STAGE_BOUNDARY_APPROXIMATE_NOT_PER_PACKET_CPU",
                   "GO_EXE_AND_RUST_DLL_SAME_PID_NOT_GO_LANGUAGE_CPU",
                   "UNKNOWN_OTHER_THREADS_ARE_NOT_PROVEN_GO",
                   "EXCLUDES_MACHINE_WIDE_NDIS_DRIVER_ISR_DPC_CPU",
                   "NOT_OLD_VS_NEW_BINARY_CAUSAL_AB"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", help="original Windows/WSL2 native Action artifact ZIP")
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--action-conclusion", default="unknown",
                        choices=("success", "failure", "cancelled", "timed_out", "unknown"))
    args = parser.parse_args(argv)
    try:
        out = analyse_zip(args.artifact, args.expected_source, args.action_conclusion)
    except (EvidenceError, KeyError, TypeError, ValueError, OSError, zipfile.BadZipFile) as e:
        out = {"verdict": "INVALID_OR_UNVERIFIED_EVIDENCE", "reason": str(e)}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["verdict"] == "PASS_SCOPED_CPU_ATTRIBUTION" else 2


if __name__ == "__main__":
    sys.exit(main())
