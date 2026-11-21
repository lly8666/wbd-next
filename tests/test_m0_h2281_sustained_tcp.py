"""H2281 long-running Win Winsock->ARM TCP two triplets, no short-bulk P99."""
import pathlib
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as h


class SustainedNativeTCP(unittest.TestCase):
    def test_source_locked_25_second_real_bulk_overlaps_160_tcp_echo(self):
        self.assertTrue(h.SUSTAINED,"H2281 explicit CI env not set")
        self.assertEqual(h.tcp.BULK_FLOWS,4)
        self.assertEqual(h.tcp.BULK_SEND_S,25)
        self.assertEqual(h.tcp.BULK_MAX_BYTES,512*1024*1024)
        self.assertEqual(h.tcp.ECHO_COUNT,160)
        self.assertGreater(h.tcp.BULK_SEND_S, h.tcp.ECHO_COUNT*h.tcp.ECHO_PERIOD_S)
        self.assertEqual(h.TIERS,(-1,0,1,5))

    def test_workflow_keeps_two_independent_triplets_and_both_loss_directions(self):
        w=(ROOT/".github/workflows/qa-h2281-dual-arm-relay-sustained-tcp.yml").read_text()
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertEqual(w.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(w.count("runs-on: windows-2025"),1)
        self.assertEqual(w.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(w.count("[m0-029-h2281-sustained-3runner]"),3)
        self.assertIn('WBD_H2281_SUSTAINED_TCP: "1"',w)
        self.assertIn("PASS_H2281_SUSTAINED_REAL_BIDIR_KERNEL_TCP_SCOPED",w)
        self.assertIn("all(stage['sparse_echo_inside_bulk_window'] for stage in d['stages'])",w)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",w)
        self.assertNotIn("PASS_FULL_PRODUCT_THROUGHPUT",w)


if __name__=="__main__":
    unittest.main()
