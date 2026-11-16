"""H1948: first physical QPC write/read joins existing genuine Direct app events."""
import unittest
from tests.test_m0_plan029_h1945_reply_qpc import fixture,SHA
from tools.m0_plan029_h1945_reply_qpc import analyze_path,read_native_path_qpc

def data():
    old,scene=fixture()
    original=old.split("rows=",1)[1].split(" source=",1)[0].split(",")
    path=[]
    for item in original:
        port,inner=map(int,item.split(":"))
        path.append(f"{port}:{inner-5000}:{inner-3000}:{inner}")
    line=("PLAN029_H1948_REPLY_PATH_QPC_FINAL frequency=10000000 "+
          f"count={len(path)} rows="+",".join(path)+
          " source=original_rust_direct_test_only")
    return old+"\n"+line,scene

class ReplyPathQPC(unittest.TestCase):
    def test_positive_true_384_direct(self):
        log,scene=data();v=analyze_path(log,scene,SHA)
        self.assertEqual(v["matched_direct_events"],384)
        self.assertEqual(v["policies"]["fin_first"]
            ["Rust_first_physical_write_to_first_physical_read"]["p99_ms"],.2)
        self.assertEqual(v["policies"]["payload_first"]
            ["Rust_first_physical_read_to_first_inner_write"]["p99_ms"],.3)
    def test_missing_path_trace(self):
        log,scene=data()
        with self.assertRaises(ValueError):analyze_path(log.split("\n")[0],scene,SHA)
    def test_invalid_write_read_order(self):
        log,scene=data()
        log=log.replace("30000:1000005000:1000007000:1000010000",
                        "30000:1000008000:1000007000:1000010000")
        with self.assertRaises(ValueError):analyze_path(log,scene,SHA)
    def test_missing_first_outer_write(self):
        log,scene=data()
        log=log.replace("30000:1000005000:1000007000:1000010000",
                        "30000:0:1000007000:1000010000")
        with self.assertRaises(ValueError):analyze_path(log,scene,SHA)
    def test_frequency_mismatch(self):
        log,scene=data()
        log=log.replace("PLAN029_H1948_REPLY_PATH_QPC_FINAL frequency=10000000",
                        "PLAN029_H1948_REPLY_PATH_QPC_FINAL frequency=10000001")
        with self.assertRaises(ValueError):analyze_path(log,scene,SHA)
    def test_duplicate_path_record(self):
        log,scene=data()
        log+="\n"+log.split("\n")[1]
        with self.assertRaises(ValueError):analyze_path(log,scene,SHA)
    def test_source_mismatch(self):
        log,scene=data()
        with self.assertRaises(ValueError):analyze_path(log,scene,"b"*40)
    def test_missing_app_window(self):
        log,scene=data()
        scene["windows"]["qpc_records"].pop()
        with self.assertRaises(ValueError):analyze_path(log,scene,SHA)
if __name__=="__main__":unittest.main()
