"""H2280 CI invariant: real native dual 3-runner loss only after bidir kernel readback.

Never substitute simulated loss or fake packet success for native Win→ARM TCP.
"""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as core


class H2280BidirNetem(unittest.TestCase):
    def test_real_source_unchanged_original_tcp_probe(self):
        self.assertEqual(core.PORT,18727)
        self.assertEqual(core.tcp.BULK_FLOWS,4)
        self.assertEqual(core.tcp.ECHO_COUNT,160)
        self.assertEqual(core.TIERS,(-1,0,1,5))

    def test_real_workflow_both_groups_same_source_same_four_stages(self):
        wf=(ROOT/".github/workflows/qa-h2280-dual-arm-relay-bidir-netem-tcp.yml").read_text()
        self.assertEqual(wf.count("group: [a, b]"),3)
        self.assertEqual(wf.count("runs-on: windows-2025"),1)
        self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(wf.count("uses: tailscale/github-action@v4"),3)
        self.assertIn('WBD_H2279_CAPACITY_AB: "0"',wf)
        self.assertEqual(wf.count("[m0-029-h2280-bidir-netem]"),3)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",wf)
        self.assertIn("PASS_H2280_REAL_BIDIR_KERNEL_NETEM_TCP_SCOPED",wf)
        self.assertEqual(wf.count("assert [x['stage_id'] for x in d['stages']]==[-1,0,1,5]"),2)
        self.assertIn(
            "assert all(x['actual_peer'] == d['stages'][0]['actual_peer'] for x in d['stages'])", wf)
        self.assertNotIn(
            "d['stages'][0]['actual_peer'] != d['stages'][1]['actual_peer']", wf)

    def test_synthetic_healthy_receipt_same_epoch_while_one_direction_absent_fails(self):
        def qdisc(up,down,updrop=0,downdrop=0):
            return [
              {"kind":"netem","parent":"1:3","handle":"30:","packets":up,"drops":updrop},
              {"kind":"netem","parent":"1:4","handle":"40:","packets":down,"drops":downdrop}
            ]
        for pct in (0,1,5):
            valid=core.netem_phase_receipt(qdisc(0,0),qdisc(400,160,20,5),pct)
            self.assertGreater(valid["per_direction"]["win_to_arm"]["egress_packets"],0)
            self.assertGreater(valid["per_direction"]["arm_to_win"]["egress_packets"],0)
        for before,after in (
            (qdisc(0,0),qdisc(400,0,20,0)),
            (qdisc(0,0),qdisc(0,400,0,20)),
            (qdisc(0,0),qdisc(400,160,2,0)),
        ):
            with self.assertRaises(RuntimeError):
                core.netem_phase_receipt(before,after,1)

    def test_explicitly_no_wbd_product_promotion(self):
        wf=(ROOT/".github/workflows/qa-h2280-dual-arm-relay-bidir-netem-tcp.yml").read_text()
        self.assertIn("NOT measured here",wf)
        self.assertNotIn("PASS_FULL_PRODUCT_THROUGHPUT",wf)


if __name__=="__main__":
    unittest.main()
