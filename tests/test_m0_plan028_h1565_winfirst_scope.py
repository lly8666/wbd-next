"""Offline source contract for H1565 one signed Win first, then four Linux peers.

Not a real native PASS: that requires exact SOURCE/OS Actions and artifacts.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class WindowsFirstThenFourLinux(unittest.TestCase):
    def test_one_real_loss0_probe_not_old_full_600_replay(self):
        code=SCRIPT.read_text()
        wf=WORKFLOW.read_text()
        ast.parse(code,filename=str(SCRIPT))
        for mark in (
            "WBD_PLAN028_WIN_FIRST_REVERSE_PROBE",
            'a.scene=="loss0" and os.environ.get("GITHUB_ACTIONS")=="true"',
            "H1565_ORIGINAL_WIN_NPF_WINTUN_FIRST_REVERSE_PRE_SIBLINGS_PASS",
            "H1565_FIVE_ORIGINAL_TLS_NATIVE_WINTUN_TUN_APP_40_OF_40_PASS",
            "PASS_SCOPED_H1565_WIN_FIRST_THEN_FOUR_ORIGINAL_LINUX_LOSS0_200MS",
        ):
            self.assertIn(mark,code)
        self.assertIn('[plan028-h1565-winfirst-five-native]',wf)
        self.assertIn('["mixed-loss0"]',wf)
        self.assertIn("WBD_PLAN028_WIN_FIRST_REVERSE_PROBE:",wf)
        self.assertIn("WBD_WL_RUNNER_MGMT_PIN:",wf)
        self.assertIn("WBD_WL_NATIVE_OUTER_MTU_REQUEST:",wf)
        self.assertIn("if($env:WBD_PLAN028_WIN_FIRST_REVERSE_PROBE -eq '1'){",wf)
        self.assertIn("600s NOT_RUN",wf)

    def test_real_os_udp_and_non_overlapping_auto_lease(self):
        code=SCRIPT.read_text()
        for mark in (
            "H1565_REAL_LINUX_TUN_ECHO_BOUND",
            's.bind(("10.66.0.1",45941))',
            "s.bind((local,0))",
            's.sendto(data,("10.66.0.1",45941))',
            "H1565_REAL_NATIVE_APP_OK",
            'ipaddress.ip_network("10.66.0.128/25")',
            'auto_os_ips[who]=inner[0]',
            'WBD_WINDOWS_CLIENT_READY',
            'WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1',
            'V4_PUBLIC_NATIVE_STOP_DRAINED role=client',
            'V4_PUBLIC_SHARED_TUN_STOP generation=',
            'report["h1565_bob_after_win_owned_stop_real_udp"]=4',
            '"600s_outer_capacity": "NOT_RUN_H1565_SHORT_FIRST_FAULT"',
            'report["h1565_five_genuine_os_udp_echoes"]=40',
            'original_WSL_bridge_restored',
            'Windows_original_WAL_leftover',
            'netem("clean",loss)',
        ):
            self.assertIn(mark,code)
        self.assertLess(
            code.index('marker(OUT/"h1548-windows-alice.log","WBD_WINDOWS_CLIENT_READY",window,105)'),
            code.index('for i,who in enumerate(names[1:],1):\n            args='),
        )
        self.assertIn('return\n        # Give each account its OWN direct client socket',code)

    def test_original_600s_hard_gates_preserved(self):
        code=SCRIPT.read_text()
        wf=WORKFLOW.read_text()
        self.assertIn('while time.monotonic()-t0<602:',code)
        self.assertIn('len(steady)>=28',code)
        self.assertIn('[plan028-h1548-win1-linux4-600]',wf)
        self.assertIn('["mixed-loss0","mixed-loss30"]',wf)
        self.assertIn("}elseif($env:WBD_PLAN028_MIXED_SCENE -in @('loss0','loss30')){",wf)
        self.assertIn('h1548-*-strict-native-report.json',wf)


if __name__=="__main__":
    unittest.main()
