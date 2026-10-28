import unittest
from tools.m0_wl_lock_profile import parse_native_lock_profile

class NativeLockReportTest(unittest.TestCase):
    def test_measured_rust_lock_report(self):
        row=parse_native_lock_profile("WBD_WINDOWS_RUST_NATIVE_ENTRY_LOCK_SAMPLED sample_every=64 tx_samples=10 tx_wait_ns=5000 tx_max_ns=1500 rx_samples=4 rx_wait_ns=900 rx_max_ns=300")
        self.assertEqual(row["status"],"MEASURED")
        self.assertEqual(row["tx_mean_wait_ns"],500)
        self.assertEqual(row["rx_mean_wait_ns"],225)
    def test_absent_report_remains_unknown(self):
        self.assertEqual(parse_native_lock_profile("")["status"],"NOT_MEASURED")
