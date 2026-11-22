"""H2302: original Windows/ARM 2-8-2MiB, FEC/repair OFF; unit != product proof."""
import os, pathlib, subprocess, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class H2302WindowsArmTCPWindow(unittest.TestCase):
    def test_scoped_real_wbd_and_off_invariants(self):
        s=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        for marker in ('("A_base","B_window","A_prime_base")',
             "H2302_WINDOW_ALONE_WITH_FEC_REPAIR_OFF",
             "H2302_OUTER_REPAIR_MUST_REMAIN_OFF_ALL_STAGES",
             "H2302_WINDOWS_REAL_TCP_SOCKET_READBACK",
             "H2302_REAL_ARM_ACCEPTED_TCP_RCVBUF_NOT_APPLIED"):
            self.assertIn(marker,s)
    def test_test_app_override_only_and_bounded(self):
        env=dict(os.environ,WBD_H2286_PRODUCT_FULL_WIN_ARM="1",
                 WBD_H2302_WINDOW_ABA="1",WBD_H2302_INNER_TCP_TEST_BYTES="8388608")
        py="import sys;sys.path.insert(0,'tools');import m0_wl_loss_tcp_probe as p;print(p.WINDOW_TEST_BYTES)"
        a=subprocess.run([sys.executable,"-c",py],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(a.returncode,0,a.stderr)
        self.assertEqual(a.stdout.strip(),"8388608")
        env["WBD_H2302_INNER_TCP_TEST_BYTES"]="67108864"
        b=subprocess.run([sys.executable,"-c",py],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertNotEqual(b.returncode,0)
        self.assertIn("H2302_UNSUPPORTED_TEST_WINDOW",b.stderr)
    def test_real_three_runner_gates(self):
        s=(ROOT/".github/workflows/qa-h2302-win-arm-tcp-window-loss5.yml").read_text()
        for marker in ('WBD_H2302_WINDOW_ABA: "1"',
            'WBD_H2294_OFF_REPAIR_ABA: "0"',
            "[m0-029-h2302-window-loss5]",
            "H2302_TCP_WINDOW_THREE_REAL_LEGS_COMPLETE",
            "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
            "PASS_H2302_MEASURED_ORIGINAL_TCP_WINDOW_ABA_FEC_OFF_SCOPED",
            "client_owned_stop","kernel_relay_qdisc"):
            self.assertIn(marker,s)
if __name__=="__main__":unittest.main()
