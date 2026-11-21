"""H2287 passive real original ARM Rust TUN TCP SYN/RST and listener witness."""
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2287_tun_tcp_trace as trace


class H2287OriginalTunnelKernelTCPHeaders(unittest.TestCase):
    def test_trace_is_read_only_kernel_tun_no_synthetic_tcp_data(self):
        source=(ROOT/"tools/m0_h2287_tun_tcp_trace.py").read_text()
        self.assertEqual(trace.IFACE,"wbds0")
        self.assertEqual(trace.PORT,45902)
        self.assertIn("socket.AF_PACKET",source)
        self.assertIn("socket.SOCK_DGRAM",source)
        self.assertIn("sock.recvfrom",source.replace("s.recvfrom","sock.recvfrom"))
        self.assertNotIn(".sendto(",source)
        self.assertNotIn(".sendall(",source)
        self.assertNotIn("subprocess.Popen",source)
        self.assertIn("listener_45902_actual_ss",source)
        self.assertIn("AttemptFails",source)
        self.assertIn("OutRsts",source)
        self.assertIn("tcp_payload_not_collected",source)
        self.assertIn("header_samples",source)
        self.assertIn("H2287_REAL_ARM_RUST_TUN_TCP_LISTENING_AND_PASSIVE_CAPTURE_READY",source)

    def test_h2286_requires_passive_real_kernel_readback_and_long_remote_accept(self):
        arm=(ROOT/"tools/m0_h2286_arm_product.py").read_text()
        work=(ROOT/".github/workflows/qa-h2286-dual-original-windows-arm.yml").read_text()
        probe=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        self.assertIn("tools/m0_h2287_tun_tcp_trace.py",arm)
        self.assertIn("H2287_TUN_PASSIVE_TRACE_MISSING",arm)
        self.assertIn("h2286-out/tcp-passive-headers.json",work)
        self.assertIn("h2286-out/tcp-passive-trace.log",work)
        self.assertIn("tests.test_m0_h2287_tun_tcp_trace",work)
        self.assertIn('LISTENER_ACCEPT_TIMEOUT_S = 120 if os.environ.get("WBD_H2286_PRODUCT_FULL_WIN_ARM") == "1" else 35',probe)
        self.assertIn("listener.settimeout(LISTENER_ACCEPT_TIMEOUT_S)",probe)
        self.assertNotIn("WBD_REPLACE_PRODUCT_TCP",arm)


if __name__=="__main__":
    unittest.main()
