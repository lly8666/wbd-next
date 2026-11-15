"""H1896 sustained ORIGINAL Win2025/WSL2 kernel TCP cost fixture contracts.

Quick pure-Python deterministic unit coverage; the actual Windows/Wintun
30+30 second socket and signed owned Stop are never simulated as passed here.
"""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import m0_plan029_h1896_sustain_tcp as fixture

ROOT=Path(__file__).resolve().parents[1]

class TestH1896SustainedCost(unittest.TestCase):
    def test_exact_block_and_delivered_hash(self):
        self.assertEqual(len(fixture.DATA),65536)
        self.assertEqual(fixture.MEASURE_BYTES,251658240)
        self.assertEqual(fixture.WARMUP_BYTES,16777216)
        self.assertEqual(fixture.DURATION_S,30)
        self.assertEqual(fixture.RATE_BYTES_S,8388608)
        self.assertEqual(fixture.expected_sha(fixture.BLOCK),
                         hashlib.sha256(fixture.DATA).hexdigest())
        class Reader:
            def __init__(self,bytes_):
                self.data=io.BytesIO(bytes_)
            def recv(self,n):return self.data.read(n)
        n,digest=fixture.recv_exact_data(Reader(fixture.DATA*2),
                                         fixture.BLOCK*2)
        self.assertEqual(n,131072)
        self.assertEqual(digest,fixture.expected_sha(fixture.BLOCK*2))
        with self.assertRaises(RuntimeError):
            fixture.recv_exact_data(Reader(fixture.DATA),
                                     fixture.BLOCK*2)

    def test_absolute_pacing_and_legacy_no_progress_log(self):
        class Sender:
            def __init__(self):self.data=bytearray()
            def sendall(self,x):self.data.extend(x)
        sock=Sender()
        elapsed=fixture.send_at_fixed_rate(sock,fixture.BLOCK,
                                            rate=128*1024*1024)
        self.assertEqual(len(sock.data),fixture.BLOCK)
        self.assertEqual(sock.data,fixture.DATA)
        self.assertGreaterEqual(elapsed,fixture.BLOCK/(128*1024*1024))
        self.assertLess(elapsed,.5)

    def test_cpu_per_gib_distinguishes_user_kernel_and_baseline_estimate(self):
        begin={"user":2.0,"kernel":4.0}
        end={"user":3.25,"kernel":4.75}
        result=fixture.cpu_delta(begin,end,30.,fixture.MEASURE_BYTES,{
            "user_cpu_s_per_s":.01,"kernel_cpu_s_per_s":.005})
        self.assertEqual(result["original_process_user_cpu_s"],1.25)
        self.assertEqual(result["original_process_kernel_cpu_s"],.75)
        self.assertGreater(result["original_process_total_cpu_s_per_gib"],0)
        self.assertEqual(result["cpu_scope"],
            "WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC")
        estimate=result["idle_udp_background_subtracted_estimate"]
        self.assertLess(estimate["user_cpu_s_per_gib"],
                        result["original_process_user_cpu_s_per_gib"])
        self.assertIn("NONCAUSAL",estimate["method"])
        with self.assertRaises(RuntimeError):
            fixture.cpu_delta(end,begin,30.,fixture.MEASURE_BYTES)

    def test_duplicate_or_missing_os_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"proof.log"
            p.write_text(fixture.MARK_LINUX+" "+json.dumps({"a":1})+"\n")
            self.assertEqual(fixture.proof(p,fixture.MARK_LINUX),{"a":1})
            p.write_text(p.read_text()*2)
            with self.assertRaises(RuntimeError):
                fixture.proof(p,fixture.MARK_LINUX)
            p.write_text("not a receipt\n")
            with self.assertRaises(RuntimeError):
                fixture.proof(p,fixture.MARK_WINDOWS)

    def test_signed_original_p2_and_30s_per_phase_tunnel_contract(self):
        short=(ROOT/"tools/m0_plan029_h1815_p2_real_mixed.py").read_text()
        original=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        ci=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        script=(ROOT/"tools/m0_plan029_h1896_sustain_tcp.py").read_text()
        self.assertIn('MAX_SUSTAIN=3200',short)
        self.assertIn('if SUSTAIN:MAX_SUSTAIN=9000',short)
        self.assertIn('args[6:6]=["env","WBD_PLAN029_P2_SUSTAIN_SCENE=1"]',short)
        self.assertNotIn("time.monotonic()",short)
        self.assertIn('if total%128==0 and not (SUSTAIN or HIGH_RATE):',short)
        self.assertIn('if HIGH_RATE:MAX_SUSTAIN=14000',short)
        self.assertIn('args[6:6]=["env","WBD_PLAN029_P2_HIGH_RATE_SCENE=1"]',short)
        self.assertIn('sustained_phase_udp',short)
        self.assertIn('set(small_win["sustained_phase_udp"])!={"upload","download"}',short)
        self.assertIn('WBD_PLAN029_P2_ORIGINAL_PID',short)
        self.assertIn('os.environ["WBD_PLAN029_P2_ORIGINAL_PID"]=str(w.pid)',original)
        self.assertIn('WBD_PLAN029_P2_SUSTAIN_SCENE:',ci)
        self.assertIn('[plan029-v3-real-p2-sustain]',ci)
        self.assertIn('PLAN029_H1896_SIGNED_30S_EACH_TCP_REAL_KERNEL_PROCESS_CPU_GIB_TUNNEL_UDP_OWNED_STOP_PASS_SCOPED',ci)
        self.assertIn('WBD_PLAN029_P2_SUSTAIN_SCENE',original)
        self.assertIn('st["owner_stop"]="PASS_BOTH_OWNED"',original)
        self.assertIn('GetProcessTimes',script)
        self.assertIn("NO_DRIVER_ISR_DPC",script)
        self.assertIn('read_control(sock,b"u")',script)
        self.assertIn('read_control(conn,b"D")',script)
        self.assertIn('read_control(conn,b"d")',script)
        self.assertIn('warmup_each_direction_s',script)
        self.assertIn('one_persistent_socket',script)

if __name__=="__main__":
    unittest.main()
