"""Offline checks for ONE frozen same-VM R OFF->ON scenario and bounded accounting."""
import json
import unittest
from pathlib import Path

from tools.network_harness.m0_plan027_linux_repair_pair import configuration, leg_summary


class Plan027PairedRepairConfigTest(unittest.TestCase):
    def test_only_repair_switch_changes_native_bundle_semantics(self):
        scene = json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
        off = configuration(scene, "a" * 40, 333, False)
        on = configuration(scene, "a" * 40, 333, True)
        self.assertEqual(off["bundles"]["A"]["repair_enabled"], False)
        self.assertEqual(on["bundles"]["A"]["repair_enabled"], True)
        self.assertEqual(off["product"]["repair_enabled"], False)
        self.assertEqual(on["product"]["repair_enabled"], True)
        for c in (off, on):
            self.assertEqual(c["traffic"]["sizes"], [[64,10], [128,15], [512,25], [1200,50]])
            self.assertEqual(c["phases"][0]["seconds"], 60)
            self.assertEqual(c["phases"][0]["c2s"]["delay_ms"], 250)

    def test_off_must_have_zero_real_repair_and_readback(self):
        leg = {"result": "PASS_SCOPED_OBSERVATION", "failures": [], "limits": [],
               "telemetry": {"outer_repair_native_verified": True,
                             "recovery_policy_verified": True,
                             "stop_drained_both": True},
               "cleanup": {"owned_namespaces_absent": True},
               "observed": [{"phase": "iid", "direction": d,
                             "injected_app_mbps": 10, "cohort_delivered_app_mbps": 10}
                            for d in ("c2s", "s2c")],
               "v3_repair_accounting": {d: {"first_wire_bytes": 1000000,
                                             "conservative_charged_wire_bytes": 0}
                                       for d in ("c2s", "s2c")},
               "measurement_cost": {r: {"cpu_s": 4.0} for r in ("client", "server")},
               "host": {"processes": {r: {"rss_peak_bytes": 4096}
                                     for r in ("client", "server")}}}
        self.assertEqual(leg_summary(leg, False)["verdict"], "PASS_SCOPED_MEASUREMENT")
        leg["v3_repair_accounting"]["c2s"]["conservative_charged_wire_bytes"] = 1
        self.assertEqual(leg_summary(leg, False)["verdict"], "FAIL_OR_INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
