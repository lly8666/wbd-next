"""Exercise actual H2471 profile code without modifying host interfaces."""
import pathlib,tempfile,unittest
from unittest.mock import patch
import m0_h2471_capacity as m

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
        self.assertEqual(module.DIRECT_SECONDS,30)
        self.assertEqual(list(module.DIRECT_RATES.values()),[250,250])
        self.assertEqual([x["rate"] for x in module.CASES],list(m.RATES)+list(reversed(m.RATES)))
        self.assertTrue(all(x["loss"]==0 and x["profile"]==-1 and x["rcvbuf"]==67108864 for x in module.CASES))
        self.assertEqual([x[0] for x in m.SPECS if x[0]>=0],list(range(len(module.CASES))))
    def test_queue_readonly(self):
        with patch.object(m,"tun_snapshot",return_value={"qlen":500}),patch.object(m,"fixture_snapshot",return_value={}),patch.object(m,"root",side_effect=AssertionError("no write")):
            self.assertEqual(m.queue("original")["qlen"],500)
            self.assertEqual(m.queue("snapshot")["qlen"],500)
        with patch.object(m,"tun_snapshot",return_value={"qlen":2000}):
            with self.assertRaises(RuntimeError):m.queue("original")
    def test_cpu_probe(self):
        import m0_h2470_probe as probe
        result=probe.run("windows",seconds=.08,repeats=2)
        self.assertEqual(len(result["workloads"]),3)
        for v in result["workloads"].values():
            self.assertEqual(len(v["samples"]),2)
            self.assertGreater(v["median_ops_per_wall_s"],0)
            self.assertGreater(v["median_ops_per_cpu_s"],0)
    def test_cpu_gate(self):
        import m0_h2471_gate as g
        for s in ("AMD EPYC 9V45 48-Core Processor","AMD EPYC 9v45","EPYC 9 V 45","amd epyc 9-v-45 @ 2.7GHz"):
            self.assertTrue(g.eligible([s]))
        for s in ("AMD EPYC 9V74","AMD EPYC 7763","Intel Xeon 8573C","AMD EPYC 9V450","Unknown",""):
            self.assertFalse(g.eligible([s]))
        self.assertFalse(g.eligible([]))
    def test_drop_deltas(self):
        import copy
        x={"fixture":{"links":{d:{s:{"dropped":0,"errors":0} for s in ("rx","tx")} for d in m.WSL_DEVS},
                      "qdisc_drops":{d+"|fq_codel":0 for d in m.WSL_DEVS},"softnet_drop":0,"softnet_time_squeeze":0}}
        y=copy.deepcopy(x)
        self.assertTrue(m.drop_deltas(x,y)["zero"])
        y["fixture"]["links"]["tailscale0"]["tx"]["dropped"]=1
        self.assertFalse(m.drop_deltas(x,y)["zero"])
        self.assertFalse(m.drop_deltas(y,x)["available"])
        del y["fixture"]["links"]["eth0"]
        self.assertFalse(m.drop_deltas(x,y)["available"])
if __name__=="__main__":unittest.main()
