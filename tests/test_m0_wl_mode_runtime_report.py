"""Exact-mode resource samples are measurements, never implicit product PASS."""
import json
import pathlib
import tempfile
import unittest
from tools.m0_wl_mode_runtime_report import (
    summarize_original_windows_process,source_locked_observability)

SCOPE="SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
class SourceLockedModeResourceTests(unittest.TestCase):
 def test_full_process_includes_native_rust_and_kernel_cpu_not_fake_go_cpu(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   rows=[
    {"scope":SCOPE,"native_pid":821,"monotonic_s":100,
     "cpu_total_s":4,"cpu_kernel_s":3,"cpu_user_s":1,
     "working_set_bytes":1200,"private_bytes":900},
    {"scope":SCOPE,"native_pid":821,"monotonic_s":102,
     "cpu_total_s":4.8,"cpu_kernel_s":3.6,"cpu_user_s":1.2,
     "working_set_bytes":1600,"private_bytes":1150}]
   (out/"windows-original-go-rust-process-1hz.jsonl").write_text(
    "".join(json.dumps(x)+"\n" for x in rows))
   result=summarize_original_windows_process(out)
   self.assertEqual(result["result"],"MEASURED_SAME_NATIVE_PID")
   self.assertEqual(result["elapsed_s"],2.0)
   self.assertEqual(result["avg_one_logical_core_pct"],40.0)
   self.assertEqual(result["peak_working_set_bytes"],1600)
   self.assertEqual(result["language_cpu_attribution"],
                    "UNKNOWN_NEEDS_SHORT_STACK_SAMPLE")
   self.assertEqual(result["cpu_kernel_s"],0.6)
 def test_missing_or_single_sample_never_counts_as_zero_cpu(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   result=summarize_original_windows_process(out)
   self.assertTrue(result["result"].startswith("NOT_MEASURED"))
   (out/"windows-original-go-rust-process-1hz.jsonl").write_text(json.dumps({
     "scope":SCOPE,"native_pid":2,"monotonic_s":1,
     "cpu_total_s":1,"cpu_kernel_s":0.8,"cpu_user_s":0.2,
     "working_set_bytes":50,"private_bytes":40})+"\n")
   result=summarize_original_windows_process(out)
   self.assertEqual(result["observations"],1)
   self.assertNotIn("avg_one_logical_core_pct",result)
 def test_native_packet_stats_whitelist_does_not_leak_tls_or_claim_applied(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)
   (out/"client.log").write_text(
    "some-secret-original-TLS-command\n"+
    "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "+
    json.dumps({"mode":"auto","tx_records":12,"npcap_ingress_local_drops":4,
                "actual_rust_m2_effective":{"business_ipv4_mtu":1300},
                "password":"not-allowed","tls_key":"not-allowed",
                "product_applied":True})+"\n")
   report=source_locked_observability(out)
   owner=report["windows_native_owner"]
   self.assertEqual(owner["result"],"OBSERVED_NATIVE_OWNER_1HZ")
   self.assertEqual(owner["fields"]["tx_records"],12)
   self.assertNotIn("password",str(report))
   self.assertNotIn("tls_key",str(report))
   self.assertNotIn("product_applied",str(report))
   self.assertTrue(report["business_oneway_p99"].startswith("NOT_MEASURED"))
