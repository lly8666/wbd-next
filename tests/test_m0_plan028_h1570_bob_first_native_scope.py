"""H1570 fail-closed source contract for Bob automatic IPv4 first actual UDP.

Offline syntax/fixture test only. It never qualifies real Windows native I/O.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WF=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class H1570BobFirstRealIPv4(unittest.TestCase):
    def test_protected_real_linux_os_source_then_bob_echo_before_five(self):
        s=SCRIPT.read_text()
        ast.parse(s,filename=str(SCRIPT))
        for mark in (
            'WBD_PLAN028_BOB_FIRST_GENUINE_NATIVE_UDP',
            'need(not bob_probe or (probe and cold_seed and a.scene=="loss0")',
            'report["h1565_probe_stage"]="bob_auto_first_reverse_before_five"',
            's.bind(("10.66.0.1",45943))',
            's.sendto(data,(bob,45944))',
            'H1570_AUTHENTICATED_NATIVE_SERVER_BOB_KERNEL_UDP_SENT count=24',
            'report["h1570_bob_server_kernel_source_sent"]=24',
            'spawn_real_echo_client("bob_alone_before_five",auto_os_ips["bob"],4,NS4[0])',
            'require_real_echo("bob_alone_before_five",bobfirst,4)',
            'report["h1570_bob_alone_native_udp_echoes"]=4',
            'H1570_ORIGINAL_TLS_NATIVE_AUTO_BOB_FIRST_REVERSE_4_REAL_UDP_PASS',
            'ipaddress.ip_network("10.66.0.128/25")',
            'H1565_FIVE_ORIGINAL_TLS_NATIVE_WINTUN_TUN_APP_40_OF_40_PASS',
        ):
            self.assertIn(mark,s)
        self.assertLess(s.index('report["h1570_bob_alone_native_udp_echoes"]=4'),
                        s.index('tasks={"alice":spawn_real_echo_client("alice",IPS[0],8)}'))
        self.assertNotIn("fake_m3",s)
    def test_one_loss0_200ms_only_bounded_native_and_artifact_logs(self):
        w=WF.read_text();s=SCRIPT.read_text()
        for mark in (
            "[plan028-h1570-bob-first-real-os-udp]",
            '["mixed-loss0"]',
            'WBD_PLAN028_BOB_FIRST_GENUINE_NATIVE_UDP:',
            '($env:WBD_PLAN028_BOB_FIRST_GENUINE_NATIVE_UDP',
            'tests.test_m0_plan028_h1570_bob_first_native_scope',
            'result/wl-public/h1565-*.log',
            'result/wl-public/h1570-*.log',
            'h1570_bob_server_kernel_source_sent',
            'h1570_bob_alone_native_udp_echoes',
        ):
            self.assertIn(mark,w)
        self.assertIn('if report["status"].startswith("PASS") and (not probe or l1_150):',s)
        self.assertIn('while time.monotonic()-t0<602:',s)
        self.assertIn('netem("clean",loss)',s)
        self.assertIn("600s NOT_RUN",w)

if __name__=="__main__":
    unittest.main()
