"""Portable scoped source-clock gap correlation regression tests."""
import unittest
from tools.m0_wl_plan027_burst_clock import burst_windows

class BurstClockTests(unittest.TestCase):
 def test_gap_uses_original_sender_same_clock_bins(self):
  sender={"sent_packets":8,"send_10ms_bucket_counts":[2,2,2,2],
          "measurement_duration_s":.04}
  rec={"received_sequence_gap_summary":{
       "first_64_missing_sequence_ranges":[{"start":2,"end_exclusive":4,
                                             "missing_packets":2}]}}
  result=burst_windows({"wl_n0_measured":{"linux":sender,"windows":rec}})
  w=result["windows"];self.assertEqual(w["status"],"SENDER_RELATIVE_10MS_OBSERVED_ONLY")
  self.assertEqual(w["gaps"][0]["sender_clock_first_bin_s"],.01)
  self.assertEqual(w["gaps"][0]["sender_clock_end_bin_exclusive_s"],.02)
  self.assertTrue(w["no_cross_os_clock_or_loss_location_inference"])
 def test_bad_bins_do_not_claim_cause(self):
  sender={"sent_packets":8,"send_10ms_bucket_counts":[2,2,2],
          "measurement_duration_s":.04}
  result=burst_windows({"wl_n0_measured":{"linux":sender,"windows":{}}})
  self.assertEqual(result["windows"]["status"],"INCONCLUSIVE_BINS_SENT_TOTAL_MISMATCH")
 def test_out_of_range_source_is_fail_closed(self):
  sender={"sent_packets":4,"send_10ms_bucket_counts":[2,2],
          "measurement_duration_s":.02}
  rec={"received_sequence_gap_summary":{"first_64_missing_sequence_ranges":
       [{"start":3,"end_exclusive":5}]}}
  result=burst_windows({"wl_n0_measured":{"linux":sender,"windows":rec}})
  self.assertEqual(result["windows"]["status"],"INCONCLUSIVE_SOURCE_SEQUENCE_OUT_OF_RANGE")

if __name__=="__main__":unittest.main()
