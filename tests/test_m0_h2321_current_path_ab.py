"""H2321 source and profile isolation contract; not a native network PASS."""
import pathlib
import sys
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2292_true_product_ab as ab

class CurrentPathAB(unittest.TestCase):
    def test_current_rebuild_and_only_explicit_request(self):
        w=(ROOT/".github/workflows/qa-h2321-current-win-arm-path-ab.yml").read_text()
        self.assertIn("docs/requests/M0/qa-h2321-current-win-arm-path-ab.md",w)
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertIn(ab.PATH_AB_LOAN_BASELINE,w)
        self.assertIn("$allowed=@('crates/wbd-platform/src/ipv4_tcp.rs')",w)
        self.assertIn("outbound_checksum_wide",w)
        self.assertIn("git worktree add --detach h2321-baseline",w)
        self.assertIn("tools/prepare_windows_wiring.py",w)
        self.assertIn("tools/m0_plan029_linux_dual_native_build.sh",w)
        self.assertIn("h2311_windows_npf_trace",w)
        self.assertNotIn("gh run download 449",w)
        self.assertNotIn("WBD_H2286_ARM_PRODUCT_FROZEN_SOURCE:",w)
        self.assertIn("H2321_NOT_ISOLATED_TX_SOURCE_DELTA",w)
        self.assertIn("x['h2312_npf_service']['npf_queue_packets']==8",w)
        self.assertIn("x['h2312_npf_service']['npf_queue_bytes']==16384",w)
        self.assertIn("PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP",w)
        self.assertEqual(ab.LEGS,("A_default","B_tx16","A_prime"))
        self.assertTrue(ab.PATH_AB_FEATURES.endswith(",h2311_windows_npf_trace"))

    def test_parallel_profile_source_and_feature_isolation(self):
        w=(ROOT/".github/workflows/qa-h2338-current-win-arm-profile-ab.yml").read_text()
        self.assertIn("h2338-profile-",w)
        self.assertIn("WBD_PATH_AB_AXIS: tx16_npf64_profile",w)
        self.assertEqual(w.count("--manifest-path h2321-baseline/Cargo.toml"),2)
        self.assertIn("[65536 if tag.startswith('B_') else 16384 for tag in order]",w)
        self.assertIn("[16 if tag.startswith('B_') else 8 for tag in order]",w)
        self.assertIn("bb=dict(source_sha=base",w)
        self.assertIn("h2291_windows_tx_service",w)

    def test_counterbalanced_order_and_drift_receipt(self):
        with patch.dict("os.environ",{},clear=True):
            self.assertEqual(ab.ordered_legs("a"),ab.LEGS)
        with patch.dict("os.environ",{"WBD_PATH_AB_CROSSOVER":"1"},clear=True):
            self.assertEqual(ab.ordered_legs("a"),("A_default","B_tx16","B_prime","A_prime"))
            self.assertEqual(ab.ordered_legs("b"),("B_tx16","A_default","A_prime","B_prime"))
            def row(tag,rate):
                return dict(candidate_enabled=ab.is_candidate(tag),tcp_mbps=rate,p99_ms=200,
                    windows_original_process_cpu_s_per_gib=20,windows_original_rust_tx_cpu_lower_bound=10,
                    arm_rx_bytes=2**30)
            for group,rates in (("a",[200,220,180,160]),("b",[220,200,160,180])):
                s=ab.summarize_legs([row(tag,r) for tag,r in zip(ab.ordered_legs(group),rates)])
                self.assertEqual(s["B_vs_same_vm_baseline_goodput_pct"],11.111)
                self.assertEqual(s["baseline_goodput_spread_pct"],22.222)
                self.assertEqual(s["paired_adjacent_goodput_pct"],[10.0,12.5])

    def test_historical_and_incremental_baselines_remain_exact(self):
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_BASELINE},clear=True):
            self.assertEqual(ab.path_ab_baseline(),ab.PATH_AB_BASELINE)
            self.assertEqual(ab.path_ab_axis(),"firstsend_copy_and_M1_ready_batch")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_SETTLEMENT_BASELINE},clear=True):
            self.assertEqual(ab.path_ab_baseline(),ab.PATH_AB_SETTLEMENT_BASELINE)
            self.assertEqual(ab.path_ab_axis(),"firstsend_settlement_and_control_poll")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_QUEUE_BASELINE},clear=True):
            self.assertEqual(ab.path_ab_baseline(),ab.PATH_AB_QUEUE_BASELINE)
            self.assertEqual(ab.path_ab_axis(),"direct_npf_queue_staging")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_SETTLEMENT_BASELINE,"WBD_PATH_AB_AXIS":"native_off_loan"},clear=True):
            self.assertEqual(ab.path_ab_axis(),"native_off_loan")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_SETTLEMENT_BASELINE,"WBD_PATH_AB_AXIS":"tx16_npf64_profile"},clear=True):
            self.assertEqual(ab.path_ab_candidate_source(),ab.PATH_AB_SETTLEMENT_BASELINE)
            self.assertTrue(ab.path_ab_candidate_features().endswith(",h2291_windows_tx_service"))
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_LOAN_BASELINE},clear=True):
            self.assertEqual(ab.path_ab_axis(),"arena_ready_batch")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_LOAN_BASELINE,"WBD_PATH_AB_AXIS":"outbound_checksum_wide"},clear=True):
            self.assertEqual(ab.path_ab_axis(),"outbound_checksum_wide")
            self.assertEqual(ab.path_ab_candidate_source(),ab.CANDIDATE_BUILD_SHA)
            self.assertEqual(ab.path_ab_candidate_features(),ab.PATH_AB_FEATURES)
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":"unapproved"},clear=True):
            with self.assertRaises(ValueError):
                ab.path_ab_baseline()

if __name__=="__main__":
    unittest.main()
