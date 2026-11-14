"""PLAN029 D4 read-only real IPv6 route witnesses, never virtual PASS."""
import unittest
from tools.m0_plan029_d4_ipv6_route_probe import normalize,evaluate

def rows(*entries,leases=()):
    return normalize({"routes":[{"prefix":p,"ifindex":i,"next_hop":"::","metric":5}
                                for p,i in entries],"wintun_ipv4_lease_indexes":list(leases)})
class IPv6RouteTests(unittest.TestCase):
    def test_physical_ipv6_default_without_wintun_sink_stays_open(self):
        result=evaluate(rows(("::/0",3)),rows(("::/0",3),leases=(17,)),rows(("::/0",3)))
        self.assertEqual(result["ipv6_policy_scope"],"OPEN_NO_GENERAL_IPV6_WINTUN_SINK")
        self.assertTrue(result["physical_default_route_observed"])
        self.assertEqual(result["actual_ipv6_app_packets"],"NOT_RUN_NO_EXTERNAL_IPV6_PRECONDITION")
    def test_route_sink_never_means_packet_block_pass(self):
        result=evaluate(rows(),rows(("::/1",17),("8000::/1",17),leases=(17,)),rows())
        self.assertEqual(result["ipv6_policy_scope"],"ROUTE_ONLY_PRESENT_PACKET_NOT_TESTED")
        self.assertEqual(result["on_link_and_physical_bound_ipv6"],"NOT_PROVEN_BLOCKED_BY_ROUTE_ONLY")
    def test_stop_exact_owned_wintun_prefix_stays_is_failure(self):
        result=evaluate(rows(),rows(("::/1",17),("8000::/1",17),leases=(17,)),rows(("::/1",17)))
        self.assertEqual(result["stop_route_baseline_readback"],"FAIL_NEW_WINTUN_PREFIX_REMAINED")
    def test_no_signed_lease_or_unknown_route_fails_closed(self):
        with self.assertRaises(ValueError):evaluate(rows(),rows(("::/0",3)),rows())
        with self.assertRaises(ValueError):normalize({"routes":"invalid","wintun_ipv4_lease_indexes":[]})
        with self.assertRaises(ValueError):
            normalize({"routes":[{"prefix":"::/64","ifindex":3,"next_hop":"::","metric":1}],
                       "wintun_ipv4_lease_indexes":[]})
if __name__=="__main__":unittest.main()
