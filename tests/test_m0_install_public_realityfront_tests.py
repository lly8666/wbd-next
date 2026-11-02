"""Only two explicitly pinned original Realityfront TEST files may be patched."""
import pathlib,subprocess,sys,unittest
from tools.m0_install_public_realityfront_tests import FILES,ROOT,manifest_rows,blob
class MSSRealityfrontInstall(unittest.TestCase):
 def test_exact_original_and_result_manifest(self):
  rows=manifest_rows()
  self.assertEqual(set(rows),{"tls_test.go","wire_qualification_test.go"})
  for name,row in rows.items():
   self.assertEqual(blob((ROOT/row["overlay_path"]).read_bytes()),row["result_blob"])
   self.assertEqual(len(row["original_blob"]),40)
   self.assertTrue(name.endswith("_test.go"))
 def test_read_only_preflight(self):
  p=subprocess.run([sys.executable,str(ROOT/"tools/m0_install_public_realityfront_tests.py"),"--check-only"],
                   check=True,capture_output=True,text=True)
  self.assertIn("V4_REALITYFRONT_MSS_TESTS_CHECKED files=2",p.stdout)
if __name__=="__main__":unittest.main()
