"""Game2/4 original game cold post-Apply TCP control must admit authenticated 2/4 lanes only.

H2143 original signed Game2 first failure: Wintun OS Applied and Rust
Game2 two original TLS lanes were correct, but this Go control shim
hardcoded len(g.members)==4 before ever reaching Rust.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Game2TCPGate(unittest.TestCase):
 def test_shared_post_apply_control_only_two_or_four_and_same_owner(self):
  b=(ROOT/"r0/go_overlay/internal/realityfront/bridge_v4_windows_game_native_io.go").read_text()
  r=(ROOT/"crates/wbd-engine/src/v4_windows_game_native_runtime.rs").read_text()
  m=(ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json").read_text()
  self.assertIn('(len(g.members)!=2&&len(g.members)!=4)',b)
  self.assertNotIn('||len(g.members)!=4||g.members[0]',b)
  self.assertIn('first.OriginalOwnerReadback()',b)
  self.assertIn('plan029PostApplyOriginalOwnerReady(state)',b)
  self.assertIn('wbd_m0_win_game_native_v4_tcp_control',b)
  self.assertIn('GameTcpColdCommand::Prepare(reply_tx)',r)
  self.assertIn('GameTcpColdCommand::Enable(q.port,reply_tx)',r)
  self.assertIn('bridge_v4_windows_game_native_io.go',m)

 def test_original_e2e_alias_static_preserves_cross_mode_and_b4(self):
  e=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
  self.assertIn('if p029_p1_policy or p029_game4_cn or p029b_b4 or p029b_game_case:',e)
  self.assertIn('if p029_direct or p029_p1_policy or p029_game4_cn or p029b_b2 or p029b_b4 or p029b_game_case:',e)
  self.assertIn('p029b_game_policy in ("off","all","lan","ordinary","advanced")',e)
  self.assertIn('p029b_game_policy=p029b_game_case.removesuffix("_fixed")',e)
  self.assertIn('p029b_game_case==(p029b_game_policy+("_fixed" if game_fixed else ""))',e)

if __name__=="__main__":
 unittest.main()
