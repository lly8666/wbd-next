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
 
 def test_natural_auto_source_probe_preserves_real_sample_gaps_and_unknown(self):
  from tools.m0_wl_mode_runtime_report import summarize_auto_udp_progress
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"natural-auto-windows.log"
   self.assertEqual(summarize_auto_udp_progress(p)["result"],
                    "NOT_MEASURED_NO_REAL_AUTO_UDP_LOG")
   rows=[{"phase":"bound","local":"fake-not-counted"},
         {"phase":"udp_1hz","sent":0,"received":0,"secret":"must-not-leak"},
         {"phase":"udp_1hz","sent":180,"received":20},
         {"phase":"udp_1hz","sent":180,"received":21},
         {"phase":"udp_1hz","sent":610,"received":280}]
   p.write_text("not-json\n"+"".join(json.dumps(x)+"\n" for x in rows))
   v=summarize_auto_udp_progress(p)
   self.assertEqual(v["result"],"OBSERVED_REAL_APP_1HZ_SOCKET_PROGRESS")
   self.assertEqual(v["observations"],4)
   self.assertEqual(v["min_socket_sent_per_observation"],0)
   self.assertEqual(v["max_socket_sent_per_observation"],430)
   self.assertEqual(v["last"]["received_first"],280)
   self.assertEqual(v["owner_m2_2s8s_denominator"],"NOT_MEASURED_BY_APP")
   self.assertNotIn("secret",str(v))
   p.write_text(json.dumps({"phase":"udp_1hz","sent":4,"received":2})+"\n"+
                json.dumps({"phase":"udp_1hz","sent":3,"received":2})+"\n")
   self.assertEqual(summarize_auto_udp_progress(p)["result"],
                    "NOT_MEASURED_AUTO_SOURCE_COUNTER_RESET")
