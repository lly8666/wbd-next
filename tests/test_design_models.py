"""Algebra design checks; never certifies compiled product performance."""
import unittest

from tools import design_models as m


class ReducedDecodeTests(unittest.TestCase):
    def test_field_polynomial_and_all_nonzero_inverses(self):
        self.assertEqual(m.polynomial_mul(0x80, 2), 0x1D)
        for value in range(1, 256):
            self.assertEqual(m.MUL[value][m.inverse_scalar(value)], 1)

    def test_systematic_generator(self):
        self.assertEqual([list(row) for row in m.generator()[:20]], m.identity(20))

    def test_all_profiles_and_erasure_counts_match_full_solve_and_original(self):
        report = m.verification_report()
        self.assertEqual(report["result"], "PASS")
        self.assertGreater(report["total_decode_cases"], 1000)
        self.assertEqual(report["product_result"], "NOT_RUN")

    def test_no_missing_source_has_no_coefficients(self):
        self.assertEqual(m.reduced_coefficients(3, (), ()), ((0, 1, 2), []))

    def test_invalid_or_insufficient_rows_rejected(self):
        for args in ((3, (0, 1), (20,)), (3, (0, 0), (20, 21)),
                     (3, (3,), (20,)), (3, (0, 1), (20, 20)), (3, (0,), (40,))):
            with self.assertRaises(ValueError):
                m.reduced_coefficients(*args)
        with self.assertRaises(ValueError):
            m.inverse([[1, 1], [1, 1]])
        with self.assertRaises(ValueError):
            m.check_case(1, 20, (0,), (21,), 0)


if __name__ == "__main__":
    unittest.main()
