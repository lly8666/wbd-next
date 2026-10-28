import unittest
from tools.m0_wl_impairment_profile import get_profile

class KernelImpairmentProfileContract(unittest.TestCase):
    def test_exact_two_os_reproducible_p200_250m_30p(self):
        p=get_profile("p200-250m-30p")
        self.assertEqual((p["delay_ms"],p["loss_pct"],p["tc_mbit"]), (200,30,250))
        self.assertEqual(p["offered_mbps"],250.0)
        self.assertEqual(p["duration_s"],60)
    def test_old_300ms_n0_is_not_reinterpreted(self):
        p=get_profile("n0")
        self.assertEqual((p["delay_ms"],p["loss_pct"],p["tc_mbit"],p["offered_mbps"]), (300,0,None,10.0))
    def test_unknown_profile_is_not_silently_clamped(self):
        with self.assertRaises(KeyError): get_profile("200ms-without-rate")
if __name__ == "__main__": unittest.main()
