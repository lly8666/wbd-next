import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class SameNormalOuterRepair(unittest.TestCase):
 def test_auto_has_normal_outer_feedback_and_retry_deadline(self):
  o=(ROOT/"crates/wbd-engine/src/v4_windows_owner.rs").read_text()
  n=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
  self.assertNotIn("if m.auto_low_rate_mode{return Ok(())}",o)
  self.assertIn("m.outer_ack.on_feedback(lane,epoch,ack32,sacks",o)
  self.assertIn("let shadow_due=m.shadow.next_deadline();",n)
  self.assertIn("m2_next_repair_entry(&mut e,cfg.epoch",n)
  self.assertIn("m2_complete_repair_entry(&mut e,cfg.epoch",n)
if __name__=="__main__":unittest.main()
