"""Exactly one source comparison 100M and one real high loss ON case, independent."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_repair_pair_cap100 import configuration
from tools.network_harness.m0_plan027_linux_repair_pair_loss30 import paired_config

class SharedIndexFixtureTest(unittest.TestCase):
    def test_same_normal100_on_config_when_sources_differ(self):
        scene=json.loads(Path("scenarios/plan027-n-normal-off-100m-25ms-loss0-60s.json").read_text())
        a=configuration(scene,"a"*40,5,True)
        b=configuration(scene,"b"*40,5,True)
        self.assertEqual(a["traffic"],b["traffic"])
        self.assertEqual(a["phases"],b["phases"])
        self.assertEqual(a["product"],b["product"])
        self.assertTrue(a["product"]["repair_enabled"])
    def test_exact_true30pct_single_on_scenario(self):
        s=json.loads(Path("scenarios/wl-outer-repair-10m-250ms-loss30-60s.json").read_text())
        c=paired_config(s,"a"*40,6,True)
        self.assertTrue(c["product"]["repair_enabled"])
        self.assertEqual(c["phases"][0]["c2s"]["loss_pct"],30)
        self.assertEqual(c["phases"][0]["s2c"]["loss_pct"],30)
        self.assertEqual(c["phases"][0]["seconds"],60)

if __name__=="__main__":unittest.main()
