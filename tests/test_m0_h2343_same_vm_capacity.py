"""Static and receipt-only calibration contract; no network qualification."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2343_same_vm_capacity as c
class Calibration(unittest.TestCase):
    def test_same_vm_reference_not_product_pass(self):
        common=dict(source_sha="a",group="a",run_id="1")
        bare=dict(**common,status="PASS_H2285_NATIVE_WSL2_L3_FORWARD_TO_INDEPENDENT_ARM_TCP_SCOPED",delivered=dict(sparse_echo_received=160,bulk_receiver_goodput_mbps=520.999,sparse_tcp_rtt_p99_ms=156))
        product=dict(**common,status="PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",h2292_same_vm_original_product_abaprime=dict(stages=[dict(stage="A_default",tcp_mbps=250)]))
        r=c.comparison(bare,product)
        self.assertFalse(r["reference_at_least_600"])
        self.assertFalse(r["reference_at_least_800"])
        self.assertAlmostEqual(r["product_legs"][0]["relative_to_bare_reference"],0.4798)
        with self.assertRaises(ValueError):c.comparison(bare,dict(product,run_id="other"))
    def test_calibration_precedes_real_product_and_preserves_receipts(self):
        for name in ("qa-h2321-current-win-arm-path-ab.yml","qa-h2338-current-win-arm-profile-ab.yml"):
            w=(ROOT/".github/workflows"/name).read_text()
            self.assertLess(w.index("H2343 same-VM bare ARM receiver"),w.index("m0_h2286_arm_product.py start"))
            self.assertLess(w.index("H2343 real bare Windows WSL2 TCP calibration"),w.index("m0_h2292_true_product_ab.py client"))
            self.assertIn("Move-Item h2276-out/client-result.json h2343-capacity/client-bare.json",w)
            self.assertIn("h2343_same_vm_bare_capacity",w)
            self.assertIn('"h2276-$env:GROUP-relay-ready" h2343-capacity/relay',w)
            self.assertIn('"h2276-$env:GROUP-relay-ready" h2276-peer/relay',w)
            self.assertIn("h2343-capacity/relay/relay-ready.json h2343-capacity/server/server-ready.json",w)
if __name__=="__main__":unittest.main()
