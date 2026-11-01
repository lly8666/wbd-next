"""One source-frozen real Game4 20Mbps/loss0 test, no silent mode downgrade."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_game4fec_zero20 import configuration

class Game4Zero20Test(unittest.TestCase):
    def test_real_four_lanes_staggered_and_fec6(self):
        s=json.loads(Path("scenarios/plan027-c-game4-fec-20m-250ms-loss0-60s.json").read_text())
        c=configuration(s,"a"*40,4420)
        self.assertEqual(c["product"]["mode"],"game4")
        self.assertEqual(c["product"]["game_fec"],"fixed6")
        self.assertEqual(c["product"]["game4_copy_schedule"],"stagger-4-50-140")
        self.assertEqual(c["bundles"]["A"]["game4_copy_schedule"],"stagger-4-50-140")
        self.assertIs(c["product"]["repair_enabled"],False)
        self.assertIs(c["bundles"]["A"]["repair_enabled"],False)
        self.assertEqual(c["traffic"]["sizes"],[[96,10],[288,15],[1060,30],[1200,45]])
        self.assertEqual(c["traffic"]["c2s_mbps"],20)
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],0)
        self.assertEqual(c["phases"][0]["seconds"],60)

if __name__=="__main__":unittest.main()
