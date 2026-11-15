"""Fail-closed scope tests; these do not prove real Windows P1."""
import unittest
from tools.m0_plan029_h1933_abba_math import score,ORDER,MODES
SHA="a"*40
def legs():
    return [
      {"name":n,"route_mode":m,"source_sha":SHA,"result":"PASS","split_trial":True,
       "owned_stop":"PASS_BOTH_OWNED","app_target":"203.0.113.77",
       "linux_alias_os_owned":True,"windows_cli_sha256":"w"*64,
       "linux_server_sha256":"l"*64,"actual_delivered_gib":.68,
       "windows_cpu":{"cpu_total_s":v},
       "rust_thread_cpu":{"rust_combined_cpu_s_lower_bound":10,"samples":58},
       "applications":{s:{"actual_delivered_mbps":49.7,
                           "rtt_probe_replies":220,"udp_rtt_p99_ms":3.3}
                        for s in ("windows","linux")}}
      for n,m,v in zip(ORDER,MODES,(20,21,21,20))]
class ABBA(unittest.TestCase):
    def test_correct_abba_and_cpu_delta(self):
        s=score(legs(),SHA)
        self.assertEqual(s["B_over_A_cpu_pct"],5)
        self.assertTrue(s["traffic_comparable"])
        self.assertIn("A_STILL_HAS_ORIGINAL_RUST_TUNNEL_TX_RX",s["excluded_claims"])
    def test_linear_drift_brackets_out(self):
        a=legs()
        for i,x in enumerate(a):x["windows_cpu"]["cpu_total_s"]=20+i
        self.assertAlmostEqual(score(a,SHA)["B_minus_A_cpu_s_per_gib"],0,places=5)
    def test_reject_wrong_order(self):
        a=legs();a[0],a[1]=a[1],a[0]
        with self.assertRaises(ValueError):score(a,SHA)
    def test_reject_other_binary(self):
        a=legs();a[2]["linux_server_sha256"]="other"
        with self.assertRaisesRegex(ValueError,"binary"):score(a,SHA)
    def test_reject_physical_or_lan_control(self):
        a=legs();a[0]["app_target"]="10.66.0.1"
        with self.assertRaises(ValueError):score(a,SHA)
    def test_reject_missing_real_stop_or_source(self):
        a=legs();a[1]["owned_stop"]="NOT_RUN"
        with self.assertRaises(ValueError):score(a,SHA)
        a=legs();a[2]["source_sha"]="b"*40
        with self.assertRaises(ValueError):score(a,SHA)
    def test_rtt_and_rust_tids_required(self):
        a=legs();a[1]["rust_thread_cpu"]["samples"]=0
        with self.assertRaises(ValueError):score(a,SHA)
        a=legs();a[2]["applications"]["linux"]["rtt_probe_replies"]=0
        with self.assertRaises(ValueError):score(a,SHA)
    def test_goodput_spread_marks_inconclusive(self):
        a=legs();a[2]["actual_delivered_gib"]=.6
        self.assertEqual(score(a,SHA)["cpu_interpretation"],"INCONCLUSIVE_UNMATCHED_GOODPUT")
if __name__=="__main__": unittest.main()
