import unittest
from tools.m0_wl_native_mtu_contract import exact_native_test_mtu,native_outer_choice,configured_native_test_mtu
from unittest.mock import patch

class NativeM4MTUTests(unittest.TestCase):
 def test_four_original_owner_cas_reconnect_mtus(self):
  for v in (1280,1400,1460,1500):
   self.assertEqual(exact_native_test_mtu(str(v)),v)
   self.assertEqual(exact_native_test_mtu(v),v)
 def test_explicitly_reject_unsupported_or_forged_mtu(self):
  for bad in ("0","576","1279","1501","9000","1400.0","01400",
              "-1","abc",1400.0,None,True):
   with self.assertRaises(ValueError):exact_native_test_mtu(bad)

 def test_default1460_and_explicit_outer_bound(self):
  for choice,mtu in [('default1460',1460),('1460',1460),('1500',1500),('legacy1400',1400)]:
   self.assertEqual(native_outer_choice(choice),choice)
   with patch.dict('os.environ',{'WBD_WL_NATIVE_OUTER_MTU_REQUEST':choice,'WBD_WL_TUN_MTU':str(mtu)}):
    self.assertEqual(configured_native_test_mtu(),mtu)
  for bad in ('default1500','0','1280',None,1460):
   with self.assertRaises(ValueError):native_outer_choice(bad)
  with patch.dict('os.environ',{'WBD_WL_NATIVE_OUTER_MTU_REQUEST':'default1460','WBD_WL_TUN_MTU':'1400'}):
   with self.assertRaises(ValueError):configured_native_test_mtu()
