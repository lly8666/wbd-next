"""H2290 actual original Windows Go+Rust Win32 process CPU attribution regression."""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2290_windows_hotpath_cpu as hot


class H2290ActualSignedWindowsCPU(unittest.TestCase):
    def rows(self,n=26):
        return [{
            "scope":hot.SCOPE,"monotonic_s":100.0+i,
            "native_pid":2211,
            "cpu_total_s":round(i*0.7,6),
            "cpu_kernel_s":round(i*0.3,6),
            "cpu_user_s":round(i*0.4,6),
            "working_set_bytes":123456+i,
            "thread_cpu":{"hottest_threads":[
                {"tid":17,"name":"wbd-native-tx","cpu_delta_s":.2,
                 "cpu_kernel_delta_s":.1,"cpu_user_delta_s":.1},
                {"tid":18,"name":"wbd-native-rx","cpu_delta_s":.1,
                 "cpu_kernel_delta_s":.04,"cpu_user_delta_s":.06},
                {"tid":19,"name":"","cpu_delta_s":.15,
                 "cpu_kernel_delta_s":.08,"cpu_user_delta_s":.07}
            ]}
        } for i in range(n)]

    def test_real_synthetic_counter_example_not_go_label(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"cpu.jsonl"
            p.write_text("".join(json.dumps(x)+"\n" for x in self.rows()))
            log=pathlib.Path(d)/"original-win-client.log"
            log.write_text("WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid=17\n"
                           "WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=RX tid=18\n")
            q=hot.original_window_cpu(p,101.0,125.0,512*1024*1024,log)
            self.assertEqual(q["status"],
                "MEASURED_ACTUAL_WINDOWS_ORIGINAL_PROCESS_WIN32_SAMPLED_BULK")
            self.assertEqual(q["samples_in_window"],25)
            self.assertEqual(q["native_pid"],2211)
            self.assertEqual(q["sample_span_s"],24)
            self.assertEqual(q["process_cpu_s"]["total"],16.8)
            self.assertEqual(q["process_cpu_s_per_actual_arm_gib"],33.6)
            self.assertEqual(q["rust_worker_os_tids_if_unambiguous"],{"TX":17,"RX":18})
            self.assertGreater(q["rust_tx_rx_top6_lower_bound_cpu_s"]["TX"],1)
            self.assertGreater(q["rust_tx_rx_top6_lower_bound_cpu_s"]["RX"],1)
            unknown=[t for t in q["hottest_os_threads_lower_bound"] if t["tid"]==19]
            self.assertEqual(unknown[0]["name"],None)
            self.assertEqual(unknown[0]["verified_rust_role"],None)
            self.assertIn("does not include driver", " ".join(q["limitations"]))

    def test_missing_or_foreign_pid_or_too_short_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"cpu.jsonl"
            with self.assertRaises(RuntimeError):
                hot.original_window_cpu(p,101,125,100)
            p.write_text("".join(json.dumps(x)+"\n" for x in self.rows(4)))
            with self.assertRaises(RuntimeError):
                hot.original_window_cpu(p,101,103,100)
            mixed=self.rows()
            mixed[12]["native_pid"]=999
            p.write_text("".join(json.dumps(x)+"\n" for x in mixed))
            with self.assertRaisesRegex(RuntimeError,"WINDOW_UNQUALIFIED"):
                hot.original_window_cpu(p,101,125,100)
            p.write_text("".join(json.dumps(x)+"\n" for x in self.rows()))
            with self.assertRaises(RuntimeError):
                hot.original_window_cpu(p,101,125,0)

    def test_real_product_two_triplets_handoff_and_win_cpu_capture_is_readonly(self):
        w=(ROOT/".github/workflows/qa-h2286-dual-original-windows-arm.yml").read_text()
        app=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertEqual(w.count("runs-on: windows-2025"),1)
        self.assertEqual(w.count("runs-on: ubuntu-24.04-arm"),3)
        self.assertIn("name: h2276-${{ matrix.group }}-client-result\n          path: h2276-out/",w)
        self.assertIn("name: h2290-${{ matrix.group }}-original-windows-hotpath-raw-evidence",w)
        self.assertIn("h2286-out/original-win-cpu.jsonl",w)
        self.assertNotIn("name: h2276-${{ matrix.group }}-client-result\n          path: |",w)
        self.assertIn('core.save(core.ROOT/"client-result.json",output)',app)
        self.assertIn("sample_windows_original_process",app)
        self.assertIn("original_window_cpu(",app)
        self.assertIn("win32_cpu_stop.set()",app)
        self.assertIn("relay_resource_delta(",app)
        self.assertIn('"tailscaled_pid_count_common"',app)
        self.assertIn("windows_original_go_rust_cpu_stage",app)
        self.assertIn("relay_tailscaled_and_host_cpu_stage",app)
        self.assertIn("H2289_ORIGINAL_WINDOWS_WINTUN_INNER_TCP_PORT45902_NOT_OUTER18727",app)
        self.assertIn("PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",app)
        self.assertNotIn("synthetic_tcp_success",app)


if __name__=="__main__":
    unittest.main()
