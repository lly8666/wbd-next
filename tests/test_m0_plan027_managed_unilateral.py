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
  # H889 native run caught a PowerShell ParserError only *after* signed
  # NPF/WSL boot: detect truncated regex/quoted guard at cheap preflight.
  guard="if($env:WBD_WL_PUBLIC_MODES -notmatch '^game[24]-fec$' -and -not $longNative -and -not $crossOsL3){throw 'MANAGEMENT_ROUTE_SCOPE_REFUSED'}"
  self.assertEqual(text.splitlines().count(guard),1)
  # L3 can only enable the existing runner-owned lease after both exact gates;
  # legacy H888 and GameFEC behavior/route scope remain unchanged.
  for clause in ("WBD_PLAN028_WIN_LINUX_L3 -eq '1'",
    "WBD_PLAN028_WIN_LINUX_COCLIENTS -eq '1'",
    "$Receipt -eq 'result/wl-public/crossos1800-management-route-lease.json'",
    "$env:WBD_WL_PUBLIC_MODES -eq 'normal'"):
   self.assertIn(clause,text)
  self.assertEqual(text.count("$crossOsL3=("),1)
  self.assertEqual(text.count("MANAGEMENT_ROUTE_SCOPE_REFUSED"),1)
  self.assertEqual(text.count("function Save-Lease($v){"),1)
  self.assertEqual(text.count("function Undo-Lease($v){"),1)
  self.assertEqual(text.count("if($env:GITHUB_ACTIONS -ne"),1)
  self.assertLess(len(text.splitlines()),135)
  self.assertNotIn("'^game[24]-fec\\n",text)
 def test_workflow_does_not_call_native_before_management_pin(self):
  s=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
  self.assertIn("H888-managed-WinC2S105-recover120",s)
  self.assertIn("PLAN027_H888_MANAGED_105_RUNNER_UNDERLAY_PINNED",s)
  self.assertIn("PLAN027_H888_MANAGED_105_RUNNER_EXACT_RESTORED",s)
  # The normal path still has exactly 24min; only explicit PLAN028 1800s L3 gets 52.
  self.assertIn("timeout-minutes: ${{ contains(github.event.head_commit.message, '[plan028-win-linux-1800]') && 52 || 24 }}",s)
  for marker in ("PLAN027_ORIGINAL_105_HOST_NET",
    "Write-Original105NetworkWitness 'before-runner-restore'",
    "Write-Original105NetworkWitness 'after-runner-restore'",
    "normal105-first-fault.json","normal105-stop-audit.json",
    "normal105-host-*.json"):
   self.assertIn(marker,s)
  self.assertLess(s.index("PLAN027_H888_MANAGED_105_RUNNER_UNDERLAY_PINNED"),
                  s.index("tools/m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py"))
  self.assertLess(s.index("PLAN027_H888_MANAGED_105_RUNNER_EXACT_RESTORED"),
                  s.index("Remove-NetFirewallRule -Name $tcpRuleName"))

class Original105FailureAudit(unittest.TestCase):
 def test_failure_has_separate_wake_and_stop_observations(self):
  text=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
  for token in ("PLAN027_ORIGINAL_105_FIRST_FAULT",
    '"wake_rc":{"windows":wa.returncode,"linux":la.returncode}',
    '"role_samples":{},"owner_markers":{}',
    '"windows_reauthorized"',
    '"linux_reauthorized"',
    '"wal_exists"',
    '"route_sidecar_exists"',
    '"both_owned_stop":"NOT_QUALIFIED_FAIL_PATH"'):
   self.assertIn(token,text)
  self.assertLess(text.index("PLAN027_ORIGINAL_105_FIRST_FAULT"),
                  text.index('raise RuntimeError("real UDP blackout wake returned nonzero")'))
  self.assertIn('if mode=="normal" and report.get("lifecycle_blackhole_failure")',text)
  self.assertNotIn("stop="+repr(True),text)
if __name__=="__main__":unittest.main()
