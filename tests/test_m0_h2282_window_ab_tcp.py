"""H2282: same-VM A/B/Aprime explicit socket buffer request, Windows/ARM real readback."""
import pathlib
import socket
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as h


class RealTCPWindowAB(unittest.TestCase):
    def test_exact_three_independent_native_stages(self):
        self.assertTrue(h.WINDOW_AB)
        self.assertTrue(h.SUSTAINED)
        self.assertEqual(h.active_stages(),("base","tuned","base_prime"))
        self.assertEqual([h.actual_loss_tier(x) for x in h.active_stages()],[0,0,0])
        self.assertEqual(h.tcp.BULK_MAX_BYTES,512*1024*1024)
        self.assertEqual(h.tcp.BULK_SEND_S,25)
        self.assertEqual(h.tcp.ECHO_COUNT,160)

    def test_real_local_os_socket_option_readback_for_tuned_leg(self):
        previous=h.tcp.WINDOW_TEST_BYTES
        try:
            h.prepare_tcp_sockbuf("base")
            self.assertEqual(h.tcp.WINDOW_TEST_BYTES,0)
            h.prepare_tcp_sockbuf("tuned")
            self.assertEqual(h.tcp.WINDOW_TEST_BYTES,8*1024*1024)
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                before=h.tcp._read_socket_buffers(sock)
                actual=h.tcp._maybe_set_buffers(sock)
                self.assertEqual(before["requested_bytes"],8*1024*1024)
                self.assertEqual(actual["requested_bytes"],8*1024*1024)
                self.assertGreater(actual["sndbuf_os"],0)
                self.assertGreater(actual["rcvbuf_os"],0)
            h.prepare_tcp_sockbuf("base_prime")
            self.assertEqual(h.tcp.WINDOW_TEST_BYTES,0)
        finally:
            h.tcp.WINDOW_TEST_BYTES=previous

    def test_two_source_identical_triplets_and_no_product_pass(self):
        w=(ROOT/".github/workflows/qa-h2282-dual-arm-relay-window-ab-tcp.yml").read_text()
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertEqual(w.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(w.count("runs-on: windows-2025"),1)
        self.assertEqual(w.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(w.count("[m0-029-h2282-window-ab-3runner]"),3)
        self.assertIn('WBD_H2281_SUSTAINED_TCP: "1"',w)
        self.assertIn('WBD_H2282_TCP_WINDOW_AB: "1"',w)
        self.assertEqual(
          w.count("assert [x['stage_id'] for x in d['stages']]==['base','tuned','base_prime']"),2)
        self.assertIn("PASS_H2282_REAL_NATIVE_WINSOCK_ARM_SOCKET_BUFFER_AB_SCOPED",w)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",w)
        self.assertIn("NOT measured here",w)
        self.assertNotIn("PASS_FULL_PRODUCT_THROUGHPUT",w)


if __name__=="__main__":
    unittest.main()
