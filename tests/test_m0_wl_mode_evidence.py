"""Never lose or leak a later mode's first failure/resource evidence."""
import json
import pathlib
import tempfile
import unittest
from tools.m0_wl_mode_evidence import archive_mode_evidence,capture_mode_evidence_baseline,select_source_locked_modes
from tools.m0_wl_business_latency import summarize_rtt

SHA="a"*40
class ModeEvidenceTests(unittest.TestCase):
 def test_separate_modes_redaction_and_no_script_or_secret_upload(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   (out/"client.log").write_text("FAIL --password topsecret --route-key-hex abcdef\n")
   (out/"windows-original-go-rust-process-1hz.jsonl").write_text(
     '{"cpu_kernel_s":2,"private_bytes":4096}\n')
   (out/"start-linux.sh").write_text("password=live-only\n")
   first=archive_mode_evidence(out,"normal",SHA,{"error":"real first failure"},1)
   meta=json.loads(first.read_text())
   self.assertFalse(meta["product_pass"])
   self.assertIn("windows-original-go-rust-process-1hz.jsonl",meta["preserved_allowlist"])
   self.assertNotIn("start-linux.sh",meta["preserved_allowlist"])
   self.assertFalse((first.parent/"start-linux.sh").exists())
   self.assertNotIn("topsecret",(first.parent/"client.log").read_text())
   self.assertNotIn("abcdef",(first.parent/"client.log").read_text())
   (out/"client.log").write_text("second mode first error\n")
   second=archive_mode_evidence(out,"game4",SHA,{"mode_public":"PASS_ACTUAL_demo"},0)
   self.assertTrue(json.loads(second.read_text())["product_pass"])
   self.assertIn("real first failure",json.loads((first.parent/"report.json").read_text())["error"])
   self.assertEqual((first.parent/"client.log").read_text().splitlines()[0].split()[0],"FAIL")
   self.assertIn("second mode first error",(second.parent/"client.log").read_text())
 def test_shared_previous_mode_log_is_not_laundered_into_new_mode(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   (out/"client.log").write_text("first-failure-only\\n")
   (out/"native-link-tcp443.log").write_text("mode1-global\\n")
   (out/"windows-original-go-rust-process-1hz.jsonl").write_text('{"cpu_s":1}\\n')
   first=archive_mode_evidence(out,"normal",SHA,{"error":"mode1"},1)
   snapshot=capture_mode_evidence_baseline(out)
   with (out/"native-link-tcp443.log").open("a") as f:f.write("mode2-global\\n")
   with (out/"windows-original-go-rust-process-1hz.jsonl").open("a") as f:f.write('{"cpu_s":2}\\n')
   second=archive_mode_evidence(out,"game4",SHA,{"mode_public":"PASS_ACTUAL_verified"},0,baseline=snapshot)
   meta=json.loads(second.read_text())
   self.assertIn("client.log",meta["unchanged_from_previous_mode"])
   self.assertFalse((second.parent/"client.log").exists())
   self.assertEqual((second.parent/"native-link-tcp443.log").read_text(),"mode2-global\\n")
   self.assertEqual((second.parent/"windows-original-go-rust-process-1hz.jsonl").read_text(),'{"cpu_s":2}\\n')
   self.assertEqual((first.parent/"client.log").read_text(),"first-failure-only\\n")
 def test_long_append_does_not_copy_older_mode_witness_prefix(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   prefix="a"*600+"\\n"
   (out/"native-windows-npf.log").write_text(prefix)
   snap=capture_mode_evidence_baseline(out)
   with (out/"native-windows-npf.log").open("a") as f:
    f.write("second-correct-mode-failure\\n")
   result=archive_mode_evidence(out,"auto",SHA,{"error":"exact"},1,baseline=snap)
   self.assertIn("native-windows-npf.log",json.loads(result.read_text())["preserved_allowlist"])
   self.assertEqual((result.parent/"native-windows-npf.log").read_text(),"second-correct-mode-failure\\n")
 def test_seven_functional_modes_not_implicitly_performance_on_main(self):
  self.assertEqual(len(select_source_locked_modes("all",False)),7)
  with self.assertRaisesRegex(ValueError,"ONE_MODE_ONE_SCENARIO"):
   select_source_locked_modes("all",True)
  for mode in ("normal","fixed","auto","game2","game4",
               "game2-fec","game4-fec","auto-adaptive"):
   self.assertEqual(select_source_locked_modes(mode,True),[mode])
  for invalid in ("","allx","../../secret","game8"):
   if invalid=="":continue # no selector means seven functional modes
   with self.assertRaises(ValueError):
    select_source_locked_modes(invalid,False)
 def test_native_business_rtt_p99_uses_same_monotonic_origin_and_reports_missing(self):
  values=[1.5]*197+[4.0,4.0,9.0]
  result=summarize_rtt(values,205)
  self.assertEqual(result["p99_ms"],4.0)
  self.assertEqual(result["not_returned"],5)
  self.assertEqual(result["real_replied"],200)
  self.assertEqual(result["late_over_2s"],0)
  self.assertIn("ROUNDTRIP_NOT_ONEWAY",result["measurement"])
  partial=summarize_rtt([1.5]*199,201)
  self.assertIsInstance(partial["p99_ms"],str)
  self.assertEqual(partial["not_returned"],2)
  late=summarize_rtt([100.0]*199+[2400.0],200)
  self.assertEqual(late["late_over_2s"],1)
  with self.assertRaises(ValueError):summarize_rtt([1.0,2.0],1)
 def test_unknown_source_and_mode_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   with self.assertRaises(ValueError):archive_mode_evidence(out,"unknown",SHA,{},0)
   with self.assertRaises(ValueError):archive_mode_evidence(out,"normal","floating",{},0)

if __name__=="__main__":unittest.main()
