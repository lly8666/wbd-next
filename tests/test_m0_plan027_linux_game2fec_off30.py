"""The same-source Game2FEC6 OFF control validates source inputs before OS work."""
import json
import unittest
from pathlib import Path

from tools.network_harness.m0_plan027_linux_game2fec_off30 import configuration

class Game2FecOuterOffConfigTest(unittest.TestCase):
    def test_real_two_lane_fec6_off_one_scenario(self):
        scene=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
        c=configuration(scene,"b"*40,999)
        self.assertEqual(c["product"]["mode"],"game2")
        self.assertEqual(c["product"]["game_fec"],"fixed6")
        self.assertIs(c["product"]["repair_enabled"],False)
        self.assertIs(c["bundles"]["A"]["repair_enabled"],False)
        self.assertEqual(c["phases"][0]["seconds"],60)
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],30)
        self.assertEqual(c["traffic"]["sizes"],[[96,10],[288,15],[1060,30],[1200,45]])

if __name__=="__main__": unittest.main()
