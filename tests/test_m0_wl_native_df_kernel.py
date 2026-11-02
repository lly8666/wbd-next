import unittest
from tools.m0_wl_native_df_kernel import SIZE,payload
class DfSourceTest(unittest.TestCase):
 def test_distinct_1728b_original_datagrams(self):
  x=payload("10.66.0.1");y=payload("10.66.0.2")
  self.assertEqual((len(x),len(y)),(SIZE,SIZE))
  self.assertEqual(SIZE,1728)
  self.assertNotEqual(x,y)
if __name__=="__main__":unittest.main()
