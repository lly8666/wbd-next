"""No OS or fake product in config unit test: original Normal Fixed6 OFF only."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_fixed6_off30 import configuration

class Fixed6OffConfigTest(unittest.TestCase):
    def test_shared_product_source_and_game2_packet_mix(self):
        s=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
        c=configuration(s,"a"*40,3104)
        self.assertEqual(c["product"]["mode"],"fec-fixed")
        self.assertEqual(c["product"]["fec_profile"],6)
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertFalse(c["bundles"]["A"]["repair_enabled"])
        self.assertEqual(c["traffic"]["sizes"],[[96,10],[288,15],[1060,30],[1200,45]])
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],30)
        self.assertEqual(c["phases"][0]["seconds"],60)

if __name__=="__main__":unittest.main()
