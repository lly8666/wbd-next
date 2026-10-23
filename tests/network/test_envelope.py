"""Arithmetic counterexamples; real product limits require Actions evidence."""
import json
import unittest
from pathlib import Path
from tools.cost_model import timers
from tools.network_harness.config import validate
from tools.network_harness.envelope import envelope, packet_cost, request_envelope, suite, PROFILES


class EnvelopeTests(unittest.TestCase):
    def test_udp_and_fec_units(self):
        self.assertEqual(packet_cost([[1172, 1]])["fresh_outer_bytes_per_logical_packet"], 1271)
        self.assertEqual(packet_cost([[1172, 1]], 1)["fresh_outer_bytes_per_logical_packet"], 2566)
        self.assertEqual(packet_cost([[64, 1]])["fresh_outer_bytes_per_logical_packet"], 163)

    def test_weight_means_packet_count_not_bytes(self):
        c = packet_cost([[64, 3], [1172, 1]])
        self.assertEqual(c["app_bytes_per_logical_packet"], 341)
        self.assertEqual(c["fresh_outer_bytes_per_logical_packet"], 440)

    def test_high_bandwidth_small_packet_is_separate_axis(self):
        small = envelope(500, 200, PROFILES["small64"])
        large = envelope(500, 200, PROFILES["near_mtu1172"])
        self.assertGreater(small["aggregate_fresh_record_pps"], 7*large["aggregate_fresh_record_pps"])
        self.assertGreater(small["shadow_current_2048_slab_worst_mib"], 512)
        self.assertEqual(large["outer_bdp_bytes"], 25_000_000)

    def test_pto_does_not_expire_before_path_feedback(self):
        self.assertAlmostEqual(timers(400, 5, 10)["pto_ms"], 435)
        self.assertAlmostEqual(timers(600, 5, 10)["cache_ms"], 1345)

    def test_lane_replication_does_not_multiply_line_capacity(self):
        one = envelope(50, 300, [[256, 1]])
        four = envelope(50, 300, [[256, 1]], lanes=4)
        self.assertLess(four["safe_app_mbps"], one["safe_app_mbps"]/4)

    def test_automatic_large_mtu_matches_actual_encapsulation(self):
        c = packet_cost([[1301,1]], inner_mtu=1329)
        self.assertEqual(c["fresh_outer_bytes_per_logical_packet"],1400)
        c = packet_cost([[1287,1]], ratio=1.25, inner_mtu=1315)
        self.assertEqual(c["fresh_outer_bytes_per_logical_packet"],3146)

    def test_sparse_partial_not_full_group_recovery(self):
        rows = suite()["rows"]
        rows = [r for r in rows if r["lanes"] == 1 and r["line_mbps"] == 50 and r["packet_profile"] == "near_mtu1172"]
        self.assertLess(rows[0]["iid_source_residual_pct"], .03)
        self.assertAlmostEqual(rows[1]["iid_source_residual_pct"], 2.7)

    def test_queue_check_is_report_only(self):
        p = Path(__file__).parent/"request.json"
        r = validate(json.loads(p.read_text()))
        r["traffic"].update(c2s_mbps=100, sizes=[[64, 1]])
        r["phases"][0]["c2s"].update(delay_ms=200)
        r["network"]["queue_packets"] = 1024
        report = request_envelope(r)
        self.assertTrue(report["rows"][0]["queue_model_short"])
        self.assertEqual(r["network"]["queue_packets"], 1024)
        self.assertEqual(report["qualification"], "ESTIMATE_ONLY_NO_VERDICT_CHANGE")

    def test_large_udp_does_not_assume_one_wire_packet(self):
        r = validate(json.loads((Path(__file__).parent/"request.json").read_text()))
        r["traffic"].update(sizes=[[4096, 1]], allow_fragmentation=True)
        self.assertEqual(request_envelope(r)["rows"], [])

    def test_observed_inner_mtu_unblocks_large_packet_model(self):
        r = validate(json.loads((Path(__file__).parent/"request.json").read_text()))
        r["traffic"]["sizes"] = [[1287,1]]
        self.assertEqual(request_envelope(r)["rows"], [])
        report = request_envelope(r, inner_mtu=1315)
        self.assertTrue(report["rows"])
        self.assertEqual(report["inner_mtu_input"],1315)
