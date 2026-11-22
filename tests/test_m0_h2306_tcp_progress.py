"""H2306: test-only failure phase progress and true ARM TCP kernel witness."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class H2306OriginalProductProgress(unittest.TestCase):
    def test_real_socket_failure_phase_and_partial_echo(self):
        p=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        for value in ("WBD_H2306_TCP_PROGRESS","CLIENT_PROGRESS_DIAGNOSTIC",
                      "await_arm_receipt","sendall_bulk","submitted_bytes",
                      "finished_bulk_flows","echo_received","socket_timeout_s",
                      "diagnostic_not_goodput_or_success"):
            self.assertIn(value,p)
        self.assertIn('sock.shutdown(socket.SHUT_WR)',p)
        self.assertIn("H2271_REAL_TCP_CLIENT_INCOMPLETE",p)
        w=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertIn("H2306_REAL_TCP_PROGRESS_ON_FAILURE",w)
        self.assertIn('output["h2306_tcp_progress_on_failure"]=rows[0]',w)
    def test_arm_read_only_accepted_tcp_info(self):
        p=(ROOT/"tools/m0_h2287_tun_tcp_trace.py").read_text()
        for value in ('established_45902_actual_ss_tin','"ss","-H","-tin","sport"',
                      'RetransSegs','socket.AF_PACKET','WBD_H2306_TCP_PROGRESS'):
            self.assertIn(value,p)
        self.assertNotIn('s.sendto(',p)
        self.assertNotIn('s.sendall(',p)
        a=(ROOT/"tools/m0_h2286_arm_product.py").read_text()
        self.assertIn('WBD_H2306_TCP_PROGRESS="+os.environ.get("WBD_H2306_TCP_PROGRESS","0")',a)
    def test_real_rust_route_drop_counters_are_opt_in_and_not_queue_resize(self):
        arm=(ROOT/"tools/m0_h2286_arm_product.py").read_text()
        self.assertIn('WBD_SHARED_TUN_ROUTE_DIAG=1',arm)
        self.assertIn('WBD_H2306_TCP_PROGRESS',arm)
        self.assertIn('*route_diag,*server',arm)
        src=(ROOT/"crates/wbd-engine/src/v4_embedded_go.rs").read_text()
        for term in ("WBD_SHARED_TUN_ROUTE_DIAG",
                     "M0_SHARED_TUN_LEASE_QUEUE_DIAG",
                     "tcp_new_dropped",
                     "SHARED_TUN_PENDING_PER_ROUTE:usize=8",
                     "SHARED_TUN_PENDING_MAX_AGE:Duration=Duration::from_millis(100)"):
            self.assertIn(term,src)

    def test_1pct_5pct_real_original_dual_triplet(self):
        for loss in (1,5):
            s=(ROOT/f".github/workflows/qa-h2306-2to8-loss{loss}.yml").read_text()
            for value in (f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',
                          'WBD_H2306_TCP_PROGRESS: "1"',
                          'WBD_H2302_BASE_BYTES: "2097152"',
                          'WBD_H2302_TUNED_BYTES: "8388608"',
                          'WBD_H2294_OFF_REPAIR_ABA: "0"',
                          f"[m0-029-h2306-2to8-loss{loss}]",
                          "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
                          "==[2097152,8388608,2097152]",
                          "client_owned_stop","kernel_relay_qdisc"):
                self.assertIn(value,s)
if __name__=="__main__":
    unittest.main()
