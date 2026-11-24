"""H2316 actual Rust M2 Stop parser must fail closed and preserve ON/OFF ABI."""
import unittest
from tools.m0_h2316_native_m2_stop import (
    TAG,CURSOR,OUTER_REPAIR,FIELDS,CURSOR_FIELDS,parse_native_m2_stop
)
class ExactStop(unittest.TestCase):
    def row(self,overrides=None):
        d={k:0 for k in FIELDS}
        d.update(overrides or {})
        c={k:0 for k in CURSOR_FIELDS}
        c["fifo_left"]=d["queued"]
        n=d["repair_accepted"]
        wire=1569 if n>0 else 0
        o={"source_wire_bytes":17883588,"repair_accepted_wire_bytes":wire,
           "repair_uncertain_wire_bytes":0,"control_wire_bytes":119755,
           "repair_packets":n,"r_to_f_ppm":87 if n>0 else 0,
           "r_to_total_ppm":87 if n>0 else 0}
        return (TAG+" ".join(f"{k}={v}" for k,v in d.items())+" joined=true\n"+
                CURSOR+" ".join(f"{k}={v}" for k,v in c.items())+"\n"+
                OUTER_REPAIR+" ".join(f"{k}={v}" for k,v in o.items())+" joined=true\n")
    def test_genuine_status_and_missing_stop_fail_closed(self):
        a=self.row({"candidate_first":3,"repair_polls":11,"repair_accepted":1})
        got=parse_native_m2_stop(a)
        self.assertEqual(got["candidate_first"],3)
        self.assertEqual(got["repair_polls"],11)
        self.assertEqual(got["repair_accepted"],1)
        self.assertTrue(got["driver_copied_not_peer_receipt"])
        self.assertEqual(got["counter_scope"],"original_windows_rust_owner_joined_stop_not_periodic_snapshot")
        self.assertEqual(got["kernel_accepted_repair_packets"],1)
        self.assertEqual(got["kernel_accepted_repair_wire_bytes"],1569)
        self.assertIsNone(parse_native_m2_stop(a.replace("repair_packets=1","repair_packets=0")))
        self.assertIsNone(parse_native_m2_stop(a.replace("repair_accepted_wire_bytes=1569","repair_accepted_wire_bytes=0")))
        self.assertIsNone(parse_native_m2_stop(a.replace(" joined=true"," joined=false")))
        self.assertIsNone(parse_native_m2_stop(a.replace("candidate_first=3","candidateFirst=3")))
        self.assertIsNone(parse_native_m2_stop(a.replace("fifo_left=0","fifo_left=12")))
        self.assertIsNone(parse_native_m2_stop(a+a))
        self.assertIsNone(parse_native_m2_stop(a.splitlines()[0]))
    def test_real_copy_after_shadow_retirement_requires_explicit_cause(self):
        a=self.row({"candidate_first":3,"repair_polls":11,"repair_accepted":1})
        a=a.replace("repair_packets=1","repair_packets=2")
        self.assertIsNone(parse_native_m2_stop(a))
        a=a.replace("queued=0 joined=true","queued=0 repair_copied_shadow_stale=1 repair_broker_unresolved=0 joined=true")
        got=parse_native_m2_stop(a)
        self.assertEqual(got["kernel_accepted_repair_packets"],2)
        self.assertEqual(got["repair_copied_shadow_stale"],1)
        self.assertEqual(got["repair_accepted"],1)
        self.assertIsNone(parse_native_m2_stop(a.replace("repair_copied_shadow_stale=1","repair_copied_shadow_stale=0")))
        self.assertIsNone(parse_native_m2_stop(a.replace(" repair_broker_unresolved=0","")))

if __name__=="__main__":unittest.main()
