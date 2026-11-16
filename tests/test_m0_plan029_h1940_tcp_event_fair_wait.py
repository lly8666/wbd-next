"""H1940 Win32 wait low-index bias: bounded 3-way priority rotation."""
import pathlib
import unittest
R=pathlib.Path(__file__).resolve().parents[1]
class EventClassFairness(unittest.TestCase):
 def test_original_rust_tx_wait_priorities_are_rotated(self):
  s=(R/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
  self.assertIn("fn native_tx_wait_order(phase:u8,has_tcp:bool)",s)
  self.assertIn("let mut wait_phase=0u8;",s)
  self.assertIn("let (mut order,n)=native_tx_wait_order(wait_phase,count==19);",s)
  self.assertIn("if n==19{",s)
  self.assertIn("rotate_tcp_shard_wait_order(&mut order,wait_phase,socket_wait_head);",s)
  self.assertIn("wait_phase=(wait_phase+1)%3;",s)
  self.assertIn("socket_wait_head=((kind-3+1)&15) as u8;",s)
  self.assertIn("fn rotate_tcp_shard_wait_order(",s)
  self.assertIn("order[start+i]=3+((usize::from(first_shard)+i)&15) as u8;",s)
  self.assertIn("assert_eq!(order[first_tcp_index],3+head);",s)
  self.assertIn("assert_eq!(once,std::array::from_fn(|i|i as u8));",s)
  self.assertIn("assert_eq!(&plain[..3],&[0,1,2]);",s)
  self.assertIn("io::wait_ready(&ordered[..n],timeout)",s)
  self.assertIn("s.note_tcp_socket_wake(kind-3);",s)
  self.assertIn("native_tx_wait_order(0,true)",s)
  self.assertIn("native_tx_wait_order(1,true)",s)
  self.assertIn("native_tx_wait_order(2,true)",s)
  self.assertIn("assert_eq!(&no[..3],&[0,1,2]);",s)
 def test_no_second_wait_or_thread_or_existing_progress_ticket_change(self):
  s=(R/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
  self.assertNotIn("io::wait_ready(&handles[..count],timeout)",s)
  d=(R/"crates/wbd-engine/src/v4_windows_native_tcp_direct.rs").read_text()
  self.assertIn("schedule_connected_first_relay_tick(",d)
  self.assertIn("if relay_needs_continuation(",d)
  self.assertIn("buffered!=0 || bytes_read!=0 || bytes_written!=0 || close_probe_due",d)
if __name__=="__main__":unittest.main()
