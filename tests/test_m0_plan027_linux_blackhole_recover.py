"""One real bilateral 100pct tc loss for >90s, then 120s recovered business."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_blackhole_recover import configuration

class BlackholeRecoverConfigTest(unittest.TestCase):
    def test_true_both_way_blackhole105_restore120_no_probes(self):
        s=json.loads(Path("scenarios/plan027-n-normal-both-blackhole105-recover120.json").read_text())
        c=configuration(s,"a"*40,77)
        self.assertEqual(c["product"]["mode"],"normal")
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertEqual(c["traffic"]["probe_hz"],0)
        self.assertEqual([(v["seconds"],v["rate_scale"],v["c2s"]["loss_pct"],v["s2c"]["loss_pct"]) for v in c["phases"]],[
            (20,1,0,0),(105,0,100,100),(120,1,0,0)])
        self.assertEqual(c["network"]["lane_loss"],"shared")

if __name__=="__main__":unittest.main()
