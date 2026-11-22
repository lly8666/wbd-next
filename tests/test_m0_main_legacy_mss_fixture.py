"""Keep main Fixed/Normal on the existing PLAN012 test-only MSS=1420 fixture.

No original Go compiled FakeTCP code is changed to reintroduce DefaultMSS.
"""
import pathlib
import unittest
from tools.m0_prepare_original_go_mss_test_fixtures import (
    EXPECTED, REMOVED, FIXTURE_SOURCE, FILE, prepare,
)
ROOT=pathlib.Path(__file__).resolve().parents[1]
class MainCanonicalMssFixture(unittest.TestCase):
    def test_exact_production_and_test_source_contract(self):
        self.assertEqual(EXPECTED["bridge_v4_probe_linux_test.go"],0)
        self.assertEqual(EXPECTED["tls_test.go"],1)
        self.assertEqual(EXPECTED["wire_qualification_test.go"],2)
        self.assertEqual(sum(EXPECTED.values()),3)
        self.assertIn("const m0CurrentV4MSSFixture = 1420",FIXTURE_SOURCE)
        self.assertIn("SetPublicV4AdvertisedMSS(m0CurrentV4MSSFixture)",FIXTURE_SOURCE)
        self.assertEqual(FILE,"m0_current_v4_mss_fixture_test.go")
        self.assertNotIn("const DefaultMSS",FIXTURE_SOURCE)
        p=(ROOT/"r0/go_overlay/internal/realityfront/bridge_v4_probe_linux_test.go").read_text()
        self.assertEqual(p.count("faketcp.PublicV4AdvertisedMSS()"),7)
        self.assertEqual(p.count(REMOVED),0)
        for workflow in ("m0-normal-product-smoke.yml","m0-fixed-real-kernel-applied.yml"):
            s=(ROOT/".github/workflows"/workflow).read_text()
            self.assertEqual(s.count("python3 tools/m0_prepare_original_go_mss_test_fixtures.py legacy"),1)
            self.assertIn('"tools/m0_prepare_original_go_mss_test_fixtures.py",',s)
            self.assertNotIn("m0_legacy_test_mss_compat.py",s)
            self.assertIn("ref: a7a82db31fe736ffedee330795a3234d358f1984",s)
        f=(ROOT/".github/workflows/m0-fixed-real-kernel-applied.yml").read_text()
        self.assertIn("for file in tls.go fec_v2_policy.go",f)
if __name__=="__main__":
    unittest.main()
