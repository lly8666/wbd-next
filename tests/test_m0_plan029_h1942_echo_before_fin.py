"""H1942 offline/direct-loopback regression for two FIN/echo sequencing probes."""
import pathlib
import socket
import threading
import unittest
from tools import m0_plan029_h1926_small_tcp_latency as tcp

class TwoPolicies(unittest.TestCase):
    def test_exact_sample_count_and_phase_percentile(self):
        self.assertEqual(tcp.TOTAL,384)
        self.assertEqual(tcp.SIZES,(64,1024,16384))
        self.assertEqual(tcp.ORDER,("physical","direct","direct","physical"))
        self.assertEqual(tcp.distribution([1,2,3,4])["p99_ms"],4)

    def check_real_local_kernel_socket_echo(self,mode):
        client,server=socket.socketpair()
        exceptions=[]
        client.settimeout(1)
        server.settimeout(1)
        def run():
            try:tcp.send_guest_echo(server,b"echo",mode)
            except Exception as e:exceptions.append(e)
        worker=threading.Thread(target=run)
        try:
            worker.start()
            if mode=="payload_first":
                # There is no client FIN yet, so the server necessarily
                # sent data before observing recv(0).
                self.assertEqual(client.recv(4),b"echo")
            client.shutdown(socket.SHUT_WR)
            if mode=="fin_first":
                self.assertEqual(client.recv(4),b"echo")
            self.assertEqual(client.recv(1),b"")
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            self.assertFalse(exceptions)
        finally:
            client.close();server.close()

    def test_payload_first_returns_without_fin_but_checks_final_fin(self):
        self.check_real_local_kernel_socket_echo("payload_first")

    def test_original_fin_first_still_requires_fin(self):
        self.check_real_local_kernel_socket_echo("fin_first")

    def test_unknown_echo_policy_fails_closed(self):
        a,b=socket.socketpair()
        try:
            with self.assertRaisesRegex(RuntimeError,"invalid"):
                tcp.send_guest_echo(b,b"x","wrong")
        finally:a.close();b.close()

    def test_one_source_and_two_original_os_receipts_not_optional(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        script=(root/"tools/m0_plan029_h1926_small_tcp_latency.py").read_text()
        workflow=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WBD_PLAN029_P2_ECHO_EARLY_CONTROL",script)
        self.assertIn("WBD_PLAN029_P2_ECHO_EARLY_CONTROL:",workflow)
        self.assertIn("[plan029-v3-real-p2-echo-early-control]",workflow)
        self.assertIn('e_win["payload_sha256"]!=e_linux["sha256_all_received"]',script)
        self.assertIn('e_win["payload_sha256"]!=w["payload_sha256"]',script)
        self.assertIn('e_linux["received_connections"]!=TOTAL',script)
        self.assertIn('e_win["wintun_lease"]!="10.66.0.2"',script)
        self.assertIn('if conn.recv(1)!=b"":',script)

if __name__=="__main__":unittest.main()
