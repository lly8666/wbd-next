import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class SameNormalOuterRepair(unittest.TestCase):
 def test_auto_has_normal_outer_feedback_and_retry_deadline(self):
  o=(ROOT/"crates/wbd-engine/src/v4_windows_owner.rs").read_text()
  n=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
  self.assertNotIn("if m.auto_low_rate_mode{return Ok(())}",o)
  self.assertIn("m.outer_ack.on_feedback(lane,epoch,ack32,sacks",o)
  # H884 shared Normal+Auto native TX uses ONE 5ms paced deadline
  # instead of an overdue shadow index that would busy-wait(0).
  self.assertIn("let repair_due=m2_repair_deadline(",n)
  self.assertIn("m.shadow.next_deadline(),m.repair_retry_after_ns",n)
  self.assertIn("retry_after_ns.map(MonoNs).or(shadow_due)",n)
  self.assertNotIn("let shadow_due=m.shadow.next_deadline();",n)
  self.assertIn("m2_next_repair_entry(&mut e,cfg.epoch",n)
  self.assertIn("m2_complete_repair_entry(&mut e,cfg.epoch",n)
if __name__=="__main__":unittest.main()
