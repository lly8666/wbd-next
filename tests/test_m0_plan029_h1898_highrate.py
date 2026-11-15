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

    def test_h1903_30s_plus_same_vm_long_load_is_source_locked(self):
        src=(pathlib.Path(__file__).resolve().parents[1]/
             "tools/m0_plan029_h1898_highrate_tcp.py").read_text()
        harness=(pathlib.Path(__file__).resolve().parents[1]/
                 "tools/m0_plan029_h1815_p2_real_mixed.py").read_text()
        e2e=(pathlib.Path(__file__).resolve().parents[1]/
             "tools/m0_wl_public_normal_e2e.py").read_text()
        workflow=(pathlib.Path(__file__).resolve().parents[1]/
                  ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn('2*1024*1024*1024 if LONG',src)
        self.assertIn('1536*1024*1024 if LONG',src)
        self.assertIn('len(sys.argv)>1 and sys.argv[-1]=="p2long"',src)
        self.assertIn('physical_args=[sys.executable',src)
        self.assertIn('physical_receipt["original_pid"]!=pid',src)
        self.assertIn('original_cpu_increment(physical_receipt,w)',src)
        self.assertIn('"physical_oneway_500mbps"',harness)
        self.assertIn('if HIGH_RATE:MAX_SUSTAIN=60000 if LONG_RATE else 14000',harness)
        self.assertIn('WBD_PLAN029_P2_LONG_RATE_SCENE',e2e)
        self.assertIn('WBD_PLAN029_P2_LONG_RATE_SCENE',workflow)
        self.assertIn('[plan029-v3-real-p2-long-ab]',workflow)
        self.assertIn('PASS_SIGNED_LONG_SAME_VM_PHYSICAL_VS_DIRECT_CPU_UDP_STOP',e2e)

    def test_h1903_incremental_original_process_cpu_is_signed_not_clamped(self):
        def row(sent,rate,total,user,kernel,host_pct):
            return {"local_sent_bytes":sent,"target_aggregate_mbps":rate,
                    "actual_aggregate_mbps":rate-0.5,"elapsed_s":35.0,
                    "original_process_cpu":{
                        "original_process_total_cpu_s_per_gib":total,
                        "original_process_user_cpu_s_per_gib":user,
                        "original_process_kernel_cpu_s_per_gib":kernel},
                    "windows_host_cpu":{"host_all_logical_cpu_busy_pct":host_pct}}
        a={"stages":{
            "oneway_500mbps":row(2*1024**3,500,2.5,1,1.5,30),
            "duplex_700mbps_aggregate":row(1536*1024**2,700,4,2,2,38)}}
        b={"stages":{
            "oneway_500mbps":row(2*1024**3,500,12,4.5,7.5,61),
            "duplex_700mbps_aggregate":row(1536*1024**2,700,3,0.8,2.2,68)}}
        result=r.original_cpu_increment(a,b)
        self.assertEqual(result["oneway_500mbps"][
            "added_process_total_cpu_s_per_gib"],9.5)
        self.assertEqual(result["oneway_500mbps"][
            "added_process_kernel_cpu_s_per_gib"],6.0)
        self.assertEqual(result["duplex_700mbps_aggregate"][
            "added_process_total_cpu_s_per_gib"],-1.0)
        self.assertIn("NOT_DRIVER_CPU",result["oneway_500mbps"]["scope"])
        b["stages"]["oneway_500mbps"]["local_sent_bytes"]=1024
        with self.assertRaises(RuntimeError):
            r.original_cpu_increment(a,b)

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
        self.assertIn('"original_process_cpu":cpu_delta(p0,p1,sec,total)',src)
        self.assertIn('"load_generator_cpu":cpu_delta(g0,g1,sec,total)',src)
        self.assertIn("WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC",(
            pathlib.Path(__file__).resolve().parents[1]/
            "tools/m0_plan029_h1896_sustain_tcp.py").read_text())
        self.assertIn("SAME_ORIGINAL_WINDOWS_PROCESS_WITH_96B_TUNNEL_UDP_NO_NEW_TCP",(
            pathlib.Path(__file__).resolve().parents[1]/
            "tools/m0_plan029_h1896_sustain_tcp.py").read_text())


    def test_h1922_long_source_run_is_after_real_4m_gate_and_push_path_matched(self):
        # H1921 only changed a cursor, feature card and evidence: GitHub
        # skipped the native workflow entirely because push.paths excludes
        # those docs. This existing test path is specifically allowlisted.
        root=pathlib.Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        harness=(root/"tools/m0_plan029_h1815_p2_real_mixed.py").read_text()
        rate=(root/"tools/m0_plan029_h1898_highrate_tcp.py").read_text()
        import m0_native_ci_scope as scope
        self.assertIn("      - tests/test_m0_plan029_h1898_highrate.py",workflow)
        flags=("[plan029-v3-real-p2-bulk]",
               "[plan029-v3-real-p2-500-700]",
               "[plan029-v3-real-p2-long-ab]")
        for flag in flags:
            self.assertIn(flag,workflow)
        self.assertTrue(scope.requires_native_smoke(
            "push",["tests/test_m0_plan029_h1898_highrate.py"],
            " ".join(flags)))
        self.assertLess(
            harness.index('direct_proofs.append(proof(dn,"PLAN029_H1815_P2_TCP_CLIENT"))'),
            harness.index("highrate=run_highrate("))
        self.assertIn('source=os.environ["GITHUB_SHA"]',rate)
        self.assertIn('physical_args=[sys.executable',rate)
        self.assertIn('original_cpu_increment(physical_receipt,w)',rate)
        self.assertIn('source_sha',rate)

if __name__=="__main__":
    unittest.main()
