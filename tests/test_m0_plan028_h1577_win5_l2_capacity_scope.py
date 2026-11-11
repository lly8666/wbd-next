"""PLAN028 H1577 offline capacity source scope, NOT actual network qualification.

One original Windows2025 + Linux4 TLS443 native 150s scenario offers 1.15x
the observed within-capacity 24Mbps/dir logical inner L1 baseline.
The actual host capacity and app integrity must be read from Actions.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
APP=ROOT/"tools/m0_plan028_h1548_mixed_os_app.py"
HARNESS=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class FiveOriginalNativeL2SingleStep(unittest.TestCase):
    def test_one_true_windows_runner_same_150s_app_with_bounded_actual_scale(self):
        h=HARNESS.read_text()
        a=APP.read_text()
        wf=WORKFLOW.read_text()
        ast.parse(h,filename=str(HARNESS))
        ast.parse(a,filename=str(APP))
        self.assertIn("[plan028-h1577-win5-capacity-115]",wf)
        self.assertIn("H1577-FiveNative-150s-115pct-capacity-UDP-TCP-And-Stop",wf)
        self.assertIn("WBD_PLAN028_WIN_L2_CAPACITY_115:",wf)
        self.assertIn("WBD_PLAN028_WIN_150S_SCALE:",wf)
        self.assertIn("1.15",wf)
        self.assertIn("WBD_PLAN028_WIN_FIVE_150S_TCPUDP:",wf)
        self.assertIn("WBD_PLAN028_WIN_150S_SCALE",h)
        self.assertIn("h1577=os.environ.get",h)
        self.assertIn("offered_scale==1.0 or (h1577 and l1_150",h)
        self.assertIn("abs(offered_scale-1.15)<.000001",h)
        self.assertIn('json.dumps({"scale":offered_scale})',h)
        self.assertIn("H1577_REAL_FIVE_OS_APPS_115PCT_OFFER_RATE_TRIGGERED",h)
        self.assertIn('h1577_actual_all_six_apps_scale',h)
        self.assertIn("h1577_actual_inner_rate_scale",h)
        self.assertIn("h1577_real_one_stage_capacity_115",h)
        self.assertIn("h1577_actual_all_six_apps_scale.PSObject.Properties",wf)
        self.assertIn("abs(v-offered_scale)<.00001",h)

    def test_hard_native_capacity_no_seconds_gap_tcp_and_owned_stop_unchanged(self):
        h=HARNESS.read_text()
        a=APP.read_text()
        wf=WORKFLOW.read_text()
        for key in (
            "H1574_TRUE_FIVE_NATIVE_150S_UDP_TCP_CLIENTS_VERIFIED_PASS",
            "max_udp_gap_client_ms",
            'recv/sent>=.98 and received/downstream>=.98',
            'need(capacity_seconds<30,',
            'b["avail_gib"]<1',
            'min(tcp_client["sent"],tcp_client["received"],',
            'V4_PUBLIC_SHARED_TUN_STOP generation=',
            'reader_joined=1',
            'h1575_bob_post_Alice_stop_on_real_live_echo',
            'H1576_ACTUAL_RUST_SHARED_TUN_SERVER_GENERATION_STOP_READER_JOINED_PASS',
            'h1576_actual_server_Rust_TUN_Stop',
        ):
            self.assertIn(key,h)
        self.assertIn("L1_BASES=(6,6,3,3,6)",a)
        self.assertIn("if duration==150:",a)
        self.assertIn('["mixed-loss0"]',wf)
        self.assertIn('[plan028-h1548-win1-linux4-600]',wf)
        self.assertIn('"600s_outer_capacity": "NOT_RUN_H1579_SHORT_30PCT_COLD_TLS" if h1579 else "NOT_RUN_H1565_SHORT_FIRST_FAULT" if probe else "PENDING_H1548"',h)


if __name__=="__main__":
    unittest.main()
