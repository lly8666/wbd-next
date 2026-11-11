"""PLAN028 H1579 source-only scoped Windows2025 30% cold TLS/M4 trial.

First solve original 30% FakeTCP/TLS bootstrap before adding Linux siblings,
business throughput, or long scenarios. No native PASS from unittest.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class WindowsThirtyPercentColdOriginalM4(unittest.TestCase):
    def test_exactly_one_real_signed_windows_30pct_cold_auth(self):
        s=SCRIPT.read_text()
        w=WORKFLOW.read_text()
        ast.parse(s,filename=str(SCRIPT))
        self.assertIn("[plan028-h1579-win30-cold-auth]",w)
        self.assertIn("H1579-Win2025-30pct-ColdTLS-M4-Stop",w)
        self.assertIn("WBD_PLAN028_WIN_30PCT_COLD_TLS:",w)
        self.assertIn("['mixed-loss30']",w.replace('"mixed-loss30"',"'mixed-loss30'"))
        self.assertIn("h1579=os.environ.get",s)
        self.assertIn('a.scene=="loss30" and not probe',s)
        self.assertIn('not bob_probe and not l1_150 and not h1577',s)
        self.assertIn("H1579 exactly one original Windows2025 native 30pct cold TLS trial, no invented UDP recovery",s)
        self.assertIn("netem(\"arm\",loss)",s)
        self.assertIn('marker(OUT/"h1548-windows-alice.log","WBD_WINDOWS_CLIENT_READY",window,160)',s)
        self.assertIn('marker(OUT/"h1548-server.log","V4_PUBLIC_MIXED_NORMAL_READY role=server",serverproc,30)',s)
        self.assertIn('h1579_real_original_TLS_M4_both_sides',s)
        self.assertIn('h1579_actual_Windows_signed_Wintun_OS_lease',s)
        self.assertIn('h1579_real_original_Rust_server_Stop',s)

    def test_hard_real_original_owner_and_cleanup_not_fake_600s(self):
        h=SCRIPT.read_text()
        w=WORKFLOW.read_text()
        for token in (
            "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1",
            "require_real_original_server_owner_stop(serverproc)",
            "V4_PUBLIC_SHARED_TUN_STOP generation=",
            "reader_joined=1",
            "V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close remaining_flows=0",
            "H1579_ORIGINAL_WINDOWS2025_NPCAP_WINTUN_30PCT_REAL_TLS_M4_AND_OWNED_STOP_PASS_SCOPED",
            "NOT_RUN_H1579_SHORT_30PCT_COLD_TLS",
            "Windows_original_WAL_leftover",
            'netem("clean",loss)',
        ):
            self.assertIn(token,h)
        self.assertIn('h1579_real_original_Rust_server_Stop.Contains',w)
        self.assertIn('H1579_ORIGINAL_WINDOWS2025_REAL_30PCT_COLD_TLS_M4_AND_STOP_PASS_SCOPED_FULL_DATA_NOT_RUN',w)
        self.assertIn('[plan028-h1548-win1-linux4-600]',w)
        self.assertIn('["mixed-loss0","mixed-loss30"]',w)
        self.assertIn('while time.monotonic()-t0<602:',h)


if __name__=="__main__":
    unittest.main()
