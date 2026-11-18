"""029B Game2/Game4 original shared Rust cold split qualification.

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
        self.assertIn('if p029_game4_cn and not p029b_game_case:\n  # 029B fresh profiles default ordinary CN',e2e)
        self.assertIn('args.extend(["--split-enable","--cn-domain-direct=true",',e2e)
        self.assertIn('"--cn-rules-file",str(rules)])',e2e)
        self.assertIn('WBD_PLAN029_GAME4_CN_SCENE:',workflow)
        self.assertIn("'[plan029-game4-cn-real]'",workflow)
        self.assertIn("WBD_WL_PUBLIC_MODES:",workflow)
        self.assertIn("tests.test_m0_plan029b_game_scope -v",workflow)
        self.assertNotIn('[plan029-game4-cn-real] [plan029b-b4-gui-three-real]',workflow)
        ast.parse(e2e)
        self.assertIn('p029b_game2_cn=os.environ.get("WBD_PLAN029B_GAME2_CN_SCENE")=="1"',e2e)
        self.assertIn('PLAN029B_GAME2_ADVANCED_REAL_TWO_TLS_LANES_DIRECT_AND_TUNNEL_TCP_UDP_STOP_PASS',e2e)
        self.assertIn("WBD_PLAN029B_GAME2_CN_SCENE:",workflow)
        self.assertIn("PLAN029B_GAME2_ADVANCED_ORIGINAL_WINTUN_RUST_V4_NATIVE_PASS_SCOPED",workflow)

    def test_game2_game4_shared_original_rust_v4_all_and_off(self):
        go=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go").read_text()
        game=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_game_windows.go").read_text()
        bridge=(ROOT/"r0/go_overlay/internal/realityfront/bridge_v4_windows_game_native_io.go").read_text()
        source=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_game_cold_handoff_windows_test.go").read_text()
        self.assertNotIn('PLAN029 CN split Game2 not wired; no OS Apply attempted',go)
        import json
        manifest=json.loads((ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json").read_text())
        entry=[p for p in manifest["operations"] if p.get("path")=="cmd/wbd-client/main_windows.go"]
        self.assertEqual(len(entry),1)
        self.assertFalse(any("Game2 not wired" in str(p) for p in entry[0]["patches"]))
        self.assertEqual(len(entry[0]["result_blob"]),40)
        self.assertIn('if m0GameBusinessSplit(o){',go)
        self.assertIn('Direct4:businessDirect,',go)
        self.assertIn('Bypass4:businessBypass,',go)
        self.assertIn('func m0GameBusinessSplit(o m0NativeV4Options) bool {',game)
        self.assertIn('return o.SplitEnable && o.RouteMode!="all"',game)
        self.assertIn('gameSplit,err:=m0Plan029TrialCold(o,',game)
        self.assertIn('plan029Cold:gameSplit,',game)
        self.assertIn('synthetic:=netip.AddrFrom4(gameSplit.TCPSynthetic4)',game)
        self.assertIn('StartNativeGameIOWithColdSplit(',bridge)
        self.assertIn('TestM0PLAN029BGame2Game4BusinessSplitAllOffNoOSRows',source)
        self.assertIn('TestM0PLAN029BGame2Game4ThreeRouteModesColdV4',source)

if __name__=="__main__":
    unittest.main()
