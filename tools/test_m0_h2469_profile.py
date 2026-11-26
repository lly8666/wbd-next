"""Exercise actual H2469 profile code without modifying host interfaces."""
import pathlib,tempfile,unittest
from unittest.mock import patch
import m0_h2469_capacity as m

class ProfileTest(unittest.TestCase):
    def test_profile_roundtrip(self):
        for role in ("client","relay","server"):
            for fixed in (False,True):
                for absent in (False,True):
                    with self.subTest(role=role,fixed=fixed,absent=absent), tempfile.TemporaryDirectory() as d:
                        state={} if absent else {"rx-udp-gro-forwarding":"off","rx-gro-list":"on"}
                        original=state.copy()
                        def command(*args):
                            return {"rc":0,"stdout":'[{"dev":"eth0"}]' if args[0]=="ip" else "version","stderr":""}
                        def root(*args):
                            if args[1]=="-k":
                                return {"rc":0,"stdout":"\n".join(f"{k}: {v}"+(" [fixed]" if fixed else "") for k,v in state.items()),"stderr":""}
                            self.assertEqual(args[1],"-K")
                            self.assertFalse(fixed)
                            state[args[3]]=args[4]
                            return {"rc":0,"stdout":"","stderr":""}
                        with patch.object(m,"ROOT",pathlib.Path(d)),patch.object(m,"command",command),patch.object(m,"root",root):
                            self.assertTrue(m.profile(role,"baseline")["baseline_restored"])
                            candidate=m.profile(role,"gro")
                            self.assertEqual(bool(candidate["diff_from_baseline"]),not fixed and not absent)
                            self.assertTrue(m.profile(role,"baseline")["baseline_restored"])
                            self.assertEqual(state,original)
    def test_case_contract(self):
        from types import SimpleNamespace
        module=SimpleNamespace()
        m.configure(module)
        self.assertEqual(module.DIRECT_SECONDS,60)
        self.assertEqual(list(module.DIRECT_RATES.values()),[250,250])
        self.assertEqual([x["rate"] for x in module.CASES],[100,150,200,150])
        self.assertTrue(all(x["loss"]==0 and x["profile"]==-1 and x["rcvbuf"]==67108864 for x in module.CASES))
        self.assertEqual([x[0] for x in m.SPECS if x[0]>=0],list(range(len(module.CASES))))
    def test_queue_readonly(self):
        with patch.object(m,"tun_snapshot",return_value={"qlen":500}),patch.object(m,"root",side_effect=AssertionError("no write")):
            self.assertEqual(m.queue("original")["qlen"],500)
            self.assertEqual(m.queue("snapshot")["qlen"],500)
        with patch.object(m,"tun_snapshot",return_value={"qlen":2000}):
            with self.assertRaises(RuntimeError):m.queue("original")
    def test_records_and_wrap(self):
        lines=["1.0 IP 10.1.1.1.443 > 10.2.2.2.41031: Flags [P.], seq 4294967290:4, ack 1, win 10, length 10",
               "1.1 IP x > y: Flags [.], seq 4:14, ack 1, win 10, length 10",
               "1.2 IP x > y: Flags [.], ack 1, win 10, length 0"]
        self.assertEqual(m.seq_records("\n".join(lines)),[(4294967290,10),(4,10)])
        self.assertEqual(m.unwrap(4,4294967290),10)
    def test_shared_sequence(self):
        records=[(1000+i*1000,1000) for i in range(600)]
        other=[r for i,r in enumerate(records) if i!=300]
        a={"records":records,"rc":124,"kernel_capture_drops":0}
        b={"records":other,"rc":124,"kernel_capture_drops":0}
        result=m.compare_forward(a,b)
        self.assertEqual(result["status"],"COMPARABLE_SAMPLE")
        self.assertEqual(result["server_only"],1)
        self.assertEqual(result["wsl_only"],0)
        self.assertEqual(result["matched"],result["wsl_unique"])
        b["kernel_capture_drops"]=1
        self.assertEqual(m.compare_forward(a,b)["status"],"INCONCLUSIVE")
        self.assertEqual(m.compare_forward(a,{"records":[]})["status"],"NO_RECORDS")
if __name__=="__main__":unittest.main()
