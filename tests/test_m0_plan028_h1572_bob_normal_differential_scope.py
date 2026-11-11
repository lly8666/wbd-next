"""PLAN028 H1572 offline source contract, not a native Windows/Linux PASS.

Control changes ONLY Bob FEC-Auto to Normal/off. Authenticated --auto-ip,
original Rust shared-TUN server/receiver, true Windows native Npcap/Wintun,
200ms physical delay and other four independent peers remain unchanged.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class BobModeControlScope(unittest.TestCase):
    def test_actual_original_mode_and_identity_are_bounded(self):
        src=SCRIPT.read_text()
        ast.parse(src,filename=str(SCRIPT))
        self.assertIn('WBD_PLAN028_BOB_NORMAL_DIFFERENTIAL',src)
        self.assertIn('need(not bob_normal or (probe and cold_seed and bob_probe and bob_listener and a.scene=="loss0")',src)
        self.assertIn('"--mode",("normal" if bob_normal and who=="bob" else MODES[i])',src)
        self.assertIn('MODES=("normal","fec-auto","game2","game4","fec-fixed")',src)
        self.assertIn('"--auto-ip","--installation-id-file"',src)
        self.assertIn('V4_PUBLIC_GO_RX_HANDOFF role=client mode=off ',src)
        self.assertIn('H1572_BOB_NORMAL_OFF_PROTECTED_RUST_HANDOFF_TRUE',src)
        self.assertIn('H1571_BOB_AUTHENTICATED_REAL_TUN_KERNEL_UDP_24_OF_24_PASS',src)
        self.assertIn('H1570_ORIGINAL_TLS_NATIVE_AUTO_BOB_FIRST_REVERSE_4_REAL_UDP_PASS',src)

    def test_real_os_source_route_and_counters_before_concluding(self):
        src=SCRIPT.read_text()
        for check in (
            'ip("-n",NS4[0],"-j","-4","route","get",',
            '"10.66.0.1","from",auto_os_ips["bob"]',
            'route[0].get("dev")=="wbd48b"',
            'h1572_bob_tun_kernel_before',
            'h1572_bob_tun_kernel_after',
            'H1572_BOB_REAL_OS_ROUTE_SELECTED',
            'H1572_BOB_OS_KERNEL_TUN_COUNTERS_CAPTURED',
            '"600s_outer_capacity": "NOT_RUN_H1579_SHORT_30PCT_COLD_TLS" if h1579 else "NOT_RUN_H1565_SHORT_FIRST_FAULT" if probe else "PENDING_H1548"',
            'V4_PUBLIC_SHARED_TUN_STOP generation=',
            'Windows_original_WAL_leftover',
            'netem("clean",loss)',
        ):
            self.assertIn(check,src)

    def test_one_win2025_loss0_job_not_legacy_loss30_or_600s(self):
        wf=WORKFLOW.read_text()
        marker='[plan028-h1572-bob-normal-control]'
        self.assertIn(marker,wf)
        self.assertIn("WBD_PLAN028_BOB_NORMAL_DIFFERENTIAL:",wf)
        self.assertIn("H1572-BobNormal-vs-Auto-authenticated-UDP-200ms",wf)
        self.assertIn('["mixed-loss0"]',wf)
        self.assertIn("h1572_bob_original_normal_mode_proven",wf)
        self.assertIn("h1572_bob_kernel_route.dev -ne 'wbd48b'",wf)
        self.assertIn("600s NOT_RUN",wf)
        self.assertIn("[plan028-h1548-win1-linux4-600]",wf)
        self.assertIn('["mixed-loss0","mixed-loss30"]',wf)


if __name__=="__main__":
    unittest.main()
