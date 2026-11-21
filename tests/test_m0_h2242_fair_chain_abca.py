"""H2242 native original TUN fair-aggregate AQM/GATE strict negative tests."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "h2242",ROOT/"tools/m0_h2242_fair_chain_abca.py")
M=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class FairChainNoHolSource(unittest.TestCase):
    def test_original_bounded_full_chain_four_phase_abca(self):
        self.assertEqual(M.PHASES,(
            ("original_before",4),("fair_aggregate_only",4),
            ("fair_aggregate_with_original_gate",4),("original_after",4)))
        self.assertEqual((M.CAKE_RATE_MBIT,M.CAKE_MEMLIMIT),(450,"4Mb"))
        script=(ROOT/"tools/m0_h2242_fair_chain_abca.py").read_text()
        rust=(ROOT/"crates/wbd-engine/src/v4_embedded_go.rs").read_text()
        for guard in ("node.start_client(1)","node.stop_client(1)",
            '"original_kernel_tun_tx_ring_2048_unchanged":True',
            '"product_default_original_per_flow_fq600_unchanged":True',
            '"cake_fairness_and_ecn_bounded_active_queue_test_only":True',
            "qualified_queued_packet_counters","gate_stop_receipt("):
            self.assertIn(guard,script)
        self.assertIn("only_live_shared_tun_route_saturated(",rust)
        self.assertIn("routes.len()!=1 || pending.len()!=1",rust)
        self.assertIn("m0_h2241_exclusive_reader_gate_refuses_cross_route_or_generation_hol",rust)
        self.assertNotIn("enforce_ordered_recovery",script)
        self.assertNotIn("reliable_outer_tunnel",script)

    def test_kernel_qdisc_and_tun_driver_are_separate_real_counters(self):
        def snap(kind,pk,dr,by,lk,ld,lb):
            return {"tc":[{"kind":kind,"root":True,
                            "packets":pk,"drops":dr,"bytes":by}],
                    "link":[{"stats64":{"tx":{"packets":lk,
                                     "dropped":ld,"bytes":lb}}}]}
        base=snap("cake",300,4,10000,299,3,9000)
        end=snap("cake",1000,16,100000,960,35,101000)
        res=M.qualified_queued_packet_counters(base,end,"cake")
        self.assertEqual(res["drops_delta"],12)
        self.assertEqual(res["link_tx_dropped_delta"],32)
        self.assertTrue(res["driver_drop_and_qdisc_drop_are_distinct"])
        with self.assertRaisesRegex(RuntimeError,"KIND_CHANGED"):
            M.qualified_queued_packet_counters(base,end,"fq")
        end["tc"][0].pop("drops")
        with self.assertRaisesRegex(RuntimeError,"STATS_UNKNOWN"):
            M.qualified_queued_packet_counters(base,end,"cake")

    def test_only_owned_tun_and_real_kernel_qdisc_cake(self):
        class Owner:
            client="h34c1234567"
            def __init__(self):self.alive=True
            def owned_pid(self,role):
                return 10021 if role=="client" and self.alive else None
        owner=Owner()
        calls=[]
        def mock_ns(n,*args,**kw):
            calls.append((n,args))
            if args[:3]==("tc","-d","qdisc"):
                found=any(a[0:3]==("tc","qdisc","replace") for _,a in calls)
                if found:
                    out="qdisc cake 8001: root bandwidth 450Mbit besteffort flows rtt 100ms memlimit 4Mb"
                else:
                    out="qdisc fq 8000: root maxrate 600Mbit flow_limit 256"
                return type("R",(),{"stdout":out})()
            if args[:3]==("ip","-j","link"):
                return type("R",(),{"stdout":
                    '[{"ifname":"wbdc0","txqlen":2048}]'})()
            if args[:3]==("tc","qdisc","replace"):
                return type("R",(),{"stdout":""})()
            raise AssertionError(args)
        with patch.object(M.L,"ns",mock_ns):
            result=M.install_owned_tun_aggregate_fair(owner)
        self.assertEqual(result["rate_mbps"],450)
        self.assertEqual(len(calls),4)
        self.assertTrue(all(n==owner.client for n,_ in calls))
        self.assertEqual(calls[2][1],(
            "tc","qdisc","replace","dev","wbdc0","root","cake",
            "bandwidth","450Mbit","besteffort","flows","rtt","100ms",
            "memlimit","4Mb"))
        owner.alive=False
        with self.assertRaisesRegex(RuntimeError,"OWNER_MISSING"):
            M.install_owned_tun_aggregate_fair(owner)

if __name__=="__main__":unittest.main()
