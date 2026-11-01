"""One original Normal raw/TUN 50Mbps clean before any 100/200M expansion."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_normal_off50 import configuration

class NormalOff50ConfigTest(unittest.TestCase):
    def test_product_source_real_clean_50mbps(self):
        s=json.loads(Path("scenarios/plan027-n-normal-off-50m-25ms-loss0-60s.json").read_text())
        c=configuration(s,"a"*40,5050)
        self.assertEqual(c["product"]["mode"],"normal")
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertFalse(c["bundles"]["A"]["repair_enabled"])
        self.assertEqual(c["traffic"]["sizes"],[[1200,100]])
        self.assertEqual(c["traffic"]["c2s_mbps"],50)
        self.assertEqual(c["traffic"]["s2c_mbps"],50)
        self.assertEqual(c["phases"][0]["seconds"],60)
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],0)
        self.assertEqual(c["phases"][0]["c2s"]["delay_ms"],25)

if __name__=="__main__":unittest.main()
