"""H2229 ACK-only appearance contract: never a per-record M2 receipt or TUN HOL gate."""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
read=lambda name:(ROOT/name).read_text()

class H2229AckSemantics(unittest.TestCase):
    def test_linux_normal_auth_10ms_and_full_window(self):
        s=read("crates/wbd-engine/src/v4_embedded_go.rs")
        self.assertIn('authenticated_at!=0',s)
        self.assertIn('ack32!=*last_ack_sent32',s)
        self.assertIn('10_000_000',s)
        self.assertIn('send_presentation_ack_sack(',s)
        self.assertNotIn('advertised_window:4096',s)
        self.assertIn('advertised_window:65_535',s)
        self.assertIn('presentation_ack.verified(absolute,len)',s)
        self.assertIn('receipt.authenticated_link>0||receipt.authenticated_control',s)
    def test_linux_game_authenticated_no_hol_then_ack(self):
        s=read("crates/wbd-engine/src/v4_game_public_kernel.rs")
        self.assertIn('rx_seqs:Vec<u32>',s)
        self.assertIn('NativePresentationAck::new(rx_initial)',s)
        self.assertIn('send_presentation_ack_sack(generation,tuple,',s)
        self.assertIn('presentation_game_ack_due(clock_ns',s)
        self.assertIn('ack32:tx_ack[index].load(Ordering::Acquire)',s)
        self.assertIn('ack32:tx_ack[0].load(Ordering::Acquire)',s)
        self.assertNotIn('advertised_window:4096',s)
        self.assertNotIn('ack32:1,',s)
        auth=s.index('let opened=lane_opener.open(&mut wire[..len]);')
        verified=s.index('let _=ack_ledger.verified(seq32,len);',auth)
        published=s.index('rx_ack[i].store(ack_ledger.ack(),Ordering::Release);',verified)
        self.assertLess(auth,verified)
        self.assertLess(verified,published)
        self.assertIn('if matches!(&opened,Ok(Some(_))){',s[auth:verified])
        self.assertIn('rx_tun.write_authenticated_ipv4',s[published:])
        # ACK is about authenticated physical DATA, not TUN logical delivery.
        self.assertIn('let _=ack_ledger.abandon_stalled(now_ns);',s[verified:published])
    def test_real_go_tls_original_boundary_and_rekey(self):
        s=read("crates/wbd-engine/src/v4_embedded_go.rs")
        self.assertIn('(lane,e.flow,u64::from(e.game_tx_boundary),e.rx_boundary)',s)
        self.assertIn('e.flows.clone(),e.tx_seqs.clone(),e.rx_seqs.clone()',s)
        self.assertIn('new_flow,new_seq,new_rx_seq,prepared',s)
        self.assertIn('g.rx_seqs[slot]=new_rx_seq;',s)
    def test_windows_original_ack_semantics_and_faster_sack(self):
        w=read("crates/wbd-engine/src/v4_windows_native_runtime.rs")
        g=read("crates/wbd-engine/src/v4_windows_game_native_runtime.rs")
        self.assertIn('Duration::from_millis(10)',w)
        self.assertIn('NativePresentationAck as AckLedger',g)
        self.assertIn('advertised_window:65535',g)
        self.assertIn('native_ack_only_due(',w)
        self.assertIn('fn send_ack(',g)
    def test_shared_ledger_only_presentation_no_feedback(self):
        s=read("crates/wbd-engine/src/v4_presentation_ack.rs")
        self.assertIn('ACK_ONLY_MIN_INTERVAL_NS:u64=10_000_000',s)
        self.assertIn('STEADY_TCP_WINDOW:u16=65_535',s)
        self.assertIn('fn verified(',s)
        self.assertNotIn('seal_record(',s)
        self.assertNotIn('receipt.on_',s)
        self.assertNotIn('sleep(',s)
        self.assertNotIn('wait(',s)
        self.assertIn('future.splice(',s)
        self.assertIn('real_out_of_order',s)
if __name__=="__main__":unittest.main()
