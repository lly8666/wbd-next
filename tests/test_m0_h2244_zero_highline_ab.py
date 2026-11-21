"""H2244 zero-loss highline native candidate: source and negative gates.

STATIC tests are not real throughput proof. No product Linux qdisc rate
or outer Rust owner is modified by these tests.
"""
import json
import pathlib
import types
import unittest
from unittest.mock import patch
from tools import m0_h2244_zero_highline_ab as Z
from tools import m0_h2234_local_netns as L

ROOT=pathlib.Path(__file__).resolve().parents[1]

class Owned:
    client="testclient"
    def owned_pid(self,role):
        return 4321 if role=="client" else None

class ZeroHighlineStatic(unittest.TestCase):
    def test_original_candidate_original_no_per_packet_controller(self):
        self.assertEqual(Z.PHASES,(
            ("original_before",0),("tbf1200_48kiB_fq_codel",1200),
            ("original_after",0)))
        text=(ROOT/"tools/m0_h2244_zero_highline_ab.py").read_text()
        for key in (
            'node.start_network()', 'node.impairment(0)',
            'node.start_client(0)', 'node.stop_client(0)',
            'node.stop_server()', 'N.owned_echo_server_stop(',
            'H.rearm_direct_capacity_listener(node)',
            'H.source_kernel_qdisc_receipt(',
            'H.scoped_diagnostic(', 'concurrent_probe(node,name,i)',
            '"test_only_fixed_1200mbit_not_default":True',
            'os.environ["WBD_H2241_NATIVE_GATE"]="0"',
            '"true_original_go_tls_rust_owner":True'):
            self.assertIn(key,text)
        self.assertNotIn('os.environ["WBD_H2241_NATIVE_GATE"]="1"',text)
        self.assertNotIn("reliable_outer_stream",text)

    def test_tbf1200_real_qdisc_readback_on_exact_owned_tun(self):
        state={"installed":False}
        calls=[]
        def ns(name,*args,**kwargs):
            calls.append(args)
            if args[:3]==("tc","-d","qdisc"):
                if state["installed"]:
                    return types.SimpleNamespace(stdout=(
                        "qdisc tbf 1: root rate 1.2Gbit burst 48Kb lat 15ms\n"
                        "qdisc fq_codel 10: parent 1:1 limit 256 target 5ms interval 100ms ecn"))
                return types.SimpleNamespace(stdout="qdisc fq 8001: root maxrate 600Mbit flow_limit 256")
            if args[:3]==("ip","-j","link"):
                return types.SimpleNamespace(stdout=json.dumps([{"ifname":"wbdc0","txqlen":2048}]))
            if args[:3]==("tc","qdisc","replace"):
                state["installed"]=True
                return types.SimpleNamespace(stdout="")
            raise AssertionError("unexpected command "+repr(args))
        with patch.object(L,"ns",side_effect=ns):
            ans=Z.install_highline_owned_tun(Owned())
        self.assertEqual(ans["test_only_fixed_rate_mbit"],1200)
        self.assertTrue(ans["no_global_or_unowned_qdisc_change"])
        self.assertEqual([a[:3] for a in calls].count(("tc","qdisc","replace")),2)
        self.assertTrue(all(a[4]=="wbdc0" for a in calls if a[:3]==("tc","qdisc","replace")))

    def test_wrong_rate_and_unowned_fail_before_false_qualification(self):
        class Wrong:
            client="unowned"
            def owned_pid(self,role):return None
        with self.assertRaisesRegex(RuntimeError,"NO_OWNED"):
            Z.install_highline_owned_tun(Wrong())
        class OwnedWrong(Owned):pass
        def bad_ns(name,*args,**kw):
            if args[:3]==("tc","-d","qdisc"):
                return types.SimpleNamespace(stdout=(
                    "qdisc fq 8001: root maxrate 600Mbit flow_limit 256" if not getattr(bad_ns,"changed",False)
                    else "qdisc tbf 1: root rate 450Mbit\nqdisc fq_codel 10: parent 1:1 ecn"))
            if args[:3]==("ip","-j","link"):
                return types.SimpleNamespace(stdout='[{"ifname":"wbdc0","txqlen":2048}]')
            if args[:3]==("tc","qdisc","replace"):
                bad_ns.changed=True
                return types.SimpleNamespace(stdout="")
            raise AssertionError(args)
        with patch.object(L,"ns",side_effect=bad_ns):
            with self.assertRaisesRegex(RuntimeError,"ACTUAL_RATE_NOT_1200"):
                Z.install_highline_owned_tun(OwnedWrong())

if __name__=="__main__":
    unittest.main()
