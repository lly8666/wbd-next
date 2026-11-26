import unittest
import m0_h2477_profile as p
class Test(unittest.TestCase):
    def test_matrix(self):
        self.assertEqual(p.RATES,(500,)*6)
        self.assertEqual(p.MODES,('copy','borrow','continue','both','copy','both'))
        self.assertEqual(p.DIRECT_RATES,{-11:500})
    def test_phase(self):
        a={"counters":{"x":3},"netem_packets":{"eth0":1,"ifbwlm0":1}}
        b={"counters":{"x":4},"netem_packets":{"eth0":2,"ifbwlm0":2}}
        self.assertTrue(p.netem_active(a,b)["both_used"])
        self.assertFalse(p.drops(a,b)["zero"])
if __name__=="__main__":unittest.main()
