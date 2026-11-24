"""Application supply is an explicit fixture profile, never a product default."""
import os,pathlib,sys,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_wl_loss_tcp_probe as tcp
import m0_h2292_true_product_ab as ab
import m0_h2285_windows_wsl_route as bare
class Supply(unittest.TestCase):
    def test_profiles(self):
        self.assertEqual(tcp.supply_profile("base"),(4,2097152))
        self.assertEqual(tcp.supply_profile("high"),(8,8388608))
        with patch.dict(os.environ,{"WBD_H2321_BASELINE_SOURCE":ab.PATH_AB_LOAN_BASELINE,"WBD_PATH_AB_AXIS":"application_supply"},clear=True):
            self.assertEqual(ab.path_ab_candidate_source(),ab.PATH_AB_LOAN_BASELINE)
            self.assertEqual(ab.path_ab_candidate_features(),ab.PATH_AB_FEATURES)
    def test_bare_profile_does_not_mutate_shared_module_on_import(self):
        self.assertEqual(tcp.BULK_FLOWS,4)
        with patch.dict(os.environ,{"WBD_H2359_SUPPLY":"1"},clear=True):
            self.assertEqual(bare.bare_application_profile(),(8,8388608))
            self.assertEqual(tcp.BULK_FLOWS,4)
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(bare.bare_application_profile(),(4,2097152))
    def test_same_binary_workflow(self):
        w=(ROOT/".github/workflows/qa-h2359-high-supply.yml").read_text()
        self.assertEqual(w.count("cargo +1.85.1 build --locked --release --manifest-path"),1)
        self.assertIn("assert aa['dll_sha256']==bb['dll_sha256']",w)
        self.assertIn("bare_bulk_flows']==8",w)
        self.assertIn("WBD_H2359_SUPPLY",w)
if __name__=="__main__":unittest.main()
