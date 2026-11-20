"""H2240 no packet/PN/order/extra owner: genuine time-source negative fixtures."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "h2240",ROOT/"tools/m0_h2240_low_loss_timeline.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class RealOriginalTunM4TimingContracts(unittest.TestCase):
    @staticmethod
    def mock_case(start=10_000_000_000,end=30_000_000_000):
        return {"iperf_start_monotonic_ns":start,
                "iperf_end_monotonic_ns":end}

    @staticmethod
    def receipts(overflows=True,mixed_generation=False):
        lines=[]
        for i in range(85):
            t=10_200_000_000+i*225_000_000
            full=max(0,i-21)*5 if overflows else 0
            gen=2 if mixed_generation and i>=70 else 1
            lines.append(
                f"V4_PUBLIC_H2240_TUN_WINDOW mono_ns={t} generation={gen} "
                f"tun_batches={i*100} tun_observed={i*800} "
                f"delivered={i*600} backpressure={i*10} queue_full={full} "
                f"queue_age=0 queue_bytes=0 retired=0 "
                f"pending_packets={min(i%9,8)} oldest_pending_ns=9500 "
                "reader_single=1 no_hol=1")
        for i in range(38):
            t=10_250_000_000+i*510_000_000
            lines.append(
                f"V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG mono_ns={t} generation=1 "
                f"source_queued={i*700} m4_copied={i*680} "
                f"tx_err=0 tx_backpressure=0 tx_worker_cpu_ns={i*100_000_000}")
        return "\n".join(lines)

    def test_align_original_kernel_monotonic_and_real_200ms_500ms_cumulative(self):
        r,t=H.scoped_diagnostic(self.receipts(),self.mock_case(),"one")
        self.assertEqual(r["status"],"REAL_ORIGINAL_TUN200MS_AND_TX500MS_MONO_TICKS")
        self.assertEqual(r["tun_points"],85)
        self.assertEqual(r["tx_points"],38)
        self.assertEqual(r["max_queue_full_in_one_200ms_bucket"],5)
        self.assertEqual(r["read_packets_observed_in_case_buckets"],84*800)
        self.assertEqual(r["tx_copied_in_case_buckets"],37*680)
        self.assertTrue(r["no_packet_logging_or_ordering"])
        self.assertEqual(len(t["tun_200ms"]),84)
        self.assertEqual(len(t["m4_tx_500ms"]),37)

    def test_fail_closed_missing_real_timing_or_receipt_mixed_generation(self):
        for bad_case in ({},self.mock_case(start=30,end=20)):
            with self.assertRaisesRegex(RuntimeError,"REAL_MONOTONIC_INTERVAL"):
                H.scoped_diagnostic(self.receipts(),bad_case,"invalid")
        with self.assertRaisesRegex(RuntimeError,"TIME_BUCKETS_UNAVAILABLE"):
            H.scoped_diagnostic("nothing",self.mock_case(),"invalid")
        with self.assertRaisesRegex(RuntimeError,"GENERATION_MIXED"):
            H.scoped_diagnostic(self.receipts(mixed_generation=True),
                                self.mock_case(),"invalid")
        invalid=self.receipts().replace("reader_single=1","reader_single=0")
        with self.assertRaisesRegex(RuntimeError,"HOL_OR_READER"):
            H.scoped_diagnostic(invalid,self.mock_case(),"invalid")
        with self.assertRaisesRegex(RuntimeError,"REAL_NATIVE_RECEIPT"):
            H.numeric_receipts(
                "V4_PUBLIC_H2240_TUN_WINDOW mono_ns=123",
                H.TUN_MARKER,("mono_ns","queue_full"))

    def test_explicit_one_four_one_real_product_and_cold_only(self):
        self.assertEqual(H.PHASES,(
            ("one_flow_before",1),("four_flows",4),("one_flow_after",1)))
        script=(ROOT/"tools/m0_h2240_low_loss_timeline.py").read_text()
        platform=(ROOT/"tools/m0_h2234_local_netns.py").read_text()
        rust=(ROOT/"crates/wbd-engine/src/v4_embedded_go.rs").read_text()
        for original in (
            "node.start_client(1)","node.stop_client(1)",
            'node.iperf_case(', "V4_PUBLIC_H2240_TUN_WINDOW"):
            self.assertTrue(original in script or original in rust)
        self.assertIn("WBD_H2240_NATIVE_TEST",platform)
        self.assertIn("WBD_H2240_TUN_TIMELINE",platform)
        self.assertIn("WBD_PLAN028_EXTERNAL_STAGE_DIAG=1",platform)
        self.assertIn("WBD_H2240_TUN_TIMELINE",rust)
        self.assertIn("let mut pressure_ticks=0u32",rust)
        self.assertIn("pressure_ticks<240",rust)
        self.assertNotIn("ordered_wait",script)
        self.assertNotIn("new_reliable_outer",script)
        self.assertIn("all_original_queue_and_outer_repair_budgets_unchanged",script)

if __name__=="__main__":unittest.main()
