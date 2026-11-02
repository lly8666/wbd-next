"""H984: fail closed before an old Go test can reintroduce DefaultMSS."""
import pathlib
import tempfile
import unittest
from tools.m0_prepare_original_go_mss_test_fixtures import (
    EXPECTED, REMOVED, FILE, FIXTURE, FIXTURE_SOURCE, prepare,
)
class OldTestSourceMSSMigration(unittest.TestCase):
 def make(self,root):
  dst=root/"internal"/"realityfront"
  dst.mkdir(parents=True)
  for name,count in EXPECTED.items():
   (dst/name).write_text("package realityfront\n// "+(" "+REMOVED)*count+"\n")
  return dst
 def test_only_exact_legacy_test_uses_migrate_to_1460_vector(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);dst=self.make(root)
   product=dst/"original_product.go";product.write_text("package realityfront\nvar currentProduct=true\n")
   prepare(root)
   self.assertEqual(product.read_text(),"package realityfront\nvar currentProduct=true\n")
   self.assertEqual(len(EXPECTED),4)
   self.assertEqual(sum(EXPECTED.values()),11)
   self.assertIn("const m0CurrentV4MSSFixture = 1420",(dst/FILE).read_text())
   self.assertIn("SetPublicV4AdvertisedMSS(m0CurrentV4MSSFixture)",(dst/FILE).read_text())
   for name in EXPECTED:
    s=(dst/name).read_text()
    self.assertNotIn(REMOVED,s)
    self.assertIn(FIXTURE,s)
 def test_missing_or_unreviewed_reference_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);dst=self.make(root)
   (dst/"tls_test.go").write_text("package realityfront\n")
   with self.assertRaisesRegex(ValueError,"reference count changed"):prepare(root)
   (dst/"tls_test.go").write_text("package realityfront\n// "+REMOVED+"\n")
   (dst/"unexpected_test.go").write_text("package realityfront\n// "+REMOVED+"\n")
   with self.assertRaisesRegex(ValueError,"unreviewed old MSS reference"):prepare(root)
 def test_production_original_go_source_guard(self):
  path=pathlib.Path(__file__).resolve().parents[1]
  wf=(path/".github/workflows/m0-plan012-combined-functional.yml").read_text()
  self.assertIn("python3 tools/m0_install_public_faketcp.py legacy",wf)
  self.assertIn("python3 tools/m0_prepare_original_go_mss_test_fixtures.py legacy",wf)
  self.assertNotIn("const DefaultMSS",FIXTURE_SOURCE)
if __name__=="__main__":unittest.main()
