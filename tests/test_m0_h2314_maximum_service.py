"""H2314: Fixed maximum r20/k16 native sender service budget and opt-in safety.

Static only; Windows Rust unit separately checks source/PN/AEAD/settlement.
Neither proves a two-OS FEC maximum product goodput result.
"""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MaximumWindowService(unittest.TestCase):
    def test_previous_original_4row_ffi_and_default_remain(self):
        owner=(ROOT/"crates/wbd-engine/src/v4_windows_fec2_owner.rs").read_text()
        runtime=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        eng=(ROOT/"crates/wbd-engine/Cargo.toml").read_text()
        self.assertIn("h2314_windows_fixed_max_burst = []",eng)
        self.assertIn("rows:[WindowsFixedParityRow;4]",owner)
        self.assertIn("rows:[WindowsFixedParityRow;20]",owner)
        self.assertIn("stream.poll_parity_quanta(m2_clock(),5",owner)
        self.assertIn("stream.profile_index()!=6",owner)
        self.assertIn("m0_windows_fixed_maximum_twenty_frozen_rows_one_original_prefix",owner)
        self.assertIn("send_fixed_maximum_parity(",runtime)
        self.assertIn("if !auto{",runtime)
        self.assertIn("for _ in 0..2{",runtime)
        self.assertIn("fixed_parity_copied_rows",runtime)
        self.assertIn(".settle_staged(copied,not_sent,uncertain)",runtime)
        self.assertIn("PLAN029_H2314_MAXIMUM_PARITY_STOP",runtime)
        self.assertIn("copied_npf_not_remote_delivery=1",runtime)
        self.assertIn("if counters.stopping.load(Ordering::Acquire){break}",runtime)
    def test_old_normal_and_auto_paths_preserved(self):
        runtime=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        self.assertIn('cfg(not(feature="h2314_windows_fixed_max_burst"))',runtime)
        self.assertIn("send_fixed_parity(&cfg,&lane,&mut npf,&counters,&mut ip_id)?",runtime)
        self.assertIn("let mut frames=[[0u8;MAX_LINK];4];",runtime)
        self.assertIn("for _ in 0..(RX_WAKE_BATCH/BATCH)",runtime)
        self.assertIn("m0_h2314_fixed_maximum_two_ready_twenty_rows_cover_full_source_turn",runtime)
        self.assertNotIn("h2314_windows_fixed_max_burst = [", (ROOT/"crates/wbd-platform/Cargo.toml").read_text())
if __name__=="__main__":
    unittest.main()
