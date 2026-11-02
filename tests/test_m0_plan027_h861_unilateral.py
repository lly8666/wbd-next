"""One-way Health-dead remains genuinely asymmetric after original config."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_h861_unilateral import configuration,stages
class OneWayOriginalCold(unittest.TestCase):
    def test_one_way_c2s_real_105s_with_no_fake_business(self):
        scene=json.loads(Path("scenarios/plan027-n-cold-unilateral-c2s105-2m.json").read_text())
        cfg=configuration(scene,"b"*40,77)
        self.assertFalse(cfg["product"]["repair_enabled"])
        self.assertEqual(cfg["traffic"]["probe_hz"],0)
        self.assertEqual((cfg["traffic"]["c2s_mbps"],cfg["traffic"]["s2c_mbps"]),(2,2))
        self.assertEqual([(p["seconds"],p["rate_scale"],p["c2s"]["loss_pct"],p["s2c"]["loss_pct"]) for p in cfg["phases"]],
                        [(20,1,0,0),(105,0,100,0),(120,1,0,0)])
        self.assertEqual(cfg["network"]["lane_loss"],"shared")
        for p in cfg["phases"]:
            self.assertIn("jitter_ms",p["c2s"])
            self.assertIn("jitter_ms",p["s2c"])

if __name__=="__main__":unittest.main()
