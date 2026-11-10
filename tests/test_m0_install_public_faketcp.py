"""H970: one canonical manifest owns Linux and Windows V4 MSS source SHA."""
import pathlib,subprocess,sys,unittest
from tools.m0_install_public_faketcp import expected_rows,blob,ROOT,REPLACE,CREATE
class V4SharedAssembly(unittest.TestCase):
 def test_exact_manifest_result_blobs_all_eleven(self):
  rows=expected_rows()
  self.assertEqual(set(rows),set(REPLACE+CREATE))
  for name,row in rows.items():
   self.assertEqual(blob((ROOT/row["overlay_path"]).read_bytes()),row["result_blob"])
   if name in REPLACE:self.assertEqual(len(row["original_blob"]),40)
 def test_original_go_transition_64_65_not_aborted_and_malformed_still_denied(self):
  rows=expected_rows()
  for name in ("transition.go","transition_test.go"):
   self.assertEqual(rows[name]["kind"],"replace")
   self.assertIn(rows[name]["original_blob"],{
     "9cd5725f0151738ffaef7016c4ab8ea9228d8080",
     "4a7ef97f3dd5971d9952114b39cf18c085aa29a7"})
  for name in ("transition_h1285_test.go","transition_h1285_association_test.go"):
   self.assertEqual(rows[name]["kind"],"create")
  s=(ROOT/rows["transition.go"]["overlay_path"]).read_text()
  self.assertIn("retaining both the existing queued data and Prepared state",s)
  self.assertNotIn("t.abortLocked()\n\t\treturn 0, ErrTransitionOverflow",s)
  self.assertIn("ErrTransitionOverlap",s)
  t=(ROOT/rows["transition_h1285_test.go"]["overlay_path"]).read_text()
  self.assertIn("TestPLAN028PreDetachBurstOverflowPreservesAuthenticatedSuccessor",t)
  self.assertIn("TestPLAN028PreDetachMalformedRecordStillAborts",t)
 def test_linux_nonmutating_preflight(self):
  p=subprocess.run([sys.executable,str(ROOT/"tools/m0_install_public_faketcp.py"),"--check-only"],
    text=True,capture_output=True,check=True)
  self.assertIn("V4_ONE_ORIGINAL_GO_FAKETCP_MSS_SOURCE_CHECKED files=11",p.stdout)
 def test_plan012_linux_real_product_never_installs_mss_helper_only(self):
  workflow=(ROOT/".github/workflows/m0-plan012-combined-functional.yml").read_text()
  self.assertIn("python3 tools/m0_install_public_faketcp.py legacy",workflow)
  self.assertIn("go test -count=1 ./internal/faketcp",workflow)
  self.assertNotIn("for file in raw_detached_data_linux.go public_v4_mss.go",workflow)
  self.assertIn("H983_PLAN012_SEVEN_FILE_CURRENT_MSS_TRUE_BYTE_SOURCE_PASS",workflow)
 def test_no_hardcoded_second_result_set(self):
  txt=(ROOT/"tools/m0_install_public_faketcp.py").read_text()
  self.assertNotIn("RESULT={",txt)
  self.assertNotIn("CREATED={",txt)
if __name__=="__main__":unittest.main()
