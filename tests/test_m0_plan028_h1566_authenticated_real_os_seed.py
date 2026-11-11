"""H1566: offline contract for genuine authenticated Linux kernel UDP as
Windows native first/reverse cold source. Product still NOT_RUN here.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class OriginalNativeColdServerSource(unittest.TestCase):
    def test_genuine_os_kernel_socket_not_faked_receipt(self):
        s=SCRIPT.read_text()
        ast.parse(s,filename=str(SCRIPT))
        for token in (
            'cold_seed=os.environ.get("WBD_PLAN028_WIN_REAL_COLD_SEED")=="1"',
            'need(not cold_seed or probe,',
            'server_log=pathlib.Path(sys.argv[1]);seed=sys.argv[2]=="1"',
            'if seed and cold_count<70 and now>=next_cold and server_log.is_file():',
            '"V4_PUBLIC_MIXED_NORMAL_READY role=server" in server_log.read_text',
            's.bind(("10.66.0.1",45941))',
            's.sendto(data,("10.66.0.2",45942))',
            'H1566_REAL_SERVER_OS_UDP_AFTER_AUTH_STARTED',
            'if cold_seed:report["h1565_probe_stage"]="Windows_original_native_after_server_kernel_UDP"',
            'H1566 no real server UDP emitted after protected TLS',
            'netem("arm",loss)',
            'h1566_real_server_os_cold_udp_started',
            'WBD_WINDOWS_CLIENT_READY',
        ):
            self.assertIn(token,s)
        self.assertLess(s.index('echo=spawn("h1565-server-echo"'),s.index('window=spawn("h1548-windows-alice"'))
        self.assertNotIn('fake_reverse_ack',s)
        self.assertNotIn('synthetic_ready',s)
    def test_only_one_real_200ms_loss0_and_no_fake_full600_receipt(self):
        s=SCRIPT.read_text()
        wf=WORKFLOW.read_text()
        for token in (
            '[plan028-h1566-real-server-cold-udp]',
            '["mixed-loss0"]',
            'WBD_PLAN028_WIN_FIRST_REVERSE_PROBE:',
            'WBD_PLAN028_WIN_REAL_COLD_SEED:',
            'H1566-Win1-real-OS-server-cold-UDP-loss0-200ms',
            'if($env:WBD_PLAN028_WIN_REAL_COLD_SEED',
            'tests.test_m0_plan028_h1566_authenticated_real_os_seed',
        ):
            self.assertIn(token,wf)
        self.assertIn('if report["status"].startswith("PASS") and not probe:',s)
        self.assertIn('while time.monotonic()-t0<602:',s)
        self.assertIn('PASS_SCOPED_H1565_WIN_FIRST_THEN_FOUR_ORIGINAL_LINUX_LOSS0_200MS',s)
        self.assertIn('Windows_original_WAL_leftover',s)
        self.assertIn('original_WSL_bridge_restored',s)
        self.assertIn('netem("clean",loss)',s)

if __name__=="__main__":
    unittest.main()
