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
