"""Native Auto 4-stage loss schedule, low segment >=120s, no fake readback."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_linux_auto_rise_fall import configuration

class AutoRiseFallTest(unittest.TestCase):
    def test_up1_15_30_1_down5_0_120s_low_gate(self):
        s=json.loads(Path("scenarios/plan027-n-auto-rise-fall-10m-250ms-240s.json").read_text())
        c=configuration(s,"a"*40,1324)
        self.assertEqual(c["product"]["mode"],"fec-auto")
        self.assertEqual(c["product"]["fec_profile"],1)
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertFalse(c["bundles"]["A"]["repair_enabled"])
        self.assertEqual([(x["name"],x["seconds"],x["c2s"]["loss_pct"],x["s2c"]["loss_pct"]) for x in c["phases"]],[
            ("uplink1_down5",25,1,5),("uplink15_down0",30,15,0),
            ("uplink30_down0",35,30,0),("uplink1_down0_low150",150,1,0)])
        self.assertEqual(c["traffic"]["sizes"],[[96,10],[288,15],[1060,30],[1200,45]])
        self.assertEqual(sum(x["seconds"] for x in c["phases"]),240)
        self.assertTrue(all("rate_scale" in x["c2s"] and "rate_scale" in x["s2c"]
                            for x in c["phases"]))
        self.assertTrue(all("blackhole_lanes" in x["c2s"] and "blackhole_lanes" in x["s2c"]
                            for x in c["phases"]))

if __name__=="__main__":unittest.main()
