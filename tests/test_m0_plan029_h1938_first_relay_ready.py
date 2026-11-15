"""H1938 first Direct TCP reply: no lost initial read after connect."""
import pathlib
import unittest
R=pathlib.Path(__file__).resolve().parents[1]
class InitialRelayReady(unittest.TestCase):
 def test_connect_handoff_always_has_one_bounded_first_read_ticket(self):
  s=(R/"crates/wbd-engine/src/v4_windows_native_tcp_direct.rs").read_text()
  begin=s.index('Ok(mut relay)=>{')
  end=s.index('flow.phase=Some(TcpPhase::Relaying(relay));',begin)
  block=s[begin:end]
  self.assertIn('relay.enable_event_driven_reads();',block)
  self.assertIn('schedule_connected_first_relay_tick(',block)
  # The old code requeued only when FD_CLOSE had already happened,
  # which cannot guarantee draining an FD_READ consumed by Connecting.
  self.assertNotIn('if flow.close_hints[0]||flow.close_hints[1]{',block)
  self.assertIn('fn plan029_h1938_connected_relay_first_tick_when_no_close_hint()',s)
 def test_no_risk_to_proven_read_and_write_progress_tickets(self):
  s=(R/"crates/wbd-engine/src/v4_windows_native_tcp_direct.rs").read_text()
  self.assertIn('buffered!=0 || bytes_read!=0 || bytes_written!=0 || close_probe_due',s)
  self.assertIn('if relay_needs_continuation(',s)
  self.assertIn('connected_first_probe_tickets=',s)
  self.assertIn('ready_wait_ge8_ms=',s)
  self.assertIn('ready_wait_ge16_ms=',s)
if __name__=="__main__":unittest.main()
