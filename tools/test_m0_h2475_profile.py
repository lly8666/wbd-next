import unittest
import m0_h2475_profile as p
import m0_h2475_fixture as f
class Test(unittest.TestCase):
    def row(self,i,ok=True):
        return {"case":i,"rate_mbps":p.RATES[i],"rx_mbps":p.RATES[i]*.9,"status":"MEASURED_EXACT",
                "business_drops":{"zero":ok},"netem_active":{"both_used":True}}
    def test_midpoint(self):
        self.assertEqual(p.midpoint([self.row(0),self.row(1,False)]),6)
        self.assertEqual(p.midpoint([self.row(0),self.row(1),self.row(2,False)]),7)
        self.assertIsNone(p.midpoint([self.row(i) for i in range(5)]))
        self.assertIsNone(p.midpoint([self.row(0,False),self.row(1)]))
    def test_deltas(self):
        a={"counters":{"x":3},"netem_packets":{"eth0":1,"ifbwlm0":2}}
        b={"counters":{"x":3},"netem_packets":{"eth0":2,"ifbwlm0":3}}
        self.assertTrue(p.drops(a,b)["zero"])
        self.assertTrue(p.netem_active(a,b)["both_used"])
        b["counters"]["x"]=4
        self.assertFalse(p.drops(a,b)["zero"])
        self.assertFalse(p.drops(b,a)["available"])
        self.assertFalse(p.drops(a,{})["available"])
    def test_readback(self):
        x={"qdisc":{d:"qdisc netem 10: root limit 32768 delay 200ms" for d in ("eth0","ifbwlm0")},
           "filters":"match 000001bb/0000ffff at 20\nmirred\nmatch 00001452/0000ffff at 20\nmirred"}
        f.verify(x)
        x["filters"]="mirred"
        with self.assertRaises(RuntimeError):f.verify(x)
if __name__=="__main__":unittest.main()
