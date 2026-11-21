"""H2241: source integrity, only-one-route gate; true Stop receipt required."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "h2241", ROOT/"tools/m0_h2241_exclusive_gate_ab.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class ExclusiveGateCrossRouteNoHol(unittest.TestCase):
    def test_only_bench_cold_client_fence_not_global(self):
        self.assertEqual(H.PHASES,(
            ("original_before",4),("exclusive_gate_candidate",4),
            ("original_after",4)))
        source=(ROOT/"crates/wbd-engine/src/v4_embedded_go.rs").read_text()
        fixture=(ROOT/"tools/m0_h2234_local_netns.py").read_text()
        script=(ROOT/"tools/m0_h2241_exclusive_gate_ab.py").read_text()
        for part in ("WBD_H2241_ONE_ROUTE_PRESSURE_GATE",
                     "only_live_shared_tun_route_saturated",
                     "routes.len()!=1 || pending.len()!=1",
                     "let stop_read=router.routes.try_lock()",
                     "Duration::from_micros(exclusive_sleep_us)",
                     "exclusive_sleep_us=(exclusive_sleep_us*2).min(1000)",
                     "V4_PUBLIC_H2241_TUN_GATE_STOP",
                     "m0_h2241_exclusive_reader_gate_refuses_cross_route_or_generation_hol"):
            self.assertIn(part,source)
        self.assertIn("WBD_H2241_NATIVE_GATE",fixture)
        self.assertIn('"test_only_exclusive_gate":candidate',script)
        self.assertIn('node.stop_client(1)',script)
        self.assertIn('gate_stop_receipt(',script)
        self.assertIn('status!="PASS_GENUINE_H2241_EXCLUSIVE_GATE_ABA_DIAGNOSTIC_NOT_PRODUCT_GAIN"',script)
        self.assertNotIn("queue_cap_expand",script)
        self.assertNotIn("outer_ack_wait",script)
        self.assertNotIn("extra_transport_reliable",script)

    def test_gate_receipt_truth_and_negative_missing_duplicate(self):
        real=("V4_PUBLIC_H2241_TUN_GATE_STOP generation=1 gated_turns=237 "
              "sleep_ns=9122333 max_sleep_ns=1000231 single_route_only=1 "
              "no_hol=1 original_owner=1 no_queue_or_wire_change=1")
        r=H.gate_stop_receipt(real,True)
        self.assertEqual(r["gated_turns"],237)
        self.assertEqual(r["sleep_ns"],9122333)
        self.assertEqual(H.gate_stop_receipt("no gate",False)["status"],
                         "ORIGINAL_PRODUCT_NO_GATE_RECEIPT")
        for bad in ("",real+"\n"+real,
                    real.replace("single_route_only=1","single_route_only=0"),
                    real.replace("no_queue_or_wire_change=1","no_queue_or_wire_change=0"),
                    real.replace("sleep_ns=9122333","sleep_ms=9")):
            with self.assertRaisesRegex(RuntimeError,"H2241_"):
                H.gate_stop_receipt(bad,True)
        with self.assertRaisesRegex(RuntimeError,"OFF_CASE"):
            H.gate_stop_receipt(real,False)

if __name__=="__main__":unittest.main()
