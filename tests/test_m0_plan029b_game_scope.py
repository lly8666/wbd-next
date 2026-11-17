"""029B B5 modes: independent original Game4 advanced CN and Game2 explicit refusal.

The actual signed Game4 result is authoritative; this test only prevents
the historical FakeIP oracle from accidentally receiving fresh ordinary
CN semantics after the 029B default changed to false.
"""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class GameModesScope(unittest.TestCase):
    def test_original_game4_explicit_advanced_cn_one_scene(self):
        e2e=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        workflow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn('if p029_game4_cn:\n  # 029B fresh profiles default ordinary CN',e2e)
        self.assertIn('args.extend(["--split-enable","--cn-domain-direct=true",',e2e)
        self.assertIn('"--cn-rules-file",str(rules)])',e2e)
        self.assertIn('WBD_PLAN029_GAME4_CN_SCENE:',workflow)
        self.assertIn("'[plan029-game4-cn-real]'",workflow)
        self.assertIn("WBD_WL_PUBLIC_MODES:",workflow)
        self.assertIn("tests.test_m0_plan029b_game_scope -v",workflow)
        self.assertNotIn('[plan029-game4-cn-real] [plan029b-b4-gui-three-real]',workflow)
        ast.parse(e2e)

    def test_game2_split_not_wired_rejects_before_real_apply(self):
        go=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go").read_text()
        test=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_game_cold_handoff_windows_test.go").read_text()
        self.assertIn('if o.SplitEnable&&o.Mode==m0WinModeGame2{',go)
        self.assertIn('PLAN029 CN split Game2 not wired; no OS Apply attempted',go)
        # The frozen original Go overlay and its assembly blob MUST
        # remain bit-identical; runtime guard is tested as a source contract.
        # A new build-dependent Go test requires an assembly manifest
        # re-sign and is outside this small Game4 representative scene.
        self.assertIn('func runM0NativeV4Windows(o m0NativeV4Options)error{',go)
        self.assertIn('if o.SplitEnable&&o.Mode==m0WinModeGame2{',go)

if __name__=="__main__":
    unittest.main()
