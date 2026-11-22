"""H2316 actual Rust M2 Stop parser must fail closed and preserve ON/OFF ABI."""
import unittest
from tools.m0_h2316_native_m2_stop import (
    TAG,CURSOR,FIELDS,CURSOR_FIELDS,parse_native_m2_stop
)
class ExactStop(unittest.TestCase):
    def row(self,overrides=None):
        d={k:0 for k in FIELDS}
        d.update(overrides or {})
        c={k:0 for k in CURSOR_FIELDS}
        c["fifo_left"]=d["queued"]
        return TAG+" ".join(f"{k}={v}" for k,v in d.items())+" joined=true\n"+CURSOR+" ".join(f"{k}={v}" for k,v in c.items())+"\n"
    def test_genuine_status_and_missing_stop_fail_closed(self):
        a=self.row({"candidate_first":3,"repair_polls":11,"repair_accepted":1})
        got=parse_native_m2_stop(a)
        self.assertEqual(got["candidate_first"],3)
        self.assertEqual(got["repair_polls"],11)
        self.assertEqual(got["repair_accepted"],1)
        self.assertTrue(got["driver_copied_not_peer_receipt"])
        self.assertEqual(got["counter_scope"],"original_windows_rust_m2_owned_stop")
        self.assertIsNone(parse_native_m2_stop(a.replace(" joined=true"," joined=false")))
        self.assertIsNone(parse_native_m2_stop(a.replace("candidate_first=3","candidateFirst=3")))
        self.assertIsNone(parse_native_m2_stop(a.replace("fifo_left=0","fifo_left=12")))
        self.assertIsNone(parse_native_m2_stop(a+a))
        self.assertIsNone(parse_native_m2_stop(a.splitlines()[0]))
if __name__=="__main__":unittest.main()
