"""W167 deterministic request contracts: no remote jobs, native product untouched."""
import tempfile
import unittest
from pathlib import Path
from tools.network_harness.fec_w167_dual_arch_matrix import (
    MODES, LOSSES, _config, timeline_cpu, analyze)


class W167MatrixContracts(unittest.TestCase):
    def test_56_native_matrix_cases_and_outer_on(self):
        self.assertEqual(len(MODES), 7)
        self.assertEqual(LOSSES, (1,5,15,30))
        for arch in ("arm64","amd64"):
            for name, mode, game_fec, profile in MODES:
                for loss in LOSSES:
                    c=_config(name,mode,game_fec,profile,loss,"a"*40,123456,arch)
                    self.assertTrue(c["product"]["repair_enabled"])
                    self.assertEqual(c["phases"][0]["seconds"],20)
                    self.assertEqual(c["traffic"]["c2s_mbps"],10)
                    self.assertEqual(c["traffic"]["s2c_mbps"],10)
                    self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],loss)
                    self.assertEqual(c["phases"][0]["s2c"]["loss_pct"],loss)
                    self.assertEqual(c["network"]["lane_loss"],"shared")
                    self.assertEqual(c["bundles"]["A"]["source"],"a"*40)
                    self.assertNotIn("artifact_id",c["bundles"]["A"])

    def test_rust_thread_cpu_is_partial_not_go_rust_split(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"log"
            p.write_text(
                "V4_PUBLIC_TIMELINE role=client unix_ns=1 rust_rx_cpu_ns=100 "
                "rust_tx_cpu_ns=200 first_wire_bytes=100 repair_wire_bytes=0\n"
                "V4_PUBLIC_TIMELINE role=client unix_ns=2 rust_rx_cpu_ns=1000000100 "
                "rust_tx_cpu_ns=2000000200 first_wire_bytes=200 repair_wire_bytes=50\n")
            out=timeline_cpu(p)
            self.assertEqual(out["status"],"RUST_NATIVE_RX_TX_THREADS_ONLY_WHOLE_TIMELINE")
            self.assertAlmostEqual(out["rust_rx_tx_sum_cpu_s"],3)

    def test_outer_wire_data_fraction_excludes_game_copies(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            leg={"result":"PASS_SCOPED_OBSERVATION","request_id":"W167_arm64_normal_maximum6_30IID",
                 "telemetry":{"outer_repair_native_verified":True,
                              "counters":{"client":{"first_wire_bytes":900,
                                                   "repair_accepted_wire_bytes":100,
                                                   "repair_uncertain_wire_bytes":0},
                                          "server":{"first_wire_bytes":900,
                                                   "repair_accepted_wire_bytes":100,
                                                   "repair_uncertain_wire_bytes":0}}}}
            x=analyze(p,leg)
            self.assertEqual(x["cpu_memory_outer"]["client"]["outer_retransmission_fraction"]["repair_over_first_plus_repair_pct"],10)
            leg["request_id"]="W167_arm64_game4_fixed6_30IID"
            x=analyze(p,leg)
            self.assertEqual(x["cpu_memory_outer"]["client"]["outer_retransmission_fraction"]["status"],
                             "NOT_APPLICABLE_GAME_FIRST_LANE_COPIES_ARE_NOT_OUTER_RETRANSMISSION")


if __name__ == "__main__":
    unittest.main()
