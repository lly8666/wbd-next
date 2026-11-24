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
        self.assertIn(ab.PATH_AB_SETTLEMENT_BASELINE,w)
        self.assertIn("$allowed=@('crates/wbd-engine/src/v4_windows_native_runtime.rs','crates/wbd-engine/src/v4_windows_owner.rs')",w)
        self.assertIn("firstsend_settlement_and_control_poll",w)
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

    def test_historical_and_incremental_baselines_remain_exact(self):
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_BASELINE}):
            self.assertEqual(ab.path_ab_baseline(),ab.PATH_AB_BASELINE)
            self.assertEqual(ab.path_ab_axis(),"firstsend_copy_and_M1_ready_batch")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_SETTLEMENT_BASELINE}):
            self.assertEqual(ab.path_ab_baseline(),ab.PATH_AB_SETTLEMENT_BASELINE)
            self.assertEqual(ab.path_ab_axis(),"firstsend_settlement_and_control_poll")
        with patch.dict("os.environ",{"WBD_H2321_BASELINE_SOURCE":"unapproved"}):
            with self.assertRaises(ValueError):
                ab.path_ab_baseline()

if __name__=="__main__":
    unittest.main()
