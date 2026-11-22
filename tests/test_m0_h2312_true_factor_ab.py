"""H2312 source-locked true Windows NPF-only/TX-only A/B/A' on H2292 harness.

Local contract checks cannot count as real Wintun/Npcap/TUN throughput qualification.
"""
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2292_true_product_ab as trial


class H2312SingleFactor(unittest.TestCase):
    def test_preserves_h2292_three_real_sessions_and_original_full_product(self):
        w=(ROOT/".github/workflows/qa-h2292-true-windows-rust-aba.yml").read_text()
        trial_source=(ROOT/"tools/m0_h2292_true_product_ab.py").read_text()
        product=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertEqual(trial.LEGS,("A_default","B_tx16","A_prime"))
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertIn("h2312_factor:",w)
        self.assertIn("[m0-029-h2312-npf]",w)
        self.assertIn("[m0-029-h2312-tx]",w)
        self.assertIn("H2312_SOURCE_LOCKED_DUAL_DLLS_COMPILED_FROM_SAME_COMMIT",w)
        self.assertIn("H2312_TRUE_SAME_SOURCE_SINGLE_FACTOR_DLL_PAIR_VERIFIED",w)
        self.assertIn("cargo +1.85.1 build --locked --release -p wbd-engine --features $aFeatures",w)
        self.assertIn("cargo +1.85.1 build --locked --release -p wbd-engine --features $bFeatures",w)
        self.assertIn("H2312_NPF8_16_TRACE",w)
        self.assertIn("H2312_NPF16_64_TRACE",w)
        self.assertIn("H2312_ORIGINAL_DRIVER_REAL_ACTUAL_TRACE_NOT_MATCHED",trial_source)
        self.assertIn("if factor=='legacy':",w)
        self.assertIn("expected=[8,16,8] if factor=='npf_only' else [16,16,16]",w)
        self.assertIn("x['h2312_npf_service']['queue_short_calls']==0",w)
        self.assertIn("assert d['client_owned_stop']=='PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP'",w)
        self.assertIn("H2312_CANDIDATE_NATIVE_OWNER_STOP_TRACE_ABSENT",product)
        self.assertIn("arm_rx_bytes",trial_source)
        self.assertIn("client_owned_stop",trial_source)
        self.assertIn("queue_bytes_copied",trial_source)
        self.assertIn('trace["queue_calls"]>0',trial_source)
        self.assertNotIn("MOCK_PRODUCT_PASS",trial_source)

    def test_opt_in_profiles_and_exact_stop_trace(self):
        with patch.dict(trial.os.environ,{"WBD_H2312_FACTOR":"npf_only"}):
            self.assertEqual(trial.h2312_mode(),"npf_only")
        with patch.dict(trial.os.environ,{"WBD_H2312_FACTOR":"tx_only"}):
            self.assertEqual(trial.h2312_mode(),"tx_only")
        self.assertIsNone(trial.h2312_profile("Not a native driver stop"))
        self.assertIsNone(trial.h2312_profile("PLAN029_H2311_NPF_STOP_PROFILE queue_calls=1"))
        fields=("queue_calls","queue_frames_submitted","queue_bytes_submitted",
                "queue_bytes_copied","queue_short_calls","direct_calls",
                "direct_bytes_submitted","direct_frames_accepted","direct_errors",
                "npf_queue_bytes","npf_queue_packets")
        line="PLAN029_H2311_NPF_STOP_PROFILE "+" ".join(
            f"{f}={i+1}" for i,f in enumerate(fields))
        result=trial.h2312_profile(line)
        self.assertEqual(len(result),11)
        self.assertEqual(result["npf_queue_packets"],11)


if __name__=="__main__":
    unittest.main()
