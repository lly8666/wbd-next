#!/usr/bin/env python3
"""Exact H1350 offline reporter phase contract; NO network runs."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/"tools"/"m0-plan028-h1286-rapid-report.py"
spec=importlib.util.spec_from_file_location("plan028_h1286_offline",SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

LEGACY=[
 ("first_wave",30,.2),("sustained",60,.5),
 ("overload",30,1.),("recovery",50,.5)]
H1349=[
 ("first_wave",20,.15),("sustained",30,.25),
 ("climb_10",30,.5),("overload_20",30,1.),("recovery",60,.5)]

class H1350ExactFivePhaseReporter(unittest.TestCase):
 def test_legacy_four_phases_remain_accepted(self):
  self.assertEqual(module.verified_capacity_workload(LEGACY),LEGACY)

 def test_exact_real_h1349_five_stage_3_5_10_20_10_accepted(self):
  self.assertEqual(module.verified_capacity_workload(H1349),H1349)
  self.assertEqual([round(20*scale,3) for _,_,scale in H1349],[3,5,10,20,10])
  self.assertEqual(10+sum(seconds for _,seconds,_ in H1349),180)

 def test_no_wrong_five_phase_rates_or_missing_recovery_pass(self):
  invalids=[
   H1349[:-1],
   H1349[:-1]+[("recovery",50,.5)],
   H1349[:2]+[("climb_10",30,.4)]+H1349[3:],
   H1349[:3]+[("overload_20",30,1.3)]+H1349[4:],
   H1349[:3]+[("overload",30,1.)]+H1349[4:],
   list(reversed(H1349)),
   [("first_wave",30,.15),*H1349[1:]],
  ]
  for row in invalids:
   with self.subTest(row=row):
    with self.assertRaises(AssertionError):
     module.verified_capacity_workload(row)

if __name__=="__main__":
 unittest.main()
