"""Source-scoped H2239 tests, not WAN or product regression proofs."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "h2239",ROOT/"tools/m0_h2239_loss_granularity.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class SegmentationNetemRules(unittest.TestCase):
    def test_original_product_immutability_and_true_kernel_only(self):
        s=(ROOT/"tools/m0_h2239_loss_granularity.py").read_text()
        self.assertEqual(H.PHASES,("original_offloads_before",
            "no_segmentation_offloads","original_offloads_after"))
        self.assertEqual((H.SEED,H.LOSS),(22390517,5))
        self.assertIn("node.start_client(LOSS)",s)
        self.assertIn("node.stop_client(LOSS)",s)
        self.assertIn("node.iperf_case(idx*2+1,LOSS",s)
        self.assertIn("node.iperf_case(idx*2+2,LOSS",s)
        self.assertIn("server_owned_stop_verified",s)
        self.assertIn('"product_improvement":"NOT_IMPLEMENTED_NOT_VERIFIED"',s)
        self.assertIn('"seed_qualification":"SEE_EACH_CASE_SEED_STATUS_NOT_ASSUMED"',s)
        self.assertNotIn("WBD_H2239_PRODUCT_ENABLE",s)
        self.assertNotIn("queue_cap_expand",s)

    def test_ethtool_exact_identity_and_restoration(self):
        class Owner:
            client="c";router="r";server="s"
        o=Owner()
        state={(n,dev):dict(tso="on",gso="on",gro="on")
               for n,dev in H.interfaces(o)}
        history=[]
        def mock_ns(n,*args,**kwargs):
            history.append((n,args))
            if args[0:2]==("ethtool","-k"):
                vals=state[(n,args[2])]
                text="\n".join(
                    long+": "+vals[short]+(" [fixed]" if short=="gro" and
                     vals[short]=="off" else "")
                    for short,long in H.FEATURES.items())+"\n"
                return type("Proc",(),{"stdout":text})()
            if args[0:2]==("ethtool","-K"):
                dev,feature,value=args[2:]
                state[(n,dev)][feature]=value
                return type("Proc",(),{"stdout":""})()
            raise AssertionError(args)
        with patch.object(H.L,"ns",mock_ns):
            before=H.offload_baseline(o)
            off=H.set_offloads(o,before,True)
            self.assertEqual(len(off),4)
            self.assertTrue(all(set(x["features"].values())=={"off"} for x in off))
            restored=H.set_offloads(o,before,False)
            self.assertEqual(before,restored)
            self.assertTrue(all(args[0]=="ethtool" for _,args in history))
            self.assertEqual(len({(n,dev) for n,dev in H.interfaces(o)}),4)
            with self.assertRaisesRegex(RuntimeError,"NOT_ORIGINAL"):
                H.set_offloads(o,[],True)

    def test_exact_seed_and_source_error_if_kernel_cannot_readback(self):
        class Owner:
            router="r"
        seen=[]
        def ok(n,*args,**kw):
            seen.append(args)
            if args[0:2]==("tc","-d"):
                return type("P",(),{"stdout":"qdisc netem 0: root delay 200ms "
                    "loss gemodel p 0.01 r 0.25 seed 22390517"})()
            return type("P",(),{"stdout":""})()
        with patch.object(H.L,"ns",ok):
            result=H.seeded_router_loss(Owner())
            self.assertEqual([x["device"] for x in result],["rcli0","rsrv0"])
            self.assertTrue(all(v["seed_applied"]==H.SEED for v in result))
            self.assertEqual(sum("seed" in args for args in seen),2)
        def old_tc(n,*args,**kw):
            if "seed" in args:
                raise RuntimeError("H2234_COMMAND_FAILED old tc unsupported seed")
            if args[0:2]==("tc","-d"):
                return type("P",(),{"stdout":"qdisc netem root delay 200ms loss gemodel p 0.1"})()
            return type("P",(),{"stdout":""})()
        with patch.object(H.L,"ns",old_tc):
            older=H.seeded_router_loss(Owner())
            self.assertTrue(all(v["seed_applied"] is None and
                v["seed_status"]=="UNAVAILABLE_UBUNTU_TC_SEED_UNSEEDED_GE"
                for v in older))
        with patch.object(H.L,"ns",return_value=type("P",(),{
             "stdout":"qdisc netem root delay 200ms loss gemodel"})()):
            with self.assertRaisesRegex(RuntimeError,"FIXED_SEED"):
                H.seeded_router_loss(Owner())

    def test_real_tc_flat_skb_counters_and_no_segment_inference(self):
        readback={
            "client":{"qdisc":[{"kind":"netem","root":True,
                "packets":1200,"bytes":300000,"drops":28}],
                "link":[{"stats64":{"tx":{"packets":100}}}]},
            "server":{"qdisc":[{"kind":"netem","root":True,
                "packets":1000,"bytes":200000,"drops":100}],
                "link":[{"stats64":{"tx":{"packets":90}}}]}
        }
        out=H.qdisc_actual(readback)
        self.assertEqual(out["client"]["netem_qdisc_drops"],28)
        self.assertEqual(out["client"]["physical_link_tx_packets"],100)
        self.assertTrue(out["client"][
            "qdisc_drops_are_skb_not_tcp_segment_or_business_bytes"])
        del readback["server"]["qdisc"][0]["drops"]
        with self.assertRaisesRegex(RuntimeError,"COUNTERS_UNKNOWN"):
            H.qdisc_actual(readback)

if __name__=="__main__":unittest.main()
