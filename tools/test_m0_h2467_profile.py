"""Exercise actual H2467 profile code without modifying host interfaces."""
import pathlib,tempfile,unittest
from unittest.mock import patch
import m0_h2467_capacity as m

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
        self.assertEqual([x["rate"] for x in module.CASES],[150,200,200,150,200,150])
        self.assertTrue(all(x["loss"]==0 and x["profile"]==-1 and x["rcvbuf"]==67108864 for x in module.CASES))
        self.assertEqual([x[0] for x in m.SPECS if x[0]>=0],list(range(len(module.CASES))))
    def test_queue_readonly(self):
        with patch.object(m,"tun_snapshot",return_value={"qlen":500}),patch.object(m,"root",side_effect=AssertionError("no write")):
            self.assertEqual(m.queue("original")["qlen"],500)
        with patch.object(m,"tun_snapshot",return_value={"qlen":2000}):
            with self.assertRaises(RuntimeError):m.queue("original")
    def test_priority_roundtrip(self):
        state={"12":0,"13":0}
        def snap():return {"pid":12,"nice":dict(state)}
        def setpriority(which,pid,nice):state[str(pid)]=nice
        with tempfile.TemporaryDirectory() as d,patch.object(m,"ROOT",pathlib.Path(d)),patch.object(m,"priority_snapshot",snap),patch.object(m.os,"PRIO_PROCESS",0,create=True),patch.object(m.os,"setpriority",setpriority,create=True):
            self.assertEqual(set(m.priority("original")["nice"].values()),{0})
            self.assertEqual(set(m.priority("candidate")["nice"].values()),{-5})
            self.assertEqual(set(m.priority("snapshot")["nice"].values()),{-5})
            self.assertEqual(set(m.priority("original")["nice"].values()),{0})
if __name__=="__main__":unittest.main()
