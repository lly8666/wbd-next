"""H2244 bounded application echo protocol and genuine runner structural gates.

Unit tests exercise framing, exact positive/negative p99 accounting and
source-owned native scene wiring. They are NOT a simulated WBD network PASS.
"""
import pathlib
import struct
import unittest
from tools import m0_h2244_smallflow_echo as E
from tools import m0_h2244_native_tail_abca as N

ROOT=pathlib.Path(__file__).resolve().parents[1]

class NativeSmallflowProbeStatic(unittest.TestCase):
    def test_exact_independent_udp_tcp_application_frame(self):
        self.assertEqual(len(E.MAGIC),8)
        self.assertEqual(E.FRAME_LEN,16)
        f=E.frame(0x12345678,444)
        self.assertEqual(len(f),16)
        self.assertEqual(E.parse_frame(f,0x12345678),444)
        self.assertEqual(f[-8:],struct.pack("!II",0x12345678,444))
        with self.assertRaisesRegex(ValueError,"NONCE_MISMATCH"):
            E.parse_frame(f,0x87654321)
        with self.assertRaisesRegex(ValueError,"CORRUPT"):
            E.parse_frame(f[:-1],0x12345678)
        with self.assertRaisesRegex(ValueError,"CORRUPT"):
            E.parse_frame(b"not-valid-frame!",0x12345678)

    def test_true_sample_p99_without_faking_missing(self):
        self.assertIsNone(E.pct([],99))
        self.assertEqual(E.pct([100.0,1.0,2.0,3.0],50),2.0)
        self.assertEqual(E.pct([100.0,1.0,2.0,3.0],95),100.0)
        self.assertEqual(E.pct([100.0,1.0,2.0,3.0],99),100.0)
        self.assertEqual(E.COUNT,160)
        self.assertEqual(E.GAP_MS,80)
        self.assertLess(E.START_DELAY_S+E.COUNT*E.GAP_MS/1000+E.DRAIN_S,20)

    def test_original_burst_original_same_source_and_all_owners_stop(self):
        self.assertEqual(N.PHASES,(
            ("original_before",0),("tbf48kb_fq_codel",48),
            ("original_after",0)))
        text=(ROOT/"tools/m0_h2244_native_tail_abca.py").read_text()
        for marker in (
            'node.start_network()', 'node.start_server()', 'node.impairment(1)',
            'node.start_client(1)', 'node.stop_client(1)',
            'node.stop_server()', 'H.rearm_direct_capacity_listener(node)',
            'H.install_owned_tun_aggregate_burst_fair(',
            'H.source_kernel_qdisc_receipt(', 'H.scoped_diagnostic(',
            'echo_receipt(node,label,i)', 'real_original_tls_rust_one_owner',
            'probe_start_monotonic_ns', 'iperf_start_monotonic_ns',
            'udp','tcp','NO_HOL'):
            if marker=="NO_HOL":
                self.assertIn("no_cross_business_hol",text)
            else:self.assertIn(marker,text)
        self.assertIn('os.environ["WBD_H2241_NATIVE_GATE"]="0"',text)
        self.assertNotIn('os.environ["WBD_H2241_NATIVE_GATE"]="1"',text)
        self.assertNotIn("full_reader_sleep",text)

    def test_undelivered_app_packets_are_not_zero_rtt(self):
        text=(ROOT/"tools/m0_h2244_smallflow_echo.py").read_text()
        for marker in (
            '"missing":len(sent[kind])-len(recv[kind])',
            '"unique_replies":len(recv[kind])',
            'record("udp",data,time.monotonic_ns())',
            'record("tcp",item,time.monotonic_ns())',
            'if not samples:', 'return None',
            'same_host_real_monotonic_ns'):
            if marker=="same_host_real_monotonic_ns":
                self.assertIn(marker,(ROOT/"tools/m0_h2244_native_tail_abca.py").read_text()
                              +(ROOT/"tools/m0_h2244_smallflow_echo.py").read_text())
            else:self.assertIn(marker,text)

if __name__=="__main__":
    unittest.main()
