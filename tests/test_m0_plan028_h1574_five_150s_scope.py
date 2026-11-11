"""PLAN028 H1574: source/fixture-only acceptance for 150s genuine Win1+Linux4.

The old 600s/250-300Mbps and loss30 remain independent NOT_RUN;
a cheap unittest is not a network qualification.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
HARNESS=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
APP=ROOT/"tools/m0_plan028_h1548_mixed_os_app.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class FiveOriginalNative150sScope(unittest.TestCase):
    def test_true_new_source_locked_single_windows2025_scene(self):
        h=HARNESS.read_text();a=APP.read_text();w=WORKFLOW.read_text()
        ast.parse(h,filename=str(HARNESS))
        ast.parse(a,filename=str(APP))
        for token in (
            "[plan028-h1574-win5-native-150s]",
            "WBD_PLAN028_WIN_FIVE_150S_TCPUDP:",
            "H1574-FiveNative-150s-UDP-TCP-And-OwnedStop",
            '["mixed-loss0"]',
            "h1574_capacity_status -ne 'PASS_WITHIN_HOST_BUDGET_NO_30S_FULL_CPU_RAM'",
            "h1574_150s_stage -ne 'verified_true_five_150s_udp_tcp_exact_owners_stopped'",
        ):
            self.assertIn(token,w)
        self.assertIn('"600s_outer_capacity": (',h)
        self.assertIn('"NOT_RUN_H1579_SHORT_30PCT_COLD_TLS" if h1579 else',h)
        self.assertIn('"NOT_RUN_H1581_TRUE_150S_FIVE_NATIVE" if h1581 else',h)
        self.assertIn('"NOT_RUN_H1574_TRUE_150S_FIVE_NATIVE" if l1_150 else',h)
        self.assertIn('"NOT_RUN_H1565_SHORT_FIRST_FAULT" if probe else "PENDING_H1548"',h)
        self.assertIn("not bob_normal and a.scene==\"loss0\"",h)
        self.assertIn('["mixed-loss0","mixed-loss30"]',w)

    def test_authenticated_dynamic_os_addresses_udp_and_tcp_real(self):
        h=HARNESS.read_text();a=APP.read_text()
        for token in (
            "WBD_PLAN028_WIN_FIVE_150S_TCPUDP",
            "H1573_ORIGINAL_MIXED_WIN_PERSONA1_LINUX_PERSONA0_TLS_RUST_M4_TRIGGERED",
            "H1570_ORIGINAL_TLS_NATIVE_AUTO_BOB_FIRST_REVERSE_4_REAL_UDP_PASS",
            "L1_BASES=(6,6,3,3,6)",
            'ap.add_argument("--inner-ips",default="")',
            'assert len(actual)==5 and len(set(actual))==5',
            'assert actual[0]=="10.66.0.2"',
            'if a.windows_auto_ip:',
            'ipaddress.ip_network("10.66.0.128/25")',
            "COMPLETE_TRUE_150S_ORIGINAL_GO_RUST_INNER_APPLICATION",
            "H1574_TRUE_FIVE_NATIVE_150S_UDP_TCP_CLIENTS_VERIFIED_PASS",
            "H1574_REAL_150S_FIVE_TRUE_TCP_UDP_AND_EXACT_ALL_SIX_OWNED_STOP_PASS",
        ):
            self.assertIn(token,h+"\n"+a)
        self.assertIn("tcp_exchange(",a)
        self.assertIn("actual_udp_unique_received",a)
        self.assertIn("tcp_real_frames",a)
        self.assertIn('rate=(L1_BASES if a.duration==150 else BASES[loss])[i]',a)
        self.assertIn("recv/sent>=.98 and received/downstream>=.98",h)
        self.assertIn("max_udp_gap_client_ms",h)
        self.assertIn('min(tcp_client["sent"],tcp_client["received"],',h)
        self.assertIn("capacity_seconds<30",h)

    def test_game_stop_marker_is_real_owner_not_normal_text(self):
        h=HARNESS.read_text()
        self.assertIn("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=",h)
        self.assertIn("V4_PUBLIC_NATIVE_STOP_DRAINED role=client",h)
        self.assertIn("V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client",h)
        self.assertIn("V4_PUBLIC_SHARED_TUN_STOP generation=",h)
        self.assertIn("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1",h)
        self.assertIn("original_WSL_bridge_restored",h)
        self.assertIn("Windows_original_WAL_leftover",h)
        self.assertIn('netem("clean",loss)',h)
        self.assertIn('echo_lifetime=int(sys.argv[3])',h)
        self.assertIn('assert 150<=echo_lifetime<=480',h)
        self.assertIn('"480" if l1_150 else "150"',h)
        self.assertIn('"h1575_real_kernel_echo_alive_after_150s"',h)
        self.assertIn('"h1575_real_kernel_echo_alive_post_windows_stop"',h)
        self.assertIn('"h1575_bob_post_Alice_stop_on_real_live_echo"',h)
        self.assertLess(h.index('H1574_TRUE_FIVE_NATIVE_150S_UDP_TCP_CLIENTS_VERIFIED_PASS'),
                        h.index('h1575_real_kernel_echo_alive_after_150s'))
        self.assertLess(h.index('h1575_real_kernel_echo_alive_post_windows_stop'),
                        h.index('bob_survives_alice'))


if __name__=="__main__":
    unittest.main()
