"""Historical WL V2 fixture audit is read-only and never invents loss origin."""
import unittest
from tools.m0_wl_v2_gap_audit import longest_steady_gaps,qdisc_delta
class GapAuditTests(unittest.TestCase):
 def test_exact_500ms_10ms_observed_gap(self):
  bins=[200]*6500
  for i in range(501,551):bins[i]=0
  g=longest_steady_gaps(bins,60)
  self.assertEqual(g,[{"start_rel_s":5.01,"end_rel_s":5.51,"duration_ms":500}])
 def test_warmup_and_terminal_zeros_excluded(self):
  bins=[0]*6500
  for i in range(100,5900):bins[i]=200
  self.assertEqual(longest_steady_gaps(bins,60),[])
 def test_top_level_netem_drop_not_nested(self):
  before={"ifb":[{"kind":"netem","handle":"10:","packets":10,"bytes":100,"drops":2,"overlimits":0,"requeues":0}]}
  after={"ifb":[{"kind":"netem","handle":"10:","packets":100,"bytes":1000,"drops":5,"overlimits":2,"requeues":0}]}
  self.assertEqual(qdisc_delta(before,after,"ifb")["drops"],3)
 def test_missing_counter_is_unknown_not_zero(self):
  with self.assertRaises(ValueError):
   qdisc_delta({"eth0":[{"kind":"netem","handle":"20:","packets":0}]},
               {"eth0":[{"kind":"netem","handle":"20:","packets":4}]},"eth0")
if __name__=="__main__":unittest.main()
