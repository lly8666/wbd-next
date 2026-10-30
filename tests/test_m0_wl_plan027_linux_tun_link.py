import unittest
from tools.m0_wl_plan027_linux_tun_link import link_delta
class LinuxTunLinkTests(unittest.TestCase):
    def test_real_linux_interface_tx_and_rx_separate(self):
        a=[{"ifname":"wbdwl4","stats64":{"rx":{"packets":10,"dropped":1,"errors":0},"tx":{"packets":20,"dropped":2,"errors":0}}}]
        b=[{"ifname":"wbdwl4","stats64":{"rx":{"packets":15,"dropped":4,"errors":0},"tx":{"packets":200,"dropped":12,"errors":0}}}]
        v=link_delta(a,b)
        self.assertEqual(v["status"],"MEASURED_ORIGINAL_LINUX_TUN_IP_LINK")
        self.assertEqual(v["tx_dropped_delta"],10)
        self.assertEqual(v["rx_dropped_delta"],3)
    def test_missing_interface_or_statistics_not_zero(self):
        self.assertEqual(link_delta([],[])["status"],"NOT_MEASURED_LINUX_TUN_INTERFACE_COUNTERS")
        self.assertEqual(link_delta([{"ifname":"wbdwl4"}],[])["status"],"NOT_MEASURED_LINUX_TUN_INTERFACE_COUNTERS")
    def test_interface_counter_reset_inconclusive(self):
        a=[{"ifname":"wbdwl4","stats":{"rx":{"packets":9,"dropped":2,"errors":0},"tx":{"packets":12,"dropped":9,"errors":0}}}]
        b=[{"ifname":"wbdwl4","stats":{"rx":{"packets":15,"dropped":2,"errors":0},"tx":{"packets":20,"dropped":1,"errors":0}}}]
        self.assertEqual(link_delta(a,b)["status"],"INCONCLUSIVE_LINK_COUNTER_RESET")
