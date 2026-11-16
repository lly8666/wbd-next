"""H1953: six first-physical-request Win32 QPC boundaries, real app joins."""
import unittest
from tests.test_m0_plan029_h1948_reply_path_qpc import data,SHA
from tools.m0_plan029_h1945_reply_qpc import analyze_prewrite

def fixture():
    base,scene=data()
    path=[x for x in base.splitlines()
          if "PLAN029_H1948_REPLY_PATH_QPC_FINAL" in x][0]
    old=path.split("rows=",1)[1].split(" source=",1)[0].split(",")
    rows=[]
    for one in old:
        port,w,r,i=map(int,one.split(":"))
        # 0.15ms accept->connect; 0.15ms connect->inner read;
        # 0.10ms inner read->first physical send on the SAME QPC clock.
        rows.append(f"{port}:{w-4000}:{w-2500}:{w-1000}:{w}:{r}:{i}")
    line=("PLAN029_H1953_PREWRITE_QPC_FINAL frequency=10000000 count="+
          str(len(rows))+" rows="+",".join(rows)+
          " source=original_rust_direct_test_only")
    return base+"\n"+line,scene

class PrephysicalQpc(unittest.TestCase):
    def test_true_384_direct_original_join(self):
        log,scene=fixture();v=analyze_prewrite(log,scene,SHA)
        self.assertEqual(v["matched_direct_events"],384)
        self.assertEqual(v["policies"]["fin_first"]
            ["Rust_listener_accept_to_physical_connected"]["p99_ms"],.15)
        self.assertEqual(v["policies"]["payload_first"]
            ["first_inner_recv_to_first_physical_write"]["p99_ms"],.1)
    def test_missing_prewrite_trace_fails(self):
        log,scene=fixture()
        with self.assertRaises(ValueError):
            analyze_prewrite("\n".join(log.splitlines()[:2]),scene,SHA)
    def test_duplicate_prewrite_trace_fails(self):
        log,scene=fixture();log+="\n"+log.splitlines()[-1]
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,SHA)
    def test_missing_real_inner_recv_fails(self):
        log,scene=fixture()
        log=log.replace("30000:1000001000:1000002500:1000004000:1000005000",
                        "30000:1000001000:1000002500:0:1000005000")
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,SHA)
    def test_connect_after_physical_send_fails(self):
        log,scene=fixture()
        log=log.replace("30000:1000001000:1000002500:1000004000:1000005000",
                        "30000:1000001000:1000006000:1000004000:1000005000")
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,SHA)
    def test_frequency_mismatch_fails(self):
        log,scene=fixture()
        log=log.replace("PLAN029_H1953_PREWRITE_QPC_FINAL frequency=10000000",
                        "PLAN029_H1953_PREWRITE_QPC_FINAL frequency=10000001")
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,SHA)
    def test_source_mismatch_fails(self):
        log,scene=fixture()
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,"b"*40)
    def test_missing_original_app_window_fails(self):
        log,scene=fixture();scene["windows"]["qpc_records"].pop()
        with self.assertRaises(ValueError):analyze_prewrite(log,scene,SHA)
if __name__=="__main__":unittest.main()
