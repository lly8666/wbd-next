"""Exercise actual H2465 profile code without modifying host interfaces."""
import pathlib,tempfile,unittest
from unittest.mock import patch
import m0_h2465_capacity as m

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
        self.assertEqual([x["rate"] for x in module.CASES],[250,250,250])
        self.assertTrue(all(x["loss"]==0 and x["profile"]==-1 and x["rcvbuf"]==67108864 for x in module.CASES))
        self.assertEqual([x[0] for x in m.SPECS if x[0]>=0],list(range(len(module.CASES))))
    def test_queue_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            state={"qlen":500}
            def snap():return dict(state)
            def root(*args):
                self.assertEqual(args[:-1],("ip","link","set","dev","tailscale0","txqueuelen"))
                state["qlen"]=int(args[-1]);return {"rc":0}
            with patch.object(m,"ROOT",pathlib.Path(d)),patch.object(m,"tun_snapshot",snap),patch.object(m,"root",root):
                self.assertEqual(m.queue("original")["qlen"],500)
                self.assertEqual(m.queue("candidate")["qlen"],2000)
                self.assertEqual(m.queue("snapshot")["qlen"],2000)
                self.assertEqual(m.queue("original")["qlen"],500)
    def test_unexpected_original(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,"ROOT",pathlib.Path(d)),patch.object(m,"tun_snapshot",return_value={"qlen":1000}):
            with self.assertRaises(RuntimeError):m.queue("candidate")
if __name__=="__main__":unittest.main()
