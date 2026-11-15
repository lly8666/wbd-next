"""No native dependencies: H1945 one-Windows-clock join safety."""
import unittest
from tools.m0_plan029_h1945_reply_qpc import analyze,read_native_qpc
SHA="a"*40
def fixture():
    rows=[];ports={"fin_first":[],"payload_first":[]}
    for j,kind in enumerate(("fin_first","payload_first")):
        for i in range(192):
            port=30000+j*192+i;half=1_000_000_000+(j*192+i)*100_000
            rows.append((port,half+10_000))
            ports[kind].extend([
                {"role":"direct","source_port":port,"half_close_qpc":half,
                 "first_echo_qpc":half+20_000},
                {"role":"physical","source_port":45000+i,
                 "half_close_qpc":half,"first_echo_qpc":half+20_000}])
    line=("PLAN029_H1945_REPLY_QPC_FINAL frequency=10000000 count=384 rows="+
          ",".join("%d:%d"%p for p in rows)+
          " source=original_rust_direct_test_only")
    def win(policy):return {"source_sha":SHA,"reply_policy":policy,
        "qpc_frequency":10_000_000,"total_connections":384,
        "qpc_records":ports[policy]}
    return line,{"source_sha":SHA,"status":"PASS_SCOPED_SMALL_TCP_A_B_B_A_SHA_FIN",
        "windows":win("fin_first"),
        "echo_before_fin_control":{"source_sha":SHA,
            "status":"PASS_SCOPED_ORIGINAL_TWO_OS_ECHO_BEFORE_FIN",
            "windows":win("payload_first")}}
class ReplyQPC(unittest.TestCase):
    def test_two_true_original_policies_join(self):
        log,s=fixture();result=analyze(log,s,SHA)
        self.assertEqual(result["matched_direct_events"],384)
        self.assertEqual(result["policies"]["fin_first"]
            ["Rust_first_inner_write_to_client_first_recv"]["p99_ms"],1.)
    def test_source_mismatch(self):
        log,s=fixture()
        with self.assertRaises(ValueError):analyze(log,s,"b"*40)
    def test_fail_on_missing_rust_qpc(self):
        log,s=fixture()
        with self.assertRaises(ValueError):analyze("",s,SHA)
    def test_fail_on_wrong_windows_frequency(self):
        log,s=fixture();s["windows"]["qpc_frequency"]=100
        with self.assertRaises(ValueError):analyze(log,s,SHA)
    def test_fail_on_missing_direct_window(self):
        log,s=fixture();s["windows"]["qpc_records"].pop()
        with self.assertRaises(ValueError):analyze(log,s,SHA)
    def test_fail_on_duplicate_native_qpc(self):
        log,s=fixture()
        log=log.replace("count=384","count=385").replace(
          "30000:1000010000,","30000:1000010000,30000:1000010000,")
        with self.assertRaises(ValueError):analyze(log,s,SHA)
    def test_fail_if_first_recv_precedes_fin(self):
        log,s=fixture();r=s["windows"]["qpc_records"][0]
        r["first_echo_qpc"]=r["half_close_qpc"]-1
        with self.assertRaises(ValueError):analyze(log,s,SHA)
    def test_fail_without_early_reply_os_receipt(self):
        log,s=fixture();s["echo_before_fin_control"]=None
        with self.assertRaises(ValueError):analyze(log,s,SHA)
if __name__=="__main__":unittest.main()
