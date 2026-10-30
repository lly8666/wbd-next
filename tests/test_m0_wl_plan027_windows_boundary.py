"""Windows native aggregate cross-layer evidence must remain fail-closed."""
import json,unittest
from tools.m0_wl_plan027_windows_boundary import windows_boundary

def sample(rate,offered,received,m3,host,source="a"*40):
    report={"linux_binary_source":source,"stop":"PASS_BOTH_OWNED",
      "WL_V2":{"owned_stop":"PASS_BOTH_OWNED","status":"MEASURED_BOTH_OS_KERNEL",
         "scenario_id":f"plan027-c-normal-{rate}m-25ms-loss0-60s",
         "declared":{"windows_to_linux":{"loss_pct":0},"linux_to_windows":{"loss_pct":0}}},
      "wl_n0_measured":{"linux":{"sent_packets":offered},
         "windows":{"received_first_packets":received,
                    "udp_socket_probe_deltas":{"windows_host_ipv4_udp_deltas":{"in_datagrams_delta":host}}}}}
    return report,"WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+json.dumps({"rx_first_delivered_ipv4":m3})
class BoundaryTests(unittest.TestCase):
    def test_actual_1767_gap_not_misattributed_to_windows_udp(self):
        candidate,log=sample(100,995179,993412,994659,994551)
        control,ctl=sample(10,99551,99551,100807,100700)
        r=windows_boundary(candidate,log,control,ctl)
        self.assertEqual(r["status"],"MEASURED_AGGREGATE_WINTUN_APP_COMPARISON_ONLY")
        self.assertEqual(r["candidate"]["original_source_first_missing"],1767)
        self.assertEqual(r["non_business_native_delta_vs_control"],-9)
        self.assertEqual(r["non_business_host_udp_delta_vs_control"],-10)
        self.assertIn("NOT_PROVEN",r["interpretation"])
    def test_mismatched_source_rejected(self):
        a,al=sample(100,1000,999,1050,1100)
        b,bl=sample(10,100,100,150,200,"b"*40)
        self.assertEqual(windows_boundary(a,al,b,bl)["status"],"INCONCLUSIVE_BINARY_SOURCE_NOT_SAME")
    def test_unowned_stop_and_missing_native_rejected(self):
        a,al=sample(100,1000,999,1050,1100)
        b,bl=sample(10,100,100,150,200)
        a["stop"]="NOT_RUN"
        self.assertEqual(windows_boundary(a,al,b,bl)["status"],"INCONCLUSIVE_MISSING_REAL_NATIVE_WINTUN_OR_UDP_COUNTERS")
        a["stop"]="PASS_BOTH_OWNED"
        self.assertEqual(windows_boundary(a,"no telemetry",b,bl)["status"],"INCONCLUSIVE_MISSING_REAL_NATIVE_WINTUN_OR_UDP_COUNTERS")
    def test_negative_or_impossible_totals_rejected(self):
        a,al=sample(100,1000,999,998,1100)
        b,bl=sample(10,100,100,150,200)
        self.assertEqual(windows_boundary(a,al,b,bl)["status"],"INCONCLUSIVE_BAD_NATIVE_OR_APP_TOTALS")
