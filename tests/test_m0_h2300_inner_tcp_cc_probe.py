"""H2300 regression: no host-global BBR, no FakeTCP/outer congestion claim."""
import os
import pathlib
import socket
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import m0_h2300_inner_tcp_cc_probe as cc


class InnerKernelTCPCC(unittest.TestCase):
    def test_reject_unsupported_or_overreach_policy(self):
        if sys.platform != "linux":
            self.skipTest("real Linux kernel TCP_CONGESTION required")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            with self.assertRaisesRegex(RuntimeError, "UNSUPPORTED_TEST_CC"):
                cc.set_linux_socket_cc_verified(s, "bbr2")
        self.assertFalse(hasattr(cc, "set_windows_global_cc"))
        self.assertFalse(hasattr(cc, "set_linux_global_sysctl"))

    @unittest.skipUnless(sys.platform == "linux", "Linux kernel only")
    def test_linux_real_kernel_readback_is_not_outer_faketcp(self):
        d = cc.probe_linux()
        self.assertIn(d["new_socket_before"], d["available"])
        self.assertEqual(d["new_socket_before"], d["kernel_default"])
        self.assertFalse(d["persistent_global_setting_changed"])
        self.assertFalse(d["proof_of_3runner_or_original_WBD_application"])
        # No sudo, no sysctl, no outer tunnel changes, exact real socket.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            before = cc.get_linux_socket_cc(s)
            result = cc.set_linux_socket_cc_verified(s, before)
            self.assertEqual(result["applied"], before)
            self.assertEqual(result["scope"],
                             "ONE_OWNED_KERNEL_TCP_SOCKET_NOT_WBD_FAKETCP")

    def test_windows_only_read_queries_never_set(self):
        source = (ROOT/"tools/m0_h2300_inner_tcp_cc_probe.py").read_text()
        self.assertIn('"supplementalports"', source)
        self.assertIn('"show", "supplemental"', source)
        self.assertNotIn('"set", "supplemental"', source)
        self.assertNotIn('"add", "supplementalport"', source)
        self.assertNotIn("sysctl -w", source)
        self.assertIn("effective_bbr2_on_specific_socket", source)
        self.assertIn('"NOT_PROVEN"', source)


if __name__ == "__main__":
    unittest.main()
