"""H2283: two independent 3-runner native TCP A/B/A' 2MiB (vs H2282 8MiB)."""
import json
import os
import pathlib
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2276_three_runner_tcp as h


class NativeTwoMiBWindow(unittest.TestCase):
    def test_size_parameter_is_only_two_approved_source_values(self):
        env=dict(os.environ,WBD_H2281_SUSTAINED_TCP="1",
                 WBD_H2282_TCP_WINDOW_AB="1",WBD_H2279_CAPACITY_AB="0",
                 WBD_H2283_B_BYTES="2097152",
                 WBD_H2284_EIGHT_TCP_CAPACITY="0")
        expression=("import json,sys;sys.path.insert(0,'tools');"
                    "import m0_h2276_three_runner_tcp as x;"
                    "print(json.dumps([x.WINDOW_B_BYTES,x.WINDOW_AB,"
                    "x.SUSTAINED,x.active_stages(),x.tcp.BULK_SEND_S]))")
        q=subprocess.run([sys.executable,"-c",expression],env=env,cwd=ROOT,
                         capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(q.stdout),
                         [2097152,True,True,["base","tuned","base_prime"],25])
        env["WBD_H2283_B_BYTES"]="67108864"
        fail=subprocess.run([sys.executable,"-c",expression],env=env,cwd=ROOT,
                            capture_output=True,text=True)
        self.assertNotEqual(fail.returncode,0)
        self.assertIn("H2283_INVALID_ONLY_TEST_BUFFER_SIZE",fail.stderr)

    def test_actual_socket_option_two_mib_and_restored_A_prime(self):
        prior=h.tcp.WINDOW_TEST_BYTES
        try:
            with patch.object(h,"WINDOW_AB",True), \
                 patch.object(h,"WINDOW_B_BYTES",2*1024*1024):
                h.prepare_tcp_sockbuf("base")
                self.assertEqual(h.tcp.WINDOW_TEST_BYTES,0)
                h.prepare_tcp_sockbuf("tuned")
                self.assertEqual(h.tcp.WINDOW_TEST_BYTES,2*1024*1024)
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                    readback=h.tcp._maybe_set_buffers(sock)
                    self.assertEqual(readback["requested_bytes"],2*1024*1024)
                    self.assertGreater(readback["sndbuf_os"],0)
                    self.assertGreater(readback["rcvbuf_os"],0)
                h.prepare_tcp_sockbuf("base_prime")
                self.assertEqual(h.tcp.WINDOW_TEST_BYTES,0)
        finally:
            h.tcp.WINDOW_TEST_BYTES=prior

    def test_workflow_requires_both_groups_actual_kernel_tcp_and_p99(self):
        wf=(ROOT/".github/workflows/qa-h2283-dual-arm-relay-window2m-ab-tcp.yml").read_text()
        self.assertEqual(wf.count("group: [a, b]"),3)
        self.assertEqual(wf.count("runs-on: ubuntu-24.04-arm"),2)
        self.assertEqual(wf.count("runs-on: windows-2025"),1)
        self.assertEqual(wf.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(wf.count("[m0-029-h2283-window2m-ab-3runner]"),3)
        self.assertIn('WBD_H2283_B_BYTES: "2097152"',wf)
        self.assertIn("PASS_H2283_REAL_2MIB_SOCKBUF_NATIVE_A_B_A_PRIME_SCOPED",wf)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",wf)
        self.assertEqual(wf.count(
          "assert [x['stage_id'] for x in d['stages']]==['base','tuned','base_prime']"),2)
        self.assertIn("NOT measured here",wf)


if __name__=="__main__":
    unittest.main()
