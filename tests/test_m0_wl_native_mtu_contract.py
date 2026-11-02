import unittest
from tools.m0_wl_native_mtu_contract import exact_native_test_mtu,native_outer_choice,configured_native_test_mtu,verified_native_windows_inner_mtu
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

 def test_live_windows_numeric_mtu_receipt_is_required_and_not_outer_argument(self):
  prefix="WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1 "
  line=prefix+"planned=1329 applied=1329 outer_config=1460"
  self.assertEqual(verified_native_windows_inner_mtu("owned start\n"+line+"\nWBD_WINDOWS_CLIENT_READY\n",1460),1329)
  self.assertEqual(verified_native_windows_inner_mtu(
   prefix+"planned=1398 applied=1398 outer_config=1500\n",1500),1398)
  for bad in (
   "",prefix+"planned=1329 applied=1328 outer_config=1460",
   prefix+"planned=1500 applied=1500 outer_config=1460",
   prefix+"planned=1329 applied=1329 outer_config=1500",
   line+"\n"+line,
   prefix+"planned=0 applied=0 outer_config=1460",
  ):
   with self.assertRaises(ValueError):
    verified_native_windows_inner_mtu(bad,1460)
  for bad_outer in (0,1501,1460.0,None,True):
   with self.assertRaises(ValueError):
    verified_native_windows_inner_mtu(line,bad_outer)
