"""Offline H1520 runner/real outer measurement hard gates; never fake product PASS."""
import importlib.util,pathlib,py_compile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(path):
    spec=importlib.util.spec_from_file_location("h1520_monitor",path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
class H1520LinuxOuterContract(unittest.TestCase):
 def test_five_modes_200ms_duplex_35_mbps_and_old75_unchanged(self):
    s=(ROOT/"tools/m0-plan028-h1259-five-client-recovery-netns.py").read_text()
    self.assertIn("RATE=(12,8,6,3,6)",s)
    self.assertIn("DELAY=(200,)*5",s)
    self.assertIn("LOSS=(physical_loss,)*5",s)
    self.assertIn("ROTATION_SECONDS=(97,109,103,117,127)",s)
    self.assertIn("RATE=(75,2,2,2,2)",s)
    self.assertIn("range(0 if H1520_OUTER_600 else 1, 5)",s)
    self.assertIn("H1520_outer_target_mbps_total_both_directions",s)
 def test_actual_kernel_counter_math_two_way_not_fec_or_config(self):
    m=load(ROOT/"tools/m0_plan028_h1520_linux_outer_monitor.py")
    old={"up":[{"bytes":100}]*5,"down":[{"bytes":50}]*5}
    new={"up":[{"bytes":1000100}]*5,"down":[{"bytes":2000050}]*5}
    v=m.mbps_delta(new,old,.1)
    self.assertEqual(v["up_mbps"],400)
    self.assertEqual(v["down_mbps"],800)
    self.assertEqual(v["total_outer_mbps"],1200)
    with self.assertRaises(ValueError):m.mbps_delta(old,new,10)
 def test_syntax_and_source_locked_scoped_separate_workflows(self):
    for p in ("tools/m0-plan028-h1259-five-client-recovery-netns.py",
              "tools/m0-plan028-h1274-30min-report.py",
              "tools/m0_plan028_h1520_linux_outer_monitor.py",
              "tools/m0_plan028_h1520_linux_outer_verdict.py"):
        py_compile.compile(str(ROOT/p),doraise=True)
    for loss in (0,30):
        s=(ROOT/f".github/workflows/m0-plan028-h1520-linux-outer100-150-loss{loss}.yml").read_text()
        self.assertIn(f"outer100to150-loss{loss}",s)
        self.assertIn("42775103187",s)
        self.assertIn("m0-plan024-linux-product",s)
        self.assertIn("h1520-outer-10s.jsonl",s)
        self.assertNotIn('cargo +1.85.1 build',s)
