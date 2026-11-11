"""Exact H1600 source+run ISA-L accelerated Windows binary manifest; retain legacy strict rules."""
import pathlib,unittest
WF=pathlib.Path(__file__).resolve().parents[1]/".github/workflows/m0-wl-public-normal-full.yml"
class H1619ExactManifest(unittest.TestCase):
    def test_successful_h1600_has_strict_three_feature_source_and_file_hashes(self):
        y=WF.read_text()
        for val in (
            "frozen_h1600=(os.environ.get('WBD_WL_REUSE_RUN_ID')=='43027983611'",
            "os.environ.get('WBD_WL_BINARY_SOURCE')=='8a31375e36bb6a93860c5579e64b4a39d0b6e346'",
            "m['source_sha']=='8a31375e36bb6a93860c5579e64b4a39d0b6e346'",
            "if os.environ.get('WBD_WL_NATIVE_ACCEL_REUSE')=='1' or frozen_h1600:",
            "assert m['native_fec_acceleration'] is True",
            "assert m['sha256']['exe']=='63b4a24abb0e7c775be5e58d3e54036f4bfab0491bc992a0147b8fe57886cd7c'",
            "assert m['sha256']['dll']=='7c8ddd808d08cfa18cf431fd5945d6c705bddaa6dd19a94e1891170ffa91d37d'",
            "assert m['features']=='m0_v4_embedded_go,fec2_product_record'",
            "assert hashlib.sha256(b).hexdigest()==m['sha256'][key]"):
            self.assertIn(val,y)
if __name__=="__main__":unittest.main()
