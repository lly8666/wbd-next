"""H2294: true 3Runner FEC-OFF original one-shot outer repair counter-test.
No product/default modification: original Windows-to-ARM hot path/GoTLS/Stop.
"""
import os
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2286_full_windows_product as product


class H2294FecOffOriginalRepair(unittest.TestCase):
    def test_original_windows_fec_off_only_repair_policy_per_cold_leg(self):
        for loss in (1,5):
            for stage,repair in (("A_off","off"),("B_repair","on"),("A_prime_off","off")):
                with self.subTest(loss=loss,stage=stage), patch.dict(os.environ,{
                    "WBD_H2294_OFF_REPAIR_ABA":"1",
                    # Legacy H2293 name means the *same kernel netem test harness*.
                    "WBD_H2293_FEC_ABA":"1",
                    "WBD_H2293_FEC_STAGE":"off",
                    "WBD_H2293_WEAK_LOSS_PCT":str(loss),
                    "WBD_H2294_REPAIR_STAGE":repair
                }):
                    args=product.original_win_client_args(
                        "original-signed-go-tls","172.20.0.2",
                        pathlib.Path("original-arm-go-tls"))
                    value=lambda k:args[args.index(k)+1]
                    self.assertEqual(value("--outer-repair"),repair)
                    self.assertEqual(value("--fec.mode"),"off")
                    self.assertEqual(value("--fec-mode"),"off")
                    self.assertEqual(value("--fec-parity"),"0")
                    self.assertEqual(value("--lanes"),"1")

    def test_h2294_must_reject_any_fec_on_or_unexpected_policy(self):
        for stage,repair in (("fixed","on"),("off","twice")):
            with self.subTest(stage=stage,repair=repair), patch.dict(os.environ,{
                "WBD_H2294_OFF_REPAIR_ABA":"1",
                "WBD_H2293_FEC_ABA":"1",
                "WBD_H2293_WEAK_LOSS_PCT":"1",
                "WBD_H2293_FEC_STAGE":stage,
                "WBD_H2294_REPAIR_STAGE":repair}):
                with self.assertRaisesRegex(RuntimeError,"H2294_FEC_MUST_BE_OFF"):
                    product.original_win_client_args(
                        "original-exe","172.20.0.2",pathlib.Path("server"))
        with patch.dict(os.environ,{
            "WBD_H2294_OFF_REPAIR_ABA":"1",
            "WBD_H2293_FEC_ABA":"0",
            "WBD_H2293_FEC_STAGE":"off",
            "WBD_H2294_REPAIR_STAGE":"on",
            "WBD_H2293_WEAK_LOSS_PCT":"1"}):
            with self.assertRaisesRegex(RuntimeError,"H2294_REAL_BIDIR_NETEM"):
                product.original_win_client_args(
                    "original-exe","172.20.0.2",pathlib.Path("server"))

    def test_three_runner_source_locks_fec_off_real_transport_and_stop(self):
        relay=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        trial=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        self.assertIn('("A_off","B_repair","A_prime_off")',relay)
        for name in ("WBD_H2294_OFF_REPAIR_ABA","WBD_H2294_REPAIR_STAGE",
                     "H2294_FEC2_MUST_NEVER_BE_INSTALLED",
                     "H2294_ORIGINAL_NATIVE_REPAIR_POLICY_NOT_APPLIED",
                     "actual_original_native_frozen_repair_packets",
                     "H2294_FEC_OFF_MUST_NEVER_TURN_ON",
                     "H2294_FEC_OFF_REPAIR_THREE_REAL_LEGS_COMPLETE",
                     "PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP"):
            self.assertIn(name,trial)
        self.assertIn("true_windows_product(group,relay,arm,ready)",trial)
        self.assertIn("arm.check_server_and_run_app(group)",trial)
        self.assertIn("start_owned_wsl_liveness(group)",trial)
        self.assertIn("stop_owned_wsl_liveness(keeper,keeper_marker)",trial)
        self.assertIn('exec cat',trial)
        self.assertIn("child.stdin.close()",trial)
        self.assertIn("! kill -0 $pid",trial)

    def test_both_loss_tiers_use_two_real_isolated_triplets(self):
        for loss in (1,5):
            wf=(ROOT/f".github/workflows/qa-h2294-win-arm-fecoff-repair-loss{loss}.yml").read_text()
            self.assertEqual(wf.count("group: [a, b]"),3)
            self.assertEqual(wf.count("uses: tailscale/github-action@v4"),3)
            self.assertEqual(wf.count("runs-on: windows-2025"),2)
            self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"),3)
            self.assertIn('WBD_H2294_OFF_REPAIR_ABA: "1"',wf)
            self.assertIn('WBD_H2293_FEC_ABA: "1"',wf)
            self.assertIn(f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',wf)
            self.assertIn("PASS_H2294_MEASURED_FEC_OFF_OUTER_REPAIR_ABA_SCOPED",wf)
            self.assertIn("H2294_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",wf)
            self.assertIn("h2294-out/",wf)
            self.assertIn("git diff --name-only $compiled $env:GITHUB_SHA -- crates r0/go_overlay Cargo.toml Cargo.lock",wf)
            self.assertIn("H2294_FEC_OFF_REPAIR",wf)
            self.assertNotIn("default_go_rust_product_promoted':True",wf)


if __name__=="__main__":
    unittest.main()
