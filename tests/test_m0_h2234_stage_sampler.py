"""H2234 bounded external scheduler forensics; no application/packet delivery claim."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "m0_h2234",ROOT/"tools/m0_h2234_stage_sampler.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

def build_process(root,pid,threads):
    folder=root/str(pid)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"comm").write_text("wbd-v4-client\n")
    (folder/"net").mkdir()
    (folder/"net"/"dev").write_text(
        "Inter-| Receive | Transmit\n"
        " face |bytes packets errs drop fifo frame compressed multicast"
        " |bytes packets errs drop fifo colls carrier compressed\n"
        "wan0: 1000 10 0 0 0 0 0 0 900 9 0 1 0 0 0 0\n"
        "wbdc0: 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\n")
    for tid,name in threads.items():
        folder2=folder/"task"/str(tid)
        folder2.mkdir(parents=True,exist_ok=True)
        (folder2/"comm").write_text(name+"\n")
        (folder2/"schedstat").write_text("1000000 200000 3\n")
        (folder2/"wchan").write_text("futex_wait_queue\n")
        (folder2/"status").write_text("voluntary_ctxt_switches:\t4\n"
                                     "nonvoluntary_ctxt_switches:\t2\n")
    return folder

class RealProcSchedulerContracts(unittest.TestCase):
    def test_exact_distinct_linux_thread_comm_names_and_bounds(self):
        src=(ROOT/"crates/wbd-engine/src/v4_embedded_go.rs").read_text()
        for name in ("wbd-m4-rx","wbd-m4-tx","wbd-tun-reader"):
            self.assertIn('.name("'+name+'".into())',src)
            self.assertLessEqual(len(name.encode()),15)
            self.assertIn(name,H.THREADS)
        self.assertNotIn('.name("wbd-original-m4-tx".into())',src)
        self.assertNotIn('.name("wbd-original-m4-rx".into())',src)

    def test_real_tid_delta_and_netns_dev_are_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            proc=build_process(root,3211,{
                3212:"wbd-m4-tx",3213:"wbd-m4-rx",3214:"wbd-tun-reader",
                3215:"not-wbd-worker"})
            first=H.snapshot(root,3211)
            self.assertEqual(first["status"],"GENUINE_ORIGINAL_PROCESS")
            self.assertEqual(len(first["threads"]),3)
            self.assertEqual(first["netdev"]["interfaces"]["wan0"]["tx_packets"],9)
            (proc/"task"/"3212"/"schedstat").write_text("9000000 3200000 8\n")
            (proc/"task"/"3212"/"status").write_text(
                "voluntary_ctxt_switches:\t12\nnonvoluntary_ctxt_switches:\t5\n")
            second=H.snapshot(root,3211)
            delta=H.deltas(first,second)
            tx=next(x for x in delta if x["name"]=="wbd-m4-tx")
            self.assertEqual(tx["cpu_run_ns"],8_000_000)
            self.assertEqual(tx["runnable_wait_ns"],3_000_000)
            self.assertEqual(tx["scheduler_slices"],5)
            rows=[{"kind":"SAMPLE","monotonic_ns":100_000_000,"value":first},
                  {"kind":"SAMPLE","monotonic_ns":300_000_000,"value":second}]
            summary=H.diagnose(rows)
            self.assertEqual(summary["status"],"SAMPLED_NOT_FULL_PACKET_CAUSAL_PROOF")
            self.assertEqual(summary["threads"]["wbd-m4-tx"]["max_wait_ns_in_sample"],3_000_000)

    def test_unknown_pid_or_schedstat_never_claims_zero_latency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            self.assertEqual(H.snapshot(root,100)["status"],
                             "UNKNOWN_NOT_VERIFIED_ORIGINAL_WORKER")
            proc=build_process(root,500, {501:"wbd-m4-tx"})
            (proc/"comm").write_text("iperf3\n")
            self.assertNotEqual(H.snapshot(root,500)["status"],"GENUINE_ORIGINAL_PROCESS")
            (proc/"comm").write_text("wbd-v4-client\n")
            (proc/"task"/"501"/"schedstat").unlink()
            self.assertEqual(H.snapshot(root,500)["threads"]["501"]["status"],
                             "UNAVAILABLE_SCHEDSTAT")
            self.assertEqual(H.diagnose([])["status"],"UNKNOWN_NO_COMPARABLE_SCHEDSTAT")

if __name__=="__main__":unittest.main()
