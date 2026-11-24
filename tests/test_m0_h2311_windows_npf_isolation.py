"""P0/H2311: source-locked two-factor isolation and NPF syscall accounting.

The historical H2292 source/ABI remains valid; no REAL Windows result is implied.
"""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class H2311WindowsNPFIsolation(unittest.TestCase):
    def test_two_independent_opt_in_flags_and_old_combined_default(self):
        e=(ROOT/"crates/wbd-engine/Cargo.toml").read_text()
        p=(ROOT/"crates/wbd-platform/Cargo.toml").read_text()
        t=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        io=(ROOT/"crates/wbd-platform/src/windows_native_io.rs").read_text()
        self.assertIn('h2291_windows_tx_service = ["wbd-platform/h2291_windows_tx_service"]',e)
        self.assertIn('h2311_windows_tx16_only = ["wbd-platform/h2311_windows_npf_trace"]',e)
        self.assertIn('h2311_windows_npf64_only = ["wbd-platform/h2311_windows_npf64_only", "wbd-platform/h2311_windows_npf_trace"]',e)
        self.assertIn('h2311_windows_npf64_only = []',p)
        self.assertIn('h2311_windows_npf_trace = []',p)
        self.assertIn('const BATCH:usize=if cfg!(any(feature="h2291_windows_tx_service",',t)
        self.assertIn('feature="h2311_windows_tx16_only")){16}else{8}',t)
        self.assertIn('NPF_QUEUE_BYTES: usize = if cfg!(any(feature="h2291_windows_tx_service", feature="h2311_windows_npf64_only"))',io)
        self.assertIn('NPF_QUEUE_PACKETS: usize = if cfg!(any(feature="h2291_windows_tx_service", feature="h2311_windows_npf64_only"))',io)
        self.assertIn('const RX_WAKE_BATCH:usize=32;',t)
        self.assertIn('for _ in 0..(RX_WAKE_BATCH/BATCH)',t)
        self.assertIn('const POST_INGRESS_RETURN_QUANTUM:usize=8;',t)
    def test_service_trace_is_opt_in_and_stop_only(self):
        io=(ROOT/"crates/wbd-platform/src/windows_native_io.rs").read_text()
        for field in ('queue_calls','queue_frames_submitted','queue_bytes_submitted',
          'queue_bytes_copied','queue_short_calls','direct_calls','direct_bytes_submitted',
          'direct_frames_accepted','direct_errors'):
            self.assertIn(field,io)
        self.assertIn('#[cfg(feature="h2311_windows_npf_trace")]',io)
        self.assertIn('PLAN029_H2311_NPF_STOP_PROFILE',io)
        self.assertIn('driver_copy_not_peer_receipt=1',io)
        self.assertIn('h2311_trace_counts_real_driver_queue_prefix_and_direct_calls',io)
if __name__=="__main__":
    unittest.main()
