"""Portable real load-fixture data accounting tests; no driver required."""
import unittest
from tools.m0_wl_rate_utils import FirstDeliveryBitmap,bounded_sequence_limit,rate_wait_seconds,receiver_buffer_request_bytes

class RateUtilsTests(unittest.TestCase):
 def test_first_arrival_exact_and_bounded_no_python_set(self):
  b=FirstDeliveryBitmap(1000000)
  for n in (0,7,8,21,65433,999999,1000000):
   self.assertTrue(b.add(n))
   self.assertFalse(b.add(n))
   self.assertIn(n,b)
  self.assertEqual((len(b),b.low,b.high),(7,0,1000000))
  self.assertNotIn(17,b)
  self.assertNotIn(1000001,b)
  with self.assertRaises(ValueError):b.add(1000001)
 def test_200m_bitmap_bounded_not_100mb_python_integer_set(self):
  b=FirstDeliveryBitmap(bounded_sequence_limit(200*1000000/8,60,64))
  self.assertLess(b.storage_bytes,7000000)
  self.assertNotIn(1<<63,b)
 def test_socket_wait_until_real_next_packet(self):
  self.assertAlmostEqual(rate_wait_seconds(10,12,13,0,1200,1200000,11),.001)
  self.assertEqual(rate_wait_seconds(10,12,13,1200,1200,1200000,11),0)
  self.assertAlmostEqual(rate_wait_seconds(10,12,13,0,1200,1200000,10.0003),.0003)
  self.assertAlmostEqual(rate_wait_seconds(12.1,12,13,0,1200,1200000,20),.05)
  self.assertEqual(rate_wait_seconds(13,12,13,0,1200,1200000,20),0)
 def test_only_windows_v2_asks_larger_socket(self):
  self.assertEqual(receiver_buffer_request_bytes("win32",True),16777216)
  self.assertEqual(receiver_buffer_request_bytes("linux",True),4194304)
  self.assertEqual(receiver_buffer_request_bytes("win32",False),2097152)

if __name__=="__main__":unittest.main()
