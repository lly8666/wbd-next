"""H2243: true original M4-sized batch fairness and kernel layered drop receipts."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "h2243",ROOT/"tools/m0_h2243_burst_fair_abca.py")
H=importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

class KernelBoundedBatchAndNoHol(unittest.TestCase):
    def test_frozen_all_original_one_owner_and_4way_1pct(self):
        self.assertEqual(H.PHASES,(
            ("original_before",4),
            ("tbf16kb_fq_codel",4),
            ("tbf48kb_fq_codel",4),
            ("original_after",4)))
        self.assertEqual(H.TBF_RATE_MBIT,450)
        script=(ROOT/"tools/m0_h2243_burst_fair_abca.py").read_text()
        for key in (
            'os.environ["WBD_H2241_NATIVE_GATE"]="0"',
            'node.start_client(1)',
            'node.stop_client(1)',
            'source_kernel_qdisc_receipt(',
            'rearm_direct_capacity_listener(node)',
            '"original_kernel_tun_tx_ring_2048_unchanged":True',
            '"product_default_original_per_flow_fq600_unchanged":True',
            '"no_second_owner_or_cross_route_pause":True'):
            self.assertIn(key,script)
        self.assertNotIn("ordered_retransmit_wait",script)
        self.assertNotIn("new_outer_reliable_transport",script)

    def test_tbf_with_fair_child_true_kernel_drops_not_double_counted(self):
        def snap(root_pk,root_drop,leaf_pk,leaf_drop,dev_drop):
            return {"tc":[
                {"kind":"tbf","root":True,"packets":root_pk,
                 "drops":root_drop,"bytes":root_pk*1000},
                {"kind":"fq_codel","parent":"1:1","packets":leaf_pk,
                 "drops":leaf_drop,"bytes":leaf_pk*1000}],
                "link":[{"stats64":{"tx":{"packets":root_pk,
                    "dropped":dev_drop,"bytes":root_pk*1000}}}]}
        s=H.source_kernel_qdisc_receipt(
            snap(10,0,10,0,0),snap(112,5,111,5,3),"tbf")
        self.assertEqual(s["tbf_drops_delta"],5)
        self.assertEqual(s["fq_codel_drops_delta"],5)
        self.assertEqual(s["actual_link_tx_dropped_delta"],3)
        self.assertTrue(s["parent_child_drops_may_overlap_not_additive"])
        with self.assertRaisesRegex(RuntimeError,"MISSING_OWNED_TBF_OR_FAIR_LEAF"):
            H.source_kernel_qdisc_receipt(
                snap(10,0,10,0,0),
                {"tc":[{"kind":"tbf","root":True,"packets":30,
                        "drops":0,"bytes":30000}],
                 "link":[{"stats64":{"tx":{"packets":30,"dropped":0,"bytes":30000}}}]},
                "tbf")

    def test_test_only_true_owned_tun_qdisc_and_no_ring_expansion(self):
        class Owned:
            client="h34c0001"
            def __init__(self):self.alive=True
            def owned_pid(self,role):
                return 12345 if role=="client" and self.alive else None
        node=Owned()
        calls=[]
        def ns(name,*args,**kw):
            calls.append((name,args))
            if args[:3]==("tc","-d","qdisc"):
                old=not any(a[:3]==("tc","qdisc","replace") for _,a in calls)
                return type("R",(),{"stdout":(
                    "qdisc fq 8001: root maxrate 600Mbit flow_limit 256" if old else
                    "qdisc tbf 1: root rate 450Mbit burst 16Kb lat 15ms\n"
                    "qdisc fq_codel 10: parent 1:1 limit 256 target 5ms interval 100ms ecn")})()
            if args[:3]==("ip","-j","link"):
                return type("R",(),{"stdout":'[{"ifname":"wbdc0","txqlen":2048}]'})()
            if args[:3]==("tc","qdisc","replace"):
                return type("R",(),{"stdout":""})()
            raise AssertionError(args)
        with patch.object(H.L,"ns",ns):
            result=H.install_owned_tun_aggregate_burst_fair(node,16)
        self.assertEqual((result["burst_kib"],result["aggregate_rate_mbps"]),(16,450))
        self.assertEqual(len(calls),5)
        self.assertTrue(all(n==node.client for n,_ in calls))
        self.assertIn(("tc","qdisc","replace","dev","wbdc0","root","handle","1:",
                       "tbf","rate","450mbit","burst","16kb","latency","15ms"),
                      [a for _,a in calls])
        self.assertTrue(result["no_original_kernel_tun_ring_capacity_change"])
        with self.assertRaisesRegex(RuntimeError,"UNAPPROVED_TBF_BURST"):
            H.install_owned_tun_aggregate_burst_fair(node,900)
        node.alive=False
        with self.assertRaisesRegex(RuntimeError,"UNOWNED_TUN"):
            H.install_owned_tun_aggregate_burst_fair(node,48)

if __name__=="__main__":unittest.main()
