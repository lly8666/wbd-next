"""Read-only thread CPU audit must never invent Go/Rust ownership."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.m0_wl_windows_cpu_audit import summarize_windows_cpu

class CpuAuditTests(unittest.TestCase):
    def test_exact_kernel_user_and_unnamed_threads_not_rust_or_go(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"cpu.jsonl"
            def row(t,total,kern,user,delta,dk,du):
                return {
                    "scope":"SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED",
                    "native_pid":42,"monotonic_s":t,"cpu_total_s":total,
                    "cpu_kernel_s":kern,"cpu_user_s":user,
                    "working_set_bytes":2_000_000,"private_bytes":3_000_000,
                    "thread_cpu":{"thread_name_status_counts":{"EMPTY":2},
                     "rust_tx_cpu_delta_s":0,"rust_rx_cpu_delta_s":0,
                     "rust_tx_kernel_delta_s":0,"rust_tx_user_delta_s":0,
                     "rust_rx_kernel_delta_s":0,"rust_rx_user_delta_s":0,
                     "hottest_threads":[{
                       "tid":11,"name":"","name_status":"EMPTY",
                       "cpu_delta_s":delta,"cpu_kernel_delta_s":dk,
                       "cpu_user_delta_s":du}]}}
            p.write_text("\n".join(json.dumps(x) for x in
                [row(1,0,0,0,0,0,0),row(2,0.3,0.2,0.1,0.3,0.2,0.1),
                 row(3,0.8,0.5,0.3,0.5,0.3,0.2)]))
            got=summarize_windows_cpu(p)
            self.assertEqual(got["status"],"MEASURED_PROCESS_AND_UNATTRIBUTED_THREADS")
            self.assertEqual(got["process_cpu_s"],{"total":0.8,"kernel":0.5,"user":0.3})
            self.assertEqual(got["top_threads_by_lower_bound_cpu"][0]["name"],None)
            self.assertEqual(got["top_threads_by_lower_bound_cpu"][0]["kernel_s_lower_bound"],0.5)
            self.assertEqual(got["thread_name_status_counts_observation_sum"]["EMPTY"],6)
    def test_no_data_and_malformed_do_not_proclaim_zero_cpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"missing.jsonl"
            self.assertEqual(summarize_windows_cpu(p)["status"],"NOT_MEASURED_FILE_MISSING")
            p.write_text("{bad JSON")
            self.assertEqual(summarize_windows_cpu(p)["status"],"INCONCLUSIVE_MALFORMED_SAMPLE")
    def test_wrong_pid_is_not_aggregated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"cpu.jsonl"
            p.write_text("\n".join(json.dumps({"scope":
                "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED",
                "native_pid":i,"monotonic_s":i,"cpu_total_s":i,
                "cpu_kernel_s":0,"cpu_user_s":i})
                for i in range(1,4)))
            self.assertEqual(summarize_windows_cpu(p)["status"],"INCONCLUSIVE_PROCESS_SCOPE")

if __name__=="__main__":unittest.main()
