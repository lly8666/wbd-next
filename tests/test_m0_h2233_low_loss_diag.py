"""H2233 source/fixture negative gates; no WAN performance is implied."""
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("h2233",ROOT/"tools/m0_h2233_low_loss_diag.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class H2233LowLossAnalysis(unittest.TestCase):
    def test_qdisc_delta_is_not_called_tcp_segment_loss(self):
        def receipt(sent,drops,tx):
            return {role:{
                "qdisc":[{"kind":"netem","handle":"1:","options":{"delay":"200ms"},
                    "packets":sent,"drops":drops}],
                "link":[{"stats64":{"tx":{"packets":tx}}}],
                "offload_features":"generic-segmentation-offload: on"
            } for role in ("client","server")}
        delta=H.delta_qdisc(receipt(100,4,20),receipt(200,9,40))
        self.assertEqual(delta["client_to_server"]["netem_emitted_skb"],100)
        self.assertEqual(delta["client_to_server"]["netem_dropped_skb"],5)
        self.assertEqual(delta["client_to_server"]["netem_emitted_over_link_tx_ratio"],5)
        self.assertIn("not ip packet loss",delta["client_to_server"]["accounting_warning"].lower())
        broken=receipt(200,9,40)
        broken["server"]["qdisc"][0]["handle"]="2:"
        self.assertEqual(H.delta_qdisc(receipt(100,4,20),broken)["client_to_server"]["status"],
                         "UNKNOWN_MISSING_OR_CHANGED_KERNEL_QDISC")

    def test_receiver_goodput_and_source_lock_cannot_be_sender_substituted(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"GITHUB_SHA":"a"*40,
                      "GITHUB_RUN_ID":"667","WBD_H2233_JITTER":"fixed"}):
            path=pathlib.Path(d)
            cases=["clear-zero-direct-12s-8p-"+direction for direction in H.DIRECTIONS]
            for loss in H.LOSSES:
                for direction in H.DIRECTIONS:
                    cases.extend(f"delay200-loss{loss}-burst-{kind}-20s-4p-{direction}"
                                 for kind in ("direct","wbd"))
                cases.append(f"delay200-loss{loss}-burst-wbd-3s-1p-upload")
            for idx,case in enumerate(cases):
                (path/f"case-{idx:03d}-{case}.json").write_text(json.dumps({
                    "status":"PASS_REAL_KERNEL_IPERF3_TCP","sender_mbps":999,
                    "receiver_goodput_mbps":850 if "clear-zero" in case else 100,
                    "tcp_mss_requested":1037,"tcp_mss_observed":[1037],
                    "tcp_retransmits":0
                }))
            (path/"clear-before-relay.json").write_text(json.dumps({
                "tail_to_client":{"tail_path":"DIRECT_CANDIDATE"},
                "tail_to_server":{"tail_path":"DIRECT_CANDIDATE"}}))
            r=H.focused_summary("normal","burst",path)
            self.assertEqual(r["status"],"PASS_FOCUSED_LOW_LOSS_TCP_MATRIX")
            self.assertEqual(len(r["comparisons"]),4)
            self.assertEqual(r["comparisons"][0]["direct_receiver_goodput_mbps"],100)
            self.assertEqual(r["comparisons"][0]["actual_mss_readback"],"UNKNOWN_OR_MISMATCH")
            self.assertEqual(r["direct_clear_receiver_goodput_mbps"]["upload"],850)
            self.assertEqual(r["relay_capacity_qualification"],">=800Mbps_BOTH_DIRECTIONS_DIRECT_TAILSCALE")
            cases[2]
            (path/f"case-002-{cases[2]}.json").unlink()
            r2=H.focused_summary("normal","burst",path)
            self.assertEqual(r2["status"],"FAIL_FOCUSED_MISSING_OR_DUPLICATED_CASE")

    def test_actual_tcp_info_requires_original_iperf_ports(self):
        with tempfile.TemporaryDirectory() as d:
            f=pathlib.Path(d)/"case-000-real.json"
            pathlib.Path(str(f)+".stdout.txt").write_text(json.dumps({
                "start":{"connected":[{"local_port":41920},{"local_port":41921}]}}))
            info=pathlib.Path(str(f)+".tcp-info.txt")
            info.write_text(
                "ESTAB 0 0 10.248.81.2:41920 10.248.82.2:5202\n"
                "bbr rtt:460/5 mss:1037 pmtu:1200\n"
                "ESTAB 0 0 10.248.81.2:41921 10.248.82.2:5202\n"
                "bbr rtt:458/5 mss:1037 pmtu:1200\n")
            ok=H.socket_mss_readback(f,"direct")
            self.assertEqual(ok["status"],"REAL_TCP_INFO_ALL_STREAMS")
            self.assertEqual(ok["mss"],[1037,1037])
            info.write_text(
                "ESTAB 0 0 10.248.81.2:41920 10.248.82.2:5202\n"
                "bbr mss:1037\n")
            self.assertEqual(H.socket_mss_readback(f,"direct")["status"],
                             "UNKNOWN_PARTIAL_TCP_INFO")
            self.assertEqual(H.socket_mss_readback(f,"wbd")["mss"],[])

    def test_branch_only_activation_and_unmodified_cold_tls(self):
        sh=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        tool=(ROOT/"tools/m0_h2228_three_runner_relay.py").read_text()
        wf=(ROOT/".github/workflows/qa-h2228-three-runner-arm-relay-ge200.yml").read_text()
        self.assertIn('for loss in 0 1 5 10 20;do',sh)
        self.assertIn('"$loss" != 1 && "$loss" != 5',sh)
        self.assertIn("before-$(basename",sh)
        self.assertIn('"receiver_goodput_mbps":delivered_rate(receive_end)',tool)
        self.assertIn('["-M",str(requested_mss)]',tool)
        self.assertIn("WBD_H2233_JITTER",tool)
        self.assertIn("feat/h2233-low-loss-forensics",wf)
        self.assertIn("tests.test_m0_h2233_low_loss_diag -v",wf)
        self.assertNotIn("wbd-recovery/src",wf)
