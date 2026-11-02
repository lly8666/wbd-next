"""Original source-locked 100Mbps high-PPS Normal one-VM OFF→ON contract."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_repair_pair_cap100 import configuration

class NormalCap100PairTest(unittest.TestCase):
    def test_only_outer_repair_switch_changes_between_legs(self):
        s=json.loads(Path("scenarios/plan027-n-normal-off-100m-25ms-loss0-60s.json").read_text())
        a=configuration(s,"a"*40,12,False)
        b=configuration(s,"a"*40,12,True)
        self.assertFalse(a["product"]["repair_enabled"])
        self.assertTrue(b["product"]["repair_enabled"])
        self.assertFalse(a["bundles"]["A"]["repair_enabled"])
        self.assertTrue(b["bundles"]["A"]["repair_enabled"])
        self.assertEqual(a["traffic"],b["traffic"])
        self.assertEqual(a["phases"],b["phases"])
        self.assertEqual(a["network"],b["network"])
        self.assertEqual(a["traffic"]["c2s_mbps"],100)
        self.assertEqual(a["traffic"]["sizes"],[[1200,100]])
        self.assertEqual(a["phases"][0]["c2s"]["delay_ms"],25)

if __name__=="__main__":unittest.main()
