"""Zero injected loss is EXACT first application delivery, not 99.9% threshold."""
import unittest
from tools.m0_wl_plan027_loss_verdict import verdict

def sample(win_sent=100,lin_sent=100,win_first=100,lin_first=100):
    return {"stop":"PASS_BOTH_OWNED","linux_binary_source":"a"*40,
            "WL_V2":{"status":"MEASURED_BOTH_OS_KERNEL","owned_stop":"PASS_BOTH_OWNED",
                      "scenario_id":"c100","declared":{"windows_to_linux":{"loss_pct":0},
                                                         "linux_to_windows":{"loss_pct":0}}},
            "wl_n0_measured":{"windows":{"sent_packets":win_sent,"received_first_packets":win_first,
                                        "invalid_packets":0,"udp_socket_probe_deltas":{
                                         "windows_host_ipv4_udp_deltas":{"in_errors_delta":0}}},
                                "linux":{"sent_packets":lin_sent,"received_first_packets":lin_first,
                                         "invalid_packets":0}}}

class StrictSourceTests(unittest.TestCase):
    def test_100m_old_99_9587_not_lossless(self):
        result=verdict(sample(lin_sent=995045,win_first=994634))
        self.assertEqual(result["status"],"FAIL_ZERO_INJECTED_LOSS_FIRST_SOURCE_GAP")
        self.assertEqual(result["missing"]["windows"],411)
    def test_100m_new_99_9834_not_lossless_even_without_win_udp_error(self):
        result=verdict(sample(lin_sent=995251,win_first=995086))
        self.assertEqual(result["missing"]["windows"],165)
        self.assertEqual(result["windows_host_ipv4_udp_global_errors"]["in_errors_delta"],0)
        self.assertEqual(result["status"],"FAIL_ZERO_INJECTED_LOSS_FIRST_SOURCE_GAP")
    def test_10m_no_loss_source_exact_both(self):
        self.assertEqual(verdict(sample())["status"],"PASS_ZERO_INJECTED_LOSS_EXACT_FIRST")
    def test_never_treat_30pct_declared_as_zero(self):
        item=sample();item["WL_V2"]["declared"]["linux_to_windows"]["loss_pct"]=30
        self.assertEqual(verdict(item)["status"],"NOT_LOSSLESS_CASE")
    def test_no_owned_stop_is_not_pass(self):
        item=sample();item["stop"]="NOT_RUN"
        self.assertEqual(verdict(item)["status"],"INCONCLUSIVE_NO_OWNED_STOP")

if __name__=="__main__":unittest.main()
