"""H2281 long-running Win Winsock->ARM TCP two triplets, no short-bulk P99."""
import pathlib
import json
import os
import subprocess
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as h


class SustainedNativeTCP(unittest.TestCase):
    def test_source_locked_25_second_real_bulk_overlaps_160_tcp_echo(self):
        # Governance maintenance is intentionally run WITHOUT workflow env;
        # verify the real opt-in source in a fresh isolated Python interpreter.
        env=dict(os.environ, WBD_H2281_SUSTAINED_TCP="1",
                 WBD_H2282_TCP_WINDOW_AB="0",
                 WBD_H2284_EIGHT_TCP_CAPACITY="0")
        code=("import json,sys; sys.path.insert(0,'tools');"
              "import m0_h2276_three_runner_tcp as x;"
              "print(json.dumps([x.SUSTAINED,x.tcp.BULK_FLOWS,"
              "x.tcp.BULK_SEND_S,x.tcp.BULK_MAX_BYTES,"
              "x.tcp.ECHO_COUNT,x.tcp.ECHO_PERIOD_S,x.TIERS]))")
        p=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=env,
                         capture_output=True,text=True,check=True)
        cfg=json.loads(p.stdout)
        self.assertEqual(cfg[:5],[True,4,25,512*1024*1024,160])
        self.assertGreater(cfg[2],cfg[4]*cfg[5])
        self.assertEqual(cfg[6],[-1,0,1,5])

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
