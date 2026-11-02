"""One meaningful same-source original cold outage diagnostic vs 10Mbps."""
import json
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_cold_dead_2m_diagnostic import configuration

class ColdDead2MDiagnosticFixture(unittest.TestCase):
    def test_only_active_source_rate_changes(self):
        s=json.loads(Path("scenarios/plan027-n-cold-dead105-2m-diagnostic.json").read_text())
        c=configuration(s,"a"*40,77)
        self.assertEqual((c["traffic"]["c2s_mbps"],c["traffic"]["s2c_mbps"]),(2,2))
        self.assertEqual(c["traffic"]["probe_hz"],0)
        self.assertFalse(c["product"]["repair_enabled"])
        self.assertEqual([(x["seconds"],x["rate_scale"],x["c2s"]["loss_pct"],x["s2c"]["loss_pct"]) for x in c["phases"]],
                         [(20,1,0,0),(105,0,100,100),(120,1,0,0)])
        self.assertEqual(c["network"]["lane_loss"],"shared")

if __name__=="__main__":unittest.main()
