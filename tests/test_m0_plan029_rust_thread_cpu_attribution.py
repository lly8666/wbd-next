"""No network/Windows dependency; test original Rust TID vs Win32 CPU proof."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from tools import m0_plan029_rust_thread_cpu_attribution as audit

SHA = "a" * 40


def sample(time, tx, rx, other=0, pid=42):
    threads = []
    for tid, value in ((111, tx), (222, rx), (333, other)):
        threads.append({"tid": tid, "name": "", "name_status": "HRESULT_10000000",
                        "cpu_delta_s": value, "cpu_user_delta_s": value / 2,
                        "cpu_kernel_delta_s": value / 2})
    return {"native_pid": pid, "scope": "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED",
            "monotonic_s": time, "cpu_total_s": (time - 10) * 10,
            "thread_cpu": {"status": "MEASURED", "named_rust_workers": 0,
                           "all_thread_cpu_delta_s": tx + rx + other,
                           "hottest_threads": threads}}


class RustWin32CPUAttribution(unittest.TestCase):
    def make_zip(self, *, source=SHA, log=None, rows=None, phase=True):
        if log is None:
            log = ("WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid=111\r\n"
                   "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=RX tid=222\r\n")
        if rows is None:
            rows = [sample(10, 0, 0), sample(11, 4, 2, 2),
                    sample(12, 3, 1, 2), sample(13, 0, 0)]
        report = {"source": source, "mode_public": "PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal",
                  "plan029_p2_mixed_real": {"highrate_direct_tcp": {
                      "phase_windows": {"source_sha": source, "windows": {
                          "oneway_500mbps": {"start_monotonic_s": 11, "end_monotonic_s": 12}}}}
                  } if phase else None}
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / "signed-original.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("report.json", json.dumps(report))
            z.writestr(audit.LOG, log)
            z.writestr(audit.SAMPLES, "\n".join(json.dumps(row) for row in rows))
        return td, path

    def test_original_explicit_win32_tid_attribution_with_broken_names(self):
        td, path = self.make_zip()
        with td:
            result = audit.analyse_zip(path, SHA, "success")
        self.assertEqual(result["verdict"], "PASS_SCOPED_CPU_ATTRIBUTION")
        self.assertEqual(result["rust_worker_windows_thread_ids"], {"TX": 111, "RX": 222})
        self.assertFalse(result["thread_names_usable"])
        self.assertEqual(result["total"]["rust_tx_cpu_s_lower_bound"], 7)
        self.assertEqual(result["total"]["rust_rx_cpu_s_lower_bound"], 3)
        self.assertEqual(result["total"]["all_thread_cpu_s_sampled"], 14)
        self.assertEqual(result["windows_highrate_phases"]["oneway_500mbps"]
                         ["rust_share_of_sampled_pct_lower_bound"], 71.43)
        self.assertIn("UNKNOWN_OTHER_THREADS_ARE_NOT_PROVEN_GO", result["limits"])

    def test_action_failure_is_never_auto_waived_even_if_logs_green(self):
        td, path = self.make_zip()
        with td:
            self.assertEqual(audit.analyse_zip(path, SHA, "failure")["verdict"],
                             "ACTION_NOT_SUCCESS_REVIEW_REQUIRED")
            self.assertEqual(audit.analyse_zip(path, SHA)["verdict"],
                             "ACTION_RESULT_NOT_ATTESTED")

    def test_original_product_source_strict_match(self):
        td, path = self.make_zip(source="b" * 40)
        with td, self.assertRaisesRegex(audit.EvidenceError, "SOURCE mismatch"):
            audit.analyse_zip(path, SHA, "success")

    def test_duplicate_or_missing_rust_thread_ids_rejected(self):
        for log in ("WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid=111\n",
                    "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid=111\n" * 2 +
                    "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=RX tid=222\n",
                    "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid=111\n" +
                    "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=RX tid=111\n"):
            td, path = self.make_zip(log=log)
            with td, self.assertRaises(audit.EvidenceError):
                audit.analyse_zip(path, SHA, "success")

    def test_no_fake_cpu_when_workers_not_in_sample_top_six(self):
        rows = [sample(10, 0, 0), sample(11, 0, 0, 2),
                sample(12, 0, 0, 2), sample(13, 0, 0)]
        td, path = self.make_zip(rows=rows)
        with td:
            result = audit.analyse_zip(path, SHA, "success")
        self.assertEqual(result["total"]["rust_combined_cpu_s_lower_bound"], 0)
        self.assertEqual(result["total"]["rust_share_of_sampled_pct_lower_bound"], 0)

    def test_duplicate_pid_and_missing_scope_fail_closed(self):
        rows = [sample(10, 0, 0), sample(11, 4, 2, 2),
                sample(12, 3, 1, 2, pid=99), sample(13, 0, 0)]
        td, path = self.make_zip(rows=rows)
        with td, self.assertRaisesRegex(audit.EvidenceError, "multiple original"):
            audit.analyse_zip(path, SHA, "success")

    def test_thread_cpu_cannot_exceed_all_sampled_cpu(self):
        rows = [sample(10, 0, 0), sample(11, 4, 2, 2),
                sample(12, 3, 1, 2), sample(13, 0, 0)]
        rows[1]["thread_cpu"]["all_thread_cpu_delta_s"] = 1
        td, path = self.make_zip(rows=rows)
        with td, self.assertRaisesRegex(audit.EvidenceError, "exceeds"):
            audit.analyse_zip(path, SHA, "success")

    def test_1hz_must_be_strictly_ordered(self):
        rows = [sample(10, 0, 0), sample(11, 4, 2, 2),
                sample(11, 3, 1, 2), sample(13, 0, 0)]
        td, path = self.make_zip(rows=rows)
        with td, self.assertRaisesRegex(audit.EvidenceError, "strictly ordered"):
            audit.analyse_zip(path, SHA, "success")


if __name__ == "__main__":
    unittest.main()
