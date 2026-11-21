"""H2293 real dual Windows2025 Npcap/Wintun→ARM FEC2 OFF/fixed/OFF.

Unit tests prove the exact configured trial and fail-closed source mapping;
only Actions with native 2x3 signed-driver product can attest application data.
"""
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as core
import m0_h2286_full_windows_product as original
import m0_h2293_true_product_fec_loss as trial


class H2293OriginalWindowsFecLoss(unittest.TestCase):
    def test_both_loss_modes_are_exact_original_windows_carrier_and_fec2(self):
        for loss,profile in ((1,"light"),(5,"mild")):
            for stage in ("off","fixed"):
                with self.subTest(loss=loss,stage=stage), patch.dict(os.environ,{
                    "WBD_H2293_FEC_ABA":"1",
                    "WBD_H2293_WEAK_LOSS_PCT":str(loss),
                    "WBD_H2293_FEC_STAGE":stage}):
                    args=original.original_win_client_args("original-windows-exe",
                        "172.20.0.2",pathlib.Path("real-arm-product-ready"))
                    def flag(f):
                        return args[args.index(f)+1]
                    self.assertEqual(flag("--lanes"),"1")
                    self.assertEqual(flag("--fec.mode"),stage)
                    self.assertEqual(flag("--fec.profile"),profile if stage=="fixed" else "strong")
                    self.assertEqual(flag("--fec-mode"),"fixed" if stage=="fixed" else "off")
                    self.assertEqual(flag("--fec-parity"),"4" if stage=="fixed" else "0")
                    self.assertEqual(flag("--outer-repair"),"off")
        with patch.dict(os.environ,{"WBD_H2293_FEC_ABA":"1",
                                     "WBD_H2293_WEAK_LOSS_PCT":"0"}):
            with self.assertRaisesRegex(RuntimeError,"H2293_FEC_COLD_MODE"):
                original.original_win_client_args("original-exe","172.20.0.2",
                                                pathlib.Path("source-locked-server"))
        # All original H2292 mode remains intact with no opt-in.
        with patch.dict(os.environ,{"WBD_H2293_FEC_ABA":"0"}):
            args=original.original_win_client_args("original-exe","172.20.0.2",
                                                   pathlib.Path("source-locked-server"))
            self.assertEqual(args[args.index("--fec.mode")+1],"off")

    def test_real_relay_three_stage_order_both_fec_and_legacy(self):
        # Control server reads the explicit same-workflow env BEFORE owning
        # authenticated source-locked ARM readiness and Windows peer queries.
        source=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        self.assertIn('("A_off","B_fixed","A_prime_off")',source)
        self.assertIn('("A_default","B_tx16","A_prime")',source)
        self.assertIn('"WBD_H2293_FEC_ABA"',source)
        self.assertIn("H2292_AUTH_WINDOWS_PEER",source)
        self.assertIn("H2292_AUTH_ARM_READY_OR_ORDER",source)
        self.assertEqual(trial.LEGS,("A_off","B_fixed","A_prime_off"))
        self.assertEqual(trial.ROOT,pathlib.Path("h2293-out"))

    def test_same_original_tx16_rust_and_true_fec_applied_dont_forge_success(self):
        code=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        self.assertIn("tuned=True",code)
        self.assertIn('fec_fixed=(tag=="B_fixed")',code)
        self.assertIn('os.environ["WBD_H2293_FEC_STAGE"]="fixed" if fec_fixed else "off"',code)
        self.assertIn("WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile=",code)
        self.assertIn("ORIGINAL_WINDOWS_FEC2_COLD_APPLIED_MUST_MATCH_REAL_LEG",code)
        self.assertIn("core.remote_shape(relay_ready,FEC_LOSS)",code)
        self.assertIn("real_kernel_drop_counts",code)
        self.assertIn("true_windows_product(group,relay,arm,ready)",code)
        self.assertIn("arm.check_server_and_run_app(group)",code)
        self.assertIn("PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP",code)
        self.assertIn("original_rust_binary_identical_all_legs",code)
        self.assertIn("shutil.copy2(ORIGINAL,BINARY)",code)
        self.assertNotIn("MOCK_PRODUCT_PASS",code)

    def test_1and5_two_independent_triplets_run_exact_source_and_true_stop(self):
        for loss in (1,5):
            path=ROOT/f".github/workflows/qa-h2293-win-arm-fec2-loss{loss}.yml"
            wf=path.read_text()
            self.assertEqual(wf.count("group: [a, b]"),3)
            self.assertEqual(wf.count("runs-on: windows-2025"),2)
            self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"),3)
            self.assertEqual(wf.count("uses: tailscale/github-action@v4"),3)
            self.assertEqual(wf.count(f"[m0-029-h2293-fec2-loss{loss}]"),5)
            self.assertIn('WBD_H2293_FEC_ABA: "1"',wf)
            self.assertIn(f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',wf)
            self.assertIn('WBD_H2292_TRUE_PRODUCT_ABA: "1"',wf)
            self.assertIn('WBD_H2292_COMPILED_SOURCE_SHA: "dc2da4b98ecc419a67e3e2ee6530f944b78d88ef"',wf)
            self.assertIn("git diff --name-only $compiled $env:GITHUB_SHA -- crates r0/go_overlay Cargo.toml Cargo.lock",wf)
            self.assertIn('gh run download 44949570906',wf)
            self.assertIn("h2293_true_product_fec_loss.py arm",wf)
            self.assertIn("h2293_true_product_fec_loss.py client",wf)
            self.assertEqual(wf.count("['A_off','B_fixed','A_prime_off']"),2)
            self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",wf)
            self.assertIn("intentional_netem_drops",wf)
            self.assertIn("real_kernel_drop_counts",wf)
            self.assertIn("fec2_genuine_rust_owner_applied_readback",wf)
            self.assertIn("client_owned_stop",wf)
            self.assertIn("h2293-out/",wf)
            self.assertIn("H2286_ARM_ORIGINAL_GO_TLS_RUST_AND_TRUE_AF_PACKET_TUN_READY",wf)
            self.assertIn("NOT measured here",wf)
            self.assertNotIn("PASS_FULL_PRODUCT_THROUGHPUT",wf)
            # Source/identity artifacts MUST go up before slow signed driver.
            peer=wf.index("      - name: Publish real Windows VM identity")
            upload=wf.index("          name: h2276-${{ matrix.group }}-client-peer")
            wsl=wf.index("      - name: Boot real Windows-owned Ubuntu WSL2 kernel")
            driver=wf.index("      - name: Real signed Npcap 1.88")
            self.assertLess(peer,upload)
            self.assertLess(upload,wsl)
            self.assertLess(wsl,driver)


if __name__=="__main__":
    unittest.main()
