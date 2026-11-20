"""H2232 real TCP connect() latency P99: isolated fixture tests, no WAN claims."""
import os
import pathlib
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tools import m0_h2232_tcp_connect_p99 as T

ROOT=pathlib.Path(__file__).resolve().parents[1]

class H2232RealConnectP99(unittest.TestCase):
    def test_exact_wbd_tun_vs_direct_underlay_allowlist(self):
        self.assertNotEqual(T.DEST["wbd"],T.DEST["direct"])
        self.assertEqual(T.DEST["wbd"][0],"10.66.0.1")
        self.assertEqual(T.DEST["direct"][0],"10.248.82.2")
        for bad in (("foreign",12,100,4),("direct",161,100,20),
                    ("direct",120,100,3),("wbd",10,500,5),
                    ("wbd",-1,100,5),("direct",5,100,40)):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                T.validate(*bad)
        T.validate("direct",120,100,15)
        T.validate("wbd",16,100,2.7)

    def test_genuine_socket_handshakes_localhost_not_wan(self):
        listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        listener.bind(("127.0.0.1",0))
        listener.listen(100)
        port=listener.getsockname()[1]
        listener.settimeout(.2)
        close=threading.Event()
        accepted=[]
        def accept():
            while not close.is_set():
                try:c,_=listener.accept()
                except socket.timeout:continue
                accepted.append(True)
                c.close()
        worker=threading.Thread(target=accept,daemon=True)
        worker.start()
        try:
            with patch.dict(T.DEST,{"direct":("127.0.0.1",port)}),\
                 patch.dict(os.environ,{"GITHUB_SHA":"b"*40,
                         "GITHUB_RUN_ID":"123456"}):
                d=T.probe("direct",6,100,2.5)
            self.assertEqual(d["attempted_independent_connections"],6)
            self.assertEqual(d["succeeded_connects"],6)
            self.assertEqual(d["failed_or_unfinished_connects"],0)
            self.assertEqual(d["source_sha"],"b"*40)
            self.assertFalse(d["valid_connect_p99"])
            self.assertIsNone(d["kernel_tcp_connect_elapsed_ms"]["p99"])
            self.assertEqual(d["kernel_tcp_connect_elapsed_ms"]["sample_count"],6)
            self.assertTrue(d["connect_elapsed_is_not_packet_rtt"])
        finally:
            close.set()
            worker.join(timeout=2)
            listener.close()

    def test_real_failed_connect_does_not_invent_p99_or_zero(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1",0))
            port=s.getsockname()[1]
        with patch.dict(T.DEST,{"wbd":("127.0.0.1",port)}):
            d=T.probe("wbd",5,100,2.4)
        self.assertEqual(d["succeeded_connects"],0)
        self.assertGreaterEqual(d["failed_or_unfinished_connects"],1)
        self.assertIsNone(d["kernel_tcp_connect_elapsed_ms"]["p99"])
        self.assertFalse(d["valid_connect_p99"])

    def test_source_validated_summary_no_missing_or_foreign(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp)/"case-connect.json"
            with patch.dict(T.DEST,{"wbd":("127.0.0.1",1)}),\
                 patch.dict(os.environ,{"GITHUB_SHA":"a"*40,
                         "GITHUB_RUN_ID":"123456"}):
                a=T.probe("wbd",1,100,2.3)
            T.write(p,a)
            saved=T.__dict__.get("SCHEMA")
            self.assertEqual(saved,a["schema"])
            self.assertEqual(a["kernel_tcp_connect_elapsed_ms"]["p99"],None)
            self.assertEqual(a["source_sha"],"a"*40)

    def test_incomplete_and_forged_origin_never_become_tcp_connect_p99(self):
        from tools import m0_h2228_three_runner_relay as H
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{
            "GITHUB_SHA":"e"*40,"GITHUB_RUN_ID":"123456"}):
            root=pathlib.Path(d)
            cases=sorted(H.expected_cases("burst"))
            for i,case in enumerate(cases):
                kind="direct" if "-direct-" in case else "wbd"
                T.write(root/("case-%03d-%s.json"%(i,case)),{
                    "status":"PASS_REAL_KERNEL_IPERF3_TCP","kind":kind,
                    "mbps":10.0,"source_sha":"e"*40,"run_id":"123456"})
            empty=H.result_summary("normal","burst",root)
            self.assertEqual(empty["h2232_real_tcp_connect_cases_observed"],0)
            item=cases[0]
            kind="direct" if "-direct-" in item else "wbd"
            path=root/("connect-case-000-"+item+".json")
            payload={
                "schema":T.SCHEMA,"source_sha":"e"*40,"run_id":"123456",
                "kind":kind,
                "origin":("REAL_LINUX_KERNEL_TCP_CONNECT_DIRECT_ARM_RELAY" if
                    kind=="direct" else
                    "REAL_LINUX_KERNEL_TCP_CONNECT_OVER_AUTHENTICATED_WBD_TUN"),
                "attempted_independent_connections":60,
                "succeeded_connects":55,"failed_or_unfinished_connects":5,
                "valid_connect_p99":True,"deadline_s":15.0,
                "kernel_tcp_connect_elapsed_ms":{"sample_count":55,"p50":450.0,
                    "p95":560.0,"p99":900.0},
                "connect_failure_pct":round(100*5/60,3),
                "connect_p99_status":"OBSERVED_SAMPLE_QUANTILE"}
            T.write(path,payload)
            valid=H.result_summary("normal","burst",root)
            self.assertEqual(valid["h2232_real_tcp_connect_cases_observed"],1)
            self.assertEqual(valid["h2232_real_tcp_connect_p99_cases_with_at_least_50_successes"],1)
            self.assertEqual(valid["raw_cases"][0]["h2232_real_tcp_connect_probe"]
                ["kernel_tcp_connect_elapsed_ms"]["p99"],900.0)
            payload["source_sha"]="foreign-run"
            T.write(path,payload)
            invalid=H.result_summary("normal","burst",root)
            self.assertEqual(invalid["h2232_real_tcp_connect_cases_observed"],0)
            self.assertEqual(invalid["raw_cases"][0]
                ["h2232_real_tcp_connect_probe"]["status"],
                "INVALID_TCP_CONNECT_PROBE_ORIGIN")
            payload["source_sha"]="e"*40
            payload["succeeded_connects"]=49
            payload["failed_or_unfinished_connects"]=11
            payload["kernel_tcp_connect_elapsed_ms"]["sample_count"]=49
            T.write(path,payload)
            forged=H.result_summary("normal","burst",root)
            self.assertEqual(forged["raw_cases"][0]
                ["h2232_real_tcp_connect_probe"]["status"],
                "INVALID_TCP_CONNECT_P99_SAMPLE_COUNT")

    def test_original_three_runner_process_runs_tcp_probe_in_parallel(self):
        sh=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        self.assertIn('tcp-serve "$kind"',sh)
        self.assertIn('tcp-probe "$kind"',sh)
        self.assertIn('connect-$(basename "$casefile")',sh)
        self.assertIn('GITHUB_SHA="$GITHUB_SHA" GITHUB_RUN_ID="$GITHUB_RUN_ID"',sh)
        self.assertIn('--outer-repair on',sh)
        self.assertLess(sh.index('tcp-probe "$kind"'),sh.index('iperf "$kind"'))
        w=(ROOT/".github/workflows/qa-h2228-three-runner-arm-relay-ge200.yml").read_text()
        self.assertIn("tests.test_m0_h2232_tcp_connect_p99",w)
        self.assertIn("H2232_TCP_CONNECT_STATIC_SMOKE_NOT_REAL_WAN",w)
        self.assertIn("PY_H2231_GOV",w)
        self.assertNotIn("<<'PY_H2231_GOV\n",w)

if __name__=="__main__":
    unittest.main()
