"""H2234 local native topology's fail-closed contracts, NOT true WAN/PASS."""
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from tools import m0_h2234_local_netns as L

class H2234LocalRealNative(unittest.TestCase):
    def test_only_owned_router_l3_both_egress_netem_and_1_or_5(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"GITHUB_RUN_ID":"987654321"}):
            root=pathlib.Path(d)
            instance=L.OwnedLocal(root,root,root)
            commands=[]
            def mock_ns(name,*argv,**kw):
                commands.append((name,argv))
                return type("Done",(),{"stdout":"[]","returncode":0})()
            with patch.object(L,"ns",mock_ns),patch.object(
                instance,"router_snapshot",return_value={"real_kernel_router_readback":True}):
                instance.impairment(1)
                instance.impairment(5)
                with self.assertRaisesRegex(RuntimeError,"INVALID_NETEM_TARGET"):
                    instance.impairment(20)
            self.assertEqual(len(commands),4)
            self.assertTrue(all(name==instance.router for name,_ in commands))
            self.assertEqual([args[4] for _,args in commands],
                             ["rcli0","rsrv0","rcli0","rsrv0"])
            self.assertTrue(all("gemodel" in args and
                                "200ms" in args and "65536" in args
                                for _,args in commands))
            self.assertTrue(all("tailscale0" not in args and
                                "rate" not in args for _,args in commands))

    def test_owned_process_identity_must_be_exact_before_stop(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"GITHUB_RUN_ID":"987654321"}):
            root=pathlib.Path(d)
            node=L.OwnedLocal(root,root,root)
            (root/"client.pid").write_text("42000\n")
            (root/"server.pid").write_text("42001\n")
            def fake_root(*argv,**kw):
                label="wbd-v4-client" if argv[-1]=="42000" else "iperf3"
                return type("Done",(),{"stdout":label+"\n","returncode":0})()
            with patch.object(L,"root",fake_root):
                self.assertEqual(node.owned_pid("client"),42000)
                self.assertIsNone(node.owned_pid("server"))
            (root/"client.pid").write_text("not-an-owned-pid")
            self.assertIsNone(node.owned_pid("client"))

    def test_m4_stage_source_truth_and_invalid_no_hol(self):
        line=("V4_PUBLIC_M4_BATCH_STAGE_STOP role=client generation=1 "
              "batches=1500 copied=18000 collect_turns=22000 collect_ns=100 "
              "prepare_ns=200 seal_ns=450 sendmmsg_ns=300 settle_ns=60 "
              "driver_route_ns=10 driver_header_ns=80 driver_iovec_ns=45 "
              "driver_syscall_ns=110 driver_classify_ns=20 "
              "max_collect_ns=20 max_prepare_ns=30 max_seal_ns=100 "
              "max_sendmmsg_ns=85 max_settle_ns=7 original_owner=1 "
              "no_wire_or_queue_change=1")
        receipt=L.original_m4_batch_stage_receipt(line)
        self.assertEqual((receipt["batches"],receipt["copied"]),(1500,18000))
        self.assertEqual(receipt["seal_ns"],450)
        self.assertEqual(receipt["driver_syscall_ns"],110)
        for bad in ("",line+"\n"+line,
                    line.replace("original_owner=1","original_owner=0"),
                    line.replace("sendmmsg_ns=300","missing_send_ns=300"),
                    line.replace("copied=18000","copied=0")):
            with self.assertRaises(RuntimeError):
                L.original_m4_batch_stage_receipt(bad)

    def test_true_product_and_honest_local_only_scope(self):
        src=pathlib.Path(L.__file__).read_text()
        self.assertIn("SAME_VM_CLIENT_ROUTER_SERVER_THREE_REAL_LINUX_NETNS",src)
        self.assertIn('"real_independent_three_runner_wan":False',src)
        self.assertIn('"product_causal_speed_qualified":False',src)
        self.assertIn('"server_owned_stop_verified":server_stop_verified',src)
        self.assertIn('"WBD_H2235_M4_STAGE_DIAG=1"',src)
        self.assertIn('original_m4_batch_stage_receipt(text)',src)
        self.assertIn("V4_PUBLIC_SHARED_TUN_STOP generation=",src)
        self.assertIn("V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED owned_rule_deleted=1",src)
        self.assertIn("V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close remaining_flows=0",src)
        self.assertNotIn('"V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server"',src)
        self.assertIn('node.start_client(0)',src)
        self.assertIn('readbacks["0"]=node.stop_client(0)',src)
        self.assertIn('H.iperf(kind,duration,streams,direction,path',src)
        self.assertIn('node.stop_client(loss)',src)
        self.assertIn('"--outer-repair","on"',src)
        self.assertIn('"--mode","normal"',src)
        self.assertIn('("upload","download")',src)
        self.assertIn('node.impairment(loss)',src)
        self.assertIn('x>=500',src)
        self.assertIn('num_real_tcp_cases',src)
        self.assertIn('kernel_tcp_mss_source_qualified',src)
        self.assertIn('local_original_tx_thread_cpu_seconds_per_receiver_gib',src)

if __name__=="__main__":unittest.main()
