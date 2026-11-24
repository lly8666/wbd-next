"""H2321 source and profile isolation contract; not a native network PASS."""
import pathlib
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2292_true_product_ab as ab

class CurrentPathAB(unittest.TestCase):
    def test_current_rebuild_and_only_explicit_request(self):
        w=(ROOT/".github/workflows/qa-h2321-current-win-arm-path-ab.yml").read_text()
        self.assertIn("docs/requests/M0/qa-h2321-current-win-arm-path-ab.md",w)
        self.assertEqual(w.count("group: [a]"),3)
        self.assertIn(ab.PATH_AB_BASELINE,w)
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

if __name__=="__main__":
    unittest.main()
