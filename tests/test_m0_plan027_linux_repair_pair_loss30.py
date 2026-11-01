"""The two legs have identical true-loss inputs except outer repair switch."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_repair_pair_loss30 import paired_config

class RealLossPairConfigTest(unittest.TestCase):
    def test_exact_one_scenario_off_on(self):
        s=json.loads(Path("scenarios/wl-outer-repair-10m-250ms-loss30-60s.json").read_text())
        a=paired_config(s,"a"*40,321,False)
        b=paired_config(s,"a"*40,321,True)
        self.assertIs(a["product"]["repair_enabled"],False)
        self.assertIs(b["product"]["repair_enabled"],True)
        self.assertEqual(a["traffic"],b["traffic"])
        self.assertEqual(a["phases"],b["phases"])
        self.assertEqual(a["phases"][0]["c2s"]["loss_pct"],30)
        self.assertEqual(a["traffic"]["sizes"],[[64,10],[128,15],[512,25],[1200,50]])

if __name__=="__main__":unittest.main()
