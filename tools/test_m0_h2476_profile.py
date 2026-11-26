import unittest
import m0_h2476_profile as p
class Test(unittest.TestCase):
    def test_matrix(self):
        self.assertEqual(p.RATES,(400,250,250,250,400,400,400,400))
        self.assertEqual(p.MODES,('optimized','copy','borrow','copy','copy','borrow','copy','frozen'))
    def test_phase(self):
        a={"counters":{"x":3},"netem_packets":{"eth0":1,"ifbwlm0":1}}
        b={"counters":{"x":4},"netem_packets":{"eth0":2,"ifbwlm0":2}}
        self.assertFalse(p.drops(a,b)["zero"])
        self.assertTrue(p.netem_active(a,b)["both_used"])
        self.assertTrue(p.comparable({"status":"MEASURED_EXACT","netem_active":p.netem_active(a,b),"steady_drops":p.drops(a,b)}))
        self.assertFalse(p.comparable({"status":"INCOMPLETE","netem_active":p.netem_active(a,b),"steady_drops":p.drops(a,b)}))
if __name__=="__main__":unittest.main()
