"""Bounded component contract for signed Windows/WSL2 high-rate target load.

This test does NOT certify 500/700 Mb/s, Wintun, Npcap, CPU or owned Stop.
Those are exclusively the same-SOURCE original Windows/WSL2 signed scene.
"""
import pathlib
import socket
import sys
import threading
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import m0_plan029_h1898_highrate_tcp as r

class HighRateComponentTests(unittest.TestCase):
    def test_exact_500_oneway_700_aggregate_targets_and_streaming_budget(self):
        self.assertEqual(r.PORT,46118)
        self.assertEqual(r.BLOCK,65536)
        self.assertEqual(r.ONE_WAY_BYTES,512*1024*1024)
        self.assertEqual(r.DUPLEX_BYTES,256*1024*1024)
        self.assertEqual(r.ONE_WAY_TARGET_BPS,500_000_000)
        self.assertEqual(r.DUPLEX_TARGET_AGG_BPS,700_000_000)
        self.assertEqual(len(r.DATA),r.BLOCK)
        self.assertEqual(r.ONE_WAY_SHA,r.expected_sha(r.ONE_WAY_BYTES))
        self.assertEqual(r.DUPLEX_SHA,r.expected_sha(r.DUPLEX_BYTES))

    def test_real_full_duplex_on_one_socket_pair_two_directions(self):
        # A small real OS socketpair exercises thread synchronization,
        # simultaneous read/write and exact SHA. The 512MiB real remote
        # Windows Wintun target is NEVER substituted with this loopback.
        a,b=socket.socketpair()
        n=r.BLOCK*2
        original_sha,original_max=r.DUPLEX_SHA,r.MAX_STAGE_S
        r.DUPLEX_SHA=r.expected_sha(n)
        r.MAX_STAGE_S=4
        records={}
        faults=[]
        try:
            a.settimeout(4);b.settimeout(4)
            def worker(name,sock):
                try:records[name]=r.duplex(sock,n,16*1024*1024)
                except BaseException as exc:faults.append(repr(exc))
            left=threading.Thread(target=worker,args=("left",a))
            right=threading.Thread(target=worker,args=("right",b))
            left.start();right.start()
            left.join(timeout=8);right.join(timeout=8)
            self.assertFalse(left.is_alive())
            self.assertFalse(right.is_alive())
            self.assertEqual(faults,[])
            self.assertEqual(set(records),{"left","right"})
            for row in records.values():
                self.assertEqual(row["local_sent_bytes"],n)
                self.assertEqual(row["local_received_bytes"],n)
                self.assertEqual(row["received_sha256"],r.expected_sha(n))
                self.assertTrue(row["same_kernel_socket"])
        finally:
            a.close();b.close()
            r.DUPLEX_SHA=original_sha
            r.MAX_STAGE_S=original_max

    def test_host_cpu_delta_includes_idle_and_other_processes(self):
        # Synthetic FILETIME-derived seconds validate units/math only.
        row=r.host_cpu_delta((10.,25.,5.),(11.,29.,7.))
        self.assertAlmostEqual(row["host_all_logical_cpu_busy_pct"],83.3333,places=3)
        self.assertEqual(row["host_cpu_time_busy_s"],5.0)
        self.assertIn("OTHER_RUNNER_PROCESSES",row["scope"])
        with self.assertRaises(RuntimeError):
            r.host_cpu_delta((1.,1.,1.),(1.,1.,1.))

    def test_target_is_reported_not_pretended_as_ci_performance_pass(self):
        src=(pathlib.Path(__file__).resolve().parents[1]/
             "tools/m0_plan029_h1898_highrate_tcp.py").read_text()
        self.assertIn('phase["target_reached"]=actual>=phase["target_aggregate_mbps"]',src)
        self.assertIn('"rate_result":"TARGET_MEASURED_NOT_PREDECLARED"',src)
        self.assertIn("WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC",src)
        self.assertIn("SAME_ORIGINAL_WINDOWS_PROCESS_WITH_96B_TUNNEL_UDP_NO_NEW_TCP",(
            pathlib.Path(__file__).resolve().parents[1]/
            "tools/m0_plan029_h1896_sustain_tcp.py").read_text())

if __name__=="__main__":
    unittest.main()
