"""Validate exact source Game2/4 FEC-off/fixed full native policy matrix fixture."""
import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MatrixScope(unittest.TestCase):
 def test_source_locked_four_parallel_five_sequential_real_sessions(self):
  runner=(ROOT/"tools/m0_plan029b_game_matrix_native.py").read_text()
  ast.parse(runner)
  for text in ("game2off","game2fixed","game4off","game4fixed",
      "CASES=(\"off\",\"all\",\"lan\",\"ordinary\",\"advanced\")",
      "WBD_PLAN029B_GAME_MATRIX_CASE=tag",
      "PASS_ACTUAL_WINDOWS_LINUX_NATIVE_",
      "PASS_BOTH_OWNED",
      "PLAN029B_GAME_REAL_FIRST_FAILURE",
      "PASS_SCOPED_FIVE_ORIGINAL_GAME_SPLIT_CASES_BOTH_OS",
      "windows_cli_sha256","linux_server_sha256"):
   self.assertIn(text,runner)
  self.assertIn('if proc.poll() is None',runner)
  self.assertIn('PLAN029B_GAME_REAL_FIVE_POLICY_PASS',runner)
  self.assertIn('plan029b-game-lan-guest.log',runner)
  self.assertIn('plan029b-game-lan-windows.log',runner)
 def test_original_kernel_and_no_synthetic_lan(self):
  fixture=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
  helper=ROOT/"tools/m0_plan029b_game_lan_probe.py"
  if helper.exists():
   p=helper.read_text()
   ast.parse(p)
   self.assertIn("socket.AF_INET,socket.SOCK_DGRAM",p)
   self.assertIn("PLAN029B_GAME_REAL_LINUX_LAN_DIRECT_UDP",p)
  self.assertIn('WBD_PLAN029B_GAME_MATRIX_CASE',fixture)
  self.assertIn('p029b_game_policy=p029b_game_case.removesuffix("_fixed")',fixture)
  self.assertLess(fixture.index('game_fixed=mode.endswith("-fec")'),
                  fixture.index('p029b_game_case==(p029b_game_policy+'))
  self.assertEqual(fixture.count('game_fixed=mode.endswith("-fec")'),1)
  self.assertIn('p029b_game_policy in ("off","all","lan","ordinary","advanced")',fixture)
  self.assertIn('if p029b_game_policy=="lan":',fixture)
  self.assertIn('"PLAN029B_GAME_REAL_LINUX_LAN_DIRECT_UDP"',fixture)
  self.assertIn('"PASS_SCOPED_REAL_PHYSICAL_LAN_UDP_AND_BOTH_OWNED_STOP"',fixture)
  for variant in ("off_fixed","all_fixed","lan_fixed","ordinary_fixed","advanced_fixed"):
   self.assertIn('suffix="_fixed" if FIXED else ""',
     (ROOT/"tools/m0_plan029b_game_matrix_native.py").read_text())

# Full signed four-way matrix is selected only by exact one commit
# marker; no 028 five-client or Normal B0–B5 job should be scheduled.
class MatrixWorkflowScope(unittest.TestCase):
 def test_four_independent_native_owners_and_source_locked_stop(self):
  w=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
  self.assertIn('["game2off","game2fixed","game4off","game4fixed"]',w)
  self.assertIn('PLAN029B-Original-Split-',w)
  self.assertIn('WBD_PLAN029B_GAME_MATRIX_SIDE:',w)
  self.assertIn('WBD_PLAN029B_GAME_MATRIX_SCENE:',w)
  self.assertIn('tools/m0_plan029b_game_matrix_native.py result/wl-public/direct-full.log',w)
  self.assertIn('PASS_SCOPED_FIVE_ORIGINAL_GAME_SPLIT_CASES_BOTH_OS',w)
  self.assertIn('plan029b-game-matrix/',w)
