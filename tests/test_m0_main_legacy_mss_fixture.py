"""Frozen original Go TEST-ONLY historic expected MSS; runtime has no fallback."""
import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("oldtest",ROOT/"tools/m0_legacy_test_mss_compat.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MssTestOnlyCompat(unittest.TestCase):
    def test_fail_closed_on_wrong_historical_source(self):
        for name in m.FROZEN:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,"pinned original Go"):
                    m.rewrite(name,b"faketcp.DefaultMSS")
    def test_mutation_scope_and_genuine_original_hashes(self):
        self.assertEqual(set(m.FROZEN),{"tls_test.go","wire_qualification_test.go"})
        self.assertEqual(sum(n for _,n in m.FROZEN.values()),3)
        self.assertEqual(m.OLD,b"faketcp.DefaultMSS")
        self.assertIn(b"1360",m.NEW)
        self.assertNotIn("func DefaultMSS", (ROOT/"r0/go_overlay/internal/faketcp/public_v4_mss.go").read_text())
        for workflow in ("m0-normal-product-smoke.yml","m0-fixed-real-kernel-applied.yml"):
            w=(ROOT/".github/workflows"/workflow).read_text()
            self.assertEqual(w.count("python3 tools/m0_legacy_test_mss_compat.py legacy"),1)
            self.assertIn("tools/m0_legacy_test_mss_compat.py",w)
            self.assertIn("ref: a7a82db31fe736ffedee330795a3234d358f1984",w)
        fixed=(ROOT/".github/workflows/m0-fixed-real-kernel-applied.yml").read_text()
        self.assertIn("for file in tls.go fec_v2_policy.go",fixed)
if __name__=="__main__":
    unittest.main()
