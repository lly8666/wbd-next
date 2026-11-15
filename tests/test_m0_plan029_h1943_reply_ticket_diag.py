"""H1943 only opt-in original Rust TX response-side ready age counters."""
import pathlib
import unittest
R=pathlib.Path(__file__).resolve().parents[1]

class ReplyTicketDiagnostics(unittest.TestCase):
    def test_reply_outer_read_and_inner_write_are_distinct(self):
        src=(R/"crates/wbd-engine/src/v4_windows_native_tcp_direct.rs").read_text()
        self.assertIn("fn note_reply_service(",src)
        self.assertIn("note_reply_service(d,ready_age_ms,",src)
        self.assertIn("tick.outer_read,tick.inner_write",src)
        self.assertIn("plan029_h1943_real_outer_reply_ticket_age_is_separate_from_generic_queue",src)
        self.assertIn("reply_outer_ready_wait_ge16_ms={}",src)
        self.assertIn("reply_outer_read_inner_write_same_turn={}",src)
        self.assertIn("relay_needs_continuation(",src)
        self.assertIn("to_requeue.push(port)",src)

    def test_only_source_locked_short_real_original_and_strict_parser(self):
        workflow=(R/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        parser=(R/"tools/m0_plan029_h1815_p2_real_mixed.py").read_text()
        self.assertIn("WBD_PLAN029_P2_REPLY_TICKET_DIAG:",workflow)
        self.assertIn("[plan029-v3-real-p2-reply-ticket-diag]",workflow)
        self.assertIn("PLAN029_H1943_SIGNED_RUST_REPLY_WINSOCK_TICKET_AGE",workflow)
        for key in ("reply_outer_read_turns","reply_outer_ready_wait_max_ms",
                    "reply_outer_ready_wait_ge8_ms","reply_outer_ready_wait_ge16_ms",
                    "reply_outer_read_inner_write_same_turn",
                    "reply_outer_read_no_inner_write",
                    "reply_inner_write_deferred_turns"):
            self.assertIn('"'+key+'"',parser)
        self.assertIn("H1943 partial/invalid original reply diagnostic",parser)
        self.assertIn("H1943 original Rust reply timing invariant failed",parser)

if __name__=="__main__":unittest.main()
