"""H1972 pure guards and synthetic QPC gap math: NOT real Windows evidence."""
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from m0_plan029_h1972_gap_attribution import analyze
from tests.test_m0_plan029_h1966_steady_qpc import scene,SRC
from m0_plan029_h1966_steady_qpc import analyze as base

class PostIngressSteady(unittest.TestCase):
    def sample(self):
        log,steady=scene()
        steady["same_source_steady_windows_qpc"]=base(log,steady,SRC)
        return log,steady

    def test_original_2048_windows_windows_gap_positive(self):
        log,steady=self.sample()
        val=analyze(log,steady,SRC)
        self.assertEqual(val["status"],"PASS_SCOPED_REAL_ORIGINAL_WINDOWS_2048_QPC_GAPS")
        self.assertEqual(val["gaps_us"]["nat_complete_to_kernel_inner_read"]["n"],2048)
        self.assertEqual(val["gaps_us"]["nat_complete_to_kernel_inner_read"]["p50_us"],20.0)
        self.assertEqual(val["gaps_us"]["kernel_inner_write_to_app_recv"]["p50_us"],2490.0)

    def test_wrong_h1966_source_join_fails(self):
        log,steady=self.sample()
        steady["same_source_steady_windows_qpc"]["source_sha"]="9"*40
        with self.assertRaisesRegex(RuntimeError,"Stop join"):
            analyze(log,steady,SRC)

    def test_truncated_original_recv_fails(self):
        log,steady=self.sample()
        p=steady["direct"]["source_port"]
        log=log.replace(f"{p}:1000000:1024:",f"{p}:1000000:1023:",1)
        with self.assertRaisesRegex(RuntimeError,"1024B"):
            analyze(log,steady,SRC)

    def test_cross_owner_clock_mismatch_fails(self):
        log,steady=self.sample()
        steady["direct"]["qpc_frequency"]=3_000_000
        with self.assertRaisesRegex(RuntimeError,"frequency"):
            analyze(log,steady,SRC)

    def test_original_wintun_rx_ownership_and_signed_only(self):
        src=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        a=src.index("if owner.has_udp_flows(){")
        b=src.index("let mut fresh_direct_ingress=false;")
        c=src.index("if same_turn_direct && fresh_direct_ingress{")
        d=src.index("// A bounded <=4-row parity quantum",c)
        self.assertLess(a,b);self.assertLess(b,c);self.assertLess(c,d)
        code=src[c:d]
        for guard in ("POST_INGRESS_RETURN_QUANTUM",
                      "owner.requeue_tcp_reverse(packet)",
                      "TrySendError::Full(packet)",
                      "TrySendError::Disconnected",
                      "direct_notify.wake()","sole"):
            self.assertIn(guard if guard!="sole" else
                          "original",code)
        before=src[src.index("let same_turn_direct="):src.index("loop {",src.index("let same_turn_direct="))]
        for gate in ("GITHUB_ACTIONS","WBD_PLAN029_NATIVE_V3_TRIAL",
                     "WBD_PLAN029_P2_MIXED_SCENE",
                     "WBD_PLAN029_P2_STEADY_QPC_SCENE",
                     "WBD_PLAN029_P2_POST_INGRESS_FLUSH_SCENE"):
            self.assertIn(gate,before)
        self.assertNotIn("thread::spawn",code)
        self.assertNotIn("split_borrowed_wintun",code)
        self.assertNotIn("deliver_native_direct_response",code)

if __name__=="__main__":unittest.main()
