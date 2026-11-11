"""H1571: real Bob Linux kernel receiver before reverse UDP diagnostic.

This offline source test is NOT product qualification. A successful exact
Windows2025+WSL2 Actions run and raw artifact are required.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WF=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class H1571GenuineLinuxBobPort(unittest.TestCase):
    def test_real_bob_socket_prevents_closed_port_icmp_pollution(self):
        s=SCRIPT.read_text()
        ast.parse(s,filename=str(SCRIPT))
        required=(
            'bob_listener=os.environ.get("WBD_PLAN028_BOB_REAL_KERNEL_SOCKET")=="1"',
            'need(not bob_listener or bob_probe',
            's.bind((ip,45944));s.settimeout(4)',
            'H1571_BOB_REAL_OS_UDP_LISTENER_READY lease=',
            'H1571_BOB_REAL_OS_UDP_RX_VERIFIED count=24',
            'seen==set(range(24))',
            'peer[0]!="10.66.0.1"',
            's.sendto(data,(bob,45944))',
            'H1570_AUTHENTICATED_NATIVE_SERVER_BOB_KERNEL_UDP_SENT count=24',
            'report["h1571_bob_kernel_app_rx"]=24',
            'H1571_BOB_AUTHENTICATED_REAL_TUN_KERNEL_UDP_24_OF_24_PASS',
            'spawn_real_echo_client("bob_alone_before_five",auto_os_ips["bob"],4,NS4[0])',
            'require_real_echo("bob_alone_before_five",bobfirst,4)',
        )
        for v in required:self.assertIn(v,s)
        self.assertLess(s.index('marker(OUT/"h1571-bob-real-udp-listener.log"'),
                        s.index('seed_proc=spawn("h1570-bob-kernel-first"'))
        self.assertLess(s.index('report["h1571_bob_kernel_app_rx"]=24'),
                        s.index('bobfirst=spawn_real_echo_client'))
    def test_one_real_loss0_200ms_source_lock_not_six_hundred(self):
        w=WF.read_text();s=SCRIPT.read_text()
        for mark in (
            '[plan028-h1571-bob-real-kernel-listener]',
            '["mixed-loss0"]',
            'WBD_PLAN028_BOB_REAL_KERNEL_SOCKET:',
            '($env:WBD_PLAN028_BOB_REAL_KERNEL_SOCKET',
            'tests.test_m0_plan028_h1571_bob_os_listener_scope',
            'result/wl-public/h1571-*.log',
            'h1571_bob_kernel_app_rx',
            'WBD_WL_RUNNER_MGMT_PIN:',
            'WBD_WL_NATIVE_OUTER_MTU_REQUEST:',
            '600s NOT_RUN',
        ):self.assertIn(mark,w)
        self.assertIn('netem("clean",loss)',s)
        self.assertIn('if report["status"].startswith("PASS") and (not probe or l1_150):',s)
        self.assertIn('while time.monotonic()-t0<602:',s)

if __name__=="__main__":
    unittest.main()
