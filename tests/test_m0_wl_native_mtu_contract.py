import unittest
from tools.m0_wl_native_mtu_contract import exact_native_test_mtu

class NativeM4MTUTests(unittest.TestCase):
 def test_three_original_owner_cas_reconnect_mtus(self):
  for v in (1280,1400,1500):
   self.assertEqual(exact_native_test_mtu(str(v)),v)
   self.assertEqual(exact_native_test_mtu(v),v)
 def test_explicitly_reject_unsupported_or_forged_mtu(self):
  for bad in ("0","576","1279","1501","9000","1400.0","01400",
              "-1","abc",1400.0,None,True):
   with self.assertRaises(ValueError):exact_native_test_mtu(bad)
