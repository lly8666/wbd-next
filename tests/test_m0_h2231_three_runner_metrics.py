"""H2231 P99 metrics safeguards. Static tests are NOT proof of real WAN p99."""
import json
import os
import pathlib
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools import m0_h2231_three_runner_metrics as M
from tools import m0_h2228_three_runner_relay as H

ROOT=pathlib.Path(__file__).resolve().parents[1]

class H2231RealMeasuredTails(unittest.TestCase):
    def test_type7_p99_and_source_sample_count(self):
        s=M.distribution(list(range(100)),50,"ms")
        self.assertEqual(s["sample_count"],100)
        self.assertAlmostEqual(s["p50"],49.5)
        self.assertAlmostEqual(s["p95"],94.05)
        self.assertAlmostEqual(s["p99"],98.01)
        self.assertEqual(s["p99_quality"],"OBSERVED_SAMPLE_QUANTILE")
        self.assertEqual(s["percentile_method"],"linear_type7_sorted_samples")

    def test_missing_invalid_or_49_samples_cannot_forge_application_p99(self):
        for seq in ([],[None,float("nan"),-1,True],[1]*49):
            with self.subTest(seq_len=len(seq)):
                stat=M.distribution(seq,50)
                self.assertIsNone(stat["p99"])
                self.assertEqual(stat["p99_quality"],"UNKNOWN_INSUFFICIENT_SAMPLES")
        with self.assertRaises(ValueError):
            M.percentile([],99)

    def test_20_s_tcp_intervals_p99_is_throughput_not_packet_tail(self):
        intervals=[]
        for i in range(20):
            intervals.append({"sum":{"bits_per_second":(100+i)*1e6,"seconds":1},
              "streams":[{"rtt":500000+i*1000,"snd_cwnd":1000000}
                         for _ in range(4)]})
        data={"intervals":intervals,"end":{"sum_sent":{
            "bytes":2**30,"retransmits":300},"sum_received":{
            "bytes":2**30}}}
        result=M.iperf_tail(data,{"status":"PASS_REAL_KERNEL_IPERF3_TCP"})
        self.assertEqual(result["business_goodput_per_interval_mbps"]["sample_count"],20)
        self.assertIsNotNone(result["business_goodput_per_interval_mbps"]["p99"])
        self.assertEqual(result["business_goodput_p01_low_tail_mbps"],100.19)
        self.assertEqual(result["kernel_tcp_sender_rtt_ms"]["sample_count"],80)
        self.assertIsNotNone(result["kernel_tcp_sender_rtt_ms"]["p99"])
        self.assertEqual(result["tcp_sum_sent_retransmits"],300)
        self.assertEqual(result["tcp_retransmits_per_gib_sent"],300.0)
        self.assertTrue(result["qualified_iperf3_completed"])
        self.assertNotEqual(result["kernel_tcp_sender_rtt_source"],
                            result["source"])

    def test_iperf_omit_warmup_is_not_p99_and_sparse_rtt_unknown(self):
        intervals=[{"sum":{"seconds":1,"bits_per_second":1e9,
                             "omitted":True},"streams":[{"rtt":100}]}]
        intervals += [{"sum":{"seconds":1,"bits_per_second":100e6},
                       "streams":[{"rtt":400_000}]} for _ in range(12)]
        x=M.iperf_tail({"intervals":intervals},{"status":"PASS_REAL_KERNEL_IPERF3_TCP"})
        self.assertEqual(x["business_goodput_per_interval_mbps"]["sample_count"],12)
        self.assertEqual(x["business_goodput_per_interval_mbps"]["max"],100.0)
        self.assertEqual(x["business_goodput_per_interval_mbps"]["p99"],100.0)
        self.assertIsNone(x["kernel_tcp_sender_rtt_ms"]["p99"])
        self.assertEqual(x["rtt_p99_absent_reason"],
                         "FEWER_THAN_50_SENDER_INTERVAL_RTT_SAMPLES")

    def test_failed_tcp_retains_telemetry_but_not_iperf_pass(self):
        raw={"intervals":[{"sum":{"seconds":1,"bits_per_second":1e6}}]*20}
        metric=M.iperf_tail(raw,{"status":"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE"})
        self.assertFalse(metric["qualified_iperf3_completed"])
        self.assertIsNotNone(metric["business_goodput_per_interval_mbps"]["p99"])

    def test_real_case_enrichment_with_raw_iperf_and_missing_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            case=p/"case-003-source-true.json"
            raw=p/"raw.txt"
            M.save(case,{"kind":"wbd","status":"PASS_REAL_KERNEL_IPERF3_TCP"})
            M.save(raw,{"intervals":[{"sum":{
                "bits_per_second":100e6,"seconds":1}}]*20})
            metric=M.enrich_case(case,raw)
            self.assertTrue(metric["qualified_iperf3_completed"])
            self.assertIn("h2231_tcp_tail",json.loads(case.read_text()))
            raw.unlink()
            unknown=M.enrich_case(case,raw)
            self.assertEqual(unknown["status"],"UNKNOWN_RAW_IPERF_NOT_PARSEABLE")
            self.assertFalse(unknown["qualified_iperf3_completed"])
            with self.assertRaises(ValueError):
                M.enrich_case(p/"profile-not-real.json",raw)

    def test_app_echo_exact_prefix_real_response_no_unsolicited_ack(self):
        self.assertEqual(M.echoed_payload(M.MAGIC+b"token/1"),
                         M.REPLY+b"token/1")
        self.assertIsNone(M.echoed_payload(b"UNTRUSTED/1"))
        self.assertIsNone(M.echoed_payload(M.MAGIC+b"x"*500))
        for kind,count,interval,deadline in [
            ("foreign",10,100,4),("wbd",257,100,24),
            ("direct",120,100,3),("direct",2,1,3)]:
            with self.assertRaises(ValueError):
                M.validate_probe_args(kind,count,interval,deadline)

    def test_real_local_udp_roundtrip_negative_and_unknown_1_sample_p99(self):
        # A genuine localhost socket exchange for the ONLY loopback test.
        # Does not qualify Tailnet/ARM/L3/WBD data as measured.
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as srv:
            srv.bind(("127.0.0.1",0));port=srv.getsockname()[1]
            srv.settimeout(.2)
            done=threading.Event()
            def reply():
                while not done.is_set():
                    try:msg,peer=srv.recvfrom(512)
                    except socket.timeout:continue
                    reply=M.echoed_payload(msg)
                    if reply:srv.sendto(reply,peer)
            t=threading.Thread(target=reply,daemon=True);t.start()
            try:
                with patch.dict(M.TARGET,{"direct":"127.0.0.1"}),patch.dict(
                    M.PORT,{"direct":port}):
                    result=M.probe("direct",1,100,2.0)
                self.assertEqual(result["valid_unique_reply_count"],1)
                self.assertEqual(result["missing_unique_reply_count"],0)
                self.assertEqual(result["roundtrip_rtt_ms"]["sample_count"],1)
                self.assertIsNone(result["roundtrip_rtt_ms"]["p99"])
                self.assertFalse(result["qualified_for_lowrate_udp_p99"])
            finally:
                done.set();t.join(timeout=2)

    def test_proc_cpu_rss_tail_requires_original_worker_and_real_pid_identity(self):
        fields=["0"]*22
        fields[11]="110";fields[12]="40";fields[19]="123456";fields[21]="101"
        raw="1001 (wbd-v4-client) "+" ".join(fields)
        with patch.object(pathlib.Path,"read_text",return_value=raw):
            row=M.native_stat(1001)
        self.assertEqual(row["cpu_ticks"],150)
        self.assertEqual(row["starttime_ticks"],123456)
        self.assertGreater(row["rss_mib"],0)
        with patch.object(pathlib.Path,"read_text",return_value=raw.replace(
                "wbd-v4-client","iperf3")):
            with self.assertRaises(ValueError):
                M.native_stat(1001)
        with self.assertRaises(ValueError):
            M.native_stat(-1)

    def test_original_three_runner_main_fixture_emits_both_authentic_paths(self):
        sh=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        self.assertIn('spawn "$TMP/udp-$kind.pid" python3 "$METRICS" echo-server "$kind"',sh)
        self.assertIn('udp-probe "$kind"',sh)
        self.assertIn('process-sample',sh)
        self.assertEqual(sh.count('env GITHUB_SHA="$GITHUB_SHA" GITHUB_RUN_ID="$GITHUB_RUN_ID"'),2)
        self.assertIn('resource-$(basename "$casefile")',sh)
        self.assertIn('iperf-enrich "$casefile"',sh)
        self.assertIn('--outer-repair on',sh)
        self.assertLess(sh.index('udp-probe "$kind"'),sh.index('iperf "$kind"'))
        script=(ROOT/"tools/m0_h2228_three_runner_relay.py").read_text()
        self.assertIn('"h2231_app_udp_probe":probe',script)
        self.assertIn('h2231_tail_metrics_are_not_new_product_pass',script)

    def test_summary_never_invents_new_p99_from_old_cases(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            names=sorted(H.expected_cases("burst"))
            for i,name in enumerate(names):
                M.save(root/f"case-{i:03d}-{name}.json",{
                    "status":"PASS_REAL_KERNEL_IPERF3_TCP","mbps":100.0,
                    "kind":"direct" if "-direct-" in name else "wbd"})
            old=H.result_summary("normal","burst",root)
            self.assertEqual(old["h2231_real_udp_probe_cases_observed"],0)
            self.assertEqual(old["h2231_real_udp_p99_cases_with_at_least_50_echoes"],0)
            self.assertEqual(old["h2231_tcp_tail_cases_observed"],0)
            self.assertEqual(old["h2231_tail_metrics_qualification"],
                "PARTIAL_OR_NOT_RUN_OR_MISSING_REAL_METRIC_RECEIPTS")
            real=root/("probe-case-000-"+names[0]+".json")
            kind="direct" if "-direct-" in names[0] else "wbd"
            M.save(real,{"schema":"H2231_TRUE_APP_UDP_RTT_V1",
                "source_sha":os.environ.get("GITHUB_SHA"),
                "run_id":os.environ.get("GITHUB_RUN_ID"),
                "kind":kind,"origin":"REAL_APP_UDP_ECHO_DIRECT_ARM_RELAY_ONLY"
                    if kind=="direct" else "REAL_APP_UDP_ECHO_WITHIN_WBD_INNER_TUN",
                "qualified_for_lowrate_udp_p99":True,
                "roundtrip_rtt_ms":{"sample_count":120,"p99":400.0}})
            new=H.result_summary("normal","burst",root)
            self.assertEqual(new["h2231_real_udp_probe_cases_observed"],1)
            self.assertEqual(new["h2231_real_udp_p99_cases_with_at_least_50_echoes"],1)
            self.assertEqual(new["status"],"PASS_REAL_THREE_RUNNER_TCP_MATRIX")
            self.assertEqual(new["raw_cases"][0]["h2231_app_udp_probe"]["roundtrip_rtt_ms"]["p99"],400.0)
            forged=json.loads(real.read_text())
            forged["source_sha"]="not_the_actions_commit"
            M.save(real,forged)
            denied=H.result_summary("normal","burst",root)
            self.assertEqual(denied["h2231_real_udp_probe_cases_observed"],0)
            self.assertEqual(denied["raw_cases"][0]["h2231_app_udp_probe"]["status"],
                             "INVALID_UDP_PROBE_ORIGIN")

if __name__=="__main__":unittest.main()
