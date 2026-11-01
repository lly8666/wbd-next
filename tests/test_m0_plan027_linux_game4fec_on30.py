"""Native source-frozen Game4 true 30pct ON differs from prior OFF only in repair."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_game4fec_on30 import configuration
from tools.network_harness.m0_plan027_linux_game4fec_zero20 import configuration as off

class Game4OnNativeConfigTest(unittest.TestCase):
    def test_native_game4_on_uses_same_network_and_parity(self):
        scene=json.loads(Path("scenarios/plan027-c-game4-fec-20m-250ms-loss30-60s.json").read_text())
        a=configuration(scene,"a"*40,42)
        b=off(scene,"a"*40,42)
        self.assertEqual(a["product"]["mode"],"game4")
        self.assertEqual(a["product"]["game_fec"],"fixed6")
        self.assertEqual(a["product"]["game4_copy_schedule"],"stagger-4-50-140")
        self.assertTrue(a["product"]["repair_enabled"])
        self.assertTrue(a["bundles"]["A"]["repair_enabled"])
        self.assertFalse(b["product"]["repair_enabled"])
        self.assertEqual(a["traffic"],b["traffic"])
        self.assertEqual(a["network"],b["network"])
        self.assertEqual(a["phases"],b["phases"])
        self.assertEqual(a["phases"][0]["c2s"]["loss_pct"],30)

if __name__=="__main__":unittest.main()
