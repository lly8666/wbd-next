"""Main original Go FakeTCP/MSS source is assembled from existing verified blobs.

Old Fixed and Normal workflows must not silently test an unpatched FakeTCP.
"""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class PinnedMssMainWorkflow(unittest.TestCase):
    def test_two_original_workflows_use_existing_content_addressed_installer(self):
        for path in (".github/workflows/m0-fixed-real-kernel-applied.yml",
                     ".github/workflows/m0-normal-product-smoke.yml"):
            with self.subTest(path=path):
                s=(ROOT/path).read_text()
                self.assertIn("ref: a7a82db31fe736ffedee330795a3234d358f1984",s)
                self.assertEqual(s.count("python3 tools/m0_install_public_faketcp.py --check-only"),1)
                self.assertEqual(s.count("python3 tools/m0_install_public_faketcp.py legacy"),1)
                self.assertIn("(cd legacy && go test -count=1 ./internal/faketcp)",s)
                self.assertIn('tools/m0_install_public_faketcp.py',s)
                self.assertIn("r0/go_overlay/assembly/manifest-plan020-m0.json",s)
                self.assertIn("r0/go_overlay/internal/faketcp/public_v4_mss.go",s)
                self.assertLess(s.index("python3 tools/m0_install_public_faketcp.py legacy"),
                                s.index("go test -tags"))
    def test_plan012_same_original_tls_owner_and_mss_assembly(self):
        plan=(ROOT/".github/workflows/m0-plan012-combined-functional.yml").read_text()
        self.assertIn("for file in tls.go bridge_v4_linux_server_product.go",plan)
        self.assertIn("grep -q 'test result: ok. 5 passed; 0 failed' fixed-kernel-result/continuous-rx.log",plan)
        self.assertIn("nm -D target/release/libwbd_engine.so >fixed-kernel-result/opt-in-abi-symbols.log",plan)
        self.assertIn("M0_PLAN012_ORIGINAL_RUST_ABI_MISSING_EXACT_SYMBOL",plan)
        self.assertIn("abi_req wbd_m0_embedded_go_fec2_probe_real_raw_tx",plan)
        self.assertNotIn("nm -D target/release/libwbd_engine.so | grep -q",plan)
        # H1067 deliberately retired the old WB-R1 route prelude, so do
        # NOT restore missing legacy TLS-product files just to satisfy CI.
        self.assertNotIn("v4_route_prelude.go",plan)
        self.assertNotIn("v4_route_prelude_test.go",plan)
        self.assertIn("mkdir -p legacy/internal/v4productcli legacy/internal/v4routekey",plan)
        self.assertIn("(cd legacy && go test -count=1 ./internal/v4routekey)",plan)
        self.assertIn("M0_PLAN012_CURRENT_V2_ROUTE_KEY_DERIVATION_SOURCE_AND_REAL_TEST_PASS",plan)
        self.assertIn('"r0/go_overlay/internal/v4routekey/short_test.go",',plan)
        self.assertIn("for file in tls.go bridge_v4_linux_server_product.go",plan)
        self.assertNotIn("grep -q 'test result: ok. 4 passed; 0 failed' fixed-kernel-result/continuous-rx.log",plan)
        self.assertIn("grep -Fq \"RootCAs\" legacy/internal/realityfront/tls.go",plan)
        self.assertIn('"r0/go_overlay/internal/realityfront/tls.go",',plan)
        self.assertIn("python3 tools/m0_install_public_faketcp.py legacy",plan)
        self.assertIn("python3 tools/m0_prepare_original_go_mss_test_fixtures.py legacy",plan)
        self.assertIn("ref: a7a82db31fe736ffedee330795a3234d358f1984",plan)

    def test_verification_not_frozen_go_mss_stub(self):
        p=(ROOT/"tools/m0_install_public_faketcp.py").read_text()
        src=(ROOT/"r0/go_overlay/internal/faketcp/public_v4_mss.go").read_text()
        self.assertIn('ORIGINAL_SOURCE="a7a82db31fe736ffedee330795a3234d358f1984"',p)
        self.assertIn('if blob(content)!=row["result_blob"]:',p)
        self.assertIn('if blob(dst.read_bytes())!=row["original_blob"]:',p)
        self.assertIn("func PublicV4AdvertisedMSS()uint16",src)
        self.assertIn("func SetPublicV4AdvertisedMSS(mss uint16)error",src)
if __name__=="__main__":
    unittest.main()
