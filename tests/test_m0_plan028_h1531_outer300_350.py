"""Source-scoped 300-350 Mbps REAL native Linux duplex five-user contract."""
import os,pathlib,runpy,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
FIX=ROOT/"tools/m0-plan028-h1259-five-client-recovery-netns.py"
class H1531DuplexOuter(unittest.TestCase):
 def test_both_losses_true_five_native_clients_packet_caps_and_legacy_unmodified(self):
    for scene,rate,loss in (
      ("outer300to350-loss0",(20,14,10,6,10),0),
      ("outer300to350-loss30",(28,20,14,6,14),30)):
      with self.subTest(scene=scene), mock.patch.dict(os.environ,{
        "WBD_PLAN028_600S_SCENE":scene,
        "WBD_PLAN028_30M_SCENE":"",
        "WBD_PLAN028_FAST_SCENE":"",
        "WBD_PLAN028_FAST_CAPACITY_STEPS":""}):
        x=runpy.run_path(str(FIX))
      self.assertTrue(x["H1531_OUTER_600"])
      self.assertTrue(x["H1520_OUTER_600"])
      self.assertEqual(tuple(x["RATE"]),rate)
      self.assertEqual(tuple(x["LOSS"]),(loss,)*5)
      self.assertEqual(tuple(x["DELAY"]),(200,)*5)
      self.assertEqual(tuple(x["MODES"]),("normal","fec-auto","game2","game4","fec-fixed"))
      self.assertEqual(sum(p[1] for p in x["LONG_PHASES"]),590)
    s=FIX.read_text()
    self.assertIn("12000000 if (LONG_SCENE or H1531_OUTER_600)",s)
    self.assertIn('RATE=(75,2,2,2,2)',s)
    self.assertIn('RATE=(20,14,10,6,10) if physical_loss==0',s)
 def test_separate_hosted_vm_jobs_and_strict_real_outer_gate(self):
    s=(ROOT/".github/workflows/m0-plan028-h1531-linux-outer300-350.yml").read_text()
    for tag in ("matrix:","outer300to350-loss0","outer300to350-loss30",
      "m0_plan028_h1525_native_m4_replay.py","--strict-band","--band-min 300",
      "m0_plan028_h1520_linux_outer_monitor.py","m0_plan028_h1504_vm_safety_guard.py",
      "m0-plan024-linux-product","42775103187","h1250-product-*.log"):
        self.assertIn(tag,s)
    self.assertNotIn("cargo +1.85.1 build",s)
    assert (ROOT/"tools/m0_plan028_h1520_linux_outer_monitor.py").is_file()
    assert (ROOT/"tools/m0_plan028_h1525_native_m4_replay.py").is_file()
