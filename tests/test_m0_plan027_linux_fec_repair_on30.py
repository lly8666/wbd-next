"""Exact two independently run modes; ON input differs from existing OFF only in repair."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_fec_repair_on30 import configuration
from tools.network_harness.m0_plan027_linux_fixed6_off30 import configuration as fixed_off
from tools.network_harness.m0_plan027_linux_auto_off30 import configuration as auto_off

class SingleLaneFecOnTest(unittest.TestCase):
    def test_on_policy_and_scene_unchanged_per_mode(self):
        s=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
        for name, off in (("fixed6",fixed_off),("auto",auto_off)):
            with self.subTest(mode=name):
                on=configuration(s,"a"*40,314,name)
                baseline=off(s,"a"*40,314)
                self.assertEqual(on["product"]["mode"],baseline["product"]["mode"])
                self.assertEqual(on["product"]["fec_profile"],baseline["product"]["fec_profile"])
                self.assertEqual(on["product"]["game_fec"],"off")
                self.assertTrue(on["product"]["repair_enabled"])
                self.assertTrue(on["bundles"]["A"]["repair_enabled"])
                self.assertFalse(baseline["bundles"]["A"]["repair_enabled"])
                self.assertEqual(on["traffic"],baseline["traffic"])
                self.assertEqual(on["phases"],baseline["phases"])
                self.assertEqual(on["network"],baseline["network"])
                self.assertEqual(on["phases"][0]["c2s"]["loss_pct"],30)
                self.assertEqual(on["traffic"]["sizes"],[[96,10],[288,15],[1060,30],[1200,45]])

if __name__=="__main__":unittest.main()
