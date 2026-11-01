"""One original 300s Normal repair-ON traffic/cross-business input contract."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_normal_on_300s import configuration

class Original300sMixedTest(unittest.TestCase):
    def test_300s_on_real_tcp_udp_independent(self):
        p=Path("scenarios/plan027-integration-normal-on-300s-mixed-hol.json")
        c=configuration(json.loads(p.read_text()),"a"*40,32121)
        self.assertEqual(c["product"]["mode"],"normal")
        self.assertTrue(c["product"]["repair_enabled"])
        self.assertTrue(c["bundles"]["A"]["repair_enabled"])
        self.assertEqual(c["phases"][0]["seconds"],300)
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],1)
        self.assertEqual(c["phases"][0]["s2c"]["delay_ms"],25)
        self.assertEqual(c["traffic"]["udp_share"],.6)
        self.assertEqual(c["traffic"]["tcp_flows"],2)
        self.assertTrue(c["traffic"]["observe_independent_flows"])
        self.assertTrue(c["acceptance"]["cross_business_hol"])
        self.assertEqual(c["phases"][0]["rate_scale"],1)

if __name__=="__main__":unittest.main()
