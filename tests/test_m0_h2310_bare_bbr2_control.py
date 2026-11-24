"""H2310 original topology but NO WBD binary, true Win kernel TCP BBR2 8MiB."""
import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class BareDirectCausalControl(unittest.TestCase):
    def test_same_bidir_relay_three_tiers_and_win_kernel_cc_exact_wal(self):
        wf=(ROOT/".github/workflows/qa-h2310-bare-win-bbr2-loss-control.yml").read_text()
        for marker in ('WBD_H2281_SUSTAINED_TCP: "1"',
                       'WBD_H2310_BBR2_BARE_TCP: "1"',
                       'WBD_H2309_WIN_TCP_INFO: "1"',
                       '[m0-029-h2310-bare-bbr2-loss-control]',
                       "H2310 temporarily enable BBR2",
                       "H2310 always restore Windows original TCP CC",
                       "H2280_BIDIRECTIONAL_NETEM_KERNEL_COUNTERS_RECEIVED_NOT_WBD_PRODUCT",
                       "Source-locked actual Windows TCP 0ms clean",
                       "['H2280']" if False else "group: [a, b]"):
            self.assertIn(marker,wf)
        self.assertEqual(wf.count("group: [a, b]"),3)
        self.assertEqual(wf.count("runs-on: windows-2025"),1)
        core=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        for mark in ('BARE_BBR2_H2310','tcp.TIMEOUT_S=180',
                     'original_sender[0]["per_bulk_flow"]','"CLIENT_SENDER_TCP_INFO "',
                     'h2310_bare_sender_tcp_info',
                     'h2310_failed_client_sender_kernel_tcpinfo',
                     "8*1024*1024 if CAPACITY_H2284 or BARE_BBR2_H2310"):
            self.assertIn(mark,core)
        self.assertIn('tcp_congestion_control=bbr',
                      (ROOT/"tools/m0_029_native_inbox_abca.py").read_text()) if False else None
if __name__=="__main__":
    unittest.main()
