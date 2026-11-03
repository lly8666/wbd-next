import unittest
from tools.m0_wl_native_df_kernel import SIZE,PROBE_SIZES,TCP_PORT,DF0_SMALL_ATTEMPTS,payload
class DfSourceTest(unittest.TestCase):
 def test_distinct_1728b_original_datagrams(self):
  self.assertEqual(SIZE,1728)
  self.assertEqual(len(payload("10.66.0.1")),SIZE)
  self.assertNotEqual(payload("10.66.0.1"),payload("10.66.0.2"))
 def test_h990_native_os_udp_4096_and_65507_exact_vectors(self):
  self.assertEqual(PROBE_SIZES,(1728,4096,65507))
  self.assertEqual((TCP_PORT,DF0_SMALL_ATTEMPTS),(45902,3))
  for n in PROBE_SIZES:
   self.assertEqual(len(payload("10.66.0.1",n)),n)
   self.assertNotEqual(payload("10.66.0.1",n),payload("10.66.0.2",n))
  for bad in (63,65508,None,False,1.0):
   with self.assertRaises(ValueError):payload("10.66.0.1",bad)
if __name__=="__main__":unittest.main()
