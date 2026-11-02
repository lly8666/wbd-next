"""H888: source-locked long unilateral native runner management safety."""
import pathlib
import unittest
from tools.m0_wl_native_step_runner import native_batch_deadline
from tools.m0_wl_perf_v2_config import read_scenario
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCENE="scenarios/plan027-h882-win-c2s105-10m-25ms0-60s.json"

class ManagedUnilateral(unittest.TestCase):
 def test_exact_blackout_source_and_bounded_work(self):
  s=read_scenario(ROOT/SCENE)
  self.assertEqual((s["public_mode"],s["lifecycle_blackhole_s"],
    s["lifecycle_blackhole_direction"],s["duration_s"]),
    ("normal",105,"windows_to_linux",60))
  env={"WBD_WL_RUNNER_MGMT_PIN":"1","WBD_WL_V2_SCENARIO":SCENE,
       "WBD_WL_PUBLIC_MODES":"normal"}
  self.assertEqual(native_batch_deadline(env),600)
  self.assertEqual(native_batch_deadline({**env,"WBD_WL_RUNNER_MGMT_PIN":"0"}),760)
  self.assertEqual(native_batch_deadline({**env,"WBD_WL_V2_SCENARIO":"other"}),760)
 def test_only_exact_management_route_lease_can_be_pinned(self):
  text=(ROOT/"tools/m0_wl_gamefec_management_route.ps1").read_text()
  for literal in ("$env:WBD_WL_RUNNER_MGMT_PIN -eq '1'",
   "$env:WBD_WL_PUBLIC_MODES -eq 'normal'",
   "$env:WBD_WL_OUTER_REPAIR -eq 'off'",
   "$Receipt -eq 'result/wl-public/normal105-management-route-lease.json'",
   "MANAGEMENT_ROUTE_SCOPE_REFUSED","FOREIGN_MANAGEMENT_LEASE",
   "PREEXISTING_SPECIFIC_HOST_ROUTE","ORIGINAL_PHYSICAL_UNDERLAY_NOT_UNAMBIGUOUS",
   "Remove-NetRoute","GITHUB_RUN_ID","GITHUB_RUN_ATTEMPT"):
   self.assertIn(literal,text)
 def test_workflow_does_not_call_native_before_management_pin(self):
  s=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
  self.assertIn("H888-managed-WinC2S105-recover120",s)
  self.assertIn("PLAN027_H888_MANAGED_105_RUNNER_UNDERLAY_PINNED",s)
  self.assertIn("PLAN027_H888_MANAGED_105_RUNNER_EXACT_RESTORED",s)
  self.assertIn("timeout-minutes: 24",s)
  self.assertLess(s.index("PLAN027_H888_MANAGED_105_RUNNER_UNDERLAY_PINNED"),
                  s.index("tools/m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py"))
  self.assertLess(s.index("PLAN027_H888_MANAGED_105_RUNNER_EXACT_RESTORED"),
                  s.index("Remove-NetFirewallRule -Name $tcpRuleName"))

if __name__=="__main__":unittest.main()
