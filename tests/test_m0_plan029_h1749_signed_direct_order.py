"""PLAN029 signed physical Direct evidence before unrelated TCP comparator."""
import unittest
from pathlib import Path
S=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_public_normal_e2e.py").read_text(encoding="utf-8")
class NativeDirectOrder(unittest.TestCase):
    def test_signed_direct_before_inbound_tcp_comparator_but_after_udp(self):
        self.assertLess(S.index(' report["actual_kernel_udp"]=real'),S.index('  # D1/D2 real physical Direct first'))
        self.assertLess(S.index('  # D1/D2 real physical Direct first'),S.index(' # Functional-only *real TCP*'))
        self.assertLess(S.index(' # Functional-only *real TCP*'),S.index(' report["tcp_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_TCP"'))
    def test_no_early_two_exits_or_false_stop(self):
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DNS_FAKE_DIRECT_UDP_STAGE_PASS_PRE_TCP_AND_STOP'),S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'))
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'),S.rindex('\n stop_windows(w)\n'))
        self.assertIn('"tunnel_tcp":"NOT_RUN_PRE_TCP_COMPARATOR"',S)
        self.assertIn('proof["tunnel_tcp"]=report["tcp_duplex"]',S)
        self.assertIn('raise RuntimeError("real public TCP apps failed;',S)
        self.assertIn('"stop":"NOT_RUN_UNTIL_OWNED_STOP"',S)
    def test_exact_windows_linux_physical_receipts(self):
        for term in ['m0_plan029_h1745_guest_dns_direct.py','m0_plan029_h1745_win_client_dns_direct.py','gdata["business_client_physical"]==host_source','gdata["dns_client_physical"]==host_source','"source_sha":os.environ["GITHUB_SHA"]','WBD_PLAN029_NATIVE_V3_TRIAL']:
            self.assertIn(term,S)
if __name__=="__main__":unittest.main()
