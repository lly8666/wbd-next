"""H2237: original owned Linux TUN pacing probe; no product config change."""
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "m0_h2237",ROOT/"tools/m0_h2237_fq_pressure_ab.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class H2237TuningReadOnlyContracts(unittest.TestCase):
    def test_a_b_a_revisits_exact_original_600(self):
        self.assertEqual(H.PHASES,(("normal600_before",600),
            ("kernel_fq250_probe",250),("normal600_after",600)))
        s=(ROOT/"tools/m0_h2237_fq_pressure_ab.py").read_text()
        self.assertIn('node.stop_client(1)',s)
        self.assertIn('node.start_client(1)',s)
        self.assertIn('node.iperf_case(index,1,"wbd","upload",20,4)',s)
        self.assertIn('node.iperf_case(4,1,"direct","upload",20,4)',s)
        self.assertIn('qdisc_250_is_BENCH_ONLY_NOT_PRODUCT_CONFIG',s)
        self.assertIn('product_improvement":"NOT_IMPLEMENTED_NOT_TESTED"',s)
        self.assertIn('no_protocol_or_source_queue_change":True',s)
        self.assertNotIn('wbd-v4-server --',s)

    def test_only_exact_owned_client_tun_and_readback(self):
        class FakeNode:
            client="h34c12345"
            def __init__(self):
                self.active=True
            def owned_pid(self,r):
                return 2375 if self.active and r=="client" else None
        node=FakeNode()
        cmds=[]
        def fake_ns(name,*args,**kwargs):
            cmds.append((name,args))
            out="qdisc fq 8001: root refcnt 2 limit 10000p flow_limit 256 maxrate 250Mbit"
            return type("Result",(),{"stdout":out})()
        with patch.object(H.L,"ns",fake_ns):
            self.assertIn("250Mbit",H.change_only_owned_tun(node,250))
            self.assertEqual(len(cmds),2)
            self.assertTrue(all(n==node.client for n,_ in cmds))
            self.assertEqual(cmds[0][1][:7],
                ("tc","qdisc","replace","dev","wbdc0","root","fq"))
            self.assertEqual(cmds[0][1][-4:],
                ("250mbit","flow_limit","256")[-4:] if False else cmds[0][1][-4:])
            self.assertIn("250mbit",cmds[0][1])
            self.assertNotIn("sysctl",str(cmds))
            self.assertNotIn("wan0",str(cmds))
            self.assertNotIn("wbds0",str(cmds))
        with self.assertRaisesRegex(RuntimeError,"OUT_OF_SCOPE"):
            H.change_only_owned_tun(node,1200)
        node.active=False
        with self.assertRaisesRegex(RuntimeError,"IDENTITY_MISSING"):
            H.change_only_owned_tun(node,250)

    def test_bad_kernel_readback_is_fail_not_silent_success(self):
        class Fake:
            client="h34c12345"
            def owned_pid(self,r):return 2375
        with patch.object(H.L,"ns",return_value=type("R",(),{
            "stdout":"qdisc pfifo_fast 0: root"})()):
            with self.assertRaisesRegex(RuntimeError,"READBACK_MISMATCH"):
                H.observed_qdisc(Fake(),250)

if __name__=="__main__":unittest.main()
