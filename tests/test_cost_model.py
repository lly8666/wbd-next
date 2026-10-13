"""Independent small-case enumeration and limiting cases, not product performance tests."""
import itertools
import math
import unittest

from tools import cost_model as m


class ModelTests(unittest.TestCase):
    def test_tagged_source_against_exhaustive_loss_patterns(self):
        k, r, p = 3, 2, 0.2
        expected = 0
        for lost in itertools.product((False, True), repeat=k+r):
            probability = math.prod(p if item else 1-p for item in lost)
            if lost[0] and sum(lost) > r:
                expected += probability
        self.assertAlmostEqual(m.fec_residual(k, r, p), expected)

    def test_partial_one_source_is_replication(self):
        for p in (0, 0.01, 0.3, 1):
            self.assertAlmostEqual(m.fec_residual(1, 1, p), p*p)

    def test_no_parity_no_loss_and_all_loss(self):
        self.assertAlmostEqual(m.fec_residual(20, 0, .3), .3)
        self.assertEqual(m.fec_residual(20, 20, 0), 0)
        self.assertEqual(m.fec_residual(20, 20, 1), 1)

    def test_2020_at_30_percent_is_not_zero(self):
        self.assertAlmostEqual(m.fec_residual(20, 20, .3), .00130108, places=8)

    def test_repair_enumerated_expected_transmissions(self):
        p = .05
        expected = 0
        residual = 0
        for lost in itertools.product((False, True), repeat=3):
            probability = math.prod(p if item else 1-p for item in lost)
            expected += (int(lost[0]) + int(lost[0] and lost[1])) * probability
            residual += int(all(lost)) * probability
        self.assertAlmostEqual(m.repair_iid(p)["extra_per_fresh"], expected)
        self.assertAlmostEqual(m.repair_iid(p)["residual"], residual)

    def test_rtt_and_one_way_are_not_interchangeable(self):
        self.assertEqual(m.timers(150, 5, 2)["cache_ms"], 400)
        self.assertEqual(m.timers(300, 5, 2)["cache_ms"], 700)
        self.assertTrue(m.timers(2000, 5, 2)["horizon_capped"])

    def test_capacity_scale_and_small_packet_memory_limit(self):
        normal = m.capacity(500, 1200, 300, 700, 1.25, 64, 1536)
        small = m.capacity(500, 128, 300, 700, 1.25, 64, 256)
        self.assertEqual(normal["slots"], 65536)
        self.assertEqual(small["slots"], 524288)
        self.assertLess(normal["shadow_mib"], 128)
        self.assertGreater(small["shadow_mib"], 128)
        self.assertAlmostEqual(normal["flight"], 15625)

    def test_invalid_domain_rejected(self):
        for args in ((0, 4, .1), (20, -1, .1), (250, 20, .1), (20, 20, 1.1)):
            with self.assertRaises(ValueError):
                m.fec_residual(*args)
