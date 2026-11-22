"""H2303 old multi-runner native TCP harness: source-locked CC only, not WBD product."""
import importlib
import os
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as tcp

class TrueKernelCCTriplets(unittest.TestCase):
    def test_3_same_loss1_stages_and_real_8mib_windows(self):
        with mock.patch.dict(os.environ, {"WBD_H2303_NATIVE_TCP_CC_AB":"1",
                                          "WBD_H2303_NATIVE_TCP_LOSS":"1",
                                          "WBD_H2281_SUSTAINED_TCP":"1"}):
            module=importlib.reload(tcp)
            self.assertEqual(module.active_stages(),
                ("cc_cubic_before","cc_bbr2_candidate","cc_cubic_after"))
            self.assertTrue(all(module.actual_loss_tier(s)==1
                                for s in module.active_stages()))
            module.prepare_tcp_sockbuf("cc_bbr2_candidate")
            self.assertEqual(module.tcp.WINDOW_TEST_BYTES,8*1024*1024)
            self.assertTrue(module.SUSTAINED)
            self.assertEqual(module.tcp.BULK_SEND_S,25)

    def test_no_original_mode_change_without_env(self):
        with mock.patch.dict(os.environ, {"WBD_H2303_NATIVE_TCP_CC_AB":"0",
                                          "WBD_H2281_SUSTAINED_TCP":"0"}):
            module=importlib.reload(tcp)
            self.assertFalse(module.CC_AB)
            self.assertEqual(module.active_stages(),(-1,0,1,5))

    def test_windows_bbr2_only_real_client_b_and_exact_restore(self):
        s=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        scoped=(ROOT/"tools/m0_h2302_windows_scoped_bbr2.py").read_text()
        wf=(ROOT/".github/workflows/qa-h2303-two-triplet-native-tcp-cc-loss1.yml").read_text()
        self.assertIn('tier=="cc_bbr2_candidate"',s)
        self.assertIn('scoped_bbr2_remoteport(PORT)',s)
        self.assertIn('with native_tcp_policy:',s)
        self.assertIn('H2303_CUBIC_BBR2_CUBIC_REAL_3RUNNER_RESULT',s)
        self.assertIn('"actual_socket_algorithm":"NOT_PROVEN_BY_TEMPLATE_READBACK"',s)
        self.assertIn('"delete","supplementalport"',scoped)
        self.assertIn('"congestionprovider="+original',scoped)
        self.assertIn('raise RuntimeError("H2303_EXACT_WINDOWS_BBR2_STOP_ROLLBACK_FAILED "',scoped)
        self.assertIn('WBD_H2303_NATIVE_TCP_LOSS: "1"',wf)
        self.assertIn('group: [a, b]',wf)
        self.assertIn('runs-on: windows-2025',wf)
        self.assertIn('runs-on: ubuntu-24.04-arm',wf)
        self.assertIn('tailscale/github-action@v4',wf)
        self.assertIn('H2303_TEST_ONLY_THREE_REAL_KERNEL_LOSS1_STAGES_STATIC_PASS',wf)

if __name__=="__main__":
    unittest.main()
