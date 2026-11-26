import unittest
import m0_h2478_profile as p
class Test(unittest.TestCase):
    def test_matrix(self):
        self.assertEqual(p.RATES,(650,)*6)
        self.assertEqual(p.MODES,('copy','both','loan','all','copy','all'))
        self.assertEqual(p.DIRECT_RATES,{-11:650})
    def test_phase(self):
        a={"counters":{"x":3},"netem_packets":{"eth0":1,"ifbwlm0":1}}
        b={"counters":{"x":4},"netem_packets":{"eth0":2,"ifbwlm0":2}}
        self.assertTrue(p.netem_active(a,b)["both_used"])
        self.assertFalse(p.drops(a,b)["zero"])
if __name__=="__main__":unittest.main()
