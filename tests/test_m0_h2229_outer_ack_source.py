"""H2229 source-scoped ACK/window guards; not a surrogate for native WAN."""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
ENGINE=ROOT/"crates/wbd-engine/src"
READ=lambda name:(ENGINE/name).read_text()

class H2229AckSource(unittest.TestCase):
    def test_linux_normal_steady_window_65535_no_4096(self):
        rust=READ("v4_embedded_go.rs")
        self.assertNotIn("advertised_window:4096",rust)
        self.assertIn("advertised_window:crate::v4_outer_ack_ledger::STEADY_TCP_WINDOW",rust)
        self.assertIn("last_ack_sent:&mut u32",rust)
        self.assertIn("ack_only_due(prior,now,changed)",rust)
        self.assertIn("authenticated_at!=0 && outer.is_some()",rust)
        self.assertIn("if sack_negotiated{presentation_ack.sacks()}else{Vec::new()}",rust)
    def test_linux_game_no_fake_ack1_window4096_and_live_contiguous_crypto(self):
        rust=READ("v4_game_public_kernel.rs")
        self.assertNotIn("ack32:1,",rust)
        self.assertNotIn("advertised_window:4096",rust)
        self.assertIn("ack32:tx_outer_ack[index].load(Ordering::Acquire)",rust)
        self.assertIn("CosmeticAckLedger::new(rx_seqs[i])",rust)
        self.assertIn("CosmeticAckLedger::new(change.rx_seq)",rust)
        self.assertIn("original_game_ack_after_commit",rust)
        self.assertIn("committed.is_ok()",rust)
        self.assertIn("finished.is_ok()",rust)
        self.assertIn("raw.send_presentation_ack_sack",rust)
    def test_win_game_shared_authenticated_ack_book_and_window(self):
        game=READ("v4_windows_game_native_runtime.rs")
        self.assertIn("CosmeticAckLedger as AckLedger",game)
        self.assertNotIn("struct AckLedger{",game)
        self.assertIn("advertised_window:65535",game)
        normal=READ("v4_windows_native_runtime.rs")
        self.assertIn("last_sack_publish.elapsed()>=Duration::from_millis(10)",normal)
        self.assertIn("build_presentation_ack_sack",normal)
        self.assertIn("if native_ack_only_due(",normal)
    def test_true_original_tls_game_rx_anchor_and_rekey(self):
        code=READ("v4_embedded_go.rs")
        self.assertIn("e.rx_seqs.clone(),e.server",code)
        self.assertIn("e.rx_boundary",code)
        self.assertIn("driver.replace_one_authenticated_lane(slot,new_flow,new_seq,new_rx,prepared)",code)
        self.assertIn("g.rx_seqs[slot]=new_rx",code)
    def test_bounded_pure_cosmetic_nothing_to_do_with_m3_hol(self):
        ledger=READ("v4_outer_ack_ledger.rs")
        self.assertIn("OUTER_ACK_COALESCE_NS:u64=10_000_000",ledger)
        self.assertIn("OUTER_ACK_STALLED_NS:u64=250_000_000",ledger)
        self.assertIn("self.future.splice(at..until",ledger)
        self.assertIn("if until==at&&self.future.len()>=256",ledger)
        self.assertIn("return self.next as u32",ledger)
        self.assertIn("positive_change&&last.is_none_or",ledger)
        for forbidden in ("write_authenticated_ipv4(", "deliver_authenticated(",
                          "on_authenticated_data(", "on_health_send_result("):
            self.assertNotIn(forbidden,ledger)
    def test_no_retransmission_maintenance_or_m2_packet_regression(self):
        game=READ("v4_game_public_kernel.rs")
        self.assertIn("cosmetic.take_due(clock_ns,&[])",game)
        self.assertIn("cosmetic.complete(copy.lane,copy.pn,copied",game)
        normal=READ("v4_embedded_go.rs")
        self.assertIn("original_process_repair_quota()",normal)
        self.assertIn("original_outer",normal)
        self.assertIn("original_presentation_ack_tests",normal)
if __name__=="__main__":
    unittest.main()
