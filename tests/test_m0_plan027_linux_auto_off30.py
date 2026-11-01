"""Auto one-lane reuses exactly same frozen 30pct matched packet mix."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_auto_off30 import configuration
from tools.network_harness.m0_plan027_linux_fixed6_off30 import configuration as fixed

class AutoFecOff30ConfigTest(unittest.TestCase):
    def test_same_scene_only_fec_strategy_differs_from_fixed6(self):
        scene=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
        a=configuration(scene,"a"*40,3142)
        b=fixed(scene,"a"*40,3142)
        self.assertEqual(a["product"]["mode"],"fec-auto")
        self.assertEqual(a["product"]["fec_profile"],1)
        self.assertFalse(a["product"]["repair_enabled"])
        self.assertFalse(a["bundles"]["A"]["repair_enabled"])
        self.assertEqual(a["phases"],b["phases"])
        self.assertEqual(a["traffic"],b["traffic"])
        self.assertEqual(a["network"],b["network"])

if __name__=="__main__":unittest.main()
