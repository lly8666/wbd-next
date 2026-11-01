"""Real 100s silence (>90s dead threshold) without synthetic probes."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_idle100_wake import configuration

class OriginalIdleWakeConfigTest(unittest.TestCase):
    def test_source_idles_over90_without_probe_then_wakes(self):
        scene=json.loads(Path("scenarios/plan027-n-normal-idle100-then-wake-160s.json").read_text())
        c=configuration(scene,"a"*40,1133)
        self.assertEqual(c["product"]["mode"],"normal")
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertFalse(c["bundles"]["A"]["repair_enabled"])
        self.assertEqual(c["traffic"]["probe_hz"],0)
        self.assertEqual([(x["name"],x["seconds"],x["rate_scale"]) for x in c["phases"]],[
            ("initial20",20,1),("payload_idle100",100,0),("resume40",40,1)])
        self.assertTrue(all(x["c2s"]["loss_pct"]==0 and x["s2c"]["loss_pct"]==0 for x in c["phases"]))

if __name__=="__main__":unittest.main()
