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
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DNS_FAKE_DIRECT_UDP_STAGE_PASS_PRE_TCP_AND_STOP'),S.index('PLAN029_H1760_SIGNED_CN_DIRECT_TCP_32K_TWO_LEG_HALF_CLOSE_PASS_PRE_TUNNEL_AND_STOP'))
        self.assertLess(S.index('PLAN029_H1760_SIGNED_CN_DIRECT_TCP_32K_TWO_LEG_HALF_CLOSE_PASS_PRE_TUNNEL_AND_STOP'),S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'))
        self.assertLess(S.index('PLAN029_H1749_SIGNED_CN_DIRECT_AND_TUNNEL_TCP_UDP_STAGE_PASS_PRE_STOP'),S.rindex('\n stop_windows(w)\n'))
        self.assertIn('"tunnel_tcp":"NOT_RUN_PRE_TCP_COMPARATOR"',S)
        self.assertIn('m0_plan029_h1760_guest_physical_direct_tcp.py',S)
        self.assertIn('m0_plan029_h1760_windows_fakeip_direct_tcp.py',S)
        self.assertIn('owned-wal.json.plan029-defender-tcp',S)
        self.assertIn('report["plan029_private_v3_cn_direct_tcp"]["stop"]',S)
        self.assertIn('source_address=(local,0)',S)
        self.assertIn('result["dial_source"]=conn.getsockname()[0]',S)
        self.assertIn('result["dial_source"]!=local',S)
        self.assertIn('proof["tunnel_tcp"]=report["tcp_duplex"]',S)
        self.assertIn('raise RuntimeError("real public TCP apps failed;',S)
        self.assertIn('"stop":"NOT_RUN_UNTIL_OWNED_STOP"',S)
    def test_exact_windows_linux_physical_receipts(self):
        for term in ['m0_plan029_h1745_guest_dns_direct.py','m0_plan029_h1745_win_client_dns_direct.py','gdata["business_client_physical"]==host_source','gdata["dns_client_physical"]==host_source','"source_sha":os.environ["GITHUB_SHA"]','WBD_PLAN029_NATIVE_V3_TRIAL']:
            self.assertIn(term,S)
    def test_h1764_tcp_core_rust_change_triggers_exact_signed_scope_only(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        for path in (
            "crates/wbd-engine/src/v4_windows_native_tcp_direct.rs",
            "crates/wbd-engine/src/v4_client_direct_tcp_nat.rs",
            "crates/wbd-engine/src/v4_windows_native_split.rs",
            "crates/wbd-engine/src/v4_windows_native_runtime.rs",
            "crates/wbd-platform/src/windows_direct_tcp.rs",
        ):
            self.assertIn("      - "+path,W)
        self.assertIn("[plan029-v3-real-direct-udp]",W)
        self.assertIn("WBD_PLAN029_V3_DIRECT_SCENE",W)
        self.assertIn("PLAN029_H1762_GUEST_TCP46112_HYPERV_EXACT_OWNER_REMOVED",W)
    def test_h1762_wsl_exact_physical_tcp_owner_and_scoped_comparator(self):
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        self.assertIn("PLAN029_H1762_PHYSICAL_GUEST_TCP46112_HYPERV_EXACT_ALLOW_READBACK",W)
        self.assertIn("-LocalPorts '46112'",W)
        self.assertIn("$directName=$ruleName+'-P029-TCP46112'",W)
        self.assertIn("Remove-NetFirewallHyperVRule -Name $name -ErrorAction Stop",W)
        self.assertIn("PLAN029_H1762_GUEST_TCP46112_HYPERV_EXACT_OWNER_REMOVED",W)
        self.assertIn("result/wl-public/hyperv-direct-tcp-owned.json",W)
        self.assertIn('plan029-h1760-guest-physical-tcp.log',M)
        self.assertIn('plan029-h1760-windows-fakeip-tcp.log',M)
        self.assertIn('m0_plan029_h1762_oneway_tunnel_tcp.py',S)
        self.assertIn('PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP',S)
        self.assertIn('historical_028_linux_to_windows_tcp',S)
    def test_h1765_scoped_real_noncn_tunnel_dns_and_safe_process_cleanup(self):
        import ast
        ast.parse(S)  # the full original signed Windows E2E runner must compile
        self.assertNotIn("  wa,li=json.loads(a[0]),json.loads(b[0])",S)
        self.assertIn("  tcp_windows_receipt,li=json.loads(a[0]),json.loads(b[0])",S)
        self.assertIn("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED",S)
        self.assertLess(S.index("PLAN029_H1762_SIGNED_DIRECT_TCP_UDP_ONEWAY_TUN_TCP_UDP_PASS_PRE_STOP"),S.index("PLAN029_H1765_SIGNED_NONCN_UDP53_TUNNEL_DNS_SINGLE_ENDPOINT_PASS_SCOPED"))
        self.assertIn("plan029-h1765-owned-tunnel-dns-alias.txt",S)
        self.assertIn("PLAN029_H1765_TUNNEL_DNS_ALIAS_CLEANUP_FAILED",S)
        self.assertIn('if dns_alias in wsl("ip","-4","-o","addr","show","dev","wbdwl4",timeout=8)',S)
        self.assertIn('wsl("ip","-4","addr","del","1.1.1.1/32","dev","wbdwl4",timeout=8)',S)
        self.assertIn('"app_tcp53":"NOT_RUN"',S)
        M=(Path(__file__).resolve().parents[1]/"tools"/"m0_wl_mode_evidence.py").read_text(encoding="utf-8")
        self.assertIn('plan029-h1765-linux-tun-dns.log',M)
        self.assertIn('plan029-h1765-windows-tun-dns.log',M)
        for path in ("tools/m0_plan029_h1765_linux_tun_dns.py",
                     "tools/m0_plan029_h1765_windows_tunnel_dns.py"):
            source=(Path(__file__).resolve().parents[1]/path).read_text(encoding="utf-8")
            ast.parse(source)
        W=(Path(__file__).resolve().parents[1]/".github"/"workflows"/"m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        self.assertIn('      - tools/m0_plan029_h1765_linux_tun_dns.py',W)
        self.assertIn('      - tools/m0_plan029_h1765_windows_tunnel_dns.py',W)
if __name__=="__main__":unittest.main()
