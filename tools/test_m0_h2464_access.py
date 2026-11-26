"""Test architecture command/rollback ordering with mocked kernel commands."""
import pathlib,tempfile,unittest
from unittest.mock import patch
import m0_h2464_access as a
import m0_h2464_capacity as c
class Tests(unittest.TestCase):
    def test_roundtrip(self):
        for role in ("client","relay"):
            with self.subTest(role=role),tempfile.TemporaryDirectory() as d:
                state=pathlib.Path(d)/"state.json";calls=[]
                def run(*args,**kw):
                    calls.append(args)
                    return "0\n" if args[:2]==("sysctl","-n") else ""
                with patch.dict(a.STATE,{role:state}),patch.object(a,"run",run),patch.object(a,"link_exists",return_value=False),patch.object(a,"info",return_value=("100.64.1.1","100.64.1.2","172.29.0.1")),patch.object(a,"snapshot",side_effect=lambda r:{"role":r,"mode":"ipip" if state.exists() else "vxlan"}):
                    self.assertEqual(a.apply(role,"ipip")["mode"],"ipip")
                    self.assertTrue(state.is_file())
                    self.assertEqual(a.apply(role,"vxlan")["mode"],"vxlan")
                    self.assertFalse(state.exists())
                    self.assertIn(("ip","tunnel","del",a.TUN),calls)
                    if role=="relay":
                        self.assertIn(("ip","link","set",a.VETH,"master",a.BR),calls)
    def test_traffic_receipt(self):
        b={"client":{"tunnel":{"rx":{"bytes":100}}},"relay":{"tunnel":{"tx":{"bytes":200}}}}
        e={"client":{"tunnel":{"rx":{"bytes":1100}}},"relay":{"tunnel":{"tx":{"bytes":1200}}}}
        self.assertTrue(a.traffic(b,e,1000))
        self.assertFalse(a.traffic(b,e,2000))
        self.assertFalse(a.traffic({},e,1000))
    def test_matrix(self):
        self.assertEqual([x[4] for x in c.SPECS],["vxlan","vxlan","ipip","ipip","vxlan","vxlan"])
        self.assertTrue(all(x[2]==200 and x[0]<0 for x in c.SPECS))
if __name__=="__main__":unittest.main()
