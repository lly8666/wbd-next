"""H2307 original FEC2 fixed-first positive control at 400ms and 1% loss."""
import os,pathlib,sys,unittest,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
class FECFixedFirst(unittest.TestCase):
    def test_1pct_fixed_first_true_original_rust_applied_and_stop(self):
        src=(ROOT/"tools/m0_h2293_true_product_fec_loss.py").read_text()
        relay=(ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text()
        wf=(ROOT/".github/workflows/qa-h2307-fixed-first-loss1.yml").read_text()
        for m in ("WBD_H2307_FEC_FIXED_FIRST",'("A_fixed","B_off","A_prime_fixed")',
                  "H2307_FIXED_OFF_FIXED_GENUINE_RUST_APPLICATION_MISSING",
                  'fec_fixed=(tag=="B_fixed")',
                  "WBD_WINDOWS_FEC2_INSTALLED mode=fec-fixed profile="):
            self.assertIn(m,src)
        self.assertIn('("A_fixed","B_off","A_prime_fixed")',relay)
        for m in ('WBD_H2307_FEC_FIXED_FIRST: "1"',
                  'WBD_H2306_TCP_PROGRESS: "1"',
                  'WBD_H2302_WINDOW_ABA: "0"',
                  'WBD_H2293_WEAK_LOSS_PCT: "1"',
                  '[m0-029-h2307-fixed-first-loss1]',
                  "PASS_H2307_MEASURED_ORIGINAL_FEC2_FIXED_OFF_FIXED_SCOPED",
                  "h2307_same_vm_original_fec2_fixed_off_fixed",
                  "H2293_REAL_ARM_TUN_THREE_FEC2_LOSS_TCP_STAGES_DONE",
                  "==[True,False,True]","client_owned_stop",
                  "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED"):
            self.assertIn(m,wf)
    def test_explicit_flag_maps_only_new_positive_control(self):
        old=os.environ.get("WBD_H2307_FEC_FIXED_FIRST")
        try:
            os.environ["WBD_H2307_FEC_FIXED_FIRST"]="1"
            spec=importlib.util.spec_from_file_location("h2307_positive",ROOT/"tools/m0_h2293_true_product_fec_loss.py")
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.LEGS,("A_fixed","B_off","A_prime_fixed"))
            self.assertTrue(mod.H2307_FIXED_FIRST)
            self.assertEqual(str(mod.ROOT),"h2307-out")
        finally:
            if old is None:os.environ.pop("WBD_H2307_FEC_FIXED_FIRST",None)
            else:os.environ["WBD_H2307_FEC_FIXED_FIRST"]=old
if __name__=="__main__":unittest.main()
