"""H2304: validate six reverse TCP-window A/B/A' cases; tests are not product performance proof."""
import os
import pathlib
import subprocess
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

class H2304ReverseWindow(unittest.TestCase):
    def test_six_real_400ms_loss_comparisons_and_no_false_bbr_fec_claim(self):
        for mode,base,tuned in (("8to2",8,2),("16to8",16,8)):
            for loss in (0,1,5):
                with self.subTest(mode=mode,loss=loss):
                    f=ROOT/f".github/workflows/qa-h2304-{mode}-loss{loss}.yml"
                    wf=f.read_text()
                    for marker in (
                        f'WBD_H2302_BASE_BYTES: "{base*1048576}"',
                        f'WBD_H2302_TUNED_BYTES: "{tuned*1048576}"',
                        f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',
                        'WBD_H2302_WINDOW_ABA: "1"',
                        'WBD_H2294_OFF_REPAIR_ABA: "0"',
                        f"[m0-029-h2304-{mode}-loss{loss}]",
                        f"==[{base*1048576},{tuned*1048576},{base*1048576}]",
                        f"real_bidir_kernel_loss_pct']=={loss}",
                        "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
                        "PASS_H2302_MEASURED_ORIGINAL_TCP_WINDOW_ABA_FEC_OFF_SCOPED",
                        "original_rust_binary_identical_all_legs",
                        "client_owned_stop",
                        "kernel_relay_qdisc",
                        "200ms",
                        "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",
                        "H2302_ARCHIVED_WINDOWS_DLL_SOURCE_BOUNDARY_NOT_CURRENT_PRODUCT",
                        "H2302_ARCHIVED_ARM_SOURCE_BOUNDARY_NOT_CURRENT_PRODUCT",
                    ):
                        self.assertIn(marker,wf)

    def test_reverse_window_gate_and_zero_loss_preserves_fec_off(self):
        trial=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        win=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        core=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        for marker in (
            "(8*1024*1024,2*1024*1024)",
            "(16*1024*1024,8*1024*1024)",
            "H2304_UNSUPPORTED_2_8_16_MIB_WINDOW_CONTRAST",
            "H2302_WINDOW_ALONE_WITH_FEC_REPAIR_OFF",
            "H2302_WINDOWS_REAL_TCP_SOCKET_READBACK",
            "H2302_REAL_ARM_ACCEPTED_TCP_RCVBUF_NOT_APPLIED",
        ):
            self.assertIn(marker,trial)
        self.assertIn('(window_only and loss==0 and requested=="off")',win)
        self.assertIn("weak_loss in (-1,0,1,5)",win)
        self.assertIn("weak_loss if weak_loss>=0 else None",win)
        self.assertIn("delay = 0 if loss == -1 else 200",core)
        self.assertIn("if stage in (1, 5):",core)

    def test_original_test_socket_16mib_readback_intent(self):
        env=dict(os.environ,WBD_H2286_PRODUCT_FULL_WIN_ARM="1",
            WBD_H2302_WINDOW_ABA="1",WBD_H2302_INNER_TCP_TEST_BYTES="16777216")
        p=subprocess.run([sys.executable,"-c",
            "import sys;sys.path.insert(0,'tools');import m0_wl_loss_tcp_probe as p;print(p.WINDOW_TEST_BYTES)"],
            cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),"16777216")

if __name__=="__main__":
    unittest.main()
