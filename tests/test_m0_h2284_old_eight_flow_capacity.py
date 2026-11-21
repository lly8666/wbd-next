"""H2284 dual 3runner native Windows ARM capacity baseline informed by H2228.

H2228 800+ Mbps was x86 Linux BBR with 8 iperf flows/64MiB netns auto
buffers and two VXLAN L2 routes; new Windows 2x3 native Winsock is different.
Tests must not equate such different OS/runtime/route/stream configurations.
"""
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as h


class H2284OldFixtureCapacity(unittest.TestCase):
    def test_real_8tcp_source_import_only_with_explicit_capacity_flag(self):
        code=("import json,sys;sys.path.insert(0,'tools');"
              "import m0_h2276_three_runner_tcp as x;"
              "print(json.dumps([x.CAPACITY_H2284,x.tcp.BULK_FLOWS,"
              "x.tcp.BULK_SEND_S,x.tcp.BULK_MAX_BYTES,"
              "x.active_stages(),x.tcp.ECHO_COUNT,x.WINDOW_AB]))")
        env=dict(os.environ,WBD_H2284_EIGHT_TCP_CAPACITY="1",
                 WBD_H2281_SUSTAINED_TCP="1",WBD_H2282_TCP_WINDOW_AB="0",
                 WBD_H2283_B_BYTES="8388608")
        x=subprocess.run([sys.executable,"-c",code],env=env,cwd=ROOT,
                         capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(x.stdout),
          [True,8,25,512*1024*1024,
           ["clean_direct","clean_relay","wan_relay"],160,False])
        with patch.object(h,"CAPACITY_H2284",True):
            relay={"relay_ip":"100.70.20.1","client_ip":"100.70.20.2"}
            server={"tail_ip":"100.70.20.3"}
            self.assertEqual(h.client_tcp_target("clean_direct",relay,server),
                             server["tail_ip"])
            self.assertEqual(h.client_tcp_target("clean_relay",relay,server),
                             relay["relay_ip"])
            self.assertEqual(h.server_expected_tcp_peer("clean_direct",relay),
                             relay["client_ip"])
            self.assertEqual(h.server_expected_tcp_peer("wan_relay",relay),
                             relay["relay_ip"])
            self.assertEqual([h.actual_loss_tier(x) for x in
                ("clean_direct","clean_relay","wan_relay")],[-1,-1,0])
            for stage in ("clean_direct","clean_relay","wan_relay"):
                h.prepare_tcp_sockbuf(stage)
                self.assertEqual(h.tcp.WINDOW_TEST_BYTES,8*1024*1024)
        h.tcp.WINDOW_TEST_BYTES=0

    def test_relay_actual_proc_cpu_delta_and_hot_single_core(self):
        prior={"at_monotonic":1.0,"host_allcore":[100,100],
               "cores":{"cpu0":[10,10],"cpu1":[90,10]},
               "tailscaled_cpu_s_by_pid":{"212":1.0}}
        after={"at_monotonic":26.0,"host_allcore":[150,150],
               "cores":{"cpu0":[10,25],"cpu1":[105,10]},
               "tailscaled_cpu_s_by_pid":{"212":13.5}}
        d=h.relay_resource_delta(prior,after)
        self.assertEqual(d["tailscaled_pid_count_common"],1)
        self.assertEqual(d["tailscaled_cpu_s"],12.5)
        self.assertEqual(d["tailscaled_pct_of_one_cpu"],50.0)
        self.assertEqual(d["relay_host_allcore_busy_pct"],50.0)
        self.assertEqual(d["relay_max_single_core_busy_pct"],100.0)
        with self.assertRaises(RuntimeError):
            h.relay_resource_delta(prior,{**after,"at_monotonic":0})

    def test_two_identical_three_runner_groups_and_actual_8flow_receipts(self):
        wf=(ROOT/".github/workflows/qa-h2284-old8-flow-capacity.yml").read_text()
        self.assertEqual(wf.count("group: [a, b]"),3)
        self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(wf.count("runs-on: windows-2025"),1)
        self.assertEqual(wf.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(wf.count("[m0-029-h2284-eightflow-capacity]"),3)
        self.assertIn('WBD_H2284_EIGHT_TCP_CAPACITY: "1"',wf)
        self.assertIn('WBD_H2281_SUSTAINED_TCP: "1"',wf)
        self.assertIn('WBD_H2282_TCP_WINDOW_AB: "0"',wf)
        self.assertIn("PASS_H2284_NATIVE_8TCP_H2228_CAPACITY_COMPARISON_SCOPED",wf)
        self.assertIn("relay_resource_receipt",wf)
        self.assertEqual(wf.count(
            "assert [x['stage_id'] for x in d['stages']]==['clean_direct','clean_relay','wan_relay']"),2)
        self.assertIn("NOT measured here",wf)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",wf)
        self.assertNotIn("PASS_FULL_PRODUCT_THROUGHPUT",wf)

    def test_old_h2228_high_speed_evidence_is_not_same_windows_arm_product(self):
        path=ROOT/"docs/evidence/M0/PLAN029-H2228-THREE-ARM-RELAY-GE200-REAL-TCP-20261120.json"
        v=json.loads(path.read_text())
        self.assertGreater(v["baseline_0ms_zero_loss_direct_8parallel_mbps"]["upload"],800)
        self.assertGreater(v["baseline_0ms_zero_loss_direct_8parallel_mbps"]["download"],800)
        self.assertEqual(v["topology"]["client"],"independent_ubuntu24_x86_64")
        self.assertEqual(v["topology"]["server"],"independent_ubuntu24_x86_64")
        self.assertFalse("windows" in v["topology"]["client"])
        self.assertEqual(v["result"],
            "ACTUAL_THREE_DISTINCT_NATIVE_RUNNERS_AND_REAL_TCP_SAMPLES; FULL_MATRIX_FAIL")


if __name__=="__main__":
    unittest.main()
