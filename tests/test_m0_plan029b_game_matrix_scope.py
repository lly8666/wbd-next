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
 def test_original_kernel_and_no_synthetic_lan(self):
  fixture=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
  helper=ROOT/"tools/m0_plan029b_game_lan_probe.py"
  if helper.exists():
   p=helper.read_text()
   ast.parse(p)
   self.assertIn("socket.AF_INET,socket.SOCK_DGRAM",p)
   self.assertIn("PLAN029B_GAME_REAL_LINUX_LAN_DIRECT_UDP",p)
  self.assertIn('WBD_PLAN029B_GAME_MATRIX_CASE',fixture)
